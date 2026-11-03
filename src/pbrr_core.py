"""PBRR: the preference-learning objective (Eq 3) and the neural correction g.

Implements the reward-repair step of Preference-Based Reward Repair,
Hatgis-Kessell, Bhamidipaty & Brunskill, arXiv:2510.13036v2, following the paper
and -- where the paper leaves a detail open -- the released code
(github.com/StanfordAI4HI/PBRR-ICLR, ``reward_modeling/reward_wrapper_pbrr.py``,
``learn_reward/pbrr.py``, AI-safety-gridworld ("tomato") configuration):

* r_hat = r_proxy + g(s, a, s')                                    (Eq 2)
* g is an MLP on [obs, next_obs, one-hot action] (code), ReLU, no output squashing.
  Gridworld: 5 Linear layers of width 512 (= 4 hidden layers; the paper's
  Appendix E.1 says "5 hidden layers", the code builds 5 Linear layers).
* Every repair refits g from scratch on ALL preferences collected so far (E.2).
  The code re-initialises with PyTorch's default Linear init (``reset_parameters``),
  i.e. the output is NOT zeroed on refits; only the very first model is
  (Xavier + zero last layer, so g == 0 before any repair). Both are available.
* Adam, lr 1e-4, coupled L2 weight decay 1e-5 (Table 2 "Weight Decay = True"; the
  value 1e-5 is from the code), 200 full-batch epochs (the code uses full batch
  for the gridworld: ``use_minibatch=False``).
* Pairs are (tau1 from pi*_rhat, tau2 from pi_ref); label 1 means tau2 preferred,
  sampled from a Boltzmann model on the ground-truth return: P = sigmoid(beta *
  (R(tau2) - R(tau1))) (E.5; the code uses beta = 1). The code discounts with
  gamma = 0.99; this project fixes gamma = 1 (CLAUDE.md 2), so returns are sums.
* Loss (code, full batch):
      mean_pairs BCE( sigmoid(R_hat(tau2) - R_hat(tau1)), label )
      + push2zero * (sum_pairs reg_pair) / n_agree       [skipped if n_agree == 0]
  with reg_pair = MSE(g on tau1 transitions, 0) + MSE(g on tau2, 0) if the proxy's
  ranking agrees with the label (D+), else MSE(g on the PREFERRED trajectory, 0)
  (D-, the L- term of Eq 3). MSE is per-transition (mean over the trajectory's
  steps), which is the code's reading of Eq 3 and matches the paper's prose.
  push2zero = 10 and the 1/n_agree normalisation are Appendix E.6's
  lambda = 10 / |D+|.
* ``no_agree``: what to do when |D+| = 0, which Eq 3 / E.6 leave undefined.
  "skip" (code) drops the regulariser; "max1" normalises by max(1, |D+|) so L- is
  active from the first preference. ``experiments/step2_pbrr_check.py`` tests both.
* Step 4 variants (defaults = the paper): ``l_minus_on="dispreferred"`` moves L- onto
  the DISPREFERRED trajectory of each D- pair, so the fit repairs a ranking by raising
  the preferred trajectory instead of lowering the dispreferred one; ``l_plus=False``
  drops L+; ``g_floor`` makes g >= 0 everywhere: "softplus" fits g = softplus(MLP)
  (on the grid the fit collapses to g = 0: the exploit-side penalty drives the shared
  pre-activation negative and softplus' gradient vanishes), "clip" fits the plain MLP
  and applies max(g, 0).

Computational note (exact, not an approximation): a trajectory's correction is
sum_t g(s_t, a_t, s_t+1) = counts(tau) . g over the finite transition set, so every
optimiser step evaluates the MLP once per *distinct* transition that appears in the
data and forms all trajectory sums with a count matrix.
"""

from dataclasses import dataclass, field, replace

import jax
import jax.numpy as jnp
import numpy as np
import optax

__all__ = [
    "GConfig",
    "Traj",
    "boltzmann_label",
    "Design",
    "build_design",
    "loss_numpy",
    "fit_correction",
    "fit_correction_tabular",
    "mlp_init",
    "mlp_apply",
]


