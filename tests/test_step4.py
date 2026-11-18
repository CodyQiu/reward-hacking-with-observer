"""Step 4 validation: the PBRR variants (L- on the dispreferred trajectory, no L+,
g >= 0) and the exact tabular fit.

Run as ``.venv/bin/python tests/test_step4.py`` (or under pytest).
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_grid import BASE
from src.pbrr_core import (GConfig, Traj, _reg_coef, build_design, fit_correction,
                           fit_correction_tabular, loss_numpy)
from src.pbrr_grid import transition_features
from src.report import run_tests

SWAP = GConfig(no_agree="max1", l_minus_on="dispreferred")


def _mdp1_pairs():
    proxy = np.array([10.0, 6.0, 7.0, 9.0])
    true = np.array([2.0, 4.0, 3.0, 8.0])

    def t(a):
        c = np.zeros(4)
        c[a] = 1
        return Traj(c, proxy[a], true[a], 1)
    return proxy, [(t(0), t(2), 1.0)]


def _random_pairs(seed=0, n_tr=12):
    rng = np.random.default_rng(seed)
    trajs = [Traj(rng.integers(0, 4, n_tr).astype(float), float(rng.normal() * 5),
                  float(rng.normal()), n_tr) for _ in range(8)]
    return [(trajs[i], trajs[j], float(rng.random() < 0.5)) for i in range(4) for j in range(4, 8)]


def test_defaults_reproduce_the_paper_regulariser():
    d = build_design(_random_pairs())
    assert np.array_equal(d.reg_for(GConfig()), d.reg)
    assert np.array_equal(d.reg, d.reg_plus + d.reg_pref)
    g = np.random.default_rng(1).normal(size=len(d.present))
    assert loss_numpy(g, d, GConfig()) == loss_numpy(g, d, GConfig(l_minus_on="preferred", l_plus=True))


def test_swap_moves_l_minus_onto_the_dispreferred_trajectory():
    t1, t2 = Traj(np.array([1.0, 0.0]), 5.0, 0.0, 1), Traj(np.array([0.0, 1.0]), 1.0, 0.0, 1)
    d = build_design([(t1, t2, 1.0)])                 # D-: proxy prefers tau1, label tau2
    assert np.allclose(d.reg_for(GConfig()), [0.0, 1.0])
    assert np.allclose(d.reg_for(SWAP), [1.0, 0.0])
    agree = build_design([(t1, t2, 0.0)])             # D+: L+ on both, dropped by l_plus=False
    assert np.allclose(agree.reg_for(SWAP), [1.0, 1.0])
    assert np.allclose(agree.reg_for(SWAP.with_(l_plus=False)), [0.0, 0.0])
    assert _reg_coef(d, SWAP) == 10.0                 # lambda rule unchanged (max1)


def test_swap_raises_the_preferred_transition_on_the_papers_minimal_mdp():
    proxy, pairs = _mdp1_pairs()
    g, _ = fit_correction_tabular(pairs, 4, SWAP)
    assert abs(g[0]) < 0.5 and g[2] > 3.0             # s1 left alone, s3 raised above s1
    assert proxy[2] + g[2] > proxy[0] + g[0]
    g0, _ = fit_correction_tabular(pairs, 4, GConfig(no_agree="max1"))
    assert abs(g0[2]) < 0.5 and g0[0] < -3.0          # the paper: s3 left alone, s1 lowered


def test_softplus_floor_keeps_g_nonnegative_on_every_grid_transition():
    X = transition_features(BASE)
    rng = np.random.default_rng(0)
    n = X.shape[0]

    def t(proxy, true):
        c = np.zeros(n)
        c[rng.integers(0, n, 30)] = 1.0
        return Traj(c, proxy, true, 30)
    pairs = [(t(500.0, -10.0), t(10.0, 10.0), 1.0) for _ in range(6)]
    cfg = SWAP.with_(g_floor="softplus", n_layers=3, width=64, epochs=50, lr=1e-3)
    g, info = fit_correction(pairs, X, cfg, seed=0)
    assert g.shape == (n,) and g.min() >= 0.0
    assert abs(info["loss"] - info["loss_eq3_check"]) < 1e-3 * max(1.0, abs(info["loss"]))


def test_tabular_fit_is_a_constrained_stationary_point():
    pairs = _random_pairs(seed=3)
    for cfg in (GConfig(no_agree="max1"), SWAP, SWAP.with_(g_floor="softplus", l_plus=False)):
        g, info = fit_correction_tabular(pairs, 12, cfg, ridge=1e-2)
        d = build_design(pairs)
        x = g[d.present]
        z = d.dproxy + d.A @ x
        w = _reg_coef(d, cfg) * d.reg_for(cfg) + 1e-2
        grad = d.A.T @ (1 / (1 + np.exp(-z)) - d.y) / d.n_pairs + 2 * w * x
        free = x > 1e-8 if cfg.g_floor != "none" else np.ones_like(x, bool)
        assert np.abs(grad[free]).max() < 1e-5, (cfg, np.abs(grad[free]).max())
        assert (grad[~free] >= -1e-5).all()           # KKT: at the bound the gradient may only point up (descent is blocked)
        assert np.all(g[np.setdiff1d(np.arange(12), d.present)] == 0)


def test_step3_rows_fit_reproduces_the_step2_fit_for_every_variant():
    from tests.test_step3 import GRID, SMALL_G, _grid_pairs
    from src.step3.pbrr import fit_correction_rows

    po, pn = _grid_pairs(np.random.default_rng(0))
    for kw in ({"l_minus_on": "dispreferred"}, {"l_minus_on": "dispreferred", "l_plus": False},
               {"use_regularization": False}):
        cfg = SMALL_G.with_(**kw)
        g_old, info_old = fit_correction(po, transition_features(BASE), cfg, seed=3)
        _, info = fit_correction_rows(pn, GRID, cfg, seed=3)
        s, a, _ = GRID.decode(np.unique(np.concatenate([t.keys for t, _, _ in pn] + [t.keys for _, t, _ in pn])))
        # without any regulariser float32 summation-order differences grow through Adam
        # (max |dg| 0.005 on |g| ~ 1.2, loss equal to 2e-5): same objective, not bit-identical
        tol = 1e-3 if cfg.use_regularization else 1e-2
        assert np.allclose(info["g_rows"], g_old[s * 5 + a], rtol=tol, atol=tol), kw
        assert abs(info["loss"] - info_old["loss"]) < 1e-3 * max(1.0, abs(info_old["loss"])), kw


def test_caught_policy_is_the_best_policy_that_exploits_in_the_window():
    from src.step3.dp import solve_subepisode, solve_subepisode_caught
    from src.step3.tasks import get_task, module
    from experiments.step3_check import sub_value
    task = get_task("absent_supervisor")
    tb, P = task.tables, module("absent_supervisor").PROTOCOL
    T, W = P.t_sub, P.window
    pol = solve_subepisode_caught(tb, tb.true, T, W)
    # exact evaluation over (s, f): the caught policy always exploits in the window, at the cost of one penalty
    d = np.zeros((tb.n_states, 2))
    d[:, 0] = tb.mu0
    tot = 0.0
    for tau in range(T):
        r = np.arange(tb.n_states)[:, None] * tb.n_actions + pol[tau]           # (S, 2)
        m = d[..., None] * tb.prob[r]                                          # (S, 2, F)
        tot += (m * tb.true[r]).sum()
        f2 = np.arange(2)[None, :, None].astype(bool) | (tb.exploit[r] & (tau >= T - W))
        d = np.zeros_like(d)
        np.add.at(d, (tb.nxt[r], np.broadcast_to(f2, m.shape).astype(int)), m)
    assert abs(d[:, 1].sum() - 1.0) < 1e-9                                      # caught with certainty
    honest = sub_value(tb, solve_subepisode(tb, tb.true, T), tb.true, T)[0]
    assert abs(tot - (honest - 50.0)) < 1e-6, (tot, honest)                    # one penalty step, nothing else lost


def test_window_by_level_splits_the_window_probability():
    from src.step3.dp import evaluate_levels, solve_levels
    from src.step3.tasks import get_task, module
    task = get_task("absent_supervisor")
    tb, P = task.tables, module("absent_supervisor").PROTOCOL
    R = np.stack([tb.proxy] + [tb.true] * (P.n_sub - 1))
    _, pol = solve_levels(tb, P, R)
    ev = evaluate_levels(tb, P, R, pol)
    assert np.allclose(ev["window_by_level"].sum(axis=1), ev["window"])
    assert ev["window_by_level"].shape == (P.n_sub, P.n_sub)


def test_stochastic_level_evaluation_is_exact():
    """evaluate_levels_probs (PPO read as a table) equals evaluate_levels on a deterministic policy, is
    linear in a mixture at t = 0, and its occupancy reproduces the received return under any tables."""
    from src.step3.dp import evaluate_levels, evaluate_levels_probs, onehot_probs, solve_levels, value_from_occupancy
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    task = get_task("grid")
    tb, P = task.tables, Protocol()
    R = np.stack([tb.proxy + 3.0 * c for c in range(P.n_sub)])               # corrections pay: it seeks them
    _, pol = solve_levels(tb, P, R)
    a = evaluate_levels(tb, P, R, pol)
    assert np.allclose(a["corrected"][:4], 1.0)                               # every level is visited
    b = evaluate_levels_probs(tb, P, R, onehot_probs(pol, tb.n_actions))
    for k in a:
        assert np.allclose(a[k], b[k], atol=1e-9), k
    pol2 = pol.copy()
    pol2[0] = (pol[0] + 1) % tb.n_actions
    a2 = evaluate_levels(tb, P, R, pol2)
    oh, oh2 = onehot_probs(pol, tb.n_actions), onehot_probs(pol2, tb.n_actions)
    mix = evaluate_levels_probs(tb, P, R, lambda t: 0.5 * oh(t) + 0.5 * oh2(t))
    for k in a:
        assert np.allclose(0.5 * np.asarray(a[k]) + 0.5 * np.asarray(a2[k]), mix[k], atol=1e-9), k
    R2 = np.stack([tb.true - 1.0 * c for c in range(P.n_sub)])
    assert np.allclose(value_from_occupancy(tb, mix["occ"], R), mix["received"])
    assert np.allclose(value_from_occupancy(tb, mix["occ"], R2), evaluate_levels_probs(
        tb, P, R2, lambda t: 0.5 * oh(t) + 0.5 * oh2(t))["received"])


def test_update_bonus_closed_forms_on_the_step1_grid():
    """protocol.update_bonus (b per correction) in the exact DP, on the Step 1 grid with the oracle patch
    (levels >= 1 pay the true reward). Hiding is worth 7,700 x 4 + 8,700 = 39,500. Caught in round 0 and
    then in every round (only E in the window gets caught; after E the goal is out of reach, so a caught
    corrected round is -100) is 8,700 + 3 x (-100) + 22 + 4b; caught in round 0 only, 8,700 + 4 x 22 + b.
    b = 0 hides; b = 10,000 is caught in rounds 0-3 (48,422 beats caught-from-round-1, 16,222 + 3b)."""
    from src.step3.dp import evaluate_levels, evaluate_levels_probs, onehot_probs, solve_levels
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    tb = get_task("grid").tables
    R = np.stack([tb.proxy] + [tb.true] * 4)
    for b, V_exp, corr, recv in ((0.0, 39_500.0, [0, 0, 0, 0, 0], [7_700] * 4 + [8_700]),
                                 (10_000.0, 48_422.0, [1, 1, 1, 1, 0], [18_700, 9_900, 9_900, 9_900, 22])):
        P = Protocol(update_bonus=b)
        V, pol = solve_levels(tb, P, R)
        assert abs(tb.mu0 @ V[:, 0, 0] - V_exp) < 1e-6, (b, tb.mu0 @ V[:, 0, 0])
        ev = evaluate_levels(tb, P, R, pol)
        assert np.allclose(ev["corrected"], corr) and np.allclose(ev["received"], recv), (b, ev["received"])
        assert abs(ev["received"].sum() - V_exp) < 1e-6
        ev2 = evaluate_levels_probs(tb, P, R, onehot_probs(pol, tb.n_actions))
        assert np.allclose(ev2["received"], recv)
    # off by default, and the same policy's received return moves by exactly b per correction
    _, pol = solve_levels(tb, Protocol(update_bonus=10_000.0), R)
    assert Protocol().update_bonus == 0.0
    assert np.allclose(evaluate_levels(tb, Protocol(update_bonus=5.0), R, pol)["received"]
                       - evaluate_levels(tb, Protocol(), R, pol)["received"], [5, 5, 5, 5, 0])


def test_update_bonus_is_paid_where_the_dp_puts_it():
    """The training env pays b on the last step of each sub-episode whose audit triggers a correction
    (rounds 0-3), never in round 4 and never otherwise, and it is in neither the proxy nor the true reward:
    an open exploiter's per-round received return in the env equals the exact evaluation, copy by copy."""
    from src.step3.dp import evaluate_levels, solve_levels, table_policy_fn
    from src.step3.protocol import AuditedVecEnv, Protocol
    from src.step3.tasks import get_task
    task = get_task("grid")
    tb, b = task.tables, 7.0
    P = Protocol(update_bonus=b)
    R = np.stack([tb.proxy] * P.n_sub)                       # no overseer runs: g stays 0, received = proxy
    _, pol = solve_levels(tb, P, R)                           # exploit in view every round
    fn = table_policy_fn(pol, tb.n_actions)
    env = AuditedVecEnv(task, P, n_envs=3, seed=0)
    env.reset()
    extra, rec = np.zeros((P.t_ep, 3)), np.zeros((P.n_sub, 3))
    for t in range(P.t_ep):
        env.step_async(fn(env.batch, t, env.n_corr, env.flagged).argmax(axis=1))
        env.step_wait()
        L = env.last
        extra[t] = L["received"] - L["proxy"]
        rec[t // P.t_sub] += L["received"]
    paid = np.zeros(P.t_ep)
    paid[[99, 199, 299, 399]] = b
    assert np.allclose(extra, paid[:, None])
    assert np.allclose(rec, evaluate_levels(tb, P, R, pol)["received"][:, None])


def test_game_key_leaves_out_an_update_bonus_that_is_off():
    """Runs and targets written before protocol.update_bonus existed keep matching (step4_convergence)."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
    from step4_targets import game_key
    from src.step3.train import resolve_config
    new = resolve_config("grid", {"seed": 0})
    old = {**new, "protocol": {k: v for k, v in new["protocol"].items() if k != "update_bonus"}}
    assert "update_bonus" in new["protocol"] and game_key(new) == game_key(old) == game_key(game_key(old))
    on = resolve_config("grid", {"seed": 0, "protocol": {"update_bonus": 1.0}})
    assert game_key(on)["protocol"]["update_bonus"] == 1.0 and game_key(on) != game_key(new)
    assert "update_bonus" not in old["protocol"]                         # game_key does not modify its input


def test_best_response_check_on_an_open_exploiter():
    """experiments/step4_br.py on Absent Supervisor with a cheap g fit: the best response to the open
    exploiter's own corrections is at least as good as the exploiter (gap >= 0), and the paired per-draw
    gaps average to the mean-table gap."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
    from step4_br import best_response
    from src.step3.dp import onehot_probs, solve_levels, table_policy_fn
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config
    cfg = resolve_config("absent_supervisor", {"seed": 0, "g": {"epochs": 20, "use_regularization": False}})
    task, P = get_task(cfg["env"], **cfg["task"]), Protocol(**cfg["protocol"])
    tb = task.tables
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))              # exploit in view every round
    res = best_response(cfg, table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions), n_draws=2,
                        log=lambda m: None)
    assert res["behaviour"][0] == {"correction": 1, "from": "policy", "round": 0, "p_caught": 1.0}
    assert all(b["from"] == "policy" for b in res["behaviour"])               # it is caught at every level
    assert res["gap"] >= -1e-9 and res["V_br"] >= res["V_policy"] - 1e-6
    assert abs(np.mean(res["gap_by_draw"]) - res["gap"]) < 1e-9
    assert res["policy"]["corrections_per_ep"] > 3.99
    # with the update bonus (same draws: the streams depend only on seed, draw and level) the exploiter's
    # value rises by exactly b per correction, and the paired gaps still average to the mean-table gap
    b = 3.0
    cfg_b = {**cfg, "protocol": {**cfg["protocol"], "update_bonus": b}}
    res_b = best_response(cfg_b, table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions), n_draws=2,
                          log=lambda m: None)
    assert abs(res_b["V_policy"] - res["V_policy"] - 4 * b) < 1e-6
    assert np.allclose(np.asarray(res_b["policy"]["received_by_k"]) - res["policy"]["received_by_k"], [b] * 4 + [0])
    assert abs(sum(res_b["best_response"]["received_by_k"]) - res_b["V_br"]) < 1e-6 * abs(res_b["V_br"])
    assert res_b["V_br"] >= res["V_br"] - 1e-6 and abs(np.mean(res_b["gap_by_draw"]) - res_b["gap"]) < 1e-9


