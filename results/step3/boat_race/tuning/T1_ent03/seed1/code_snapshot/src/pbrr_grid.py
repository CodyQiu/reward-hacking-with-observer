"""PBRR on the Step 1 audit grid: transition features, trajectories, sub-episode
rollouts, and the reference policy.

Reward-model input (the paper's code: [obs, next_obs, one-hot action]). The
"observation" given to g is the base-MDP state -- the agent's position, one-hot
over 225 cells -- not the agent's augmented observation (clock, correction count,
audit flag). The reward being repaired is defined on (s, a, s') of the base MDP;
the clock and the correction count are the overseer's bookkeeping. With
deterministic transitions s' = next(s, a), so the 1,125 (s, a) pairs are the whole
transition set and g is a table over them once fitted.

Reference policy (paper App. B / K.8: "trained with a handful of human
demonstrations or from imperfect hand-written rules"; behaviour cloning on a few
demonstrations is the paper's recipe for three of its four environments). Here: a
hand-written rule -- go right along row 0 to the last column, then down to GOAL --
executed with action noise to give a handful of imperfect demonstrations, then
cloned by an MLP on the one-hot position. The cloned policy is sampled
stochastically. Its quality is reported, not assumed: what matters (K.8) is its
coverage relative to the exploiting policy, and -- in this environment -- whether
it reaches GOAL, because an exploiter and a reference that both fail to reach
GOAL tie at -100 under the true reward and get a coin-flip Boltzmann label.
"""

import jax
import jax.numpy as jnp
import numpy as np
import optax

from .audit_grid import ACTIONS, BASE, build_tables
from .pbrr_core import Traj

__all__ = [
    "N_A",
    "transition_features",
    "make_traj",
    "rollout_subepisode",
    "hand_rule_action",
    "make_demonstrations",
    "BCPolicy",
    "train_bc_reference",
    "random_init_reference",
    "dp_policy_fn",
]

N_A = len(ACTIONS)
STAY, UP, DOWN, LEFT, RIGHT = range(N_A)


def transition_features(cfg=BASE):
    """(n_pos * A, 2 * n_pos + A) features [one-hot s, one-hot s', one-hot a];
    row index = s * A + a."""
    tb = build_tables(cfg)
    n = cfg.n_pos
    X = np.zeros((n * N_A, 2 * n + N_A), np.float32)
    for s in range(n):
        for a in range(N_A):
            r = s * N_A + a
            X[r, s] = 1.0
            X[r, n + tb.next_pos[s, a]] = 1.0
            X[r, 2 * n + a] = 1.0
    return X


def make_traj(positions, actions, cfg=BASE, tables=None, **meta):
    """Trajectory from the positions each action was taken in. Returns are scored
    under the ORIGINAL proxy (PBRR repairs, it does not patch) and the true reward."""
    tb = tables or build_tables(cfg)
    p = np.asarray(positions, int)
    a = np.asarray(actions, int)
    counts = np.bincount(p * N_A + a, minlength=cfg.n_pos * N_A).astype(float)
    return Traj(counts, float(tb.reward[p, a, 0].sum()), float(tb.true[p, a].sum()),
                len(p), dict(meta))


def rollout_subepisode(policy_fn, n, rng, cfg=BASE, tables=None, t0=0):
    """``n`` independent rollouts of one sub-episode (t_sub steps from START).

    ``policy_fn(t, pos, flagged) -> (n, A)`` action probabilities for a batch.
    ``flagged`` is the audit flag the agent observes (bonus collected in the window
    of this sub-episode); it is tracked here under the original proxy's bonus.
    Returns (positions (n, T), actions (n, T)).
    """
    tb = tables or build_tables(cfg)
    T = cfg.t_sub
    pos = np.full(n, tb.start, int)
    flagged = np.zeros(n, bool)
    P = np.zeros((n, T), int)
    Acts = np.zeros((n, T), int)
    for tau in range(T):
        t = t0 + tau
        probs = np.asarray(policy_fn(t, pos, flagged), float)
        cum = probs.cumsum(axis=1)
        a = (rng.random((n, 1)) < cum / cum[:, -1:]).argmax(axis=1)
        P[:, tau], Acts[:, tau] = pos, a
        if cfg.in_window(t):
            flagged |= tb.bonus[pos, a, 0]
        pos = tb.next_pos[pos, a]
    return P, Acts


