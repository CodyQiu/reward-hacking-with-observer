"""The base-task interface every Step 3 environment implements.

A *task* is the base MDP only -- no clock, no audit, no correction. The protocol
(src/step3/protocol.py) wraps it. A task hands out *batches*: n independent copies
of the base MDP stepped together, so that training (16 copies), PBRR rollouts (19
copies) and demonstrations share one simulator and cannot disagree about the rules.

A batch exposes
    reset()        every copy to a fresh start state (the start of a sub-episode)
    obs()          (n, obs_dim) float32 base features for the policy
    step(a)        -> StepOut: proxy and true reward of the transition, the reward
                   model's input row [phi(s), phi(s'), one-hot a] (the PBRR code's
                   [obs, next_obs, action]) and, for tabular tasks, an integer key
                   that identifies the transition exactly
    absorbed       (n,) bool: the copy is in an absorbing state (goal, at rest, ...)
    rule()         (n,) actions of the task's hand-written honest rule

The exploit indicator is not task-specific: a step exploits the bug iff the proxy
and the true reward differ there (the suite-wide detection rule, CLAUDE.md 4e).

Tabular tasks are given as padded transition tables -- for each (s, a) up to F
successor states with probabilities -- which serve both the sampler below and the
exact DP (src/step3/dp.py).
"""

from dataclasses import dataclass

import numpy as np

__all__ = ["EXPLOIT_TOL", "StepOut", "TabularTables", "TabularTask", "TabularBatch", "exploit_mask"]

EXPLOIT_TOL = 1e-9


def exploit_mask(proxy, true):
    return np.abs(np.asarray(proxy, float) - np.asarray(true, float)) > EXPLOIT_TOL


@dataclass
class StepOut:
    proxy: np.ndarray            # (n,) original-proxy reward of the transition
    true: np.ndarray             # (n,) ground-truth reward
    feat: np.ndarray             # (n, g_in_dim) float32 reward-model input row
    key: np.ndarray | None       # (n,) int64 exact transition id (tabular tasks only)

    @property
    def exploit(self):
        return exploit_mask(self.proxy, self.true)


@dataclass
class TabularTables:
    """Padded rules, row r = s * A + a, column j = j-th possible successor."""

    nxt: np.ndarray              # (S*A, F) int64 successor states (padding repeats a valid one)
    prob: np.ndarray             # (S*A, F) float64 successor probabilities (padding 0)
    proxy: np.ndarray            # (S*A, F) original-proxy reward of (s, a, s')
    true: np.ndarray             # (S*A, F) ground-truth reward of (s, a, s')
    mu0: np.ndarray              # (S,) start distribution of every sub-episode
    phi_obs: np.ndarray          # (S, obs_dim) float32 policy features
    phi_g: np.ndarray            # (S, g_dim) float32 reward-model state features
    absorbing: np.ndarray        # (S,) bool
    n_actions: int
    phi_ref: np.ndarray | None = None   # (S, d) features the BC reference sees (default phi_obs)

    @property
    def n_states(self):
        return len(self.mu0)

    @property
    def exploit(self):
        return exploit_mask(self.proxy, self.true) & (self.prob > 0)

    def check(self):
        S, A = self.n_states, self.n_actions
        assert self.nxt.shape == self.prob.shape == self.proxy.shape == self.true.shape
        assert self.nxt.shape[0] == S * A
        assert np.allclose(self.prob.sum(axis=1), 1.0), "transition rows must sum to 1"
        pos = self.prob > 0
        assert (pos[:, 1:] <= pos[:, :-1]).all(), "successors must be a prefix of each row"
        assert np.isclose(self.mu0.sum(), 1.0)
        assert self.phi_obs.shape[0] == S and self.phi_g.shape[0] == S
        return self


class TabularTask:
    """A finite MDP given by ``TabularTables`` plus a hand-written honest rule
    ``rule_fn(states) -> actions`` (on state indices)."""

    tabular = True

    def __init__(self, name, tables, rule_fn=None):
        self.name = name
        self.tables = tables.check()
        self.rule_fn = rule_fn
        S, A, F = tables.n_states, tables.n_actions, tables.nxt.shape[1]
        self.n_states, self.n_actions, self.fanout = S, A, F
        self.obs_dim = tables.phi_obs.shape[1]
        self.g_dim = tables.phi_g.shape[1]
        self.g_in_dim = 2 * self.g_dim + A
        cum = np.cumsum(tables.prob, axis=1)
        cum[np.arange(len(cum)), (tables.prob > 0).cumsum(axis=1).argmax(axis=1)] = 1.0
        cum[tables.prob <= 0] = 2.0           # never selected
        self._cum = cum
        self._eye_a = np.eye(A, dtype=np.float32)

    def make_batch(self, n, seed=None):
        return TabularBatch(self, n, seed)

    # -- transition keys and reward-model rows ----------------------------------------
    def key(self, s, a, s2):
        return (np.asarray(s, np.int64) * self.n_actions + np.asarray(a, np.int64)) * self.n_states \
            + np.asarray(s2, np.int64)

    def decode(self, key):
        key = np.asarray(key, np.int64)
        s2 = key % self.n_states
        sa = key // self.n_states
        return sa // self.n_actions, sa % self.n_actions, s2

    def g_rows(self, s, a, s2):
        phi = self.tables.phi_g
        return np.concatenate([phi[s], phi[s2], self._eye_a[a]], axis=1).astype(np.float32)

    def g_rows_from_keys(self, key):
        return self.g_rows(*self.decode(key))

    def support_keys(self):
        """(S*A, F) keys of every (s, a, s') row of the padded tables."""
        S, A = self.n_states, self.n_actions
        s = np.repeat(np.arange(S), A)
        a = np.tile(np.arange(A), S)
        return self.key(s[:, None], a[:, None], self.tables.nxt)


class TabularBatch:
    def __init__(self, task, n, seed=None):
        self.task, self.n = task, n
        self.rng = np.random.default_rng(seed)
        self.s = np.zeros(n, np.int64)
        self.reset()

    def seed(self, seed):
        self.rng = np.random.default_rng(seed)

    def reset(self):
        mu0 = self.task.tables.mu0
        if np.count_nonzero(mu0) == 1:
            self.s = np.full(self.n, int(np.argmax(mu0)), np.int64)
        else:
            self.s = self.rng.choice(len(mu0), size=self.n, p=mu0).astype(np.int64)

    def obs(self):
        return self.task.tables.phi_obs[self.s]

    def ref_obs(self):
        """Features of the reference policy (fixed by Phase A, independent of the
        learner's observation encoding)."""
        tb = self.task.tables
        return (tb.phi_obs if tb.phi_ref is None else tb.phi_ref)[self.s]

    @property
    def absorbed(self):
        return self.task.tables.absorbing[self.s]

    def rule(self):
        return np.asarray(self.task.rule_fn(self.s), np.int64)

    def step(self, a):
        tk, tb = self.task, self.task.tables
        a = np.asarray(a, np.int64).reshape(-1)
        r = self.s * tk.n_actions + a
        if tk.fanout == 1:
            j = np.zeros(self.n, np.int64)
        else:
            u = self.rng.random(self.n)
            j = (u[:, None] >= tk._cum[r]).sum(axis=1)
        s2 = tb.nxt[r, j]
        out = StepOut(tb.proxy[r, j].astype(float), tb.true[r, j].astype(float),
                      tk.g_rows(self.s, a, s2), tk.key(self.s, a, s2))
        self.s = s2
        return out