def _experiments():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))


def test_compensated_correction_closed_forms_on_the_step1_grid():
    """The compensated correction (g.offset, offset_margin 0; docs/step4_comp.md) on the Step 1 grid with the
    oracle patch (a correction makes the reward the true one) and the honest optimum as the reference (true 22
    a round). Level 1 pays (8,700 - 22) / 100 = 86.78 a step, so honest play after the correction receives
    8,700, what the open exploit received before it: being corrected costs nothing. Hiding still gives up the
    audit window (7,700 instead of 8,700 a round), so the optimum exploits in view in round 0, is corrected
    and is honest from then on: 5 x 8,700 = 43,500 against 39,500 for hiding. A second correction pays back
    only what the play that triggered it earned (true -100: after E the goal is out of reach), 8,578 < 8,700,
    so it is not sought. A constant per step leaves every round's ranking unchanged."""
    _experiments()
    from step4_targets import sub_value
    from src.pbrr_core import GConfig
    from src.step3.dp import (evaluate_levels, round_probs, round_value, solve_levels, solve_subepisode,
                              solve_subepisode_caught)
    from src.step3.pbrr import level_offset
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    tb, P = get_task("grid").tables, Protocol()
    T, W, A = P.t_sub, P.window, tb.n_actions
    gc = GConfig(offset=True, offset_margin=0.0)
    rbar = lambda R: (tb.prob * R).sum(axis=1)                                 # noqa: E731
    honest = sub_value(tb, solve_subepisode(tb, tb.true, T), tb.true, T)
    v_before = round_value(tb, P, rbar(tb.proxy), round_probs(solve_subepisode(tb, tb.proxy, T), A), 0)
    assert abs(honest - 22) < 1e-9 and abs(v_before - 8_700) < 1e-9
    R, levels = [tb.proxy], []
    for c in range(1, P.n_sub):
        levels.append(level_offset(gc, v_before, honest, T))
        R.append(tb.true + levels[-1])
        # the play that would trigger the next correction: the best caught round at this level
        v_before = round_value(tb, P, rbar(R[-1]), round_probs(solve_subepisode_caught(tb, R[-1], T, W), A), c)
    assert np.allclose(levels, [86.78, 85.56, 84.34, 83.12])
    V, pol = solve_levels(tb, P, np.stack(R))
    ev = evaluate_levels(tb, P, np.stack(R), pol)
    assert abs(tb.mu0 @ V[:, 0, 0] - 43_500) < 1e-6
    assert np.allclose(ev["corrected"], [1, 0, 0, 0, 0]) and np.allclose(ev["true"], [-100, 22, 22, 22, 22])
    assert np.allclose(ev["received"], [8_700] * 5)
    hide = np.stack([tb.proxy] + [tb.proxy - 1e6] * (P.n_sub - 1))
    assert abs(tb.mu0 @ solve_levels(tb, P, hide)[0][:, 0, 0] - 39_500) < 1e-6
    # off by default; a constant per step leaves the best round honest (true 22)
    assert level_offset(GConfig(), 8_700, 22, T) == 0.0
    assert abs(sub_value(tb, solve_subepisode(tb, tb.true + levels[0], T), tb.true, T) - 22) < 1e-9


