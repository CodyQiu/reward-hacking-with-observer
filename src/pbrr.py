"""PBRR: the preference-learning objective and the fit of the correction term g.

Implements Preference-Based Reward Repair from

    Hatgis-Kessell, Bhamidipaty & Brunskill, "Repairing Reward Functions with
    Feedback to Mitigate Reward Hacking", arXiv:2510.13036v2.
    Reference code: github.com/StanfordAI4HI/PBRR-ICLR

The repaired reward is additive and transition-dependent, and does NOT compound --
every iteration refits g against the *original* proxy (their Eq 2):

    r_hat_{t+1}(s,a,s') = r_proxy(s,a,s') + g_t(s,a,s')

Given preference data D = {(tau_1, tau_2, mu)} with mu in {0, 1, 1/2} (0 means
tau_1 is preferred, 1/2 means indifferent), D is partitioned by whether the
*proxy* already ranks the pair the way the labeller did:

    D+ = { (t1,t2,mu) : sign(R_proxy(t2) - R_proxy(t1)) == sign(mu - 0.5) }
    D- = D \\ D+

and g minimises (their Eq 3)

    L(g) = L_pref(r_proxy + g; D)  +  lambda * [ L+ + L- ]

    L+  regularises g toward zero on BOTH trajectories of an agreeing pair, so a
        reward signal that was already right does not get degraded.
    L-  regularises g toward zero on the PREFERRED trajectory only of a
        disagreeing pair. Fixing a misranked pair is underspecified -- raise the
        good or lower the bad -- and penalising only the good one forces "lower
        the bad", which is what makes the learned correction a negative, localised
        penalty on the hacking behaviour rather than an arbitrary separator.

THREE PLACES WHERE THE PRINTED Eq 3 AND THE RELEASED CODE DISAGREE. The code is
what produced the paper's numbers, so ``variant="code"`` (the default) follows it
and ``variant="paper"`` follows the printed equation:

1. Regulariser target. Eq 3 writes g(tau)^2, the square of the summed correction.
   The code applies ``F.mse_loss`` to the per-timestep outputs, i.e. the *mean of
   squared per-transition* corrections -- and the paper's own prose says
   "regularizing the correction term g to zero on transitions in the preferred
   trajectories". Per-transition is used here.
2. Normalisation. Eq 3 divides L+ by |D+| and L- by |D-|. The code accumulates
   both into one running total and divides the whole thing by |D+| only
   (``batch_reg_loss / batch_agreements``).
3. lambda. Appendix E.6 states lambda_1 = lambda_2 = 10/|D+|, which combined with
   Eq 3's own 1/|D+| would give 10/|D+|^2. The code multiplies once by
   ``push2zero = 10``. Net coefficient 10/|D+|, which is the decay E.6 describes:
   as the proxy gets repaired more pairs agree, |D+| grows, the regulariser fades.

Also from the code: if there are no agreeing pairs at all, the regulariser is
skipped entirely (``if batch_agreements > 0``). That is reproduced.

Ties (mu = 1/2) occur for real in our environment -- under the true reward,
dwelling k steps on the bonus tile and dawdling k steps anywhere else both score
2-k -- so they are handled explicitly rather than left to fall through a branch:
by default a tie contributes to L_pref only and is excluded from the regulariser
(``tie_handling="pref_only"``). The reference code's if/else would silently route a
tie into the disagree branch and penalise tau_2; that is available as
``tie_handling="code"``.
"""

import numpy as np

from .waypoint_env import (
    ACTIONS,
    CELL_INDEX,
    FREE_CELLS,
    N_FREE,
    WAYPOINT,
    move,
    r_proxy,
    r_true,
)

__all__ = [
    "N_ACTIONS",
    "N_TRANSITIONS",
    "transition_index",
    "TRANSITION_TRIPLES",
    "Trajectory",
    "make_trajectory",
    "g_return",
    "count_vector",
    "ideal_g",
    "partition_pairs",
    "Design",
    "build_design",
    "design_loss_and_grad",
    "loss_and_grad",
    "fit_g",
    "PUSH2ZERO",
]

