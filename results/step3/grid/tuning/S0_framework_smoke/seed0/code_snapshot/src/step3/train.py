"""Step 3 training harness: SBX PPO on any task under the audit + PBRR protocol, one
run directory per (env, run id, seed), never overwritten.

A run's configuration is a nested dict:
    env, seed, n_envs, episodes, reward_scale
    task      -- the task's bug parameters (frozen from Phase A)
    protocol  -- t_sub, n_sub, window, p_detect, show_monitor
    ppo       -- PPO hyperparameters (the tuning knobs; defaults = Step 1's config)
    pbrr      -- k (rollouts per round), beta, reference (n_demos, noise, seed)
    g         -- the correction network / Eq 3 fit (Phase A's E.1 search winner, max1)
    refs      -- the idealised optimum's numbers the criteria are relative to
Defaults come from the task module and its Phase A summary
(results/step3/<env>/phase_a/summary.json; for the grid, Step 2's Phase A).
"""

import copy
import csv
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict

import numpy as np
from sbx import PPO

from ..audit_train import PPO_KWARGS
from ..pbrr_core import GConfig
from .metrics import metrics_from_logs
from .pbrr import Overseer, rollouts
from .protocol import AuditedVecEnv, Protocol
from .reference import train_bc_reference
from .tasks import get_task, module

__all__ = ["ROOT", "RESULTS", "phase_a_path", "resolve_config", "train_run"]

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS = os.path.join(ROOT, "results", "step3")

BASE_CONFIG = {
    "seed": 0,
    "n_envs": 16,
    "episodes": 384,
    "ppo": {**{k: v for k, v in PPO_KWARGS.items() if k != "verbose"}, "net_arch": [64, 64]},
    "pbrr": {"k": 19, "beta": 1.0, "ref_seed": 0, "n_demos": 5, "noise": 0.1},
}


def phase_a_path(env):
    if env == "grid":
        return os.path.join(ROOT, "results", "step2", "phase_a", "summary.json")
    return os.path.join(RESULTS, env, "phase_a", "summary.json")


def resolve_config(env, overrides=None):
    mod = module(env)
    cfg = copy.deepcopy(BASE_CONFIG)
    cfg["env"] = env
    cfg["protocol"] = asdict(mod.PROTOCOL)
    cfg["reward_scale"] = mod.DEFAULTS["reward_scale"]
    cfg["task"] = dict(mod.DEFAULTS.get("task", {}))
    path = phase_a_path(env)
    if os.path.exists(path):
        with open(path) as fh:
            pa = json.load(fh)
        cfg["g"] = {**pa["g_config"], "no_agree": "max1"}
        cfg["task"].update(pa.get("task_params", {}))
        cfg["refs"] = pa.get("refs") or mod.refs(cfg)
        cfg["pbrr"].update(pa.get("reference_settings", {}))
        cfg["protocol"].update(pa.get("protocol", {}))
        cfg["reward_scale"] = pa.get("reward_scale", cfg["reward_scale"])
    else:
        cfg["g"] = {"no_agree": "max1"}
        cfg["refs"] = None
    for key, val in (overrides or {}).items():
        if isinstance(val, dict):
            cfg.setdefault(key, {}).update(val)
        else:
            cfg[key] = val
    return cfg