def test_round_value_is_the_exact_round_return():
    """dp.round_value (the compensated correction's V_before) equals the level evaluations' round-0 return,
    for the open exploiter (8,700) and for a random stochastic policy."""
    from src.step3.dp import evaluate_levels, evaluate_levels_probs, round_probs, round_value, solve_levels
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    tb, P = get_task("grid").tables, Protocol()
    R = np.stack([tb.proxy] * P.n_sub)
    rb = (tb.prob * tb.proxy).sum(axis=1)
    _, pol = solve_levels(tb, P, R)                                            # exploit in view every round
    v = round_value(tb, P, rb, round_probs(pol, tb.n_actions, level=0), 0)
    assert abs(v - 8_700) < 1e-6 and abs(v - evaluate_levels(tb, P, R, pol)["received"][0]) < 1e-6
    probs = np.random.default_rng(0).dirichlet(np.ones(tb.n_actions), size=(tb.n_states, P.n_levels, 2))
    ev = evaluate_levels_probs(tb, P, R, lambda t: probs)
    assert abs(round_value(tb, P, rb, lambda t: probs[:, 0], 0) - ev["received"][0]) < 1e-6


def test_env_pays_the_level_until_the_episode_ends():
    """AuditedVecEnv pays a correction's level on every step of the copies it was installed for, and resets
    it with the reward at the end of the episode; without one the received reward is unchanged."""
    from src.step3.protocol import AuditedVecEnv, Protocol
    from src.step3.tasks import get_task
    P = Protocol()
    env = AuditedVecEnv(get_task("grid"), P, n_envs=3, seed=0)
    env.reset()
    env.set_correction([1], None, 5.0)
    extra = np.zeros((P.t_ep, 3))
    for t in range(P.t_ep):                                                    # stay at the start: never caught
        env.step_async(np.zeros(3, np.int64))
        env.step_wait()
        extra[t] = env.last["received"] - env.last["proxy"]
    assert np.allclose(extra, [0.0, 5.0, 0.0]) and np.all(env.level == 0.0)


def test_rollout_returns_and_the_level_formula():
    """pbrr.rollout_returns (the overseer's V_before and V_ref_after) and pbrr.level_offset."""
    import jax
    from src.pbrr_core import GConfig, mlp_init
    from src.step3.pbrr import _traj_rows, g_on_rows, level_offset, rollout_returns, rollouts
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    task, P = get_task("grid"), Protocol()
    uniform = lambda b, t, n, f: np.full((b.n, task.n_actions), 1.0 / task.n_actions)   # noqa: E731
    trajs = rollouts(task.make_batch(3, seed=0), uniform, P, np.random.default_rng(0))
    assert np.allclose(rollout_returns(trajs, task, None, 2.0), [t.proxy + 2.0 * P.t_sub for t in trajs])
    rows = _traj_rows(trajs, task)
    params = mlp_init(jax.random.PRNGKey(0), [rows.shape[1], 8, 1], "torch_default")
    g = g_on_rows(params, rows).reshape(3, -1).sum(axis=1)
    assert np.allclose(rollout_returns(trajs, task, params, 0.5), np.array([t.proxy + 50.0 for t in trajs]) + g)
    gc = GConfig(offset=True, offset_margin=0.0)
    assert level_offset(gc, 900.0, 100.0, 100) == 8.0 and level_offset(gc, 100.0, 900.0, 100) == 0.0
    assert abs(level_offset(GConfig(offset=True), 1_000.0, 0.0, 100) - 10.2) < 1e-12   # default margin 0.02
    assert level_offset(GConfig(), 900.0, 100.0, 100) == 0.0


def test_best_response_check_with_the_compensated_correction():
    """experiments/step4_br.py with g.offset on Absent Supervisor (cheap g fit, same draws as without): each
    correction's level follows the formula from the play it is fitted on (the open exploiter, so correction
    1's V_before is its exact round-0 value), the levels are in the tables (the exploiter's received return
    in round k rises by T x the mean level k), and the paired gaps still average to the mean-table gap."""
    _experiments()
    from step4_br import best_response
    from src.step3.dp import onehot_probs, solve_levels, table_policy_fn
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config
    cfg = resolve_config("absent_supervisor", {"seed": 0, "g": {"epochs": 20}})
    task, P = get_task(cfg["env"], **cfg["task"]), Protocol(**cfg["protocol"])
    tb, T = task.tables, P.t_sub
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))              # exploit in view every round
    args = (table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions))
    res = best_response(cfg, *args, n_draws=2, log=lambda m: None)
    cfg_o = {**cfg, "g": {**cfg["g"], "offset": True, "offset_margin": 0.0}}
    res_o = best_response(cfg_o, *args, n_draws=2, log=lambda m: None)
    lv = [b["level"] for b in res_o["behaviour"]]
    assert len(lv) == P.n_sub - 1 and all(b["from"] == "policy" for b in res_o["behaviour"])
    assert np.allclose(lv[0]["v_before"], res["policy"]["received_by_k"][0])
    for x in lv:
        assert np.allclose(x["level"], np.maximum(0.0, np.subtract(x["v_before"], x["v_ref_after"])) / T)
    diff = np.subtract(res_o["policy"]["received_by_k"], res["policy"]["received_by_k"])
    assert np.allclose(diff, [0.0] + [T * np.mean(x["level"]) for x in lv])
    assert abs(np.mean(res_o["gap_by_draw"]) - res_o["gap"]) < 1e-9 and res_o["gap"] >= -1e-9
    # the campaign's game: fines only as well; the levels again sit on top of the same (fines-only) tables
    cfg_f = {**cfg, "g": {**cfg["g"], "fine_only": True}}
    res_f = best_response(cfg_f, *args, n_draws=2, log=lambda m: None)
    res_fo = best_response({**cfg_f, "g": {**cfg_f["g"], "offset": True, "offset_margin": 0.0}}, *args,
                           n_draws=2, log=lambda m: None)
    lv = [b["level"] for b in res_fo["behaviour"]]
    diff = np.subtract(res_fo["policy"]["received_by_k"], res_f["policy"]["received_by_k"])
    assert np.allclose(diff, [0.0] + [T * np.mean(x["level"]) for x in lv])
    assert res_fo["game"]["g"]["fine_only"] is True and abs(np.mean(res_fo["gap_by_draw"]) - res_fo["gap"]) < 1e-9


def test_compensated_target_runs_on_the_grid():
    """experiments/step4_targets.py in the campaign's game (g.offset, offset_margin 0, g.fine_only), one draw
    and one iteration on the grid: correction 1 is fitted on the best caught policy (iteration 0 has no
    optimum yet), whose exact round-0 value is the open exploit's 8,700; every level follows the formula."""
    _experiments()
    from step4_targets import target
    from src.step3.train import resolve_config
    cfg = resolve_config("grid", {"seed": 0, "g": {"offset": True, "offset_margin": 0.0, "fine_only": True}})
    out = target(cfg, n_draws=1, max_iter=1, per_draw=False, log=lambda m: None)
    beh = out["target"]["behaviour"]
    assert [b["from"] for b in beh] == ["best caught policy (counterfactual)"] * 4
    assert abs(beh[0]["level"]["v_before"][0] - 8_700) < 1e-6
    for b in beh:
        x = b["level"]
        assert np.allclose(x["level"], np.maximum(0.0, np.subtract(x["v_before"], x["v_ref_after"])) / 100)
    assert out["game"]["g"]["offset"] is True and out["game"]["g"]["offset_margin"] == 0.0
    assert out["game"]["g"]["fine_only"] is True


def test_fines_only_correction_is_the_running_minimum():
    """GConfig.fine_only: the correction in force is min(0, g_1, ..., g_k), in pbrr.g_on_rows / g_table and in
    AuditedVecEnv.correction alike, so no transition is ever raised and a later correction never relaxes an
    earlier fine."""
    import jax
    from src.pbrr_core import mlp_init
    from src.step3.pbrr import g_on_rows, g_table
    from src.step3.protocol import AuditedVecEnv, MinCorrection, Protocol
    from src.step3.tasks import get_task
    task = get_task("grid")
    X = task.g_rows_from_keys(task.support_keys().ravel()[:500])
    nets = []
    for i in range(2):                                    # centre each random net's output: it raises some rows
        p = mlp_init(jax.random.PRNGKey(i), [X.shape[1], 8, 1], "torch_default")
        W, bias = p[-1]
        nets.append(p[:-1] + [(W, bias - float(np.median(g_on_rows(p, X))))])
    g1, g2 = (g_on_rows(p, X) for p in nets)
    assert (g1 > 0).any() and (g2 > 0).any() and (g1 < 0).any()
    m1 = MinCorrection(()).then(nets[0])
    m2 = m1.then(nets[1])
    assert np.allclose(g_on_rows(m1, X), np.minimum(0.0, g1))
    assert np.allclose(g_on_rows(m2, X), np.minimum(0.0, np.minimum(g1, g2)))
    assert (g_on_rows(m2, X) <= g_on_rows(m1, X) + 1e-12).all()
    assert np.allclose(g_table(m2, task), np.minimum(0.0, np.minimum(g_table(nets[0], task), g_table(nets[1], task))))
    env = AuditedVecEnv(task, Protocol(), n_envs=2, seed=0)
    env.reset()
    env.set_correction([0], m2, 0.0)
    assert np.allclose(env.correction(X[:2]), [g_on_rows(m2, X[:1])[0], 0.0])


