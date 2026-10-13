"""The Step 1 / Step 2 audit grid as a Step 3 task -- the regression anchor.

Same rules as ``src/audit_grid.py`` (built from its tables): 15x15, START (0,0),
GOAL (14,14) absorbing, the exploit tile E pays +100 per arrival under the proxy.
Policy and reward-model features are the one-hot position, so the reward-model row
[phi(s), phi(s'), one-hot a] is exactly Step 2's ``transition_features`` row, and
proxy != true holds exactly on the transitions that arrive on E (Step 1's flag).
"""

import numpy as np

from ...audit_grid import BASE, build_tables
from ..protocol import Protocol
from ..task import TabularTables, TabularTask

PROTOCOL = Protocol(t_sub=100, n_sub=5, window=10)
DEFAULTS = {"protocol": PROTOCOL, "reward_scale": 0.01}
RIGHT, DOWN, STAY = 4, 2, 0


def make_task(cfg=BASE):
    tb = build_tables(cfg)
    S, A = cfg.n_pos, 5
    eye = np.eye(S, dtype=np.float32)
    mu0 = np.zeros(S)
    mu0[tb.start] = 1.0
    absorbing = np.zeros(S, bool)
    absorbing[tb.goal] = True
    tables = TabularTables(
        nxt=tb.next_pos.reshape(S * A, 1), prob=np.ones((S * A, 1)),
        proxy=tb.reward[:, :, 0].reshape(S * A, 1), true=tb.true.reshape(S * A, 1),
        mu0=mu0, phi_obs=eye, phi_g=eye, absorbing=absorbing, n_actions=A)

    def rule(s):
        r, c = np.divmod(np.asarray(s), cfg.n)
        a = np.where(c < cfg.n - 1, RIGHT, DOWN)
        return np.where(np.asarray(s) == tb.goal, STAY, a)

    task = TabularTask("grid", tables, rule)
    task.cfg = cfg
    return task


def refs(config=None):
    """Idealised optimum under Step 2's canonical PBRR levels (Step 2 Phase A)."""
    import os
    from ..dp import evaluate_levels, refs_from_eval, solve_levels
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    R = np.load(os.path.join(root, "results", "step2", "phase_a", "canonical_rewards_max1.npz"))["R"]
    R = R.reshape(R.shape[0], -1, 1)
    task = make_task()
    _, pol = solve_levels(task.tables, PROTOCOL, R)
    return refs_from_eval(evaluate_levels(task.tables, PROTOCOL, R, pol), PROTOCOL)


def honest_optimum(task, proto=PROTOCOL):
    """True return of the honest optimum per sub-episode: 28 steps to GOAL, +50."""
    d = task.cfg.n - 1
    return -2 * d + task.cfg.goal_bonus
