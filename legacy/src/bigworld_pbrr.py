"""PBRR on the multi-exploit big world, and the interleaved training loop.

Two loops live here.

``bigworld_pbrr_dp``  -- PBRR with pi*_{r_hat} solved exactly by DP. Fast, noise-free,
                        and the right tool for the question "does one refit of g close
                        one exploit or all six?"

``sawtooth_run``      -- a fresh PPO policy is trained each repair round. Preference
                        rollouts can come from that learner (the legacy control) or from
                        exact pi*_{r_hat} (the convergent, exactly audited run).

The preference-learning objective itself is imported unchanged from ``src.pbrr``
(``fit_g`` / ``build_design``), which is only possible because that module was written
against a Trajectory carrying its own ``g_idx`` and ``n_transitions``. This module
supplies big-world trajectories; none of the loss code knows the difference.

IMPORTANT on reading the sawtooth: the amplitude of each tooth is a *design choice*,
not a property of PBRR. It is set by how many environment steps PPO gets between
refits -- refit often and exploits are closed before PPO can exploit them much, so the
teeth are small; refit rarely and they are large. ``experiments/exp4_sawtooth.py``
therefore runs several refit intervals and says so.
"""

import numpy as np

from .bigworld import (
    BONUS,
    BONUS_TILES,
    CELL_INDEX,
    GOAL,
    HORIZON,
    N_ACTIONS,
    N_FREE,
    N_TRANSITIONS,
    OBS_MATRIX,
    START,
    BigWorldEnv,
    bfs_dist,
    dp_optimal_policy,
    live_exploits,
    move,
    obs_row,
    policy_rollout,
    policy_true_return,
    r_proxy,
    r_true,
    shaping_term,
    transition_index,
)
from .pbrr import Trajectory, fit_g

__all__ = [
    "make_trajectory",
    "step_toward_goal",
    "eps_greedy_reference",
    "rollout_action_fn",
    "boltzmann_label",
    "cross_pairs",
    "expand_correction",
    "bigworld_pbrr_dp",
    "action_prob_table",
    "policy_table_rollout",
    "evaluate_table",
    "sawtooth_run",
]

_D_GOAL = bfs_dist(GOAL)


def expand_correction(g, correction_scope="transition"):
    """Expand fitted parameters to the environment's (state, action) table.

    ``transition`` is the original fully tabular parameterisation. ``state`` shares
    one parameter across all five actions leaving a state. The state-shared model is
    the tabular analogue of the paper's parameter-sharing neural correction and is
    exactly expressive for this environment's state-based bonus bug.
    """
    g = np.asarray(g, dtype=float)
    if correction_scope == "transition":
        if g.shape != (N_TRANSITIONS,):
            raise ValueError(
                f"transition correction must have shape {(N_TRANSITIONS,)}, got {g.shape}"
            )
        return g.copy()
    if correction_scope == "state":
        if g.shape != (N_FREE,):
            raise ValueError(f"state correction must have shape {(N_FREE,)}, got {g.shape}")
        return np.repeat(g, N_ACTIONS)
    raise ValueError("correction_scope must be 'transition' or 'state'")


def make_trajectory(
    states, actions, bonus=BONUS, tiles=BONUS_TILES, correction_scope="transition",
):
    proxy = sum(r_proxy(p, a, bonus, tiles) for p, a in zip(states, actions))
    true = sum(r_true(p, a) for p, a in zip(states, actions))
    if correction_scope == "state":
        g_idx = [CELL_INDEX[p] for p in states]
        n_parameters = N_FREE
    elif correction_scope == "transition":
        g_idx = [transition_index(p, a) for p, a in zip(states, actions)]
        n_parameters = N_TRANSITIONS
    else:
        raise ValueError("correction_scope must be 'transition' or 'state'")
    return Trajectory(
        states, actions, proxy, true,
        g_idx=g_idx,
        n_transitions=n_parameters,
    )


def step_toward_goal(pos):
    for a in range(N_ACTIONS):
        nxt = move(pos, a)
        if nxt != pos and _D_GOAL[nxt] < _D_GOAL[pos]:
            return a
    return 4