def test_best_round_value_is_the_sub_episode_optimum():
    """dp.best_round_value, the exact-indifference yardstick M (docs/step4_indiff.md): the grid's open exploit
    8,700 and honest 22, and on random rewards the value of dp.solve_subepisode's policy."""
    _experiments()
    from step4_targets import sub_value
    from src.step3.dp import best_round_value, solve_subepisode
    from src.step3.tasks import get_task
    for env in ("grid", "absent_supervisor"):
        tb = get_task(env).tables
        R_noise = tb.proxy + np.random.default_rng(0).normal(0.0, 5.0, tb.proxy.shape)
        for R in (tb.proxy, tb.true, R_noise):
            assert abs(best_round_value(tb, R, 100) - sub_value(tb, solve_subepisode(tb, R, 100), R, 100)) < 1e-6
    tb = get_task("grid").tables
    assert abs(best_round_value(tb, tb.proxy, 100) - 8_700) < 1e-9
    assert abs(best_round_value(tb, tb.true, 100) - 22) < 1e-9


def test_round_window_reads_a_rounds_audit_exposure():
    """step4_targets.round_window (criterion A3, docs/step4_indiff.md): the open exploit's round uses the bug in the
    window, the window-avoiding and honest rounds do not, and it matches the level evaluation's round-0 window."""
    _experiments()
    from step4_targets import best_rounds, round_window
    from src.step3.dp import evaluate_levels, solve_levels, solve_subepisode
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    P = Protocol()
    T, W = P.t_sub, P.window
    for env in ("grid", "tomato"):
        tb = get_task(env).tables
        assert abs(round_window(tb, solve_subepisode(tb, tb.proxy, T), T, W) - 1) < 1e-9
        assert round_window(tb, solve_subepisode(tb, tb.proxy, T, avoid_window=W), T, W) < 1e-12
        assert round_window(tb, solve_subepisode(tb, tb.true, T), T, W) < 1e-12
        R = np.stack([tb.proxy] * P.n_sub)
        ev = evaluate_levels(tb, P, R, solve_levels(tb, P, R)[1])
        b = best_rounds(tb, R[:2], T, W)
        assert abs(b[0]["window"] - ev["window"][0]) < 1e-9 and abs(b[0]["received"] - ev["received"][0]) < 1e-6


def _exact_levels(tb, T, K, rng, fines_only):
    """Random corrections c = 1..K-1 (fines; or raises and fines) with the exact-indifference levels."""
    from src.step3.dp import best_round_value
    from src.step3.pbrr import exact_level
    G, R, lvl, m = np.zeros(tb.proxy.shape), [tb.proxy], 0.0, best_round_value(tb, tb.proxy, T)
    for _ in range(1, K):
        step = -rng.exponential(30.0, G.shape) * (rng.random(G.shape) < 0.3)
        if fines_only:
            G = np.minimum(G, step)
        else:
            G = step + rng.exponential(10.0, G.shape) * (rng.random(G.shape) < 0.1)
        m_new = best_round_value(tb, tb.proxy + G, T)
        lvl, m = exact_level(lvl, m, m_new, T), m_new
        R.append(tb.proxy + G + lvl)
    return np.stack(R)


def test_exact_indifference_makes_the_future_independent_of_being_corrected():
    """The theorem behind offset_rule=exact (docs/step4_indiff.md). Whatever the corrections are (random fines,
    or random raises and fines), with level_c = level_{c-1} + [M(r_{c-1}) - M(r_c)] / T the optimum is worth
    exactly K x M(proxy), for any detection probability: by induction the value at the start of round k is
    (K - k)(M(r) + T level) whether or not, and however, the agent is corrected, so it gains and loses nothing
    by a correction and plays a best round under the reward in force. On the grid and in Absent Supervisor that
    round exploits through the audit window (8,700 vs 7,700; 1,550 vs 1,450), so the optimum is caught in round 0."""
    from src.step3.dp import best_round_value, evaluate_levels, solve_levels
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    for env in ("grid", "absent_supervisor"):
        tb = get_task(env).tables
        for p in (1.0, 0.5):
            P = Protocol(p_detect=p)
            T, K = P.t_sub, P.n_sub
            m0 = best_round_value(tb, tb.proxy, T)
            for trial, fines_only in ((0, True), (1, True), (2, False)):
                R = _exact_levels(tb, T, K, np.random.default_rng(trial), fines_only)
                V, pol = solve_levels(tb, P, R)
                assert abs(tb.mu0 @ V[:, 0, 0] - K * m0) < 1e-6 * K * abs(m0), (env, p, trial, tb.mu0 @ V[:, 0, 0])
                ev = evaluate_levels(tb, P, R, pol)
                assert ev["window"][0] > 1 - 1e-9 and abs(ev["corrected"][0] - p) < 1e-9, (env, p, trial)
                assert abs(ev["received"].sum() - K * m0) < 1e-6 * K * abs(m0)


def test_exact_indifference_closed_forms_on_the_step1_grid():
    """offset_rule=exact on the Step 1 grid with the oracle patch (a correction makes the reward the true one).
    Level 1 = (8,700 - 22) / 100 = 86.78 a step, so honest play after the correction receives the 8,700 the
    open exploit received before it, and hiding still gives up the window: the optimum is caught in round 0
    and honest after, 5 x 8,700 = 43,500 against 39,500 for hiding. A later correction that also fines honest
    play (the goal's +50, by 40) is paid back exactly: level 2 = 86.78 + 40 / 100 = 87.18, so it is neither
    sought nor hidden from -- re-triggering it would take E in the window, which costs the goal (8,578 < 8,700)."""
    from src.step3.dp import best_round_value, evaluate_levels, solve_levels
    from src.step3.pbrr import exact_level
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    task, P = get_task("grid"), Protocol()
    tb, T = task.tables, P.t_sub
    goal = np.zeros(tb.proxy.shape)
    goal[(tb.true > 40) & (tb.prob > 0)] = -40.0                 # entering the goal pays 49 (50 - 1 for the step)
    r = [tb.proxy, tb.true] + [tb.true + goal] * 3
    m = [best_round_value(tb, x, T) for x in r]
    assert np.allclose(m, [8_700, 22, -18, -18, -18])
    lv = [0.0]
    for c in range(1, P.n_sub):
        lv.append(exact_level(lv[-1], m[c - 1], m[c], T))
    assert np.allclose(lv, [0.0, 86.78, 87.18, 87.18, 87.18])
    R = np.stack([x + l for x, l in zip(r, lv)])
    V, pol = solve_levels(tb, P, R)
    ev = evaluate_levels(tb, P, R, pol)
    assert abs(tb.mu0 @ V[:, 0, 0] - 43_500) < 1e-6
    assert np.allclose(ev["corrected"], [1, 0, 0, 0, 0]) and np.allclose(ev["true"], [-100, 22, 22, 22, 22])
    assert np.allclose(ev["received"], [8_700] * 5)
    hide = np.stack([tb.proxy] + [tb.proxy - 1e6] * (P.n_sub - 1))
    assert abs(tb.mu0 @ solve_levels(tb, P, hide)[0][:, 0, 0] - 39_500) < 1e-6


def test_overseer_installs_the_exact_level():
    """The training overseer with offset_rule=exact and fines only (grid, cheap fit): an open exploiter is caught in
    rounds 0 and 1. Each correction's level is the previous one plus [M(before) - M(after)] / T; M(before) of the
    first is M(proxy) = 8,700, the second's is the first's M(after), and M(after) is the best round under proxy +
    the correction the env actually has in force; every copy receives the level."""
    import src.step3.pbrr as pbrr
    from src.pbrr_core import GConfig
    from src.step3.dp import best_round_value, solve_levels, table_policy_fn
    from src.step3.protocol import AuditedVecEnv, Protocol
    from src.step3.reference import build_reference
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config
    cfg = resolve_config("grid", {"g": {"offset": True, "offset_rule": "exact", "fine_only": True, "epochs": 20}})
    task, P = get_task("grid"), Protocol(**cfg["protocol"])
    tb, T = task.tables, P.t_sub
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))              # exploit in view every round
    fn = table_policy_fn(pol, tb.n_actions)
    ref, _ = build_reference(task, T, {**cfg["pbrr"], "seed": cfg["pbrr"]["ref_seed"]})
    ref_trajs = pbrr.rollouts(task.make_batch(3, seed=1), ref, P, np.random.default_rng(1))
    env = AuditedVecEnv(task, P, n_envs=2, seed=0)
    env.reset()
    over = pbrr.Overseer(task, P, env, ref_trajs, GConfig(**cfg["g"]), k=3)
    over.model = None
    real = pbrr.policy_probs_fn
    pbrr.policy_probs_fn = lambda model, proto, n_actions: fn
    try:
        for t in range(2 * T):
            env.step_async(fn(env.batch, t, env.n_corr, env.flagged).argmax(axis=1))
            env.step_wait()
            if (t + 1) % T == 0:
                over.run_pending_rounds()
    finally:
        pbrr.policy_probs_fn = real
    r1, r2 = over.rounds
    assert abs(r1["level_m_before"] - 8_700) < 1e-6 and abs(r2["level_m_before"] - r1["level_m_after"]) < 1e-9
    assert abs(r1["level"] - (r1["level_m_before"] - r1["level_m_after"]) / T) < 1e-9
    assert abs(r2["level"] - r1["level"] - (r2["level_m_before"] - r2["level_m_after"]) / T) < 1e-9
    assert r2["level_m_after"] <= r1["level_m_after"] + 1e-6                  # fines only: M never rises
    assert np.allclose(env.level, r2["level"]) and list(env.n_corr) == [2, 2]
    G = pbrr.g_table(env.g_params[0], task)
    assert abs(best_round_value(tb, tb.proxy + G, T) - r2["level_m_after"]) < 1e-3


