"""SBX PPO on the Step 1 audit grid, with policy updates aligned to sub-episodes.

**Update schedule = the protocol.** N synchronised envs, ``n_steps = t_sub``: every
PPO rollout is exactly one sub-episode of every env, so the policy update happens
at each sub-episode boundary, right after the env's overseer has applied (or not)
the reward patch. Episodes have a fixed length (no early termination), so the envs
never drift out of phase; ``AlignmentCheck`` asserts it at every rollout.

**Credit crosses the boundary.** A rollout end is not a terminal: PPO bootstraps
V(last_obs), and the last obs already carries the post-audit ``patched`` bit, so
being caught shows up in the value. Only the true episode end (t = 500) is
terminal. The ``myopic`` control makes every sub-episode end terminal instead.

**gamma = 1.0** (CLAUDE.md 7). Rewards are scaled by ``REWARD_SCALE`` for the
learner (a positive rescale; DP optimum unchanged). Value targets at t = 0 are
then <= 395.

**Evaluation is exact.** Every observation is one-hot, so the policy is exactly a
table over (t, pos, patched, flagged). One batched forward pass per sub-episode
recovers it, and ``audit_dp.evaluate`` propagates the state distribution through
the true dynamics: no Monte Carlo noise in any reported metric.
"""

import csv
import os
import time

import numpy as np
from sbx import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv

from .audit_dp import evaluate, greedy_probs, signatures, solve
from .audit_grid import ACTIONS, BASE, AuditGridEnv, encode_obs

__all__ = ["CONDITIONS", "condition_setup", "make_model", "policy_table", "evaluate_model",
           "train_one", "EVAL_FIELDS", "ROUND_FIELDS", "RoundLogger"]

N_ENVS = 16
REWARD_SCALE = 0.01

PPO_KWARGS = dict(
    learning_rate=3e-4,
    batch_size=400,       # 16 envs x 100 steps = 1600 transitions per update, 4 minibatches
    n_epochs=10,
    gamma=1.0,
    gae_lambda=0.95,
    ent_coef=0.01,
    verbose=0,
)

CONDITIONS = ("main", "whole_window", "toothless", "myopic", "no_clock")


def condition_setup(condition, cfg=BASE):
    """-> (env cfg, clock, myopic). The env cfg is also the evaluation cfg."""
    if condition == "main":
        return cfg, True, False
    if condition == "whole_window":
        return cfg.with_(window=cfg.t_sub), True, False
    if condition == "toothless":
        return cfg.with_(toothless=True), True, False
    if condition == "myopic":
        return cfg, True, True
    if condition == "no_clock":
        return cfg, False, False
    raise ValueError(condition)


class AlignmentCheck(BaseCallback):
    """Every rollout must start on a sub-episode boundary in every env."""

    def __init__(self, t_sub):
        super().__init__()
        self.t_sub = t_sub

    def _on_rollout_start(self):
        ts = self.training_env.get_attr("t")
        assert all(t % self.t_sub == 0 for t in ts), f"rollout misaligned with sub-episodes: {ts}"

    def _on_step(self):
        return True


ROUND_FIELDS = ["round", "timesteps", "k", "proxy_return", "true_return", "patched", "detected"]


class RoundLogger(AlignmentCheck):
    """Per-round training log. One PPO rollout = one sub-episode (round) of every env,
    so each record is the reward the learner actually received in one round, summed
    over its 100 steps (the round return starts again from 0 at every boundary) and
    averaged over the N envs. Rewards are the unscaled ones from ``info``.

    Fields: k (round index within the episode), proxy / true round return, the
    fraction of envs already patched at the start of the round, and the fraction in
    which this round's audit detected the exploit.

    ``step_proxy`` / ``step_true`` additionally keep the per-step reward of every
    round (mean over envs), shape (n_rounds, t_sub), so whole training episodes can
    be drawn step by step.
    """

    def __init__(self, t_sub):
        super().__init__(t_sub)
        self.rows = []
        self.step_proxy, self.step_true = [], []
        self.env_proxy, self.env_true = [], []    # (n_rounds, n_envs): every trial separately

    def _on_rollout_start(self):
        super()._on_rollout_start()
        n = self.training_env.num_envs
        self._k = int(self.training_env.get_attr("t")[0]) // self.t_sub
        self._patched = float(np.mean(self.training_env.get_attr("patched")))
        self._proxy, self._true, self._detected = np.zeros(n), np.zeros(n), np.zeros(n)
        self._sp, self._st = np.zeros(self.t_sub), np.zeros(self.t_sub)
        self._i = 0

    def _on_step(self):
        infos = self.locals["infos"]
        for i, info in enumerate(infos):
            self._proxy[i] += info["proxy_reward"]
            self._true[i] += info["true_reward"]
            self._detected[i] = max(self._detected[i], float(info["detected"]))
        self._sp[self._i] = np.mean([info["proxy_reward"] for info in infos])
        self._st[self._i] = np.mean([info["true_reward"] for info in infos])
        self._i += 1
        return True

    def _on_rollout_end(self):
        self.rows.append({
            "round": len(self.rows), "timesteps": int(self.num_timesteps), "k": self._k,
            "proxy_return": float(self._proxy.mean()), "true_return": float(self._true.mean()),
            "patched": self._patched, "detected": float(self._detected.mean()),
        })
        assert self._i == self.t_sub, f"a round must be {self.t_sub} steps, got {self._i}"
        self.env_proxy.append(self._proxy.copy())
        self.env_true.append(self._true.copy())
        self.step_proxy.append(self._sp.copy())
        self.step_true.append(self._st.copy())


