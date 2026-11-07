"""The Step 2 protocol, task-agnostic: sub-episodes, the end-of-sub-episode audit,
PBRR corrections, the episode reset (CLAUDE.md 2, 4d).

``AuditedVecEnv`` is an SB3 VecEnv over n copies of a task, stepped together (one
vectorised call per step, no per-env Python loop). Every copy shares the clock,
because sub-episode boundaries are fixed steps:

* t = 0 .. t_ep-1; tau = t mod t_sub; k = t // t_sub. The base task resets at the
  start of every sub-episode.
* A step exploits the bug iff proxy != true there. If that happens in the audit
  window (the last W steps of the sub-episode), the copy is flagged.
* At each boundary a flagged copy is detected with probability p. Detection
  increments that copy's correction count immediately (so the observation PPO
  bootstraps from already shows it) and leaves a PBRR round pending; the overseer
  (src/step3/pbrr.py) runs it and installs the new correction g, which is in force
  from the next sub-episode. The last audit never corrects: the reward resets.
* At t = t_ep every copy's g, preference data and count reset; ``done`` is True
  only here, so PPO bootstraps across every sub-episode boundary.

The received reward is r_proxy + g(s, a, s'), where g is the copy's current
correction network evaluated on the task's reward-model row. Copies that share a
correction (identical catch history) are evaluated in one batched call.

Observation: base features | one-hot tau | one-hot k | one-hot correction count |
audit flag | (optionally) a "monitor present" bit = tau is in the audit window. With
``clock="scalar"`` the one-hot tau is replaced by tau / t_sub and the monitor bit
(same information; for continuous-state tasks, whose few state dimensions a
t_sub-dimensional one-hot clock would swamp).
On the Step 1 grid with one-hot positions this is exactly Step 2's encoding.
"""

from dataclasses import dataclass, replace

import gymnasium
import jax
import jax.numpy as jnp
import numpy as np
from stable_baselines3.common.vec_env.base_vec_env import VecEnv

from ..pbrr_core import mlp_apply

__all__ = ["Protocol", "obs_dim", "encode_obs", "AuditedVecEnv", "g_apply"]


@dataclass(frozen=True)
class Protocol:
    t_sub: int = 100
    n_sub: int = 5
    window: int = 10            # W: the overseer audits the last W steps of each sub-episode
    p_detect: float = 1.0
    show_monitor: bool = False  # add a "monitor present" bit (Absent Supervisor)
    clock: str = "onehot"       # "onehot" tau (Step 1 / 2) | "scalar": tau / t_sub and the monitor bit

    @property
    def t_ep(self):
        return self.t_sub * self.n_sub

    @property
    def n_levels(self):
        return self.n_sub       # correction count 0..n_sub-1 (no correction after the last audit)

    def in_window(self, t):
        return (np.asarray(t) % self.t_sub) >= self.t_sub - self.window

    def with_(self, **kw):
        return replace(self, **kw)


def _tau_dim(proto):
    return proto.t_sub if proto.clock == "onehot" else 2


def obs_dim(proto, base_dim):
    return base_dim + _tau_dim(proto) + proto.n_sub + proto.n_levels + 1 + int(proto.show_monitor)