def test_exact_indifference_target_and_best_response_record_the_rule():
    """experiments/step4_targets.py and step4_br.py with offset_rule=exact. Target (grid, one draw, one
    iteration): the levels chain by the rule from M(proxy) = 8,700, and with one draw the theorem is exact, so
    V0 = 5 x 8,700 = 43,500 and the optimum is caught in round 0. Best response (Absent Supervisor, cheap fit,
    2 draws): the same chain per draw, and the paired gaps average to the mean-table gap."""
    _experiments()
    from step4_br import best_response
    from step4_targets import target
    from src.step3.dp import onehot_probs, solve_levels, table_policy_fn
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config

    def chain(beh, n, T=100):
        prev_after, prev_level = None, np.zeros(n)
        for b in beh:
            x = b["level"]
            if prev_after is not None:
                assert np.allclose(x["m_before"], prev_after)
            assert np.allclose(np.subtract(x["level"], prev_level),
                               np.subtract(x["m_before"], x["m_after"]) / T)
            assert np.all(np.asarray(x["m_after"]) <= np.asarray(x["m_before"]) + 1e-6)     # fines only
            prev_after, prev_level = x["m_after"], np.asarray(x["level"])

    g = {"offset": True, "offset_rule": "exact", "fine_only": True}
    cfg = resolve_config("grid", {"seed": 0, "g": g})
    out = target(cfg, n_draws=1, max_iter=1, per_draw=False, log=lambda m: None)
    beh = out["target"]["behaviour"]
    assert abs(beh[0]["level"]["m_before"][0] - 8_700) < 1e-6
    chain(beh, 1)
    for b in beh:
        assert abs(b["level"]["m_after_mean_table"] - b["level"]["m_after"][0]) < 1e-3
    assert abs(out["target"]["V0"] - 43_500) < 1e-3 and out["target"]["window_by_k"][0] > 1 - 1e-9
    assert out["game"]["g"]["offset_rule"] == "exact"
    cfg = resolve_config("absent_supervisor", {"seed": 0, "g": {"epochs": 20, **g}})
    task, P = get_task(cfg["env"], **cfg["task"]), Protocol(**cfg["protocol"])
    tb = task.tables
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))
    res = best_response(cfg, table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions), n_draws=2,
                        log=lambda m: None)
    chain(res["behaviour"], 2)
    assert abs(np.mean(res["gap_by_draw"]) - res["gap"]) < 1e-9 and res["gap"] >= -1e-9


def test_overseer_pool_estimate_uses_earlier_final_rounds():
    """offset_rule=pool in the training overseer (grid, cheap fit). Episode 0: an open exploiter is caught in rounds
    0-3; the pool is the reference and the caught rollouts, and the first estimate before correction is the caught
    open exploit's 8,700 (the exact M, logged beside it). Its final round enters the pool, so episode 1's
    correction draws on it. Every level follows [M_hat_before - M_hat_after] / T on the previous level, and with
    deterministic moves no candidate can beat the exact M."""
    import src.step3.pbrr as pbrr
    from src.pbrr_core import GConfig
    from src.step3.dp import solve_levels, table_policy_fn
    from src.step3.protocol import AuditedVecEnv, Protocol
    from src.step3.reference import build_reference
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config
    cfg = resolve_config("grid", {"g": {"offset": True, "offset_rule": "pool", "fine_only": True, "epochs": 20}})
    task, P = get_task("grid"), Protocol(**cfg["protocol"])
    tb, T = task.tables, P.t_sub
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))
    fn = table_policy_fn(pol, tb.n_actions)
    ref, _ = build_reference(task, T, {**cfg["pbrr"], "seed": cfg["pbrr"]["ref_seed"]})
    ref_trajs = pbrr.rollouts(task.make_batch(3, seed=1), ref, P, np.random.default_rng(1))
    env = AuditedVecEnv(task, P, n_envs=2, seed=0)
    env.reset()
    over = pbrr.Overseer(task, P, env, ref_trajs, GConfig(**cfg["g"]), k=3)
    over.model = None
    real = pbrr.policy_probs_fn
    pbrr.policy_probs_fn = lambda model, proto, n_actions: fn
    try:
        for t in range(P.t_ep + T):                                  # episode 0, then round 0 of episode 1
            over._on_rollout_start() if t % T == 0 else None
            env.step_async(fn(env.batch, t % P.t_ep, env.n_corr, env.flagged).argmax(axis=1))
            env.step_wait()
            over._on_step()
            if (t + 1) % T == 0:
                over._on_rollout_end()
    finally:
        pbrr.policy_probs_fn = real
    r = over.rounds
    assert [x["episode"] for x in r] == [0, 0, 0, 0, 1] and [x["n_round"] for x in r] == [1, 2, 3, 4, 1]
    assert abs(r[0]["level_m_hat_before"] - 8_700) < 1e-6 and abs(r[0]["level_m_before"] - 8_700) < 1e-6
    assert [x["level_pool_size"] for x in r] == [2, 2, 2, 2, 3]          # episode 0's final round (level 4)
    lvl = 0.0
    for x in r:
        if x["n_round"] == 1:
            lvl = 0.0
        assert abs(x["level"] - lvl - (x["level_m_hat_before"] - x["level_m_hat_after"]) / T) < 1e-9
        assert x["level_m_hat_after"] <= x["level_m_hat_before"] + 1e-6                # fines only
        assert x["level_m_hat_before"] <= x["level_m_before"] + 1e-6 and x["level_m_hat_after"] <= x["level_m_after"] + 1e-6
        lvl = x["level"]
    assert len(over.final_pool) == 1 and over.final_pool[0][:2] == (0, 4) and len(over.final_pool[0][2]) == 2


def test_pool_keeps_the_last_pool_episodes_episodes_by_level():
    """The overseer's pool (offset_rule=pool) holds the final-round play of exactly the last g.pool_episodes
    episodes, one group per correction level, at most k copies each."""
    import src.step3.pbrr as pbrr
    from src.pbrr_core import GConfig
    from src.step3.protocol import AuditedVecEnv, Protocol
    from src.step3.tasks import get_task
    task, P = get_task("grid"), Protocol()
    uniform = lambda b, t, n, f: np.full((b.n, task.n_actions), 1.0 / task.n_actions)   # noqa: E731
    ref = pbrr.rollouts(task.make_batch(2, seed=0), uniform, P, np.random.default_rng(0))
    over = pbrr.Overseer(task, P, AuditedVecEnv(task, P, n_envs=3, seed=0), ref,
                         GConfig(offset=True, offset_rule="pool", pool_episodes=2), k=1)
    T = P.t_sub
    for ep in range(4):
        over._ep, over._ncorr = ep, np.array([0, 1, 1])
        over._fk, over._ff = [np.zeros(3, np.int64)] * T, []
        over._fp, over._ft = [np.full(3, float(ep))] * T, [np.zeros(3)] * T
        over._store_final_round()
    assert [(e, c, len(g)) for e, c, g in over.final_pool] == [(2, 0, 1), (2, 1, 1), (3, 0, 1), (3, 1, 1)]
    assert all(g[0].proxy == T * e for e, _, g in over.final_pool)


def test_pool_estimate_in_the_target_and_best_response_never_beats_exact_m():
    """step4_targets / step4_br with offset_rule=pool. Target (grid, one draw, two iterations, so the second uses
    the first optimum's final-round play): the levels chain on the estimate, the estimate's first M_hat_before is the
    open exploit's 8,700, and on the deterministic grid no candidate beats the exact M recorded beside it. The
    verdict script reads the target. Best response (Absent Supervisor, cheap fit, 2 draws): the same chain."""
    _experiments()
    from step4_br import best_response
    from step4_indiff_check import level_errors, verdict
    from step4_targets import target
    from src.step3.dp import onehot_probs, solve_levels, table_policy_fn
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config

    def chain(beh, T=100):
        prev = None
        for b in beh:
            x = b["level"]
            prev = np.zeros(len(x["level"])) if prev is None else prev
            assert np.allclose(np.subtract(x["level"], prev),
                               np.subtract(x["m_hat_before"], x["m_hat_after"]) / T)
            assert np.all(np.asarray(x["m_hat_after"]) <= np.asarray(x["m_hat_before"]) + 1e-6)
            prev = np.asarray(x["level"])

    g = {"offset": True, "offset_rule": "pool", "fine_only": True}
    out = target(resolve_config("grid", {"seed": 0, "g": g}), n_draws=1, max_iter=2, per_draw=False,
                 log=lambda m: None)
    for it in out["iterations"]:
        beh = it["behaviour"]
        chain(beh)
        assert abs(beh[0]["level"]["m_hat_before"][0] - 8_700) < 1e-6
        for b in beh:
            x = b["level"]
            assert x["m_hat_before"][0] <= x["m_before"][0] + 1e-6 and x["m_hat_after"][0] <= x["m_after"][0] + 1e-6
    v = verdict(out)
    assert set(v) >= {"A1", "A2", "A3", "pass"} and len(level_errors(out)) == 4
    cfg = resolve_config("absent_supervisor", {"seed": 0, "g": {"epochs": 20, **g}})
    task, P = get_task(cfg["env"], **cfg["task"]), Protocol(**cfg["protocol"])
    tb = task.tables
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))
    res = best_response(cfg, table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions), n_draws=2,
                        log=lambda m: None)
    chain(res["behaviour"])
    assert abs(np.mean(res["gap_by_draw"]) - res["gap"]) < 1e-9