N_ACTIONS = len(ACTIONS)
N_TRANSITIONS = N_FREE * N_ACTIONS      # 105 reachable (s,a,s') triples
PUSH2ZERO = 10.0                        # the paper's lambda_1 = lambda_2 numerator


def transition_index(pos, action):
    """Flat index of the transition (s, a, s') taken by doing ``action`` at ``pos``.

    g is indexed by the transition, as in the paper. Note the degeneracy: our
    dynamics are deterministic, so s' = move(s,a) and only N_FREE * N_ACTIONS of
    the N_FREE * N_ACTIONS * N_FREE conceivable triples are reachable. g(s,a,s') is
    therefore transition-dependent in notation and state-action-dependent in
    substance. The paper needs a neural net because its domains are
    high-dimensional; a table of 105 entries is the exact analogue here.
    """
    return CELL_INDEX[pos] * N_ACTIONS + int(action)


# (s, a, s') for every flat index, for diagnostics and for the EPIC computation.
TRANSITION_TRIPLES = [
    (cell, a, move(cell, a)) for cell in FREE_CELLS for a in range(N_ACTIONS)
]


class Trajectory:
    """A rollout, reduced to what the PBRR objective needs.

    ``g_idx`` is the per-timestep flat transition index, so the correction's
    contribution to the return is just ``g[g_idx].sum()``. ``counts`` is the same
    thing as a visitation vector, cached because the design matrices below are
    built out of it.
    """

    __slots__ = (
        "g_idx", "proxy_return", "true_return", "length", "states", "actions",
        "n_transitions", "_counts",
    )

    def __init__(
        self, states, actions, proxy_return, true_return, g_idx=None,
        n_transitions=N_TRANSITIONS,
    ):
        self.states = states
        self.actions = actions
        # g_idx may be supplied directly so that the objective below can be used on
        # any tabular MDP -- e.g. the paper's minimal MDPs of Appendix H, which have
        # their own transition index space.
        self.g_idx = (
            np.array([transition_index(p, a) for p, a in zip(states, actions)], dtype=int)
            if g_idx is None
            else np.asarray(g_idx, dtype=int)
        )
        self.proxy_return = float(proxy_return)
        self.true_return = float(true_return)
        self.length = len(self.g_idx)
        self.n_transitions = int(n_transitions)
        self._counts = None

    @property
    def counts(self):
        if self._counts is None:
            n = np.zeros(self.n_transitions)
            np.add.at(n, self.g_idx, 1.0)
            self._counts = n
        return self._counts

    def __repr__(self):
        return (
            f"Trajectory(len={self.length}, proxy={self.proxy_return:+.2f}, "
            f"true={self.true_return:+.2f})"
        )


def make_trajectory(states, actions, bonus=2.0):
    """Build a Trajectory from a (positions, actions) rollout, scoring both rewards.

    ``states[i]`` is the position from which ``actions[i]`` was taken. Rewards are
    evaluated with the bonus live (patched=False): PBRR never patches the proxy, it
    repairs it.
    """
    proxy = sum(r_proxy(p, a, False, bonus) for p, a in zip(states, actions))
    true = sum(r_true(p, a) for p, a in zip(states, actions))
    return Trajectory(states, actions, proxy, true)


def g_return(g, traj):
    """The correction's contribution to a trajectory's return, sum_t g(s,a,s')."""
    return float(np.asarray(g)[traj.g_idx].sum())


def count_vector(traj):
    """Transition visitation counts, length N_TRANSITIONS."""
    n = np.zeros(N_TRANSITIONS)
    np.add.at(n, traj.g_idx, 1.0)
    return n


def ideal_g(bonus=2.0):
    """The analytic minimal repair: -bonus on every transition out of the waypoint.

    With this g, r_proxy + g == r_true identically, so it is the exact anchor the
    learned g can be compared against. Its existence is also why "the repaired
    reward need not equal the true reward" needs a *learned* g to demonstrate.
    """
    g = np.zeros(N_TRANSITIONS)
    for a in range(N_ACTIONS):
        g[transition_index(WAYPOINT, a)] = -float(bonus)
    return g


