"""Exact DP for tabular Step 3 tasks: the idealised Step 2 model on any finite MDP.

Generalises ``src/step2_dp.py`` (deterministic grid, one start state) to stochastic
transitions and a start distribution. The state is (s, c, f): base state, the
correction level c (c = 0 is the original proxy; R_levels[c] is the received reward
after c corrections) and the audit flag f. A step flags the copy iff it is in the
audit window and exploits (proxy != true on that transition). At a boundary a
flagged copy is detected with probability p and moves to level c + 1 from the next
sub-episode; the base state is redrawn from mu0. The last audit never corrects.
gamma = 1.

``solve_levels`` returns V at t = 0 and the optimal policy (t, s, c, f);
``evaluate_levels`` propagates the exact state distribution of a deterministic
policy and returns per-sub-episode expected received / proxy / true returns, the
per-step probability of exploiting, and the probability that each audit window is
exploited. ``solve_subepisode`` is the single-sub-episode optimum of a fixed reward
(no audit), used for "the policy optimal for the current repaired reward".
"""

import numpy as np

__all__ = ["solve_levels", "evaluate_levels", "solve_subepisode", "table_policy_fn", "refs_from_eval"]


def _q(tb, R, cont):
    """Q[s, a, ...] = sum_j prob[r, j] (R[r, j] + cont[r, j, ...]). R (SA, F)."""
    S, A = tb.n_states, tb.n_actions
    extra = cont.shape[2:]
    q = np.einsum("rj,rj...->r...", tb.prob, R.reshape(R.shape + (1,) * len(extra)) + cont)
    return q.reshape((S, A) + extra)


def solve_levels(tb, proto, R_levels, keep_values=False):
    """R_levels (L, S*A, F). Returns (V0 (S, L, 2), policy (t_ep, S, L, 2) int8, [V])."""
    R = np.asarray(R_levels, float)
    L = R.shape[0]
    S = tb.n_states
    ex = tb.exploit
    up = np.minimum(np.arange(L) + 1, L - 1)
    p = proto.p_detect
    V = np.zeros((S, L, 2))
    policy = np.zeros((proto.t_ep, S, L, 2), np.int8)
    Vs = [V] if keep_values else None
    for t in range(proto.t_ep - 1, -1, -1):
        tau = t % proto.t_sub
        fl = ex & bool(proto.in_window(t))                       # (SA, F) flags this step
        if tau < proto.t_sub - 1:
            Vn = V[tb.nxt]                                       # (SA, F, L, 2)
            c0 = np.where(fl[..., None], Vn[..., 1], Vn[..., 0])
            cont = np.stack([c0, Vn[..., 1]], axis=-1)
        elif t == proto.t_ep - 1:
            cont = np.zeros(tb.nxt.shape + (L, 2))
        else:
            v_clean = tb.mu0 @ V[:, :, 0]                        # (L,)
            v_hit = p * v_clean[up] + (1 - p) * v_clean
            c0 = np.where(fl[..., None], v_hit[None, None, :], v_clean[None, None, :])
            cont = np.stack([c0, np.broadcast_to(v_hit, c0.shape)], axis=-1)
        Q = np.stack([_q(tb, R[c], cont[:, :, c, :]) for c in range(L)], axis=2)   # (S, A, L, 2)
        policy[t] = Q.argmax(axis=1)
        V = Q.max(axis=1)
        if keep_values:
            Vs.append(V)
    if keep_values:
        return V, policy, Vs[::-1]
    return V, policy