def eps_greedy_reference(eps=0.3):
    """Suboptimal but honest reference: heads for the goal, never dwells on a tile.

    Theorem 4.3 only guarantees PBRR does no worse than pi_ref, so the reference is
    deliberately imperfect -- otherwise the answer is handed to the algorithm.
    """

    def action_fn(pos, rng):
        if rng.random() < eps:
            return int(rng.integers(0, N_ACTIONS))
        return step_toward_goal(pos)

    return action_fn


def rollout_action_fn(
    action_fn, rng, horizon=HORIZON, start=START, correction_scope="transition",
):
    pos, states, actions = start, [], []
    for _ in range(horizon):
        a = int(action_fn(pos, rng))
        states.append(pos)
        actions.append(a)
        pos = move(pos, a)
        if pos == GOAL:
            break
    return make_trajectory(states, actions, correction_scope=correction_scope)


def boltzmann_label(a, b, rng, beta=1.0, tol=1e-9):
    d = a.true_return - b.true_return
    if abs(d) <= tol:
        return 0.5
    p = 1.0 / (1.0 + np.exp(-np.clip(beta * d, -500, 500)))
    return 0.0 if rng.random() < p else 1.0


def cross_pairs(set_a, set_b, trajs, rng, beta=1.0):
    base = len(trajs)
    trajs.extend(set_a)
    trajs.extend(set_b)
    ia = range(base, base + len(set_a))
    ib = range(base + len(set_a), base + len(set_a) + len(set_b))
    return [(i, j, boltzmann_label(trajs[i], trajs[j], rng, beta)) for i in ia for j in ib]


def _eps_soft_dp(policy, eps, horizon=HORIZON):
    from .bigworld import CELL_INDEX

    state = {"t": 0}

    def action_fn(pos, rng):
        t = min(state["t"], horizon - 1)
        state["t"] += 1
        if rng.random() < eps:
            return int(rng.integers(0, N_ACTIONS))
        return int(policy[t, CELL_INDEX[pos]])

    return action_fn


def bigworld_pbrr_dp(
    n_iterations=8, k=12, seed=0, lam=10.0, eps_ref=0.3, proxy_eps=0.05,
    use_regularization=True, weight_decay=0.0, correction_scope="transition",
    preference_margin=0.0, verbose=False,
):
    """PBRR with an exact-DP inner solve. Returns per-iteration history.

    The point of interest is ``live`` -- which of the six exploits are still
    profitable after each refit.
    """
    rng = np.random.default_rng(seed)
    ref = eps_greedy_reference(eps_ref)
    trajs, pairs, history = [], [], []
    n_parameters = N_FREE if correction_scope == "state" else N_TRANSITIONS
    g_parameters = np.zeros(n_parameters)
    g = expand_correction(g_parameters, correction_scope)

    for it in range(n_iterations):
        policy = dp_optimal_policy(g)
        set_a = [
            rollout_action_fn(
                _eps_soft_dp(policy, proxy_eps), rng,
                correction_scope=correction_scope,
            )
            for _ in range(k)
        ]
        set_b = [
            rollout_action_fn(ref, rng, correction_scope=correction_scope)
            for _ in range(k)
        ]
        pairs.extend(cross_pairs(set_a, set_b, trajs, rng))
        g_parameters, info = fit_g(
            pairs, trajs, lam=lam, use_regularization=use_regularization,
            weight_decay=weight_decay, preference_margin=preference_margin,
            seed=seed + it,
        )
        g = expand_correction(g_parameters, correction_scope)

        new_policy = dp_optimal_policy(g)
        states, _ = policy_rollout(new_policy)
        farm = {t: sum(1 for p in states if p == t) for t in BONUS_TILES}
        live = live_exploits(g)
        history.append(
            dict(
                iteration=it + 1, n_preferences=len(pairs), g=g.copy(),
                true_return=policy_true_return(new_policy),
                farm=farm, live=live,
                n_live=sum(1 for v in live.values() if v > 0),
                n_agree=info.get("n_agree", 0),
            )
        )
        if verbose:
            print(
                f"    iter {it+1:2d}  prefs {len(pairs):5d}  true {history[-1]['true_return']:+7.2f}  "
                f"live exploits {history[-1]['n_live']}/{len(BONUS_TILES)}  "
                f"dwell values {[round(v, 2) for v in live.values()]}  "
                f"farmed {max(farm.values())} steps at {max(farm, key=farm.get)}"
            )
    return dict(
        history=history, g=g, g_parameters=g_parameters, pairs=pairs, trajs=trajs,
        correction_scope=correction_scope,
    )