@dataclass(frozen=True)
class GConfig:
    n_layers: int = 5            # Linear layers (code); hidden layers = n_layers - 1
    width: int = 512
    lr: float = 1e-4
    weight_decay: float = 1e-5   # 0.0 = off (Table 2 "False")
    epochs: int = 200            # full-batch Adam steps
    push2zero: float = 10.0      # lambda = push2zero / |D+|   (E.6)
    no_agree: str = "skip"       # "skip" (code) | "max1"
    use_regularization: bool = True   # False = Eq 1 (plain preference loss)
    init: str = "torch_default"  # refit init: "torch_default" (code) | "zero_last"
    beta: float = 1.0            # Boltzmann label inverse temperature
    l_minus_on: str = "preferred"     # D- pairs: regularise the "preferred" (paper) | "dispreferred" one
    l_plus: bool = True               # False = drop L+ (the D+ term)
    g_floor: str = "none"             # "none" | "softplus" | "clip" (g >= 0 on every transition)
    # Step 4 level offset (applied by the overseer, not the fit): after correction k every step also pays
    # c_k = ([V_before - V_ref_after]^+ + offset_margin |V_before|) / T_sub, where V_before is the caught
    # agent rollouts' mean return under r_hat_{k-1} and V_ref_after the reference rollouts' under proxy + g_k
    offset: bool = False
    offset_margin: float = 0.02

    def with_(self, **kw):
        return replace(self, **kw)


@dataclass
class Traj:
    """A trajectory reduced to what Eq 3 needs: transition visit counts and returns."""

    counts: np.ndarray           # (n_transitions,) visit counts
    proxy: float                 # return under the ORIGINAL proxy
    true: float                  # return under the ground-truth reward
    length: int
    meta: dict = field(default_factory=dict)


def boltzmann_label(t1, t2, rng, beta=1.0):
    """1.0 if tau2 is preferred: sampled with P = sigmoid(beta * (R(t2) - R(t1)))."""
    z = np.clip(beta * (t2.true - t1.true), -500.0, 500.0)
    return float(rng.random() < 1.0 / (1.0 + np.exp(-z)))


@dataclass
class Design:
    """Eq 3 in matrix form, restricted to the transitions present in the data.

        R_hat(tau2) - R_hat(tau1) = dproxy[k] + A[k] . g[present]
        regulariser               = sum_t reg[t] * g[present_t]^2
    """

    present: np.ndarray          # (T,) indices of transitions that occur in the data
    A: np.ndarray                # (P, T) counts(tau2) - counts(tau1)
    dproxy: np.ndarray           # (P,)
    y: np.ndarray                # (P,) labels, 1 = tau2 preferred
    reg: np.ndarray              # (T,) summed per-transition regulariser weights (paper: L+ and L-)
    n_agree: int
    n_pairs: int
    reg_plus: np.ndarray = None  # (T,) L+ weights: both trajectories of D+ pairs
    reg_pref: np.ndarray = None  # (T,) L- weights on the preferred trajectory of D- pairs (paper)
    reg_disp: np.ndarray = None  # (T,) the same on the dispreferred trajectory (Step 4 swap)

    def reg_for(self, cfg):
        """Regulariser weights for ``cfg``'s choice of L- side and L+."""
        lm = {"preferred": self.reg_pref, "dispreferred": self.reg_disp}[cfg.l_minus_on]
        return lm + self.reg_plus if cfg.l_plus else lm


def build_design(pairs):
    """``pairs``: list of (tau1, tau2, label) with tau1 from pi*_rhat, tau2 from pi_ref."""
    if not pairs:
        raise ValueError("no preferences")
    n_tr = len(pairs[0][0].counts)
    used = np.zeros(n_tr, dtype=bool)
    for t1, t2, _ in pairs:
        used |= (t1.counts > 0) | (t2.counts > 0)
    present = np.flatnonzero(used)
    P = len(pairs)
    A = np.zeros((P, len(present)))
    dproxy = np.zeros(P)
    y = np.zeros(P)
    reg_plus, reg_pref, reg_disp = (np.zeros(len(present)) for _ in range(3))
    n_agree = 0
    for k, (t1, t2, lab) in enumerate(pairs):
        c1, c2 = t1.counts[present], t2.counts[present]
        A[k] = c2 - c1
        dproxy[k] = t2.proxy - t1.proxy
        y[k] = lab
        det = int(np.argmax([t1.proxy, t2.proxy]))     # code: argmax, ties -> 0
        if det == int(lab):                             # D+: the proxy already agrees
            reg_plus += c1 / t1.length + c2 / t2.length
            n_agree += 1
        else:                                           # D-: paper regularises the preferred one
            pref, disp = (t1, t2) if lab == 0 else (t2, t1)
            reg_pref += pref.counts[present] / pref.length
            reg_disp += disp.counts[present] / disp.length
    return Design(present, A, dproxy, y, reg_plus + reg_pref, n_agree, P,
                  reg_plus, reg_pref, reg_disp)