# --------------------------------------------------------------------------- #
# D+ / D- partition
# --------------------------------------------------------------------------- #

def partition_pairs(pairs, trajs):
    """Split pairs into (agree, disagree) index lists.

    A pair agrees when the proxy's higher-return trajectory is the preferred one.
    Ties (mu = 1/2) can never agree: the proxy assigns them different returns in
    general, so there is no ranking to match.
    """
    agree, disagree = [], []
    for k, (i, j, mu) in enumerate(pairs):
        if mu == 0.5:
            disagree.append(k)
            continue
        proxy_sign = np.sign(trajs[j].proxy_return - trajs[i].proxy_return)
        if proxy_sign == np.sign(mu - 0.5):
            agree.append(k)
        else:
            disagree.append(k)
    return agree, disagree


# --------------------------------------------------------------------------- #
# objective
# --------------------------------------------------------------------------- #

def _reg_targets(pairs, agree_idx, disagree_idx, tie_handling):
    """Which trajectories each pair regularises toward zero.

    Returns a list of (trajectory index, pair kind) with kind in {"+", "-"}.
    L+ hits both trajectories of an agreeing pair; L- hits only the preferred
    trajectory of a disagreeing pair.
    """
    targets = []
    for k in agree_idx:
        i, j, _ = pairs[k]
        targets.append((i, "+"))
        targets.append((j, "+"))
    for k in disagree_idx:
        i, j, mu = pairs[k]
        if mu == 0.5:
            if tie_handling == "pref_only":
                continue                      # documented default: ties skip L-
            if tie_handling == "both":
                targets.append((i, "-"))
                targets.append((j, "-"))
                continue
            targets.append((j, "-"))          # "code": reference if/else fallthrough
        elif mu == 0:
            targets.append((i, "-"))          # tau_1 preferred -> penalise tau_1
        else:
            targets.append((j, "-"))          # tau_2 preferred -> penalise tau_2
    return targets


class Design:
    """The objective in matrix form, built once and reused across optimiser steps.

    The whole loss is a function of three precomputed pieces:

        delta = b + A @ g          A[k] = counts(tau_i) - counts(tau_j)
                                   b[k] = R_proxy(tau_i) - R_proxy(tau_j)
        y[k]  = 1 - mu_k           probability that tau_i is preferred

    and the regulariser. Under the released code's per-transition reading the
    regulariser collapses to a *diagonal* quadratic,

        reg = sum_k c[k] g[k]^2,   c = sum_targets w * counts(tau)/len(tau)

    which makes the convexity obvious and the gradient a single elementwise
    product. Under the printed Eq 3 (square of the summed correction) it is a
    general quadratic and needs the stacked count matrix ``M``.
    """

    __slots__ = ("A", "b", "y", "reg_diag", "M", "Mw", "n_agree", "n_disagree", "variant")

    def __init__(self, A, b, y, reg_diag, M, Mw, n_agree, n_disagree, variant):
        self.A, self.b, self.y = A, b, y
        self.reg_diag, self.M, self.Mw = reg_diag, M, Mw
        self.n_agree, self.n_disagree, self.variant = n_agree, n_disagree, variant