# --------------------------------------------------------------------------- #
# interleaved PPO + PBRR
# --------------------------------------------------------------------------- #

def action_prob_table(model):
    """(N_FREE, N_ACTIONS) action probabilities -- the policy read as a lookup table."""
    st = model.policy.actor_state
    dist = st.apply_fn(st.params, OBS_MATRIX)
    p = np.asarray(dist.probs_parameter()).reshape(N_FREE, -1)[:, :N_ACTIONS]
    p = np.clip(p, 0.0, None)
    return p / p.sum(axis=1, keepdims=True)


def policy_table_rollout(
    table, rng, correction=None, horizon=HORIZON, correction_scope="transition",
):
    env = BigWorldEnv(correction=correction, horizon=horizon)
    env.reset()
    states, actions = [], []
    terminated = truncated = False
    while not (terminated or truncated):
        states.append(env.pos)
        a = int(rng.choice(N_ACTIONS, p=table[obs_row(env.pos)]))
        actions.append(a)
        _, _, terminated, truncated, _ = env.step(a)
    return make_trajectory(states, actions, correction_scope=correction_scope)


def evaluate_table(table, rng, correction=None, n_episodes=200, horizon=HORIZON):
    """Received and true return of the current policy, plus per-tile farming."""
    env = BigWorldEnv(correction=correction, horizon=horizon)
    recv, true, shaping, goal = [], [], [], []
    farm = {t: [] for t in BONUS_TILES}
    for _ in range(n_episodes):
        env.reset()
        terminated = truncated = False
        info = {}
        shaping_return = 0.0
        while not (terminated or truncated):
            a = int(rng.choice(N_ACTIONS, p=table[obs_row(env.pos)]))
            shaping_return += shaping_term(env.pos, a)
            _, _, terminated, truncated, info = env.step(a)
        recv.append(info["episode_recv_return"])
        true.append(info["episode_true_return"])
        shaping.append(shaping_return)
        goal.append(info["reached_goal"])
        for t in BONUS_TILES:
            farm[t].append(info["farm_steps"][t])
    return dict(
        recv=float(np.mean(recv)), true=float(np.mean(true)),
        shaping=float(np.mean(shaping)),
        recv_unshaped=float(np.mean(np.asarray(recv) - np.asarray(shaping))),
        goal=float(np.mean(goal)),
        farm={t: float(np.mean(v)) for t, v in farm.items()},
        farm_total=float(sum(np.mean(v) for v in farm.values())),
    )