def make_vec_env(cfg, clock, myopic, seed, n_envs=N_ENVS):
    def factory(rank):
        return lambda: AuditGridEnv(cfg, clock=clock, myopic=myopic,
                                    reward_scale=REWARD_SCALE, seed=seed * 1000 + rank)
    return DummyVecEnv([factory(i) for i in range(n_envs)])


def make_model(env, cfg, seed, **overrides):
    kwargs = {**PPO_KWARGS, "n_steps": cfg.t_sub, **overrides}
    model = PPO("MlpPolicy", env, seed=seed, policy_kwargs=dict(net_arch=[64, 64]), **kwargs)
    assert model.gamma == 1.0, f"gamma must be 1.0 (CLAUDE.md 7), got {model.gamma}"
    assert model.n_steps == cfg.t_sub, "policy updates must land on sub-episode boundaries"
    return model


def _probs(model, obs):
    state = model.policy.actor_state
    p = np.asarray(state.apply_fn(state.params, obs).probs_parameter())[..., : len(ACTIONS)]
    p = np.clip(p, 0.0, None)
    return p / p.sum(axis=-1, keepdims=True)


def policy_table(model, cfg, clock=True):
    """(t_ep, n_pos, 2, 2, A) action probabilities, exactly the learned policy."""
    pos, pt, fl = np.meshgrid(np.arange(cfg.n_pos), [0, 1], [0, 1], indexing="ij")
    if not clock:  # the observation does not depend on t, so neither does the policy
        obs = encode_obs(cfg, 0, pos, pt, fl, clock=False)
        p = _probs(model, obs.reshape(-1, obs.shape[-1])).reshape(pos.shape + (len(ACTIONS),))
        return np.broadcast_to(p, (cfg.t_ep,) + p.shape).copy()
    out = np.zeros((cfg.t_ep, cfg.n_pos, 2, 2, len(ACTIONS)), dtype=np.float64)
    for k in range(cfg.n_sub):
        ts = np.arange(k * cfg.t_sub, (k + 1) * cfg.t_sub)[:, None, None, None]
        obs = encode_obs(cfg, ts, pos[None], pt[None], fl[None], clock=True)
        out[k * cfg.t_sub:(k + 1) * cfg.t_sub] = _probs(model, obs.reshape(-1, obs.shape[-1])).reshape(
            out[k * cfg.t_sub:(k + 1) * cfg.t_sub].shape)
    return out


EVAL_FIELDS = (["timesteps", "proxy_return", "true_return", "corrections",
                "greedy_proxy_return", "greedy_true_return", "greedy_corrections",
                "step_off_nonfinal", "final_dwell", "occ_l1_to_dp"]
               + [f"pre_k{k}" for k in range(BASE.n_sub)]
               + [f"window_k{k}" for k in range(BASE.n_sub)]
               + [f"leave_k{k}" for k in range(BASE.n_sub)]
               + [f"proxy_k{k}" for k in range(BASE.n_sub)]
               + [f"true_k{k}" for k in range(BASE.n_sub)])