def build_design(pairs, trajs, variant="code", tie_handling="pref_only",
                 reg_terms=("+", "-")):
    """Precompute the design of the PBRR objective for a fixed preference set.

    ``reg_terms`` selects which of the two ridge terms are active, so L+ and L- can
    be ablated individually (the paper ablates them only jointly, as "Eq 1").
    """
    n = len(pairs)
    n_tr = trajs[0].n_transitions if trajs else N_TRANSITIONS
    A = np.zeros((n, n_tr))
    b = np.zeros(n)
    y = np.zeros(n)
    for k, (i, j, mu) in enumerate(pairs):
        A[k] = trajs[i].counts - trajs[j].counts
        b[k] = trajs[i].proxy_return - trajs[j].proxy_return
        y[k] = 1.0 - mu

    agree_idx, disagree_idx = partition_pairs(pairs, trajs)
    targets = [
        (t, kind)
        for t, kind in _reg_targets(pairs, agree_idx, disagree_idx, tie_handling)
        if kind in reg_terms
    ]
    n_agree, n_disagree = len(agree_idx), len(disagree_idx)

    if variant == "paper":
        weight = {"+": 1.0 / max(1, n_agree), "-": 1.0 / max(1, n_disagree)}
        M = np.zeros((len(targets), n_tr))
        Mw = np.zeros(len(targets))
        for r, (t_idx, kind) in enumerate(targets):
            M[r] = trajs[t_idx].counts
            Mw[r] = weight[kind]
        reg_diag = None
    else:
        reg_diag = np.zeros(n_tr)
        for t_idx, _kind in targets:
            traj = trajs[t_idx]
            reg_diag += traj.counts / traj.length
        M = Mw = None

    return Design(A, b, y, reg_diag, M, Mw, n_agree, n_disagree, variant)


def design_loss_and_grad(
    g, design, lam=PUSH2ZERO, use_regularization=True,
    skip_reg_when_no_agreement=False, weight_decay=0.0,
    preference_margin=0.0,
):
    """Vectorised PBRR loss and gradient from a prebuilt Design.

    ``skip_reg_when_no_agreement`` reproduces the released code's
    ``if batch_agreements > 0`` guard literally. It defaults to False, which is a
    deliberate documented deviation: with |D+| = 0 the guard leaves a completely
    unregularised logistic fit, whose minimiser drives the score difference to
    -infinity and inflates g on the *preferred* trajectory as readily as it
    decrements the dispreferred one. That contradicts the paper's own account of
    Appendix H MDP 1 ("the proxy reward function is updated so that the proxy reward
    for s1 is lower than the proxy reward for s3" -- s1 decremented, s3 left alone)
    and breaks Theorem H.1. With the default, |D+| = 0 simply normalises by 1 so L-
    is active from the very first preference, which is what the paper describes.
    Set True to see the literal-code behaviour."""
    g = np.asarray(g, dtype=float)
    n_pairs = max(1, len(design.b))

    # Plain L2 on g, on top of L+/L-. The paper's Table 2 sets "Weight Decay = True"
    # for the correction term in the AI-safety-gridworld environment, i.e. this term is
    # part of their configuration and is separate from Eq 3's two ridge terms. Without
    # it nothing bounds g on transitions the preferences do not pin down, which is how a
    # learner ends up exploiting the correction itself.
    wd_loss = weight_decay * float(g @ g)
    wd_grad = 2.0 * weight_decay * g

    delta = design.b + design.A @ g
    p = 1.0 / (1.0 + np.exp(-np.clip(delta, -500.0, 500.0)))
    eps = 1e-12
    margin = float(preference_margin)
    if margin < 0:
        raise ValueError("preference_margin must be non-negative")
    if margin:
        pref_terms = -(
            design.y * np.log(p + eps) + (1.0 - design.y) * np.log(1.0 - p + eps)
        )
        pref_deriv = p - design.y
        # Eq. 3 only asks for the right ranking. In a threshold environment, its
        # minimum-norm separator can sit arbitrarily close to flipping back. For hard
        # labels, shift the logistic loss so signed score >= margin. Ties retain BCE.
        hard = design.y != 0.5
        direction = 2.0 * design.y[hard] - 1.0
        signed = direction * delta[hard]
        pref_terms[hard] = np.logaddexp(0.0, margin - signed)
        pref_deriv[hard] = -direction / (
            1.0 + np.exp(-np.clip(margin - signed, -500.0, 500.0))
        )

        loss_pref = float(np.mean(pref_terms))
        grad = design.A.T @ (pref_deriv / n_pairs)
    else:
        # Keep the original Eq. 3 numerical path bit-for-bit when the extension is
        # disabled; several induced policies sit exactly on a tie boundary.
        loss_pref = float(
            -np.mean(
                design.y * np.log(p + eps)
                + (1.0 - design.y) * np.log(1.0 - p + eps)
            )
        )
        grad = design.A.T @ ((p - design.y) / n_pairs)

    if not use_regularization or (design.n_agree == 0 and skip_reg_when_no_agreement):
        return loss_pref + wd_loss, grad + wd_grad, {
            "pref": loss_pref, "reg": 0.0, "lam_eff": 0.0,
            "n_agree": design.n_agree, "n_disagree": design.n_disagree,
        }

    lam_eff = lam / max(1, design.n_agree)
    if design.variant == "paper":
        s = design.M @ g
        reg = float(np.sum(design.Mw * s * s))
        reg_grad = 2.0 * (design.M.T @ (design.Mw * s))
    else:
        reg = float(np.sum(design.reg_diag * g * g))
        reg_grad = 2.0 * design.reg_diag * g

    return loss_pref + lam_eff * reg + wd_loss, grad + lam_eff * reg_grad + wd_grad, {
        "pref": loss_pref, "reg": reg, "lam_eff": lam_eff,
        "n_agree": design.n_agree, "n_disagree": design.n_disagree,
    }


