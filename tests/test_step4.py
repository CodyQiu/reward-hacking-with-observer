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


if __name__ == "__main__":
    run_tests(globals(), "Step 4 -- PBRR variants and the tabular fit")