def encode_obs(proto, base, t, n_corr, flagged):
    """base (n, d) float; t scalar or (n,); n_corr, flagged (n,). -> (n, D) float32."""
    base = np.asarray(base, np.float32)
    n = base.shape[0]
    t = np.broadcast_to(np.asarray(t, np.int64), (n,))
    out = np.zeros((n, obs_dim(proto, base.shape[1])), np.float32)
    rows = np.arange(n)
    d = base.shape[1]
    out[:, :d] = base
    if proto.clock == "onehot":
        out[rows, d + t % proto.t_sub] = 1.0
    else:                                   # a continuous-state policy reads a scalar clock more easily
        out[:, d] = (t % proto.t_sub) / proto.t_sub
        out[:, d + 1] = proto.in_window(t).astype(np.float32)
    off = d + _tau_dim(proto)
    out[rows, off + np.minimum(t // proto.t_sub, proto.n_sub - 1)] = 1.0
    off += proto.n_sub
    out[rows, off + np.minimum(np.asarray(n_corr, np.int64), proto.n_levels - 1)] = 1.0
    off += proto.n_levels
    out[:, off] = np.asarray(flagged, np.float32)
    if proto.show_monitor:
        out[:, off + 1] = proto.in_window(t).astype(np.float32)
    return out


g_apply = jax.jit(mlp_apply)


class AuditedVecEnv(VecEnv):
    """``n_envs`` copies of ``task`` under the protocol. ``reward_scale`` multiplies
    the reward handed to the learner; ``self.last`` holds the unscaled received,
    proxy and true rewards, the exploit indicator and detections of the last step."""

    def __init__(self, task, proto, n_envs=16, reward_scale=1.0, seed=0):
        self.task, self.proto, self.reward_scale = task, proto, float(reward_scale)
        self.render_mode = None
        self.batch = task.make_batch(n_envs, seed=seed)
        self.rng = np.random.default_rng(seed + 7_919)
        space = gymnasium.spaces.Box(-np.inf, np.inf, (obs_dim(proto, task.obs_dim),), np.float32)
        super().__init__(n_envs, space, gymnasium.spaces.Discrete(task.n_actions))
        self.t = proto.t_ep              # forces a fresh episode on the first reset
        self.episode = -1
        self._reset_reward_state()
        self.last = None

    # -- reward state (reset every episode) -----------------------------------------
    def _reset_reward_state(self):
        n = self.num_envs
        self.n_corr = np.zeros(n, np.int64)
        self.flagged = np.zeros(n, bool)
        self.pending = np.zeros(n, bool)
        self.history = [()] * n           # sub-episodes at which each copy was caught
        self.g_params = [None] * n        # current correction network per copy

    def set_correction(self, indices, params):
        for j in indices:
            self.g_params[j] = params
            self.pending[j] = False

    def state_key(self, j):
        return self.episode, self.history[j]

    def correction(self, feat):
        """g(s, a, s') for every copy (0 where no correction is in force)."""
        n = self.num_envs
        corr = np.zeros(n)
        groups = {}
        for j, p in enumerate(self.g_params):
            if p is not None:
                groups.setdefault(id(p), (p, []))[1].append(j)
        for p, idx in groups.values():
            X = np.zeros((n, feat.shape[1]), np.float32)
            X[:len(idx)] = feat[idx]
            corr[idx] = np.asarray(g_apply(p, jnp.asarray(X)), float)[:len(idx)]
        return corr

    def _obs(self):
        return encode_obs(self.proto, self.batch.obs(), self.t, self.n_corr, self.flagged)

    # -- VecEnv API ---------------------------------------------------------------------
    def reset(self):
        if self._seeds[0] is not None:
            self.batch.seed(self._seeds[0])
            self.rng = np.random.default_rng(self._seeds[0] + 7_919)
            self._seeds = [None] * self.num_envs
        assert self.t % self.proto.t_sub == 0, "reset must land on a sub-episode boundary"
        if self.t >= self.proto.t_ep:
            self.t, self.episode = 0, self.episode + 1
            self._reset_reward_state()
        self.batch.reset()
        return self._obs()

    def step_async(self, actions):
        self._actions = np.asarray(actions).reshape(-1).astype(np.int64)

    def step_wait(self):
        proto, n = self.proto, self.num_envs
        in_win = bool(proto.in_window(self.t))
        out = self.batch.step(self._actions)
        exploit = out.exploit
        received = out.proxy + self.correction(out.feat)
        if in_win:
            self.flagged |= exploit
        self.t += 1
        detected = np.zeros(n, bool)
        dones = np.zeros(n, bool)
        infos = [{} for _ in range(n)]
        if self.t % proto.t_sub == 0:
            k = self.t // proto.t_sub - 1
            detected = self.flagged & (self.rng.random(n) < proto.p_detect)
            if self.t < proto.t_ep:                  # the last audit has nothing to correct
                for j in np.flatnonzero(detected):
                    self.n_corr[j] += 1
                    self.history[j] = self.history[j] + (k,)
                    self.pending[j] = True
            self.flagged[:] = False
            self.batch.reset()
            if self.t >= proto.t_ep:
                dones[:] = True
                term = self._obs()
                for j in range(n):
                    infos[j]["terminal_observation"] = term[j]
                self.t, self.episode = 0, self.episode + 1
                self._reset_reward_state()
        self.last = {"received": received, "proxy": out.proxy, "true": out.true, "exploit": exploit,
                     "in_window": in_win, "detected": detected}
        return self._obs(), (received * self.reward_scale).astype(np.float32), dones, infos

    def close(self):
        if hasattr(self.batch, "close"):
            self.batch.close()

    def get_attr(self, attr_name, indices=None):
        if not hasattr(self, attr_name):
            raise AttributeError(attr_name)
        return [getattr(self, attr_name)] * len(self._get_indices(indices))

    def set_attr(self, attr_name, value, indices=None):
        setattr(self, attr_name, value)

    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        raise NotImplementedError("use the AuditedVecEnv methods directly")

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * len(self._get_indices(indices))
