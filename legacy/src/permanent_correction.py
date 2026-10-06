"""Exp 2, optional phase 2 (spec section 10): the permanent correction.

On top of the per-episode monitor, the overseer keeps a running count of how many
times it has caught the agent farming *across training episodes*. Once that count
reaches ``n_permanent``, it stops patching episode by episode and simply replaces
the proxy with the true reward from then on -- the bug is fixed for good.

Implemented as a Gymnasium wrapper that flips the base environment's existing
``start_patched`` flag. The base env's step logic is untouched, per the spec.

The counter is shared across the parallel training environments, because the
correction is a property of the overseer, not of one worker.

Expected shape of the received-reward curve: it rises as the agent learns to farm,
drops sharply when the swap lands, then climbs back as it relearns the real task,
with true return converging to the honest optimum of +2.0.
"""

import csv
import os

import gymnasium
import numpy as np
from stable_baselines3.common.vec_env import DummyVecEnv

from .train import evaluate, make_model
from .waypoint_env import WaypointFarmEnv

__all__ = [
    "DetectionCounter",
    "PermanentCorrectionWrapper",
    "train_with_permanent_correction",
    "EPISODE_FIELDS",
]

EPISODE_FIELDS = [
    "timestep",
    "proxy_return",
    "true_return",
    "farm_steps",
    "reached_goal",
    "episode_length",
    "corrected",
]


class DetectionCounter:
    """Shared across workers: total detections, and whether the swap has landed."""

    def __init__(self, n_permanent=50):
        self.n_permanent = int(n_permanent)
        self.detections = 0
        self.total_steps = 0
        self.swap_step = None      # env step at which the permanent swap fired
        self.episodes = []         # (timestep, proxy, true, farm, goal, length, corrected)

    @property
    def corrected(self):
        return self.detections >= self.n_permanent

    def record_detection(self):
        self.detections += 1
        if self.corrected and self.swap_step is None:
            self.swap_step = self.total_steps


class PermanentCorrectionWrapper(gymnasium.Wrapper):
    def __init__(self, env, counter):
        super().__init__(env)
        self.counter = counter

    def reset(self, **kwargs):
        # Flip the base env's existing flag; never touch its step logic.
        self.env.unwrapped.start_patched = self.counter.corrected
        return self.env.reset(**kwargs)

    def step(self, action):
        obs, reward, terminated, truncated, info = self.env.step(action)
        self.counter.total_steps += 1
        if info.get("detected_this_step"):
            self.counter.record_detection()
        if terminated or truncated:
            self.counter.episodes.append(
                (
                    self.counter.total_steps,
                    info["episode_proxy_return"],
                    info["episode_true_return"],
                    info["farm_steps"],
                    int(info["reached_goal"]),
                    info["episode_length"],
                    int(self.counter.corrected),
                )
            )
        return obs, reward, terminated, truncated, info


def train_with_permanent_correction(
    monitor="suspicion",
    seed=0,
    n_permanent=50,
    total_timesteps=300_000,
    n_envs=4,
    results_dir="results",
    verbose=True,
):
    """Train with the training-level correction active. Returns (counter, path)."""
    os.makedirs(results_dir, exist_ok=True)
    counter = DetectionCounter(n_permanent)

    def factory(rank):
        def _init():
            return PermanentCorrectionWrapper(
                WaypointFarmEnv(monitor=monitor, seed=seed * 1000 + rank), counter
            )

        return _init

    vec_env = DummyVecEnv([factory(i) for i in range(n_envs)])
    model = make_model(vec_env, seed)
    model.learn(total_timesteps=total_timesteps, progress_bar=False)

    # n_permanent is in the filename: the threshold changes *when* the swap lands
    # relative to learning, which changes the result qualitatively, so runs at
    # different thresholds must not collide.
    path = os.path.join(
        results_dir, f"permanent_{monitor}_n{n_permanent}_seed{seed}.csv"
    )
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(EPISODE_FIELDS)
        writer.writerows(counter.episodes)

    # where did the policy end up, measured in the regime now in force?
    final = evaluate(
        model, monitor, n_episodes=500, seed=seed + 31,
        start_patched=counter.corrected,
    )
    if verbose:
        print(
            f"  [permanent/{monitor} seed {seed}] detections {counter.detections}, "
            f"swap at env step {counter.swap_step}, "
            f"final true return {final['true_return']:+.2f}, "
            f"goal {final['goal_rate']:.2f}, farm {final['farm_steps']:.2f}"
        )
    return counter, final, path