def _git_hash():
    try:
        return subprocess.check_output(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def _snapshot(run_dir):
    snap = os.path.join(run_dir, "code_snapshot")
    for sub in ("src", os.path.join("src", "step3"), os.path.join("src", "step3", "tasks")):
        d = os.path.join(ROOT, sub)
        os.makedirs(os.path.join(snap, sub), exist_ok=True)
        for name in sorted(os.listdir(d)):
            if name.endswith(".py"):
                shutil.copy(os.path.join(d, name), os.path.join(snap, sub, name))
    exp = os.path.join(ROOT, "experiments")
    os.makedirs(os.path.join(snap, "experiments"), exist_ok=True)
    for name in sorted(os.listdir(exp)):
        if name.startswith("step3_") and name.endswith(".py"):
            shutil.copy(os.path.join(exp, name), os.path.join(snap, "experiments", name))


def train_run(run_dir, config, verbose=True):
    """Train one seed. Refuses to touch an existing ``run_dir``."""
    if os.path.exists(run_dir):
        raise FileExistsError(f"{run_dir} exists; results are never overwritten")
    assert config.get("refs"), "run Phase A first (experiments/step3_check.py): no reference numbers"
    os.makedirs(run_dir)
    _snapshot(run_dir)
    with open(os.path.join(run_dir, "config.json"), "w") as fh:
        json.dump({**config, "git": _git_hash(), "started": time.strftime("%Y-%m-%d %H:%M:%S")},
                  fh, indent=1)
    seed = int(config["seed"])
    task = get_task(config["env"], **config["task"])
    proto = Protocol(**config["protocol"])
    pb = config["pbrr"]
    ref, _ = train_bc_reference(task, proto.t_sub, pb["n_demos"], pb["noise"], seed=pb["ref_seed"])
    ref_trajs = rollouts(task.make_batch(pb["k"], seed=1000 + seed), ref, proto,
                         np.random.default_rng(1000 + seed))

    n_envs = int(config["n_envs"])
    venv = AuditedVecEnv(task, proto, n_envs, config["reward_scale"], seed=seed * 1000)
    ppo = dict(config["ppo"])
    net_arch = ppo.pop("net_arch")
    ppo["n_steps"] = proto.t_sub
    assert ppo.get("gamma", 1.0) == 1.0, "gamma is fixed at 1 (CLAUDE.md 2)"
    model = PPO("MlpPolicy", venv, seed=seed, policy_kwargs=dict(net_arch=list(net_arch)), verbose=0, **ppo)
    overseer = Overseer(task, proto, venv, ref_trajs, GConfig(**config["g"]), k=pb["k"], beta=pb["beta"],
                        seed=seed)
    refs = config["refs"]
    timesteps = int(config["episodes"]) * n_envs * proto.t_ep
    chunk = n_envs * proto.t_ep * 24                       # report every 24 episodes
    t0 = time.time()
    while model.num_timesteps < timesteps:
        model.learn(total_timesteps=chunk, reset_num_timesteps=False, callback=overseer, progress_bar=False)
        if verbose:
            n_ep = len(overseer.caught) // proto.n_sub
            m = metrics_from_logs(np.array(overseer.on_exploit), np.array(overseer.caught),
                                  np.array(overseer.env_proxy), proto, refs,
                                  ep_slice=slice(max(0, n_ep - 24), n_ep))
            print(f"  [{config['env']} s{seed}] {model.num_timesteps:>10,}  win0-3 {m['window_0_3']:.2f}  "
                  f"off {m['offwindow_rel']:.2f}  corr/ep {m['corrections_per_ep']:.2f}  winF "
                  f"{m['window_final']:.2f}  proxy0-3 {m['proxy_0_3']:8.1f}  rounds {len(overseer.rounds)}  "
                  f"({time.time() - t0:.0f}s)", flush=True)
    wall = time.time() - t0

    on = np.array(overseer.on_exploit, np.uint8)
    ca = np.array(overseer.caught, np.uint8)
    px = np.array(overseer.env_proxy, np.float32)
    np.savez_compressed(os.path.join(run_dir, "logs.npz"),
                        env_received=np.array(overseer.env_received, np.float32), env_proxy=px,
                        env_true=np.array(overseer.env_true, np.float32), on_exploit=on, caught=ca,
                        step_received=np.array(overseer.step_received, np.float32),
                        step_proxy=np.array(overseer.step_proxy, np.float32),
                        step_true=np.array(overseer.step_true, np.float32))
    for name, rows in (("rounds_training.csv", overseer.rows), ("pbrr_rounds.csv", overseer.rounds)):
        if rows:
            with open(os.path.join(run_dir, name), "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
    model.save(os.path.join(run_dir, "model"))
    final = metrics_from_logs(on, ca, px, proto, refs)
    n_ep = len(ca) // proto.n_sub
    ckpts = [metrics_from_logs(on, ca, px, proto, refs, ep_slice=slice(max(0, e - n_ep // 10), e))
             for e in np.linspace(n_ep // 10, n_ep, 10).astype(int)]
    out = {"final": final, "checkpoints": ckpts, "wall_seconds": wall, "n_pbrr_rounds": len(overseer.rounds),
           "pbrr_seconds": float(sum(r["seconds"] for r in overseer.rounds))}
    with open(os.path.join(run_dir, "metrics.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return out
