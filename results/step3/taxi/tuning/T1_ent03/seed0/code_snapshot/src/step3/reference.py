"""The PBRR reference policy for any task: behaviour cloning on a handful of noisy
demonstrations of the task's hand-written honest rule (the paper's recipe, App. B /
K.8, and Step 2's). The rule is near-optimal for the true reward; the demonstrations
are imperfect (each action replaced by a uniform one with probability ``noise``);
the clone is sampled stochastically. Its quality is measured, not assumed
(``reference_quality``), against a uniform-random policy and the honest optimum.
"""

import jax
import jax.numpy as jnp
import numpy as np
import optax

from .pbrr import rollouts

__all__ = ["make_demonstrations", "BCPolicy", "train_bc_reference", "uniform_policy_fn",
           "rule_policy_fn", "build_reference", "reference_quality"]


def make_demonstrations(task, t_sub, n_demos=5, noise=0.1, seed=0):
    """``n_demos`` sub-episodes of the rule; steps in an absorbing state are dropped."""
    rng = np.random.default_rng(seed)
    batch = task.make_batch(n_demos, seed=seed)
    batch.reset()
    X, Y = [], []
    for _ in range(t_sub):
        alive = ~np.asarray(batch.absorbed, bool)
        a = batch.rule()
        rand = rng.random(n_demos) < noise
        a = np.where(rand, rng.integers(task.n_actions, size=n_demos), a)
        if alive.any():
            X.append(batch.obs()[alive])
            Y.append(a[alive])
        batch.step(a)
    return np.concatenate(X).astype(np.float32), np.concatenate(Y).astype(np.int32)


def _logits(params, x):
    for W, b in params[:-1]:
        x = jnp.tanh(x @ W + b)
    W, b = params[-1]
    return x @ W + b


def _init(key, sizes):
    ps = []
    for fi, fo in zip(sizes[:-1], sizes[1:]):
        key, kw = jax.random.split(key)
        lim = 1.0 / np.sqrt(fi)
        ps.append((jax.random.uniform(kw, (fi, fo), minval=-lim, maxval=lim), jnp.zeros(fo)))
    return ps


_logits_jit = jax.jit(_logits)


class BCPolicy:
    """MLP on the base observation -> softmax over actions. Tabular tasks get an exact
    table over states (one forward pass), continuous ones are evaluated per call."""

    def __init__(self, params, task):
        self.params, self.task = params, task
        self.table = None
        if getattr(task, "tabular", False):
            obs = jnp.asarray(task.tables.phi_obs)
            self.table = np.asarray(jax.nn.softmax(_logits_jit(params, obs), axis=-1), float)

    def probs(self, batch):
        if self.table is not None:
            return self.table[batch.s]
        return np.asarray(jax.nn.softmax(_logits_jit(self.params, jnp.asarray(batch.obs())), axis=-1), float)

    def __call__(self, batch, t, n_corr, flagged):
        return self.probs(batch)


def train_bc_reference(task, t_sub, n_demos=5, noise=0.1, seed=0, hidden=(64, 64), steps=500, lr=1e-3):
    X, Y = make_demonstrations(task, t_sub, n_demos, noise, seed)
    params = _init(jax.random.PRNGKey(seed), [X.shape[1], *hidden, task.n_actions])
    tx = optax.adam(lr)
    Xj, Yj = jnp.asarray(X), jnp.asarray(Y)

    def loss(p):
        return jnp.mean(optax.softmax_cross_entropy_with_integer_labels(_logits(p, Xj), Yj))

    @jax.jit
    def run(p):
        st = tx.init(p)

        def body(_, c):
            p, st = c
            upd, st = tx.update(jax.grad(loss)(p), st, p)
            return optax.apply_updates(p, upd), st

        return jax.lax.fori_loop(0, steps, body, (p, st))[0]

    params = run(params)
    return BCPolicy(params, task), {"n_demos": n_demos, "noise": noise, "n_samples": len(X),
                                    "bc_loss": float(loss(params))}


def uniform_policy_fn(n_actions):
    return lambda batch, t, n_corr, flagged: np.full((batch.n, n_actions), 1.0 / n_actions)


def rule_policy_fn(n_actions, eps=0.0):
    def fn(batch, t, n_corr, flagged):
        a = batch.rule()
        p = np.full((batch.n, n_actions), eps / n_actions)
        p[np.arange(batch.n), a] += 1.0 - eps
        return p
    return fn


def build_reference(task, t_sub, settings):
    """The reference named by ``settings``: kind "bc" (default; n_demos, noise, steps,
    seed) or "rule" -- the hand-written rule itself executed with action noise
    ``noise`` (the paper's other recipe, "imperfect hand-written rules")."""
    if settings.get("kind", "bc") == "rule":
        return rule_policy_fn(task.n_actions, settings["noise"]), {"kind": "rule", "noise": settings["noise"]}
    return train_bc_reference(task, t_sub, settings["n_demos"], settings["noise"], seed=settings.get("seed", 0),
                              steps=settings.get("steps", 500))


def reference_quality(task, proto, ref, r_opt, n=2000, seed=0):
    """Mean true return of the reference and of a uniform policy over ``n`` fresh
    sub-episodes, the normalised score (R_ref - R_rand) / (R_opt - R_rand), and how
    often the reference exploits the bug at all in a sub-episode."""
    rng = np.random.default_rng(seed)
    batch = task.make_batch(n, seed=seed + 1)
    ref_r = rollouts(batch, ref, proto, rng)
    rnd_r = rollouts(batch, uniform_policy_fn(task.n_actions), proto, rng)
    R_ref = float(np.mean([r.true for r in ref_r]))
    R_rand = float(np.mean([r.true for r in rnd_r]))
    return {"R_ref": R_ref, "R_rand": R_rand, "R_opt": float(r_opt),
            "score": (R_ref - R_rand) / (r_opt - R_rand),
            "p_exploit": float(np.mean([r.exploit.any() for r in ref_r])),
            "exploit_step_rate": float(np.mean([r.exploit.mean() for r in ref_r])),
            "ref_proxy": float(np.mean([r.proxy for r in ref_r]))}