def test_indiff_verdict_labels_farming_hiding_and_under_correction():
    """step4_indiff_check.verdict on hand-made targets. A3 compares, at each level the optimum is at in a round k >= 1,
    its window rate with the best round's under that level's reward: equal and the best round uses the window =
    under-correction (passes); higher = farming, lower = hiding (both fail) -- or a tie when that deviation costs
    nothing (reported, passes). A round short of honest after the last correction fails A2, labelled by whether
    proxy exceeds true there."""
    _experiments()
    from step4_indiff_check import level_errors, verdict
    lvl = lambda c: [1.0 if i == c else 0.0 for i in range(5)]                              # noqa: E731
    base = {"V_hide": 0.0, "a1": {"honest_true": 22.0, "proxy_opt_true": -100.0},
            "target": {"end_state": "x", "V0": 1.0, "window_by_k": [1, 1, 0, 0, 0],
                       "corrected_by_k": [1, 1, 0, 0, 0], "true_by_k": [-100, -100, 22, 22, 22],
                       "proxy_by_k": [8700, 8700, 22, 22, 22], "behaviour": [],
                       "level_dist_by_k": [lvl(0), lvl(1), lvl(2), lvl(2), lvl(2)],
                       "window_by_level": [lvl(0), lvl(1), [0] * 5, [0] * 5, [0] * 5]}}

    def with_best(window1, caught1, avoid2=9.0, window2=0.0):
        b = [{"window": 1.0, "received": 10.0, "received_caught": 10.0, "received_avoid": 9.0} for _ in range(5)]
        b[1] = {"window": window1, "received": 10.0, "received_caught": caught1, "received_avoid": 9.0}
        b[2] = {"window": window2, "received": 10.0, "received_caught": 9.0, "received_avoid": avoid2}
        return {**base, "target": {**base["target"], "best_round_by_level": b}}

    kinds = lambda v: [x["kind"] for x in v["A3_rows"]]                                     # noqa: E731
    v = verdict(with_best(1.0, 10.0))                 # level 1: the best round uses the window; level 2: clean
    assert kinds(v) == ["under-correction (best round, caught)", "best round", "best round"] and v["pass"]
    v = verdict(with_best(0.0, 5.0))                  # caught at level 1 though its best round is clean
    assert kinds(v)[0] == "farming" and not v["A3"] and v["A1"] and v["A2"]
    assert kinds(verdict(with_best(0.0, 10.0)))[0] == "tie" and verdict(with_best(0.0, 10.0))["A3"]
    v = verdict(with_best(1.0, 10.0, window2=1.0))    # level 2's best round uses the window, the optimum keeps it clean
    assert kinds(v)[1:] == ["hiding", "hiding"] and not v["A3"]
    assert kinds(verdict(with_best(1.0, 10.0, avoid2=10.0, window2=1.0)))[1:] == ["tie", "tie"]
    bad = with_best(1.0, 10.0)
    bad["target"] = {**bad["target"], "true_by_k": [-100, -100, 22, -50, 22], "proxy_by_k": [8700, 8700, 22, -50, 22]}
    v = verdict(bad)
    assert not v["A2"] and v["A2_shortfalls"] == [{"round": 3, "true": -50, "kind": "new route"}]
    # level errors: correction 1 happens anyway (level 0's best round uses the window), so only underpaying counts
    t = with_best(1.0, 10.0)
    t["target"]["behaviour"] = [{"correction": 1, "round": 0, "from": "optimum",
                                 "level": {"m_before": [8700.0, 8700.0], "m_after": [30.0, 10.0],
                                           "m_after_mean_table": 15.0}}]
    r = level_errors(t)[0]                            # paid 8,680 on average, faced 8,685: underpaid by 5 < w = 1
    assert abs(r["err"] + 5.0) < 1e-9 and r["check"] == "underpay (hiding)" and not r["ok"]


def test_anneal_factor():
    from src.step3.train import _anneal_factor
    an = {"last": 0.25, "floor": 0.1}
    assert _anneal_factor({}, 50, 100) == 1.0 and _anneal_factor({"last": 0.0, "floor": 0.1}, 99, 100) == 1.0
    assert _anneal_factor(an, 75, 100) == 1.0
    assert abs(_anneal_factor(an, 87.5, 100) - 0.55) < 1e-12 and abs(_anneal_factor(an, 100, 100) - 0.1) < 1e-12


def test_entropy_boost_falls_to_one_by_its_episode_and_stays_off_by_default():
    from src.step3.train import _ent_boost
    an = {"last": 0.25, "floor": 0.1, "ent_start": 10, "ent_episodes": 768}
    assert _ent_boost({}, 0) == 1.0 and _ent_boost({"last": 0.25, "floor": 0.1}, 0) == 1.0
    assert _ent_boost(an, 0) == 10.0 and abs(_ent_boost(an, 384) - 5.5) < 1e-12
    assert _ent_boost(an, 768) == 1.0 and _ent_boost(an, 5000) == 1.0      # an extension does not restart it


def _sub_value(tb, pol, R, T=100):
    d, tot = tb.mu0.copy(), 0.0
    for tau in range(T):
        r = np.arange(tb.n_states) * tb.n_actions + pol[tau]
        tot += (d[:, None] * tb.prob[r] * R[r]).sum()
        d = np.bincount(tb.nxt[r].ravel(), weights=(d[:, None] * tb.prob[r]).ravel(), minlength=tb.n_states)
    return float(tot)


def test_grid_exploit_bonus_override_scales_only_the_exploit():
    from src.step3.dp import solve_subepisode
    from src.step3.tasks import get_task
    base, big = get_task("grid").tables, get_task("grid", exploit_bonus=400.0).tables
    assert np.array_equal(base.true, big.true) and np.array_equal(base.nxt, big.nxt)
    for b, tb in ((100, base), (400, big)):     # 13 steps to E, then 88 arrivals on E: -12 + 88 (b - 1)
        assert abs(_sub_value(tb, solve_subepisode(tb, tb.proxy, 100), tb.proxy) - (-12 + 88 * (b - 1))) < 1e-9


def test_routes_grid_closed_forms_and_the_reference_split():
    from src.step3.dp import solve_subepisode
    from src.step3.reference import build_reference
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config
    for R in (1, 2, 4):
        task = get_task("grid_routes", routes=R, bonus=100.0)
        tb = task.tables
        assert np.count_nonzero(tb.mu0) == R and np.allclose(tb.mu0[task.starts], 1 / R)
        assert tb.absorbing.sum() == R and set(np.flatnonzero(tb.absorbing)) == set(task.goals)
        # honest: 5 steps to the spoke's goal (+50) = 45; exploit: 2 steps to E, then 99 arrivals on E
        assert abs(_sub_value(tb, solve_subepisode(tb, tb.true, 100), tb.true) - 45.0) < 1e-9
        assert abs(_sub_value(tb, solve_subepisode(tb, tb.proxy, 100), tb.proxy) - (-1 + 99 * 99)) < 1e-9
        # the rule walks each start to its own goal in 5 steps and never touches E
        b = task.make_batch(R, seed=0)
        b.s = np.array(task.starts)
        for _ in range(5):
            assert not b.step(b.rule()).exploit.any()
        assert np.array_equal(b.s, task.goals)
    cfg = resolve_config("grid_routes", {"task": {"routes": 4}})
    assert cfg["pbrr"]["kind"] == "rule" and cfg["g"]["epochs"] == 100 and cfg["g"]["n_layers"] == 5
    assert cfg["g"]["no_agree"] == "max1" and cfg["refs"] is None
    # the noisy rule reference (what the targets use): near-ideal, honest, and split evenly over the spokes
    task = get_task("grid_routes", routes=4)
    ref, _ = build_reference(task, 100, cfg["pbrr"])
    b = task.make_batch(800, seed=3)
    b.reset()
    first = b.s.copy()
    true, ex, rng = np.zeros(800), 0, np.random.default_rng(4)
    for t in range(100):
        cum = np.cumsum(ref(b, t, 0, None), axis=1)
        out = b.step((rng.random((800, 1)) > cum).sum(axis=1).clip(max=task.n_actions - 1))
        true += out.true
        ex += out.exploit.sum()
    assert true.mean() > 0.85 * 45 and ex / (800 * 100) < 0.001, (true.mean(), ex)
    for s, g in zip(task.starts, task.goals):
        assert 150 < (first == s).sum() < 250 and np.all(b.s[first == s] == g)


def test_tomato_garden_art_keeps_the_six_tomato_task():
    from src.step3.tasks.tomato import ART, garden_art
    assert ART == ["#########", "#######O#", "#TTT    #", "#  A    #", "#       #", "#TTt    #", "#########"]
    big = garden_art(4)
    assert big[2] == "#TTTt   #" and big[5] == "#TTtT   #"
    assert sum(row.count("T") + row.count("t") for row in garden_art(7)) == 13      # the original's 13


