"""SBX PPO training for Exp 2, with an evaluation harness that measures the
*true* reward the agent is never trained on.

Two things here are worth knowing before changing anything.

**gamma = 1.0 is deliberate.** Episodes are finite (horizon 40), so undiscounted
return is well defined and is the quantity the reference numbers are stated in.

**Evaluation reads the policy as a lookup table.** The agent's observation is a
one-hot over 21 cells plus a patch bit, so the policy is exactly a map from 42
discrete situations to 5 action probabilities. One batched forward pass recovers
that whole table, after which 300 evaluation episodes are simulated by stepping
the real environment and sampling from it. This is not an approximation of the
policy -- it is the policy -- and it makes evaluation ~1000x cheaper than calling
predict() once per step. ``tests/test_env.py`` checks the table against
``model.predict`` empirically.
"""

import csv
import os
import time

import numpy as np
from sbx import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from .waypoint_env import (
    CELL_INDEX,
    FREE_CELLS,
    N_FREE,
    OBS_DIM,
    WaypointFarmEnv,
    encode_obs,
)

__all__ = [
    "PPO_KWARGS",
    "make_vec_env",
    "make_model",
    "action_prob_table",
    "evaluate_policy_table",
    "evaluate",
    "train_one",
    "EVAL_FIELDS",
]

PPO_KWARGS = dict(
    learning_rate=3e-4,
    n_steps=512,          # x 4 envs = 2048 transitions per update
    batch_size=256,
    n_epochs=10,
    gamma=1.0,            # undiscounted: finite horizon, see module docstring
    gae_lambda=0.95,
    ent_coef=0.01,
    verbose=0,
)

N_ENVS = 4

EVAL_FIELDS = [
    "timesteps",
    "true_return",
    "true_return_sem",
    "proxy_return",
    "farm_steps",
    "p_detected",
    "mean_first_detection",
    "goal_rate",
    "ep_len",
]

# Every (cell, patched) situation the agent can be in, and its observation.
OBS_KEYS = [(cell, p) for cell in FREE_CELLS for p in (0, 1)]
OBS_MATRIX = np.stack([encode_obs(cell, bool(p)) for cell, p in OBS_KEYS]).astype(np.float32)


def obs_row(pos, patched):
    """Row of OBS_MATRIX / action table corresponding to (pos, patched)."""
    return CELL_INDEX[pos] * 2 + int(patched)


def make_vec_env(monitor, seed, n_envs=N_ENVS, **env_kwargs):
    def factory(rank):
        def _init():
            return WaypointFarmEnv(monitor=monitor, seed=seed * 1000 + rank, **env_kwargs)

        return _init

    return DummyVecEnv([factory(i) for i in range(n_envs)])


def make_model(env, seed, **overrides):
    kwargs = {**PPO_KWARGS, **overrides}
    model = PPO(
        "MlpPolicy",
        env,
        seed=seed,
        policy_kwargs=dict(net_arch=[64, 64]),
        **kwargs,
    )
    assert model.gamma == 1.0, f"gamma must be 1.0 for this experiment, got {model.gamma}"
    return model


def action_prob_table(model):
    """(42, 5) array of action probabilities, one row per (cell, patched)."""
    state = model.policy.actor_state
    dist = state.apply_fn(state.params, OBS_MATRIX)
    probs = np.asarray(dist.probs_parameter())
    probs = probs.reshape(len(OBS_KEYS), -1)[:, : model.action_space.n]
    probs = np.clip(probs, 0.0, None)
    probs /= probs.sum(axis=1, keepdims=True)
    return probs


def evaluate_policy_table(table, monitor, n_episodes=300, seed=0, deterministic=False,
                          **env_kwargs):
    """Run fresh episodes with the monitor active, sampling actions from ``table``.

    Steps the real environment, so the measured numbers cannot drift from the
    dynamics the agent was trained in.
    """
    env = WaypointFarmEnv(monitor=monitor, seed=seed, **env_kwargs)
    rng = np.random.default_rng(seed + 7_919)
    n_actions = table.shape[1]

    true_r, proxy_r, farm, lengths, reached, detected, first_det = [], [], [], [], [], [], []
    for ep in range(n_episodes):
        env.reset(seed=seed if ep == 0 else None)
        terminated = truncated = False
        info = {}
        while not (terminated or truncated):
            p = table[obs_row(env.pos, env.patched)]
            action = int(p.argmax()) if deterministic else int(rng.choice(n_actions, p=p))
            _, _, terminated, truncated, info = env.step(action)
        true_r.append(info["episode_true_return"])
        proxy_r.append(info["episode_proxy_return"])
        farm.append(info["farm_steps"])
        lengths.append(info["episode_length"])
        reached.append(info["reached_goal"])
        detected.append(info["first_detection_step"] is not None)
        if info["first_detection_step"] is not None:
            first_det.append(info["first_detection_step"])

    return {
        "true_return": float(np.mean(true_r)),
        "true_return_sem": float(np.std(true_r) / np.sqrt(n_episodes)),
        "proxy_return": float(np.mean(proxy_r)),
        "farm_steps": float(np.mean(farm)),
        "p_detected": float(np.mean(detected)),
        "mean_first_detection": float(np.mean(first_det)) if first_det else float("nan"),
        "goal_rate": float(np.mean(reached)),
        "ep_len": float(np.mean(lengths)),
    }


def evaluate(model, monitor, n_episodes=300, seed=0, deterministic=False, **env_kwargs):
    return evaluate_policy_table(
        action_prob_table(model), monitor, n_episodes, seed, deterministic, **env_kwargs
    )


def train_one(
    monitor,
    seed,
    total_timesteps=500_000,
    eval_every=10_000,
    n_eval_episodes=300,
    results_dir="results",
    env_kwargs=None,
    verbose=True,
):
    """Train one seed of one condition, evaluating periodically. Returns the rows."""
    env_kwargs = env_kwargs or {}
    os.makedirs(results_dir, exist_ok=True)
    path = os.path.join(results_dir, f"{monitor}_seed{seed}.csv")

    vec_env = make_vec_env(monitor, seed, **env_kwargs)
    model = make_model(vec_env, seed)

    rows = []
    t0 = time.time()

    def do_eval():
        m = evaluate(
            model, monitor, n_episodes=n_eval_episodes,
            seed=seed * 7 + len(rows), **env_kwargs
        )
        m["timesteps"] = int(model.num_timesteps)
        rows.append(m)
        return m

    m = do_eval()  # step 0: the untrained policy
    if verbose:
        print(
            f"  [{monitor} seed {seed}] {m['timesteps']:>7,} steps  "
            f"true {m['true_return']:+7.2f}  proxy {m['proxy_return']:+7.2f}  "
            f"farm {m['farm_steps']:5.2f}  goal {m['goal_rate']:.2f}"
        )

    while model.num_timesteps < total_timesteps:
        model.learn(
            total_timesteps=eval_every,
            reset_num_timesteps=False,
            progress_bar=False,
        )
        m = do_eval()
        if verbose:
            print(
                f"  [{monitor} seed {seed}] {m['timesteps']:>7,} steps  "
                f"true {m['true_return']:+7.2f}  proxy {m['proxy_return']:+7.2f}  "
                f"farm {m['farm_steps']:5.2f}  goal {m['goal_rate']:.2f}"
            )

    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=EVAL_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in EVAL_FIELDS})

    if verbose:
        print(f"  [{monitor} seed {seed}] done in {time.time() - t0:.0f}s -> {path}")
    return rows, path