def _reg_coef(design, cfg):
    if not cfg.use_regularization:
        return 0.0
    if design.n_agree == 0:
        return 0.0 if cfg.no_agree == "skip" else cfg.push2zero
    return cfg.push2zero / design.n_agree


def loss_numpy(g_present, design, cfg):
    """The Eq 3 objective for given correction values on the present transitions
    (without weight decay, which acts on network parameters). Reference for tests."""
    d = design.dproxy + design.A @ g_present
    bce = np.mean(np.logaddexp(0.0, d) - design.y * d)
    return float(bce + _reg_coef(design, cfg) * np.sum(design.reg_for(cfg) * g_present ** 2))


# ---------------------------------------------------------------------------------
# The MLP (pure JAX, so the whole 200-step fit compiles into one XLA program)
# ---------------------------------------------------------------------------------


def mlp_init(key, sizes, init):
    """PyTorch-equivalent initialisations.

    torch_default: Linear.reset_parameters -> W, b ~ U(-1/sqrt(fan_in), 1/sqrt(fan_in)).
    zero_last:     Xavier-uniform W, zero b, and the last layer all zero (g == 0).
    """
    params = []
    n = len(sizes) - 1
    for i, (fan_in, fan_out) in enumerate(zip(sizes[:-1], sizes[1:])):
        key, kw, kb = jax.random.split(key, 3)
        if init == "torch_default":
            lim = 1.0 / np.sqrt(fan_in)
            W = jax.random.uniform(kw, (fan_in, fan_out), minval=-lim, maxval=lim)
            b = jax.random.uniform(kb, (fan_out,), minval=-lim, maxval=lim)
        elif init == "zero_last":
            lim = np.sqrt(6.0 / (fan_in + fan_out))
            W = jax.random.uniform(kw, (fan_in, fan_out), minval=-lim, maxval=lim)
            b = jnp.zeros((fan_out,))
            if i == n - 1:
                W, b = jnp.zeros_like(W), jnp.zeros_like(b)
        else:
            raise ValueError(init)
        params.append((W, b))
    return params


def mlp_apply(params, x, floor="none"):
    for W, b in params[:-1]:
        x = jax.nn.relu(x @ W + b)
    W, b = params[-1]
    out = (x @ W + b)[:, 0]
    return jax.nn.softplus(out) if floor == "softplus" else out


def _bucket(n, sizes=(64, 128, 256, 512, 1024, 2048, 4096, 8192)):
    for s in sizes:
        if n <= s:
            return s
    return int(2 ** np.ceil(np.log2(n)))


_FIT_CACHE = {}


def _compiled_fit(cfg):
    key = (cfg.lr, cfg.weight_decay, cfg.epochs, cfg.g_floor)
    if key in _FIT_CACHE:
        return _FIT_CACHE[key]
    tx = optax.chain(optax.add_decayed_weights(cfg.weight_decay), optax.adam(cfg.lr)) \
        if cfg.weight_decay > 0 else optax.adam(cfg.lr)

    def loss(params, X, A, dproxy, y, pmask, reg, coef, n_pairs):
        g = mlp_apply(params, X, cfg.g_floor)
        d = dproxy + A @ g
        bce = jnp.sum(pmask * (jnp.logaddexp(0.0, d) - y * d)) / n_pairs
        return bce + coef * jnp.sum(reg * g * g)

    grad = jax.grad(loss)

    @jax.jit
    def fit(params, X, A, dproxy, y, pmask, reg, coef, n_pairs):
        state = tx.init(params)

        def body(_, carry):
            p, s = carry
            upd, s = tx.update(grad(p, X, A, dproxy, y, pmask, reg, coef, n_pairs), s, p)
            return optax.apply_updates(p, upd), s

        p, _ = jax.lax.fori_loop(0, cfg.epochs, body, (params, state))
        return p, loss(p, X, A, dproxy, y, pmask, reg, coef, n_pairs)

    _FIT_CACHE[key] = fit
    return fit