def loss_and_grad(
    g,
    pairs,
    trajs,
    lam=PUSH2ZERO,
    use_regularization=True,
    variant="code",
    tie_handling="pref_only",
    preference_margin=0.0,
    return_parts=False,
):
    """Reference (explicit, per-pair) PBRR objective and gradient. Convex in g.

    Kept deliberately naive and readable: ``tests/test_pbrr.py`` cross-checks the
    vectorised ``design_loss_and_grad`` against it, which is the repo's standing
    convention that two independent implementations must agree.

    ``use_regularization=False`` gives Eq 1 -- the plain cross-entropy objective,
    which is the paper's RRM baseline and the target of their §5.4 ablation.
    """
    g = np.asarray(g, dtype=float)
    grad = np.zeros_like(g)
    n_pairs = max(1, len(pairs))

    # --- preference term: mean binary cross-entropy over pairs ---------------
    loss_pref = 0.0
    for i, j, mu in pairs:
        delta = (trajs[i].proxy_return + g_return(g, trajs[i])) - (
            trajs[j].proxy_return + g_return(g, trajs[j])
        )
        p = 1.0 / (1.0 + np.exp(-np.clip(delta, -500, 500)))   # P(tau_i > tau_j)
        y = 1.0 - mu                                           # mu=0 -> y=1
        eps = 1e-12
        if preference_margin and y != 0.5:
            direction = 2.0 * y - 1.0
            signed = direction * delta
            loss_pref += float(np.logaddexp(0.0, preference_margin - signed))
            coeff = -direction / (
                1.0 + np.exp(-np.clip(preference_margin - signed, -500.0, 500.0))
            ) / n_pairs
        else:
            loss_pref += -(y * np.log(p + eps) + (1.0 - y) * np.log(1.0 - p + eps))
            coeff = (p - y) / n_pairs
        np.add.at(grad, trajs[i].g_idx, coeff)
        np.add.at(grad, trajs[j].g_idx, -coeff)
    loss_pref /= n_pairs

    if not use_regularization:
        total = loss_pref
        return (total, grad, {"pref": loss_pref, "reg": 0.0, "lam_eff": 0.0}) if return_parts else (total, grad)

    # --- the two ridge terms ------------------------------------------------
    agree_idx, disagree_idx = partition_pairs(pairs, trajs)
    n_agree = len(agree_idx)

    targets = _reg_targets(pairs, agree_idx, disagree_idx, tie_handling)

    # "code": per-transition mean square, one shared 1/|D+| normaliser.
    # "paper": square of the summed correction, 1/|D+| on L+ and 1/|D-| on L-.
    if variant == "paper":
        weight = {"+": 1.0 / n_agree, "-": 1.0 / max(1, len(disagree_idx))}
    else:
        weight = {"+": 1.0, "-": 1.0}

    reg = 0.0
    reg_grad = np.zeros_like(g)
    for t_idx, kind in targets:
        traj = trajs[t_idx]
        w = weight[kind]
        if variant == "paper":
            s = g_return(g, traj)
            reg += w * s * s
            np.add.at(reg_grad, traj.g_idx, w * 2.0 * s)
        else:
            vals = g[traj.g_idx]
            reg += w * float((vals**2).mean())
            np.add.at(reg_grad, traj.g_idx, w * 2.0 * vals / traj.length)

    lam_eff = lam / max(1, n_agree)
    total = loss_pref + lam_eff * reg
    grad += lam_eff * reg_grad

    if return_parts:
        return total, grad, {
            "pref": loss_pref,
            "reg": float(reg),
            "lam_eff": float(lam_eff),
            "n_agree": n_agree,
            "n_disagree": len(disagree_idx),
        }
    return total, grad


