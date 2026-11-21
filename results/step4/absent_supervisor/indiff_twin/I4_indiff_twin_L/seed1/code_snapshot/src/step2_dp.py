"""Exact DP for an *idealised* Step 2: the audit grid with a correction COUNT.

Step 1's state carried a patched bit; here the reward after c corrections in the
current episode is a fixed table R_c (c = 0 is the original proxy). In the real
Step 2 R_c is whatever PBRR fits from the agent's own trajectories, so this model
plugs in a *canonical* sequence R_1..R_4 (fitted in experiments/step2_pbrr_check.py
from rollouts of the policy each correction level induces) and answers the
question that matters before any PPO: with PBRR-shaped corrections, is hiding from
the audit still the optimal policy, and what does it earn?

Detection is unchanged from Step 1: the overseer flags the agent if it arrives on
the exploit tile during the audit window (under PBRR the proxy's bonus is never
removed, only offset by g, so arriving on the tile is the observable event). A
detected flag at a boundary advances c by one (with probability p), from the next
sub-episode. gamma = 1.
"""

import numpy as np

from .audit_grid import ACTIONS, build_tables

__all__ = ["solve_levels", "evaluate_levels"]


def solve_levels(cfg, R_levels, detect=None):
    """R_levels: (L, n_pos, A) received reward at each correction level.
    Returns V (t_ep+1, n_pos, L, 2) and policy (t_ep, n_pos, L, 2)."""
    tb = build_tables(cfg)
    R = np.asarray(R_levels, float)
    L = R.shape[0]
    det = tb.bonus[:, :, 0] if detect is None else detect          # (P, A)
    n_pos, n_a = cfg.n_pos, len(ACTIONS)
    V = np.zeros((cfg.t_ep + 1, n_pos, L, 2))
    policy = np.zeros((cfg.t_ep, n_pos, L, 2), dtype=np.int64)
    lv = np.arange(L)[None, None, :, None]
    ff = np.arange(2)[None, None, None, :].astype(bool)
    nxt = tb.next_pos[:, :, None, None]
    up = np.minimum(np.arange(L) + 1, L - 1)
    for t in range(cfg.t_ep - 1, -1, -1):
        Vn = V[t + 1]
        tau = t % cfg.t_sub
        f_next = ff | (cfg.in_window(t) & det[:, :, None, None])       # (P, A, 1|L, 2)
        f_next = np.broadcast_to(f_next, (n_pos, n_a, L, 2))
        if tau < cfg.t_sub - 1:
            cont = Vn[nxt, lv, f_next.astype(np.int64)]
        elif t == cfg.t_ep - 1:
            cont = np.zeros((n_pos, n_a, L, 2))
        else:
            v_clean = Vn[tb.start, :, 0]                                 # (L,)
            v_hit = cfg.p_detect * Vn[tb.start, up, 0] + (1 - cfg.p_detect) * v_clean
            cont = np.where(f_next, v_hit[lv], v_clean[lv])
        Q = R.transpose(1, 2, 0)[:, :, :, None] + cont                   # (P, A, L, 2)
        policy[t] = Q.argmax(axis=1)
        V[t] = Q.max(axis=1)
    return V, policy


def evaluate_levels(cfg, R_levels, policy, detect=None):
    """Deterministic rollout of ``policy`` (p_detect = 1 assumed for a single path).
    Returns per-sub-episode received / proxy / true returns, corrections, and the
    per-step bonus indicator."""
    tb = build_tables(cfg)
    R = np.asarray(R_levels, float)
    det = tb.bonus[:, :, 0] if detect is None else detect
    L = R.shape[0]
    pos, lvl, flag = tb.start, 0, False
    out = {k: np.zeros(cfg.n_sub) for k in ("received", "proxy", "true")}
    on_exploit = np.zeros(cfg.t_ep, bool)
    levels = np.zeros(cfg.n_sub, int)
    for t in range(cfg.t_ep):
        k = t // cfg.t_sub
        levels[k] = lvl
        a = policy[t, pos, lvl, int(flag)]
        out["received"][k] += R[lvl, pos, a]
        out["proxy"][k] += tb.reward[pos, a, 0]
        out["true"][k] += tb.true[pos, a]
        on_exploit[t] = det[pos, a]
        if cfg.in_window(t) and det[pos, a]:
            flag = True
        pos = tb.next_pos[pos, a]
        if (t + 1) % cfg.t_sub == 0:
            if flag and t + 1 < cfg.t_ep:
                lvl = min(lvl + 1, L - 1)
            flag, pos = False, tb.start
    out["levels"] = levels
    out["on_exploit"] = on_exploit
    return out
