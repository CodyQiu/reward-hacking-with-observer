"""Step 3 training harness: SBX PPO on any task under the audit + PBRR protocol, one
run directory per (env, run id, seed), never overwritten.

A run's configuration is a nested dict:
    env, seed, n_envs, episodes, reward_scale
    task      -- the task's bug parameters (frozen from Phase A)
    protocol  -- t_sub, n_sub, window, p_detect, show_monitor
    ppo       -- PPO hyperparameters (the tuning knobs; defaults = Step 1's config)
    anneal    -- last, floor: over the last ``last`` fraction of the episodes the learning rate and
                 the entropy coefficient fall linearly to ``floor`` x their values (default off);
                 ent_start, ent_episodes: the entropy coefficient alone starts at ``ent_start`` x its
                 value and falls linearly to 1x by episode ``ent_episodes`` (default off)
    pbrr      -- k (rollouts per round), beta, reference (n_demos, noise, seed)
    g         -- the correction network / Eq 3 fit (Phase A's E.1 search winner, max1)
    refs      -- the idealised optimum's numbers the criteria are relative to
Defaults come from the task module and its Phase A summary
(results/step3/<env>/phase_a/summary.json; for the grid, Step 2's Phase A).

Checkpoints every 24 episodes (an episode boundary, where the reward resets anyway) hold the
model (policy, value net and their optimiser states), the logs and progress.json, so a run can be
resumed after a time limit and extended to more episodes (``train_run(..., resume=True)``): the
same run directory continues, ``config.json`` records every resume, and a finished run's
metrics.json is kept as metrics_ep<N>.json before the extension writes a new one. A resumed run
draws fresh environment / overseer random streams (it is not bit-identical to an uninterrupted
one).
"""

import copy
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict

import numpy as np
from sbx import PPO

from ..audit_train import PPO_KWARGS
from ..pbrr_core import GConfig
from .metrics import metrics_from_logs
from .pbrr import Overseer, rollouts
from .protocol import AuditedVecEnv, Protocol
from .reference import build_reference
from .tasks import get_task, module

__all__ = ["ROOT", "RESULTS", "phase_a_path", "resolve_config", "train_run"]

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESULTS = os.path.join(ROOT, "results", "step3")