def fit_g(
    pairs,
    trajs,
    lam=PUSH2ZERO,
    use_regularization=True,
    variant="code",
    tie_handling="pref_only",
    reg_terms=("+", "-"),
    lr=0.05,
    max_iter=6000,
    tol=1e-7,
    seed=0,
    init=None,
    skip_reg_when_no_agreement=False,
    weight_decay=0.0,
    preference_margin=0.0,
    solver="lbfgs",
):
    """Fit g by Adam on the convex objective. Returns (g, info).

    The objective is convex in g (cross-entropy of a linear score, plus a positive
    semi-definite quadratic), so the optimum is unique up to directions the data
    does not constrain, and the gradient norm at the solution is the convergence
    certificate that ``info`` reports.
    """
    rng = np.random.default_rng(seed)
    n_tr = trajs[0].n_transitions if trajs else N_TRANSITIONS
    g = np.zeros(n_tr) if init is None else np.array(init, dtype=float)
    if init is None:
        g += 1e-6 * rng.standard_normal(n_tr)

    design = build_design(pairs, trajs, variant, tie_handling, reg_terms)

    if solver == "lbfgs":
        # The objective is convex, so a quasi-Newton method reaches a far tighter
        # optimum than a fixed Adam budget and does it in ~100 rather than ~6000
        # gradient evaluations. Under-converged fits are a plausible source of
        # round-to-round oscillation in the repair loop, so this matters for more than
        # speed.
        from scipy.optimize import minimize

        def fun(z):
            loss, grad, _ = design_loss_and_grad(
                z, design, lam, use_regularization, skip_reg_when_no_agreement,
                weight_decay, preference_margin,
            )
            return float(loss), np.asarray(grad, dtype=float)

        res = minimize(fun, g, jac=True, method="L-BFGS-B",
                       options=dict(maxiter=20_000, ftol=1e-14, gtol=1e-12))
        g = res.x
        loss, grad, parts = design_loss_and_grad(
            g, design, lam, use_regularization, skip_reg_when_no_agreement,
            weight_decay, preference_margin,
        )
        return g, {
            "loss": float(loss), "grad_norm": float(np.max(np.abs(grad))),
            "n_iter": int(res.nit), "converged": bool(np.max(np.abs(grad)) < 1e-6),
            **parts,
        }

    m = np.zeros_like(g)
    v = np.zeros_like(g)
    b1, b2, eps = 0.9, 0.999, 1e-8
    step = 0
    for step in range(1, max_iter + 1):
        _loss, grad, _parts = design_loss_and_grad(
            g, design, lam, use_regularization, skip_reg_when_no_agreement,
            weight_decay, preference_margin,
        )
        if float(np.max(np.abs(grad))) < tol:
            break
        m = b1 * m + (1 - b1) * grad
        v = b2 * v + (1 - b2) * grad**2
        g = g - lr * (m / (1 - b1**step)) / (np.sqrt(v / (1 - b2**step)) + eps)

    loss, grad, parts = design_loss_and_grad(
        g, design, lam, use_regularization, skip_reg_when_no_agreement,
        weight_decay, preference_margin,
    )
    info = {
        "loss": float(loss),
        "grad_norm": float(np.max(np.abs(grad))),
        "n_iter": step,
        "converged": bool(np.max(np.abs(grad)) < 1e-4),
        **parts,
    }
    return g, info