def fit_correction(pairs, X_all, cfg=GConfig(), seed=0, init=None):
    """Refit g from scratch on ``pairs``; return (g on every transition, info).

    ``X_all``: (n_transitions, d) input features of every transition of the MDP,
    rows aligned with ``Traj.counts``. ``init`` overrides ``cfg.init`` (e.g. the
    very first, zeroed model).
    """
    design = build_design(pairs)
    T, P = len(design.present), design.n_pairs
    Tp, Pp = _bucket(T), _bucket(P)
    X = np.zeros((Tp, X_all.shape[1]), np.float32)
    X[:T] = X_all[design.present]
    A = np.zeros((Pp, Tp), np.float32)
    A[:P, :T] = design.A
    dproxy = np.zeros(Pp, np.float32)
    dproxy[:P] = design.dproxy
    y = np.zeros(Pp, np.float32)
    y[:P] = design.y
    pmask = np.zeros(Pp, np.float32)
    pmask[:P] = 1.0
    reg = np.zeros(Tp, np.float32)
    reg[:T] = design.reg_for(cfg)
    coef = np.float32(_reg_coef(design, cfg))

    sizes = [X_all.shape[1]] + [cfg.width] * (cfg.n_layers - 1) + [1]
    params = mlp_init(jax.random.PRNGKey(seed), sizes, init or cfg.init)
    params, final_loss = _compiled_fit(cfg)(
        params, X, A, dproxy, y, pmask, reg, coef, np.float32(P))
    g_all = np.asarray(mlp_apply(params, jnp.asarray(X_all, jnp.float32), cfg.g_floor), dtype=float)
    if cfg.g_floor == "clip":
        g_all = np.maximum(g_all, 0.0)
    info = {
        "loss": float(final_loss),
        "loss_eq3_check": loss_numpy(g_all[design.present], design, cfg),
        "n_pairs": P,
        "n_agree": design.n_agree,
        "n_disagree": P - design.n_agree,
        "reg_coef": float(coef),
        "n_present": T,
    }
    return g_all, info


def fit_correction_tabular(pairs, n_transitions, cfg=GConfig(), ridge=1e-3):
    """Eq 3 with a TABULAR g (Theorem H.1's assumption: uncompared transitions keep
    g = 0), solved to convergence with L-BFGS-B. ``g_floor != "none"`` becomes the
    bound g >= 0. Eq 3 alone has no minimiser whenever a transition that only the
    unregularised side of the pairs visits can move freely (the BCE keeps falling as
    the margin grows), so a small ridge on every present transition picks the
    minimal change; the network's version of this limit is its finite optimiser budget.
    Returns (g on every transition, info)."""
    from scipy.optimize import minimize

    design = build_design(pairs)
    coef = _reg_coef(design, cfg)
    w = coef * design.reg_for(cfg) + ridge
    A, dproxy, y, P = design.A, design.dproxy, design.y, design.n_pairs

    def f(g):
        d = dproxy + A @ g
        s = 1.0 / (1.0 + np.exp(-np.clip(d, -500, 500)))
        val = np.mean(np.logaddexp(0.0, d) - y * d) + np.sum(w * g * g)
        return val, A.T @ (s - y) / P + 2 * w * g

    T = len(design.present)
    bounds = [(0.0, None)] * T if cfg.g_floor != "none" else None
    res = minimize(f, np.zeros(T), jac=True, method="L-BFGS-B", bounds=bounds,
                   options={"maxiter": 20_000, "ftol": 1e-15, "gtol": 1e-10})
    g_all = np.zeros(n_transitions)
    g_all[design.present] = res.x
    info = {"loss": float(res.fun), "loss_eq3": loss_numpy(res.x, design, cfg), "converged": bool(res.success),
            "n_iter": int(res.nit), "n_pairs": P, "n_agree": design.n_agree, "reg_coef": float(coef),
            "ridge": ridge, "n_present": T}
    return g_all, info