def evaluate_levels(tb, proto, R_levels, policy):
    """Exact forward evaluation of a deterministic ``policy`` (t, S, L, 2)."""
    R = np.asarray(R_levels, float)
    L = R.shape[0]
    S, A, F = tb.n_states, tb.n_actions, tb.nxt.shape[1]
    K, T = proto.n_sub, proto.t_sub
    ex = tb.exploit
    d = np.zeros((S, L, 2))
    d[:, 0, 0] = tb.mu0
    out = {k: np.zeros(K) for k in ("received", "proxy", "true", "window", "corrected")}
    out["exploit_t"] = np.zeros(proto.t_ep)
    out["level_dist"] = np.zeros((K, L))
    sidx = np.arange(S)[:, None, None]
    lidx = np.broadcast_to(np.arange(L)[None, :, None], (S, L, 2))
    fidx = np.broadcast_to(np.arange(2)[None, None, :].astype(bool), (S, L, 2))
    for t in range(proto.t_ep):
        k, tau = divmod(t, T)
        if tau == 0:
            out["level_dist"][k] = d.sum(axis=(0, 2))
        r = sidx * A + policy[t].astype(np.int64)                  # (S, L, 2)
        pr = tb.prob[r]                                            # (S, L, 2, F)
        m = d[..., None] * pr
        Rl = R[lidx, r]                                            # (S, L, 2, F)
        out["received"][k] += (m * Rl).sum()
        out["proxy"][k] += (m * tb.proxy[r]).sum()
        out["true"][k] += (m * tb.true[r]).sum()
        e = ex[r]
        out["exploit_t"][t] = (m * e).sum()
        f2 = fidx[..., None] | (e & bool(proto.in_window(t)))
        nd = np.zeros((S, L, 2))
        if tau < T - 1:
            flat = (tb.nxt[r] * L + lidx[..., None]) * 2 + f2.astype(np.int64)
            nd = np.bincount(flat.ravel(), weights=m.ravel(), minlength=S * L * 2).reshape(S, L, 2)
        else:
            mf = np.stack([(m * ~f2).sum(axis=(0, 2, 3)), (m * f2).sum(axis=(0, 2, 3))], axis=-1)  # (L, 2)
            out["window"][k] = mf[:, 1].sum()
            if t < proto.t_ep - 1:
                p = proto.p_detect
                lv = np.zeros(L)
                lv += mf[:, 0] + (1 - p) * mf[:, 1]
                np.add.at(lv, np.minimum(np.arange(L) + 1, L - 1), p * mf[:, 1])
                out["corrected"][k] = p * mf[:, 1].sum()
                nd[:, :, 0] = tb.mu0[:, None] * lv[None, :]
        d = nd
    return out


def solve_subepisode(tb, R, T):
    """Finite-horizon optimum of one sub-episode under reward R (S*A, F), no audit.
    Returns policy (T, S)."""
    V = np.zeros(tb.n_states)
    pol = np.zeros((T, tb.n_states), np.int64)
    for tau in range(T - 1, -1, -1):
        Q = _q(tb, R, V[tb.nxt])
        pol[tau] = Q.argmax(axis=1)
        V = Q.max(axis=1)
    return pol


def table_policy_fn(pol, n_actions, eps=0.0):
    """A ``policy_fn`` for ``pbrr.rollouts`` from a policy table on state indices:
    (T, S) for a single sub-episode, or (t_ep, S, L, 2) from ``solve_levels``. With
    probability ``eps`` the action is uniform (the "soft" policies of Phase A)."""
    pol = np.asarray(pol)

    def fn(batch, t, n_corr, flagged):
        s = batch.s
        if pol.ndim == 2:
            a = pol[t % pol.shape[0], s]
        else:
            a = pol[t, s, np.minimum(n_corr, pol.shape[2] - 1), np.asarray(flagged, np.int64)]
        p = np.full((len(s), n_actions), eps / n_actions)
        p[np.arange(len(s)), a] += 1.0 - eps
        return p
    return fn


def refs_from_eval(ev, proto):
    """The numbers the success criteria are relative to, from ``evaluate_levels`` of
    the idealised optimum: its off-window exploit-step rate in sub-episodes 0..K-2
    and its proxy return per sub-episode 0..K-2."""
    K, T, W = proto.n_sub, proto.t_sub, proto.window
    ex = np.asarray(ev["exploit_t"]).reshape(K, T)
    return {"offwindow_rate": float(ex[:K - 1, :T - W].mean()),
            "proxy_0_3": float(np.mean(ev["proxy"][:K - 1])),
            "proxy_by_k": [float(x) for x in ev["proxy"]], "true_by_k": [float(x) for x in ev["true"]],
            "window_by_k": [float(x) for x in ev["window"]]}
