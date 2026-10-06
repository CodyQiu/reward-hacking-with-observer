"""EPIC distance between reward functions (Gleave et al., 2021).

Used to make the claim "the repaired reward need not equal the true reward"
quantitative: PBRR can induce the honest optimal policy with an r_proxy + g that is
a long way from r_true, and EPIC is the scale- and shaping-invariant way to say how
far.

Canonically shaped reward, with gamma = 1 to match this environment:

    C(R)(s,a,s') = R(s,a,s') + E[R(s',A,S')] - E[R(s,A,S')] - E[R(S,A,S')]

The middle two terms are a potential function h(x) = E_A[R(x, A, move(x,A))], so
canonicalisation subtracts exactly the potential-based shaping component
(Ng, Harada & Russell 1999) -- which is why EPIC does not punish two rewards for
differing by shaping, and why it is the right instrument for "same policy,
different reward". The last term is a constant and drops out of the correlation.

    EPIC(R1, R2) = sqrt( (1 - pearson(C(R1), C(R2))) / 2 )

0 means identical up to shaping and positive scaling; 1 means anticorrelated. Note
EPIC is usually stated for gamma < 1; with gamma = 1 the shaping term is still
h(s') - h(s), so the construction goes through unchanged.
"""

import numpy as np

from .pbrr import N_ACTIONS, TRANSITION_TRIPLES, transition_index
from .waypoint_env import FREE_CELLS, move

__all__ = ["canonicalize", "epic_distance", "reward_vector"]


def reward_vector(reward_fn):
    """Flatten reward_fn(pos, action) over the reachable transitions."""
    return np.array([reward_fn(pos, a) for pos, a, _ in TRANSITION_TRIPLES])


def canonicalize(reward_fn):
    """C(R) over the reachable transitions, with A and S uniform."""
    # h(x) = E_A[ R(x, A, move(x, A)) ]
    h = {cell: np.mean([reward_fn(cell, a) for a in range(N_ACTIONS)]) for cell in FREE_CELLS}
    h_bar = float(np.mean(list(h.values())))
    return np.array(
        [reward_fn(pos, a) + h[nxt] - h[pos] - h_bar for pos, a, nxt in TRANSITION_TRIPLES]
    )


def epic_distance(reward_fn_a, reward_fn_b):
    """EPIC distance in [0, 1]."""
    ca, cb = canonicalize(reward_fn_a), canonicalize(reward_fn_b)
    sa, sb = ca.std(), cb.std()
    if sa < 1e-12 or sb < 1e-12:
        return float("nan")
    rho = float(np.corrcoef(ca, cb)[0, 1])
    return float(np.sqrt(max(0.0, (1.0 - rho) / 2.0)))