def dp_policy_fn(policy, patched=0):
    """Wrap an ``audit_dp.solve`` policy table (t, pos, patched, flagged) as policy_fn."""
    def fn(t, pos, flagged):
        acts = policy[t, pos, patched, flagged.astype(int)]
        return np.eye(N_A)[acts]
    return fn


# ---------------------------------------------------------------------------------
# Reference policy: behaviour cloning on a handful of imperfect demonstrations
# ---------------------------------------------------------------------------------


def hand_rule_action(pos, cfg=BASE):
    """Hand-written rule: right along the row until the last column, then down."""
    r, c = divmod(int(pos), cfg.n)
    if (r, c) == cfg.goal:
        return STAY
    return RIGHT if c < cfg.n - 1 else DOWN


def make_demonstrations(n_demos=5, noise=0.1, seed=0, cfg=BASE):
    """``n_demos`` executions of the hand rule from START, each step replaced by a
    uniformly random action with probability ``noise``, until GOAL or t_sub steps."""
    tb = build_tables(cfg)
    rng = np.random.default_rng(seed)
    demos = []
    for _ in range(n_demos):
        pos, states, acts = tb.start, [], []
        for _ in range(cfg.t_sub):
            if pos == tb.goal:
                break
            a = hand_rule_action(pos, cfg)
            if rng.random() < noise:
                a = int(rng.integers(N_A))
            states.append(pos)
            acts.append(a)
            pos = int(tb.next_pos[pos, a])
        demos.append((np.array(states), np.array(acts)))
    return demos


class BCPolicy:
    """MLP on one-hot position -> softmax over actions; sampled stochastically."""

    def __init__(self, params, cfg=BASE):
        self.params, self.cfg = params, cfg
        eye = jnp.eye(cfg.n_pos, dtype=jnp.float32)
        self.table = np.asarray(jax.nn.softmax(_bc_logits(params, eye), axis=-1), float)

    def __call__(self, t, pos, flagged=None):
        return self.table[np.asarray(pos, int)]


def _bc_logits(params, x):
    for W, b in params[:-1]:
        x = jnp.tanh(x @ W + b)
    W, b = params[-1]
    return x @ W + b


def _bc_init(key, sizes):
    ps = []
    for fi, fo in zip(sizes[:-1], sizes[1:]):
        key, kw = jax.random.split(key)
        lim = 1.0 / np.sqrt(fi)
        ps.append((jax.random.uniform(kw, (fi, fo), minval=-lim, maxval=lim), jnp.zeros(fo)))
    return ps


def train_bc_reference(n_demos=5, noise=0.1, seed=0, hidden=(64, 64), steps=500, lr=1e-3,
                       cfg=BASE):
    """Behaviour cloning (cross-entropy on demonstrated (state, action) pairs)."""
    demos = make_demonstrations(n_demos, noise, seed, cfg)
    S = np.concatenate([s for s, _ in demos])
    A = np.concatenate([a for _, a in demos])
    X = jnp.asarray(np.eye(cfg.n_pos, dtype=np.float32)[S])
    Y = jnp.asarray(A)
    params = _bc_init(jax.random.PRNGKey(seed), [cfg.n_pos, *hidden, N_A])
    tx = optax.adam(lr)

    def loss(p):
        logits = _bc_logits(p, X)
        return jnp.mean(optax.softmax_cross_entropy_with_integer_labels(logits, Y))

    @jax.jit
    def run(p):
        st = tx.init(p)

        def body(_, c):
            p, st = c
            upd, st = tx.update(jax.grad(loss)(p), st, p)
            return optax.apply_updates(p, upd), st

        return jax.lax.fori_loop(0, steps, body, (p, st))[0]

    params = run(params)
    return BCPolicy(params, cfg), {"n_demos": n_demos, "noise": noise, "n_pairs": len(S),
                                   "bc_loss": float(loss(params))}


def random_init_reference(seed=0, hidden=(64, 64), cfg=BASE):
    """K.8 ablation: an untrained, randomly initialised policy network."""
    params = _bc_init(jax.random.PRNGKey(seed), [cfg.n_pos, *hidden, N_A])
    return BCPolicy(params, cfg)
