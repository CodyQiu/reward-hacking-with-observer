"""The outcome audit (docs/step4_goal.md): a goal per round, a hidden state, and the "still learning" exemption.

The user's design (2026-11-25, as stated): "correction occurs at the end of each sub episode, and it's based off the
agent's performance i.e. whether or not goal has been reached". "Assuming goal isn't reached: if r_proxy(current
policy) < r_proxy(reference) then we don't update the reward function, as it is very clear that the policy has not
been optimized yet and is still learning. otherwise, we update the proxy via corrections" -- compared on "the current
round's trajectory on the current in-force [reward] compared to a reference trajectory". And "there should be a state
where it's hiding and even if the goal isn't met its reward function isn't updated": in it the round "looks like
progress toward the goal".

So at the end of every round a copy is corrected iff
    the goal is not met  and  it does not end the round in the hidden state  and
    its return under the reward in force >= the reference's (Protocol.learn_exempt; src/step3/protocol.py).

``with_goal`` builds this onto any tabular task:
- **A progress counter** in the state (laps, deliveries, steps taken), capped, starting at 0 every round (the state is
  redrawn from mu0 at each round). The goal and the hidden state are predicates of the round's final state.
- **The audit flag** of the round's last transition = not goal and not hidden at its successor
  (``TabularTables.flag_table``), with the protocol's window = 1: exactly "judged on the final state", so the exact DP
  (src/step3/dp.py) needs nothing new.
- **The learning exemption** depends on the round's whole return, which the exact DP does not carry in its state. It
  is applied in training (AuditedVecEnv). The exact targets solve the game without it and record, per correction level,
  whether it could change the optimum (``exemption_check``): it cannot when the best uncorrected round and the best
  corrected round are both worth at least the reference's return under that reward (an uncorrected round below the
  bar is then dominated by the best uncorrected round, and the best corrected round clears the bar).
- Features: the policy sees the base features plus a one-hot of the counter; the reward model g and the reference see
  the base features only, so PBRR and the reference are those of the base task.
"""

import numpy as np

from .task import TabularTables, TabularTask

__all__ = ["with_goal", "oracle_refs", "goal_rate", "exemption_check", "ref_table_value"]


def with_goal(task, name, inc, cap, goal_fn, hidden_fn):
    """``task`` (a TabularTask) with a per-round counter n in 0..cap.

    inc: (S*A, F) int, how much a transition adds to n (capped at ``cap``).
    goal_fn(base_states, n) -> bool and hidden_fn(base_states) -> bool, both on the round's final state.
    The augmented state is s * (cap + 1) + n."""
    tb, N = task.tables, int(cap) + 1
    S, A, F = tb.n_states, tb.n_actions, tb.nxt.shape[1]
    s2 = np.arange(S * N)
    base, n = s2 // N, s2 % N
    rows2 = (s2[:, None] * A + np.arange(A)).reshape(-1)               # augmented rows, in order
    brows = (base[:, None] * A + np.arange(A)).reshape(-1)             # their base rows
    nrow = np.repeat(n, A)
    inc = np.asarray(inc, np.int64).reshape(S * A, F)
    nxt = tb.nxt[brows] * N + np.minimum(nrow[:, None] + inc[brows], cap)
    assert np.array_equal(rows2, np.arange(S * N * A))
    nb, nn = nxt // N, nxt % N
    flag = ~np.asarray(goal_fn(nb, nn), bool) & ~np.asarray(hidden_fn(nb), bool)
    mu0 = np.zeros(S * N)
    mu0[np.arange(S) * N] = tb.mu0
    eyeN = np.eye(N, dtype=np.float32)
    phi_obs = tb.phi_obs[base] if N == 1 else np.concatenate([tb.phi_obs[base], eyeN[n]], axis=1)
    phi_ref = (tb.phi_obs if tb.phi_ref is None else tb.phi_ref)[base]
    tables = TabularTables(nxt=nxt, prob=tb.prob[brows], proxy=tb.proxy[brows], true=tb.true[brows], mu0=mu0,
                           phi_obs=phi_obs.astype(np.float32), phi_g=tb.phi_g[base], absorbing=tb.absorbing[base],
                           n_actions=A, phi_ref=phi_ref.astype(np.float32), flag_table=flag)
    rule = task.rule_fn
    out = TabularTask(name, tables, (lambda s: rule(np.asarray(s) // N)) if rule is not None else None)
    out.base, out.cap, out.n_counter = task, int(cap), N
    out.goal_fn, out.hidden_fn = goal_fn, hidden_fn
    return out


def _final_dist(tb, pol, T):
    """State distribution after T steps of a (T, S) policy from mu0."""
    d = tb.mu0.copy()
    for tau in range(T):
        r = np.arange(tb.n_states) * tb.n_actions + pol[tau]
        m = d[:, None] * tb.prob[r]
        d = np.bincount(tb.nxt[r].ravel(), weights=m.ravel(), minlength=tb.n_states)
    return d


def goal_rate(task, pol, T):
    """P(goal met), P(hidden), P(flagged) at the end of one round of a (T, S) policy on a ``with_goal`` task."""
    d = _final_dist(task.tables, pol, T)
    s = np.arange(task.tables.n_states)
    b, n = s // task.n_counter, s % task.n_counter
    g, h = np.asarray(task.goal_fn(b, n), bool), np.asarray(task.hidden_fn(b), bool)
    return {"goal": float(d[g].sum()), "hidden": float(d[h & ~g].sum()), "flagged": float(d[~g & ~h].sum())}


def ref_table_value(task, ref_trajs, R):
    """Mean return of the reference rollouts under a reward table R (S*A, F): the learning exemption's bar."""
    tb, A = task.tables, task.tables.n_actions
    tot = []
    for tr in ref_trajs:
        s, a, s2 = task.decode(tr.keys)
        row = s * A + a
        j = np.argmax(tb.nxt[row] == s2[:, None], axis=1)
        tot.append(float(np.asarray(R, float)[row, j].sum()))
    return float(np.mean(tot))


def exemption_check(theta, best_uncaught, best_caught):
    """Can the learning exemption (a flagged round below the bar ``theta`` is not corrected) change the optimum the
    exact DP finds without it, at one correction level? It cannot if the best uncorrected round (goal met or hidden)
    and the best corrected round are both worth >= theta."""
    return {"theta": float(theta), "best_uncaught": float(best_uncaught), "best_caught": float(best_caught),
            "binds": bool(best_uncaught < theta or best_caught < theta)}


def oracle_refs(task, proto):
    """The Step 3 criteria's reference numbers: the idealised optimum under an oracle patch (the correction makes
    the reward the true reward). They feed only S1-S5, not the Step 4 verdict."""
    from .dp import evaluate_levels, refs_from_eval, solve_levels
    tb = task.tables
    R = np.stack([tb.proxy] + [tb.true] * (proto.n_sub - 1))
    _, pol = solve_levels(tb, proto, R)
    return refs_from_eval(evaluate_levels(tb, proto, R, pol), proto)