BASE_CONFIG = {
    "seed": 0,
    "n_envs": 16,
    "episodes": 384,
    "ppo": {**{k: v for k, v in PPO_KWARGS.items() if k != "verbose"}, "net_arch": [64, 64]},
    "pbrr": {"k": 19, "beta": 1.0, "ref_seed": 0, "n_demos": 5, "noise": 0.1, "steps": 500},
    "anneal": {"last": 0.0, "floor": 1.0},
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


def _save_logs(run_dir, overseer, model):
    """Write logs.npz, the round CSVs and the model (rewritten at every checkpoint of the same run;
    each file goes through a temporary name, so a kill mid-write leaves the previous checkpoint)."""
    on = np.array(overseer.on_exploit, np.uint8)
    ca = np.array(overseer.caught, np.uint8)
    px = np.array(overseer.env_proxy, np.float32)
    np.savez_compressed(os.path.join(run_dir, "logs.tmp.npz"),
                        env_received=np.array(overseer.env_received, np.float32), env_proxy=px,
                        env_true=np.array(overseer.env_true, np.float32), on_exploit=on, caught=ca,
                        step_received=np.array(overseer.step_received, np.float32),
                        step_proxy=np.array(overseer.step_proxy, np.float32),
                        step_true=np.array(overseer.step_true, np.float32))
    os.replace(os.path.join(run_dir, "logs.tmp.npz"), os.path.join(run_dir, "logs.npz"))
    for name, rows in (("rounds_training.csv", overseer.rows), ("pbrr_rounds.csv", overseer.rounds)):
        if rows:
            with open(os.path.join(run_dir, name + ".tmp"), "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            os.replace(os.path.join(run_dir, name + ".tmp"), os.path.join(run_dir, name))
    model.save(os.path.join(run_dir, "model.tmp.zip"))
    os.replace(os.path.join(run_dir, "model.tmp.zip"), os.path.join(run_dir, "model.zip"))
    return on, ca, px


def _anneal_factor(an, done, total):
    """Multiplier on the learning rate and the entropy coefficient at progress done / total."""
    last, floor = float(an.get("last", 0.0)), float(an.get("floor", 1.0))
    x = done / total
    if last <= 0 or x <= 1 - last:
        return 1.0
    return 1.0 - (1.0 - floor) * min(1.0, (x - (1 - last)) / last)


def _ent_boost(an, episodes_done):
    """Early-exploration multiplier on the entropy coefficient alone: ``anneal.ent_start`` at episode 0,
    falling linearly to 1 at episode ``anneal.ent_episodes`` (absolute, so an extension does not restart
    it), then 1. Default off. The Step 4 campaign's exploration wave (docs/step4_optimal.md, rule 6b):
    a seed's outcome there is settled in its first ~1500 episodes."""
    start, n = float(an.get("ent_start", 1.0)), float(an.get("ent_episodes", 0))
    if n <= 0:
        return 1.0
    return 1.0 + (start - 1.0) * max(0.0, 1.0 - episodes_done / n)


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v


def _restore(run_dir, overseer, proto, n_ep):
    """Load a checkpoint's logs into ``overseer``, cut to the first ``n_ep`` episodes (the logs are
    written before the model, so after a kill between the two they can be one checkpoint ahead)."""
    d = np.load(os.path.join(run_dir, "logs.npz"))
    n = n_ep * proto.n_sub
    if len(d["caught"]) < n:
        raise RuntimeError(f"{run_dir}: logs hold {len(d['caught']) // proto.n_sub} episodes, model {n_ep}")
    for name in ("env_received", "env_proxy", "env_true", "on_exploit", "caught", "step_received",
                 "step_proxy", "step_true"):
        getattr(overseer, name).extend(list(d[name][:n]))
    for name, attr in (("rounds_training.csv", "rows"), ("pbrr_rounds.csv", "rounds")):
        path = os.path.join(run_dir, name)
        if os.path.exists(path):
            with open(path) as fh:
                rows = [{k: _num(v) for k, v in r.items()} for r in csv.DictReader(fh)]
            keep = rows[:n] if attr == "rows" else [r for r in rows if r["episode"] < n_ep]
            getattr(overseer, attr).extend(keep)


def _say(msg):
    """A progress line to the seed log (the worker's stdout). FarmShare's NFS can revoke an open log file
    (PermissionError, stale handle: iterations 72 and 91 of docs/step4_optimal_log.md). Losing log lines must
    not kill the run, whose results are written by path at every checkpoint, so later output goes to /dev/null
    (which also keeps the interpreter's exit-time flush from failing)."""
    try:
        print(msg, flush=True)
    except OSError:
        sys.stdout = sys.stderr = open(os.devnull, "w")


def train_run(run_dir, config, verbose=True, resume=False):
    """Train one seed. Refuses to touch an existing ``run_dir`` unless ``resume``: then it continues
    that run from its last checkpoint up to ``config["episodes"]`` (which may exceed the original
    target: an extension). Only ``episodes`` and ``anneal`` may differ from the run's own config."""
    assert config.get("refs"), "run Phase A first (experiments/step3_check.py): no reference numbers"
    cfg_path = os.path.join(run_dir, "config.json")
    if resume:
        with open(cfg_path) as fh:
            saved = json.load(fh)
        with open(os.path.join(run_dir, "progress.json")) as fh:
            prog = json.load(fh)
        changed = {k for k in config if k not in ("git", "started", "resumes", "episodes", "anneal")
                   and saved.get(k) != config[k]}
        if changed:
            raise ValueError(f"{run_dir}: a resume may change only episodes / anneal, not {sorted(changed)}")
        metrics = os.path.join(run_dir, "metrics.json")
        if os.path.exists(metrics):
            os.replace(metrics, os.path.join(run_dir, f"metrics_ep{prog['episodes']}.json"))
        resumes = saved.get("resumes", []) + [{"at_episodes": prog["episodes"], "episodes": config["episodes"],
                                                "anneal": config["anneal"], "git": _git_hash(),
                                                "time": time.strftime("%Y-%m-%d %H:%M:%S")}]
        config = {**saved, "episodes": config["episodes"], "anneal": config["anneal"], "resumes": resumes}
        with open(cfg_path + ".tmp", "w") as fh:
            json.dump(config, fh, indent=1)
        os.replace(cfg_path + ".tmp", cfg_path)
    else:
        if os.path.exists(run_dir):
            raise FileExistsError(f"{run_dir} exists; results are never overwritten")
        os.makedirs(run_dir)
        _snapshot(run_dir)
        with open(cfg_path, "w") as fh:
            json.dump({**config, "git": _git_hash(), "started": time.strftime("%Y-%m-%d %H:%M:%S")},
                      fh, indent=1)
    n_resume = len(config.get("resumes", []))
    seed = int(config["seed"])
    task = get_task(config["env"], **config["task"])
    proto = Protocol(**config["protocol"])
    pb = config["pbrr"]
    ref, _ = build_reference(task, proto.t_sub, {**pb, "seed": pb["ref_seed"]})
    ref_trajs = rollouts(task.make_batch(pb["k"], seed=1000 + seed), ref, proto,
                         np.random.default_rng(1000 + seed))

    n_envs = int(config["n_envs"])
    # a resume draws fresh env / overseer streams (the original run's are not saved)
    venv = AuditedVecEnv(task, proto, n_envs, config["reward_scale"], seed=seed * 1000 + 101 * n_resume)
    ppo = dict(config["ppo"])
    net_arch = ppo.pop("net_arch")
    ppo["n_steps"] = proto.t_sub
    assert ppo.get("gamma", 1.0) == 1.0, "gamma is fixed at 1 (CLAUDE.md 2)"
    overseer = Overseer(task, proto, venv, ref_trajs, GConfig(**config["g"]), k=pb["k"], beta=pb["beta"],
                        seed=seed + 7_000 * n_resume)
    ep_steps = n_envs * proto.t_ep
    if resume:
        model = PPO.load(os.path.join(run_dir, "model.zip"), env=venv, device="cpu")
        assert model.num_timesteps % ep_steps == 0, "checkpoints sit on episode boundaries"
        n_done = model.num_timesteps // ep_steps
        _restore(run_dir, overseer, proto, n_done)
        venv.episode = n_done - 1                            # the next reset starts episode n_done
        _say(f"  [{config['env']} s{seed}] resumed at episode {n_done} -> {config['episodes']}")
    else:
        model = PPO("MlpPolicy", venv, seed=seed, policy_kwargs=dict(net_arch=list(net_arch)), verbose=0,
                    **ppo)
    refs = config["refs"]
    timesteps = int(config["episodes"]) * ep_steps
    chunk = ep_steps * 24                                   # report and checkpoint every 24 episodes
    lr0, ent0 = float(ppo["learning_rate"]), float(ppo.get("ent_coef", 0.0))
    t0 = time.time()
    while model.num_timesteps < timesteps:
        fac = _anneal_factor(config.get("anneal", {}), model.num_timesteps, timesteps)
        boost = _ent_boost(config.get("anneal", {}), model.num_timesteps // ep_steps)
        model.ent_coef = ent0 * fac * boost                 # read by every update (not a jit constant)
        model.lr_schedule = (lambda lr: (lambda _: lr))(lr0 * fac)
        model.learn(total_timesteps=min(chunk, timesteps - model.num_timesteps), reset_num_timesteps=False,
                    callback=overseer, progress_bar=False)
        if verbose:
            n_ep = len(overseer.caught) // proto.n_sub
            m = metrics_from_logs(np.array(overseer.on_exploit), np.array(overseer.caught),
                                  np.array(overseer.env_proxy), proto, refs,
                                  ep_slice=slice(max(0, n_ep - 24), n_ep))
            _say(f"  [{config['env']} s{seed}] {model.num_timesteps:>10,}  win0-3 {m['window_0_3']:.2f}  "
                  f"off {m['offwindow_rel']:.2f}  corr/ep {m['corrections_per_ep']:.2f}  winF "
                  f"{m['window_final']:.2f}  proxy0-3 {m['proxy_0_3']:8.1f}  rounds {len(overseer.rounds)}  "
                  f"({time.time() - t0:.0f}s)")
        # checkpoint: a run killed by a time limit keeps everything up to here (no metrics.json = unfinished)
        on, ca, px = _save_logs(run_dir, overseer, model)
        with open(os.path.join(run_dir, "progress.tmp.json"), "w") as fh:
            json.dump({"timesteps": int(model.num_timesteps), "of": timesteps,
                       "episodes": len(overseer.caught) // proto.n_sub, "of_episodes": int(config["episodes"]),
                       "seconds": time.time() - t0, "anneal_factor": fac, "ent_coef": float(model.ent_coef),
                       "resumes": n_resume}, fh)
        os.replace(os.path.join(run_dir, "progress.tmp.json"), os.path.join(run_dir, "progress.json"))
    wall = time.time() - t0

    on, ca, px = _save_logs(run_dir, overseer, model)
    final = metrics_from_logs(on, ca, px, proto, refs)
    n_ep = len(ca) // proto.n_sub
    ckpts = [metrics_from_logs(on, ca, px, proto, refs, ep_slice=slice(max(0, e - n_ep // 10), e))
             for e in np.linspace(n_ep // 10, n_ep, 10).astype(int)]
    out = {"final": final, "checkpoints": ckpts, "wall_seconds": wall, "n_pbrr_rounds": len(overseer.rounds),
           "pbrr_seconds": float(sum(r["seconds"] for r in overseer.rounds))}
    with open(os.path.join(run_dir, "metrics.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    return out