def sawtooth_run(
    n_rounds=12, steps_per_round=80_000, eval_every=10_000, k=12, seed=0, lam=10.0,
    eps_ref=0.3, n_eval=120, n_envs=8, ent_coef=0.01, weight_decay=0.01,
    correction_scope="transition", preference_margin=0.0,
    preference_source="ppo", proxy_eps=0.05, verbose=False,
):
    """PBRR the way Algorithm 1 actually specifies it: a FRESH policy each round.

    Line 4 of Algorithm 1 computes pi*_{r_hat_t}, and footnote 3 says "we train a
    policy using r_hat_t" -- a new policy per iteration, not a continuation. That
    distinction is the whole experiment here:

      * continuing to train one policy across refits produces LOCK-IN. The converged
        agent responds to its exploit being weakened by farming it less, never by
        going to find another one.
      * retraining per round means each round's agent re-explores from scratch and
        independently discovers whichever exploit is still the most profitable. The
        proxy/true gap therefore opens once per round and is reset by the next refit,
        which is a sawtooth.

    ``weight_decay`` is an explicit L2-loss coefficient. The released paper code uses
    Adam weight decay 1e-5 (Table 2 only reports the Boolean setting); those coefficients
    are not numerically interchangeable. The local default 0.01 is a stabilizer selected
    for this exact tabular fit and should not be described as the paper's value.

    So the sawtooth is not a property of PBRR, nor of having several exploits -- it is
    a property of the agent re-exploring after each repair. Returns one row per
    evaluation with the round index attached, so the teeth can be cut at round
    boundaries.
    """
    from sbx import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    # Evaluation must not perturb the preferences that train g. Previously the same
    # RNG drove both, so changing n_eval or eval_every silently changed the learned
    # reward and even whether a run converged.
    rng = np.random.default_rng(seed)
    eval_rng = np.random.default_rng(np.random.SeedSequence(seed).spawn(1)[0])
    ref = eps_greedy_reference(eps_ref)
    n_parameters = N_FREE if correction_scope == "state" else N_TRANSITIONS
    g_parameters = np.zeros(n_parameters)
    g = expand_correction(g_parameters, correction_scope)
    trajs, pairs, rows, refits = [], [], [], []
    cumulative = 0

    for rnd in range(n_rounds):
        g_round = g.copy()          # frozen for the duration of the round
        vec = DummyVecEnv(
            [(lambda i=i: BigWorldEnv(seed=seed * 1000 + rnd * 50 + i,
                                      correction=g_round))
             for i in range(n_envs)]
        )
        model = PPO(
            "MlpPolicy", vec, seed=seed * 100 + rnd, learning_rate=3e-4, n_steps=256,
            batch_size=256, n_epochs=10, gamma=1.0, gae_lambda=0.95,
            ent_coef=ent_coef, policy_kwargs=dict(net_arch=[64, 64]), verbose=0,
        )
        while model.num_timesteps < steps_per_round:
            model.learn(total_timesteps=eval_every, reset_num_timesteps=False)
            table = action_prob_table(model)
            m = evaluate_table(table, eval_rng, correction=g_round, n_episodes=n_eval)
            rows.append(
                dict(round=rnd + 1, step_in_round=int(model.num_timesteps),
                     cumulative_steps=cumulative + int(model.num_timesteps),
                     n_preferences=len(pairs), **m)
            )
        cumulative += int(model.num_timesteps)

        table = action_prob_table(model)
        if preference_source == "ppo":
            set_a = [
                policy_table_rollout(
                    table, rng, g_round, correction_scope=correction_scope,
                )
                for _ in range(k)
            ]
        elif preference_source == "exact_dp":
            exact_policy = dp_optimal_policy(g_round)
            set_a = [
                rollout_action_fn(
                    _eps_soft_dp(exact_policy, proxy_eps), rng,
                    correction_scope=correction_scope,
                )
                for _ in range(k)
            ]
        else:
            raise ValueError("preference_source must be 'ppo' or 'exact_dp'")
        set_b = [
            rollout_action_fn(ref, rng, correction_scope=correction_scope)
            for _ in range(k)
        ]
        pairs.extend(cross_pairs(set_a, set_b, trajs, rng))
        g_parameters, info = fit_g(
            pairs, trajs, lam=lam, weight_decay=weight_decay,
            preference_margin=preference_margin, seed=seed + rnd,
        )
        g = expand_correction(g_parameters, correction_scope)
        live = live_exploits(g)
        exact_true = policy_true_return(dp_optimal_policy(g))
        end = rows[-1]
        refits.append(
            dict(round=rnd + 1, cumulative_steps=cumulative, n_preferences=len(pairs),
                 n_live=sum(1 for v in live.values() if v > 0),
                 exact_true=exact_true,
                 dwell_values=tuple(float(v) for v in live.values()),
                 gap_at_end=end["recv"] - end["true"], true_at_end=end["true"],
                 adjusted_gap_at_end=end["recv_unshaped"] - end["true"],
                 farm_at_end=end["farm_total"],
                 top_tile=max(end["farm"], key=end["farm"].get))
        )
        if verbose:
            print(
                f"    round {rnd+1:2d}: fresh PPO -> recv {end['recv']:+7.2f} "
                f"true {end['true']:+7.2f} gap {end['recv']-end['true']:6.2f} "
                f"farm {end['farm_total']:5.1f} @ {refits[-1]['top_tile']} "
                f"| refit -> {len(pairs)} prefs, live {refits[-1]['n_live']}/{len(BONUS_TILES)}"
            )

    return dict(
        rows=rows, refits=refits, g=g, g_parameters=g_parameters, pairs=pairs,
        trajs=trajs, correction_scope=correction_scope,
        preference_source=preference_source,
    )