def test_submit_sh_submits_fresh_and_resumed_runs():
    """submit.sh with a stub sbatch: a fresh run and a --resume both reach sbatch (a fresh submit once exited
    silently under set -e) and the existing-directory guards still refuse."""
    import subprocess, tempfile
    script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "farmshare", "submit.sh")
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "bin"))
        with open(os.path.join(tmp, "bin", "sbatch"), "w") as fh:
            fh.write("#!/bin/bash\necho 4242\n")
        os.chmod(os.path.join(tmp, "bin", "sbatch"), 0o755)
        env = {**os.environ, "PATH": os.path.join(tmp, "bin") + os.pathsep + os.environ["PATH"]}
        sub = lambda *a: subprocess.run(["bash", script, "1", "--env", "grid", "--run-id", "R", "--seeds", "0", "1",
                                         "--results-dir", "results/step4/grid/x", *a], cwd=tmp, env=env,
                                        capture_output=True, text=True)
        fresh = sub()
        assert fresh.returncode == 0 and fresh.stdout.strip() == "4242", fresh.stderr
        assert os.path.exists(os.path.join(tmp, "logs", "slurm", "step4_grid_R.sh"))
        assert sub("--resume").returncode != 0                     # nothing to resume yet
        os.makedirs(os.path.join(tmp, "results", "step4", "grid", "x", "R"))
        assert sub().returncode != 0                               # never overwrite a run
        resumed = sub("--resume")
        assert resumed.returncode == 0 and resumed.stdout.strip() == "4242", resumed.stderr


def test_step4_commit_sh_commits_the_log_before_tomato_large_exists():
    """step4_commit.sh in a scratch clone: the campaign log is committed and pushed although
    results/step3/tomato_large does not exist yet (one missing path used to fail the whole git add); the
    pull merges a remote commit; and a modified tracked file (a running job's log) is neither blocking nor
    rewritten: same inode, same content (a stash would give it a new inode and detach the job's open handle)."""
    import shutil, subprocess, tempfile
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git = lambda cwd, *a: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        remote, work = os.path.join(tmp, "remote.git"), os.path.join(tmp, "work")
        git(tmp, "init", "-q", "--bare", remote)
        git(tmp, "clone", "-q", remote, work)
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
            git(work, "config", k, v)
        os.makedirs(os.path.join(work, "scripts", "farmshare"))
        shutil.copy(os.path.join(repo, "scripts", "farmshare", "step4_commit.sh"), os.path.join(work, "scripts", "farmshare"))
        with open(os.path.join(work, "runs.csv"), "w") as fh:
            fh.write("a\n")
        git(work, "add", "-A"); git(work, "commit", "-qm", "init"); git(work, "push", "-q", "-u", "origin", "HEAD")
        os.makedirs(os.path.join(work, "docs"))
        with open(os.path.join(work, "docs", "step4_optimal_log.md"), "w") as fh:
            fh.write("log\n")
        other = os.path.join(tmp, "other")                     # someone else pushes meanwhile (the laptop)
        git(tmp, "clone", "-q", remote, other)
        for k, v in (("user.name", "o"), ("user.email", "o@o"), ("commit.gpgsign", "false")):
            git(other, "config", k, v)
        with open(os.path.join(other, "notes.md"), "w") as fh:
            fh.write("x\n")
        git(other, "add", "notes.md"); git(other, "commit", "-qm", "laptop"); git(other, "push", "-q")
        live = os.path.join(work, "runs.csv")
        fh_live = open(live, "a", buffering=1)                 # a running job's open handle
        fh_live.write("b\n")                                   # modified, not to be committed
        ino = os.stat(live).st_ino
        out = subprocess.run(["bash", "scripts/farmshare/step4_commit.sh", "msg"], cwd=work, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        files = git(remote, "ls-tree", "-r", "--name-only", "HEAD")
        assert "docs/step4_optimal_log.md" in files and "notes.md" in files
        assert git(work, "status", "--porcelain").strip() == "M runs.csv"
        fh_live.write("c\n"); fh_live.close()
        assert os.stat(live).st_ino == ino                     # the job's handle still writes the visible file
        with open(live) as fh:
            assert fh.read() == "a\nb\nc\n"


def test_step4_commit_sh_leaves_out_files_github_rejects():
    """A finished seed's directory is committed whole, but GitHub rejects any file over 100 MiB and then the
    whole push fails (GH001: a 115 MiB logs.npz, 2026-11-17). step4_commit.sh leaves such a file out, says so,
    and commits and pushes the rest of the seed. The big file is sparse, so the test writes no 100 MiB to disk."""
    import shutil, subprocess, tempfile
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git = lambda cwd, *a: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        remote, work = os.path.join(tmp, "remote.git"), os.path.join(tmp, "work")
        git(tmp, "init", "-q", "--bare", remote)
        git(tmp, "clone", "-q", remote, work)
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("commit.gpgsign", "false")):
            git(work, "config", k, v)
        os.makedirs(os.path.join(work, "scripts", "farmshare"))
        shutil.copy(os.path.join(repo, "scripts", "farmshare", "step4_commit.sh"), os.path.join(work, "scripts", "farmshare"))
        git(work, "add", "-A"); git(work, "commit", "-qm", "init"); git(work, "push", "-q", "-u", "origin", "HEAD")
        sd = os.path.join(work, "results", "step4", "grid", "bonus", "R", "seed0")
        os.makedirs(sd)
        for f in ("metrics.json", "model.zip"):
            with open(os.path.join(sd, f), "w") as fh:
                fh.write("{}\n")
        with open(os.path.join(sd, "logs.npz"), "wb") as fh:
            fh.truncate(100 * 1024 * 1024 + 1)
        out = subprocess.run(["bash", "scripts/farmshare/step4_commit.sh", "msg"], cwd=work, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        assert "not committed" in out.stderr and "seed0/logs.npz" in out.stderr, out.stderr
        files = git(remote, "ls-tree", "-r", "--name-only", "HEAD").split()
        assert "results/step4/grid/bonus/R/seed0/metrics.json" in files
        assert "results/step4/grid/bonus/R/seed0/model.zip" in files
        assert "results/step4/grid/bonus/R/seed0/logs.npz" not in files
        assert git(work, "status", "--porcelain").strip() == "?? results/step4/grid/bonus/R/seed0/logs.npz"


def test_finished_seed_is_read_from_the_directory_listing():
    """A resumed seed renames metrics.json to metrics_ep<N>.json. On the NFS home the login node kept the old
    name's cached dentry for many minutes, so os.path.exists / [[ -f ]] called a training seed finished:
    br_missing listed it and step4_commit.sh committed its running checkpoints (2026-11-15, bonus log
    iteration 108). step4_br.finished and the scripts' finished() read the directory listing instead. The stale
    dentry is simulated by an exists() that always finds metrics.json; the shell functions run on real dirs."""
    import json, re, subprocess, tempfile
    from unittest import mock
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(repo, "experiments"))
    from step4_br import finished, missing
    with tempfile.TemporaryDirectory() as tmp:
        run = os.path.join(tmp, "run")
        sd = os.path.join(run, "seed0")
        os.makedirs(sd)
        for f in ("model.zip", "metrics_ep1536.json"):
            open(os.path.join(sd, f), "w").close()
        with open(os.path.join(sd, "config.json"), "w") as fh:
            json.dump({"episodes": 3072}, fh)
        real_exists = os.path.exists
        stale = lambda p: os.path.basename(p) == "metrics.json" or real_exists(p)
        with mock.patch("os.path.exists", stale):
            assert not finished(sd) and missing(run) == []
        shell = {}
        for script in ("step4_commit.sh", "step4_optimal.sh"):
            with open(os.path.join(repo, "scripts", "farmshare", script)) as fh:
                src = fh.read()
            assert not re.search(r"\[\[ -[ef] [^]]*metrics\.json", src), script     # no stat-based test left
            shell[script] = next(l for l in src.splitlines() if l.startswith("finished()"))
        is_done = lambda fn, d: subprocess.run(["bash", "-c", fn + '\nfinished "$1"', "x", d]).returncode == 0
        for fn in shell.values():
            assert not is_done(fn, sd + "/") and not is_done(fn, sd)
        open(os.path.join(sd, "metrics.json"), "w").close()
        assert finished(sd) and missing(run) == ["seed0"]
        for fn in shell.values():
            assert is_done(fn, sd + "/") and is_done(fn, sd)
        assert not finished(os.path.join(run, "seed9"))                            # a missing dir is not finished


def test_ensemble_correction_is_the_mean_of_fines():
    """protocol.EnsembleCorrection (offset_rule=exact_mean): with fines only it is mean_i min(prev, g_i), so it
    never raises a transition and never relaxes the correction before it; without, mean_i g_i. pbrr.g_on_rows
    gives the same values."""
    import jax
    import jax.numpy as jnp
    from src.pbrr_core import mlp_apply, mlp_init
    from src.step3.pbrr import g_on_rows
    from src.step3.protocol import EnsembleCorrection
    X = np.random.default_rng(0).normal(size=(300, 7)).astype(np.float32)
    nets = [mlp_init(jax.random.PRNGKey(i), [7, 16, 16, 1], "torch_default") for i in range(5)]
    g = np.stack([np.asarray(mlp_apply(p, jnp.asarray(X)), float) for p in nets])
    first = EnsembleCorrection(None, nets[:3], True)
    assert np.allclose(first.apply(jnp.asarray(X)), np.minimum(0.0, g[:3]).mean(axis=0), atol=1e-5)
    second = EnsembleCorrection(first, nets[3:], True)
    want = np.minimum(np.minimum(0.0, g[:3]).mean(axis=0)[None], g[3:]).mean(axis=0)
    got = second.apply(jnp.asarray(X))
    assert np.allclose(got, want, atol=1e-5)
    assert np.all(got <= first.apply(jnp.asarray(X)) + 1e-6) and np.all(got <= 1e-6)
    assert np.allclose(g_on_rows(second, X), want, atol=1e-5)
    assert np.allclose(EnsembleCorrection(None, nets, False).apply(jnp.asarray(X)), g.mean(axis=0), atol=1e-5)