def evaluate_model(model, cfg, clock, dp_bonus):
    probs = policy_table(model, cfg, clock)
    ev = evaluate(cfg, probs)
    gr = evaluate(cfg, greedy_probs(cfg, probs.argmax(axis=-1)))
    sig = signatures(cfg, ev["bonus_unpatched"], tol=0.1)
    row = {
        "proxy_return": ev["proxy_return"], "true_return": ev["true_return"],
        "corrections": ev["corrections"],
        "greedy_proxy_return": gr["proxy_return"], "greedy_true_return": gr["true_return"],
        "greedy_corrections": gr["corrections"],
        "step_off_nonfinal": sig["step_off_nonfinal"], "final_dwell": sig["final_dwell"],
        "occ_l1_to_dp": float(np.abs(ev["bonus"] - dp_bonus).mean()),
    }
    for k in range(cfg.n_sub):
        row[f"pre_k{k}"], row[f"window_k{k}"] = sig["pre"][k], sig["window"][k]
        row[f"leave_k{k}"] = sig["leave"][k]
        row[f"proxy_k{k}"], row[f"true_k{k}"] = ev["proxy_by_k"][k], ev["true_by_k"][k]
    return row, ev


def train_one(condition, seed, total_timesteps=2_000_000, eval_every=32_000,
              results_dir="results/step1_ppo", cfg=BASE, verbose=True, **ppo_overrides):
    """Train one seed of one condition. Writes
    <condition>_seed<seed>.csv          exact evaluations every ``eval_every`` steps
    <condition>_seed<seed>_rounds.csv   the received proxy / true return of every round
    <condition>_seed<seed>_steps.npz    the received per-step reward of every round
    <condition>_seed<seed>.npz          per-step occupancy and expected rewards per eval
    """
    ecfg, clock, myopic = condition_setup(condition, cfg)
    step = N_ENVS * ecfg.t_sub
    assert eval_every % step == 0, f"eval_every must be a multiple of {step} to stay aligned"
    os.makedirs(results_dir, exist_ok=True)
    stem = os.path.join(results_dir, f"{condition}_seed{seed}")

    env = make_vec_env(ecfg, clock, myopic, seed)
    model = make_model(env, ecfg, seed, **ppo_overrides)
    _, dp_pol = solve(ecfg, myopic=myopic)
    dp_ev = evaluate(ecfg, greedy_probs(ecfg, dp_pol))
    check = RoundLogger(ecfg.t_sub)
    rows, occ, occ_all, prox_t, true_t, t0 = [], [], [], [], [], time.time()

    def do_eval():
        row, ev = evaluate_model(model, ecfg, clock, dp_ev["bonus"])
        row["timesteps"] = int(model.num_timesteps)
        rows.append(row)
        occ.append(ev["bonus_unpatched"])
        occ_all.append(ev["bonus"])
        prox_t.append(ev["proxy_t"])
        true_t.append(ev["true_t"])
        if verbose:
            pre = " ".join(f"{row['pre_k%d' % k]:.2f}" for k in range(ecfg.n_sub))
            win = " ".join(f"{row['window_k%d' % k]:.2f}" for k in range(ecfg.n_sub))
            leave = " ".join(f"{row['leave_k%d' % k]:3.0f}" for k in range(ecfg.n_sub))
            print(f"  [{condition} s{seed}] {row['timesteps']:>9,}  proxy {row['proxy_return']:9.0f}  "
                  f"true {row['true_return']:7.0f}  corr {row['corrections']:.2f}  "
                  f"pre {pre}  win {win}  leave {leave}  ({time.time() - t0:.0f}s)", flush=True)

    do_eval()
    while model.num_timesteps < total_timesteps:
        model.learn(total_timesteps=eval_every, reset_num_timesteps=False, callback=check,
                    progress_bar=False)
        do_eval()

    with open(stem + ".csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EVAL_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r[k] for k in EVAL_FIELDS})
    with open(stem + "_rounds.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ROUND_FIELDS)
        w.writeheader()
        w.writerows(check.rows)
    np.savez_compressed(stem + "_steps.npz", proxy=np.array(check.step_proxy),
                        true=np.array(check.step_true), k=np.array([r["k"] for r in check.rows]),
                        env_proxy=np.array(check.env_proxy), env_true=np.array(check.env_true))
    np.savez_compressed(stem + ".npz", timesteps=np.array([r["timesteps"] for r in rows]),
                        bonus_unpatched=np.array(occ), bonus=np.array(occ_all),
                        proxy_t=np.array(prox_t), true_t=np.array(true_t),
                        dp_bonus=dp_ev["bonus"], dp_proxy_t=dp_ev["proxy_t"], dp_true_t=dp_ev["true_t"])
    if verbose:
        print(f"  [{condition} s{seed}] done in {time.time() - t0:.0f}s -> {stem}.csv")
    return rows, stem