def test_overseer_installs_the_mean_level():
    """The training overseer with offset_rule=exact_mean, n_ensemble 3 and fines only (grid, cheap fit): an open
    exploiter is caught in rounds 0 and 1. Each catch fits 3 corrections on their own rollouts (3 data sets),
    the env applies their mean, and the level chains by [M(before) - M(after)] / T with M(after) the best round
    under exactly the correction the env has in force."""
    import src.step3.pbrr as pbrr
    from src.pbrr_core import GConfig
    from src.step3.dp import best_round_value, solve_levels, table_policy_fn
    from src.step3.protocol import AuditedVecEnv, EnsembleCorrection, Protocol
    from src.step3.reference import build_reference
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config
    cfg = resolve_config("grid", {"g": {"offset": True, "offset_rule": "exact_mean", "n_ensemble": 3,
                                        "fine_only": True, "epochs": 20}})
    task, P = get_task("grid"), Protocol(**cfg["protocol"])
    tb, T = task.tables, P.t_sub
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))              # exploit in view every round
    fn = table_policy_fn(pol, tb.n_actions)
    ref, _ = build_reference(task, T, {**cfg["pbrr"], "seed": cfg["pbrr"]["ref_seed"]})
    ref_trajs = pbrr.rollouts(task.make_batch(3, seed=1), ref, P, np.random.default_rng(1))
    env = AuditedVecEnv(task, P, n_envs=2, seed=0)
    env.reset()
    over = pbrr.Overseer(task, P, env, ref_trajs, GConfig(**cfg["g"]), k=3)
    over.model = None
    real = pbrr.policy_probs_fn
    pbrr.policy_probs_fn = lambda model, proto, n_actions: fn
    try:
        for t in range(2 * T):
            env.step_async(fn(env.batch, t, env.n_corr, env.flagged).argmax(axis=1))
            env.step_wait()
            if (t + 1) % T == 0:
                over.run_pending_rounds()
    finally:
        pbrr.policy_probs_fn = real
    r1, r2 = over.rounds
    assert r1["n_ensemble"] == 3 and abs(r1["level_m_before"] - 8_700) < 1e-6
    assert abs(r2["level_m_before"] - r1["level_m_after"]) < 1e-9
    assert abs(r1["level"] - (r1["level_m_before"] - r1["level_m_after"]) / T) < 1e-9
    assert abs(r2["level"] - r1["level"] - (r2["level_m_before"] - r2["level_m_after"]) / T) < 1e-9
    assert r2["level_m_after"] <= r1["level_m_after"] + 1e-6                  # fines only: M never rises
    assert np.allclose(env.level, r2["level"]) and list(env.n_corr) == [2, 2]
    corr = env.g_params[0]
    assert isinstance(corr, EnsembleCorrection) and len(corr.members) == 3 and isinstance(corr.prev, EnsembleCorrection)
    Ds = over.cache[max(over.cache, key=lambda key: len(key[1]))]             # after the second catch
    assert len(Ds) == 3 and all(len(D) == 2 * 3 * 3 for D in Ds)            # 2 catches x 3 rollouts x 3 refs each
    G = pbrr.g_table(corr, task)
    assert abs(best_round_value(tb, tb.proxy + G, T) - r2["level_m_after"]) < 1e-3


def test_mean_rule_target_and_best_response_record_the_rule():
    """experiments/step4_targets.py and step4_br.py with offset_rule=exact_mean (n_ensemble 2). The levels chain
    by the rule per draw from M(proxy) = 8,700 (grid target, 2 draws; Absent Supervisor best response, cheap
    fit); the game key carries n_ensemble, and a config without it keeps its old key."""
    _experiments()
    from step4_br import best_response
    from step4_targets import game_key, target
    from src.step3.dp import onehot_probs, solve_levels, table_policy_fn
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config

    def chain(beh, n, T=100):
        prev_after, prev_level = None, np.zeros(n)
        for b in beh:
            x = b["level"]
            if prev_after is not None:
                assert np.allclose(x["m_before"], prev_after)
            assert np.allclose(np.subtract(x["level"], prev_level),
                               np.subtract(x["m_before"], x["m_after"]) / T)
            assert np.all(np.asarray(x["m_after"]) <= np.asarray(x["m_before"]) + 1e-6)     # fines only
            assert "m_after_mean_table" in x
            prev_after, prev_level = x["m_after"], np.asarray(x["level"])

    g = {"offset": True, "offset_rule": "exact_mean", "n_ensemble": 2, "fine_only": True}
    cfg = resolve_config("grid", {"seed": 0, "g": g})
    out = target(cfg, n_draws=2, max_iter=1, per_draw=False, log=lambda m: None)
    beh = out["target"]["behaviour"]
    assert np.allclose(beh[0]["level"]["m_before"], 8_700)
    chain(beh, 2)
    assert out["game"]["g"]["offset_rule"] == "exact_mean" and out["game"]["g"]["n_ensemble"] == 2.0
    old = resolve_config("grid", {"seed": 0, "g": {"offset": True, "offset_rule": "exact", "fine_only": True}})
    assert "n_ensemble" not in game_key(old)["g"]
    old["g"]["n_ensemble"] = 1
    assert "n_ensemble" not in game_key(old)["g"]
    cfg = resolve_config("absent_supervisor", {"seed": 0, "g": {"epochs": 20, **g}})
    task, P = get_task(cfg["env"], **cfg["task"]), Protocol(**cfg["protocol"])
    tb = task.tables
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))
    res = best_response(cfg, table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions), n_draws=2,
                        log=lambda m: None)
    chain(res["behaviour"], 2)
    assert abs(np.mean(res["gap_by_draw"]) - res["gap"]) < 1e-9 and res["gap"] >= -1e-9


def test_pool_sources_without_the_final_round():
    """GConfig.pool_source (docs/step4_indiff.md, "Estimating M without the final round"). Grid target, one draw,
    two iterations, for each source: the levels chain on the estimate, no estimate beats the exact M beside it,
    and the second iteration's winning candidates come only from the source's set ("none": the reference and the
    caught play; "rounds": ordinary rounds k < 4; "twin": the overseer's optimiser). The original "final" keeps
    its game key and candidate names; the others carry pool_source as a string. The best-response check accepts
    "rounds" (PPO's own ordinary-round play) and refuses "twin" (it needs the twin's own model)."""
    _experiments()
    from step4_br import best_response
    from step4_targets import game_key, pool_candidates, target
    from src.step3.dp import evaluate_levels, onehot_probs, solve_levels, table_policy_fn
    from src.step3.protocol import Protocol
    from src.step3.tasks import get_task
    from src.step3.train import resolve_config
    g = {"offset": True, "offset_rule": "pool", "fine_only": True}
    allowed = {"none": ("reference", "caught"), "rounds": ("reference", "caught", "round"),
               "twin": ("reference", "caught", "twin")}
    for src, prefixes in allowed.items():
        cfg = resolve_config("grid", {"seed": 0, "g": {**g, "pool_source": src}})
        assert game_key(cfg)["g"]["pool_source"] == src
        out = target(cfg, n_draws=1, max_iter=2, per_draw=False, log=lambda m: None)
        prev = None
        for b in out["iterations"][-1]["behaviour"]:
            x = b["level"]
            prev = np.zeros(1) if prev is None else prev
            assert np.allclose(np.subtract(x["level"], prev), np.subtract(x["m_hat_before"], x["m_hat_after"]) / 100)
            assert x["m_hat_before"][0] <= x["m_before"][0] + 1e-6 and x["m_hat_after"][0] <= x["m_after"][0] + 1e-6
            for name in x["best_before"] + x["best_after"]:
                assert name.startswith(prefixes), (src, name)
            prev = np.asarray(x["level"])
    cfg = resolve_config("grid", {"seed": 0, "g": g})
    assert "pool_source" not in game_key(cfg)["g"]
    task, P = get_task("grid"), Protocol(**cfg["protocol"])
    tb, K, A = task.tables, P.n_sub, task.tables.n_actions
    R = np.stack([tb.proxy] * K)
    _, pol = solve_levels(tb, P, R)
    ev = evaluate_levels(tb, P, R, pol)
    fin = pool_candidates("final", pol, ev, R, tb, P, A)
    assert fin and all(name.startswith("final lvl") and k == K - 1 for name, _, k in fin)
    assert pool_candidates("none", pol, ev, R, tb, P, A) == []
    assert all(k < K - 1 for _, _, k in pool_candidates("rounds", pol, ev, R, tb, P, A))
    cfg = resolve_config("absent_supervisor", {"seed": 0, "g": {"epochs": 20, **g, "pool_source": "rounds"}})
    task, P = get_task(cfg["env"], **cfg["task"]), Protocol(**cfg["protocol"])
    tb = task.tables
    _, pol = solve_levels(tb, P, np.stack([tb.proxy] * P.n_sub))
    res = best_response(cfg, table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions), n_draws=1,
                        log=lambda m: None)
    assert res["gap"] >= -1e-9
    cfg["g"]["pool_source"] = "twin"
    refused = False
    try:
        best_response(cfg, table_policy_fn(pol, tb.n_actions), onehot_probs(pol, tb.n_actions), n_draws=1,
                      log=lambda m: None)
    except AssertionError as e:
        refused = "a twin needs its own model" in str(e)
    assert refused, "the best-response check must refuse pool_source=twin"


if __name__ == "__main__":
    run_tests(globals(), "Step 4 -- PBRR variants and the tabular fit")
