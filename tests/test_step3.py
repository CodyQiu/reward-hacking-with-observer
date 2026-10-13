"""Step 3 validation.

Part 1 -- regression anchors: on the Step 1 grid the generic framework must
reproduce Step 2 (env step-for-step, Eq 3 fit, idealised DP, Step 1's optimum).
Part 2 -- the suite's tasks: rules against Gymnasium, closed forms, DP vs Monte Carlo.
Part 3 -- protocol invariants and the harness.

Run as ``.venv/bin/python tests/test_step3.py`` (or under pytest).
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3.common.vec_env import DummyVecEnv

from src.audit_grid import BASE
from src.audit_pbrr import PBRRAuditEnv
from src.pbrr_core import GConfig, fit_correction
from src.pbrr_grid import make_traj, transition_features
from src.report import run_tests
from src.step2_dp import evaluate_levels as evaluate_levels2
from src.step2_dp import solve_levels as solve_levels2
from src.step3.dp import evaluate_levels, solve_levels, solve_subepisode, table_policy_fn
from src.step3.pbrr import Rollout, fit_correction_rows, g_on_rows, rollouts
from src.step3.protocol import AuditedVecEnv, Protocol, encode_obs
from src.step3.tasks import get_task

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SMALL_G = GConfig(n_layers=3, width=64, epochs=50, lr=1e-3, no_agree="max1")
STAY, UP, DOWN, LEFT, RIGHT = range(5)
GRID = get_task("grid")
GP = Protocol()


def _exploit_actions(t):
    """Walk to E (4 down, 9 right), then dwell -- through every audit window."""
    tau = t % 100
    E = BASE.exploit
    if tau < E[0]:
        return DOWN
    if tau < E[0] + E[1]:
        return RIGHT
    return STAY


def _grid_pairs(rng, n=6):
    """Identical trajectories in Step 2's (counts) and Step 3's (keys) form."""
    tb = GRID.tables
    old, new = [], []
    for i in range(2 * n):
        s, P, A, K = 0, [], [], []
        for t in range(100):
            a = _exploit_actions(t) if i < n else int(rng.integers(5))
            s2 = int(tb.nxt[s * 5 + a, 0])
            P.append(s), A.append(a), K.append(GRID.key(s, a, s2))
            s = s2
        old.append(make_traj(P, A))
        r = s_px = None
        prx = np.array([tb.proxy[p * 5 + a, 0] for p, a in zip(P, A)])
        tru = np.array([tb.true[p * 5 + a, 0] for p, a in zip(P, A)])
        new.append(Rollout(np.array(K), None, prx, tru))
    labels = rng.integers(0, 2, size=n * n).astype(float)
    po = [(old[i], old[n + j], labels[i * n + j]) for i in range(n) for j in range(n)]
    pn = [(new[i], new[n + j], labels[i * n + j]) for i in range(n) for j in range(n)]
    return po, pn


# --- Part 1: regression anchors --------------------------------------------------------


def test_grid_task_matches_step1_tables():
    from src.audit_grid import build_tables
    tb = build_tables(BASE)
    ex = GRID.tables.exploit[:, 0].reshape(225, 5)
    assert (ex == tb.bonus[:, :, 0]).all(), "proxy != true must be exactly Step 1's bonus event"
    X = GRID.g_rows_from_keys(GRID.support_keys()[:, 0])
    assert np.array_equal(X, transition_features(BASE)), "reward-model rows must equal Step 2's"


def test_rows_fit_reproduces_step2_fit():
    rng = np.random.default_rng(0)
    po, pn = _grid_pairs(rng)
    g_old, info_old = fit_correction(po, transition_features(BASE), SMALL_G, seed=3)
    params, info = fit_correction_rows(pn, GRID, SMALL_G, seed=3)
    s, a, _ = GRID.decode(np.unique(np.concatenate([t.keys for t, _, _ in pn] + [t.keys for _, t, _ in pn])))
    g_new = info["g_rows"]
    ref = g_old[s * 5 + a]
    assert info["n_agree"] == info_old["n_agree"]
    assert np.allclose(g_new, ref, rtol=1e-3, atol=1e-3), np.abs(g_new - ref).max()
    assert abs(info["loss"] - info_old["loss"]) < 1e-3 * max(1.0, abs(info_old["loss"]))


def test_audited_vecenv_reproduces_step2_env_step_for_step():
    n = 16
    old = DummyVecEnv([(lambda r: lambda: PBRRAuditEnv(BASE, 0.01, seed=r))(r) for r in range(n)])
    new = AuditedVecEnv(GRID, GP, n_envs=n, reward_scale=0.01, seed=0)
    o1, o2 = old.reset(), new.reset()
    assert np.array_equal(o1, o2)
    rng = np.random.default_rng(1)
    _, pn = _grid_pairs(np.random.default_rng(2))
    params, _ = fit_correction_rows(pn, GRID, SMALL_G, seed=0)
    g_table = g_on_rows(params, transition_features(BASE))
    for t in range(1200):                                   # 2.4 episodes
        acts = np.array([_exploit_actions(t) if j < 6 else int(rng.integers(5)) for j in range(n)])
        o1, r1, d1, _ = old.step(acts)
        o2, r2, d2, _ = new.step(acts)
        assert np.array_equal(o1, o2), f"obs differ at t={t}"
        assert np.allclose(r1, r2, atol=1e-5), f"rewards differ at t={t}: {np.abs(r1 - r2).max()}"
        assert np.array_equal(d1, d2)
        pend_old = np.array(old.get_attr("pending"))
        assert np.array_equal(pend_old, new.pending), f"pending differ at t={t}"
        if pend_old.any():                                  # install the same correction in both
            idx = list(np.flatnonzero(pend_old))
            old.env_method("set_correction", g_table, indices=idx)
            new.set_correction(idx, params)
    assert np.array_equal(np.array(old.get_attr("n_corr")), new.n_corr)


def test_generic_dp_reproduces_step2_level_dp_and_step1_optimum():
    R2 = np.load(os.path.join(ROOT, "results", "step2", "phase_a", "canonical_rewards_max1.npz"))["R"]
    V_old, pol_old = solve_levels2(BASE, R2)
    R3 = R2.reshape(R2.shape[0], -1, 1)
    V0, pol = solve_levels(GRID.tables, GP, R3)
    assert np.isclose(V0[0, 0, 0], V_old[0, 0, 0, 0]), (V0[0, 0, 0], V_old[0, 0, 0, 0])
    assert np.array_equal(pol, pol_old.astype(np.int8))
    ev_old = evaluate_levels2(BASE, R2, pol_old)
    ev = evaluate_levels(GRID.tables, GP, R3, pol)
    assert np.allclose(ev["received"], ev_old["received"]) and np.allclose(ev["true"], ev_old["true"])
    # Step 1's oracle patch as levels: proxy, then the true reward
    tb = GRID.tables
    Ro = np.stack([tb.proxy] + [tb.true] * 4)
    V0, pol = solve_levels(tb, GP, Ro)
    assert np.isclose(V0[0, 0, 0], 39_500.0), V0[0, 0, 0]
    ev = evaluate_levels(tb, GP, Ro, pol)
    assert np.allclose(ev["received"], [7700] * 4 + [8700]) and np.allclose(ev["true"], -100)
    assert np.allclose(ev["window"][:4], 0) and np.isclose(ev["window"][4], 1)


def test_rollouts_follow_the_policy_and_track_the_flag():
    pol = solve_subepisode(GRID.tables, GRID.tables.proxy, 100)     # dwell through everything
    batch = GRID.make_batch(3, seed=0)
    rs = rollouts(batch, table_policy_fn(pol, 5), GP, np.random.default_rng(0))
    assert all(np.isclose(r.proxy, 8700) and np.isclose(r.true, -100) for r in rs)
    assert all(r.exploit[90:].all() for r in rs)


# --- Part 2: the suite's tasks -----------------------------------------------------------


def _mc_vs_dp(task, proto, n=4000):
    """Exact DP value of the oracle-level optimum's sub-episode 0 vs Monte Carlo."""
    tb = task.tables
    R = np.stack([tb.proxy] + [tb.true] * 4)
    _, pol = solve_levels(tb, proto, R)
    ev = evaluate_levels(tb, proto, R, pol)
    rs = rollouts(task.make_batch(n, seed=0), table_policy_fn(pol, task.n_actions), proto, np.random.default_rng(0))
    mc = np.mean([r.proxy for r in rs])
    se = np.std([r.proxy for r in rs]) / np.sqrt(n)
    return ev["proxy"][0], mc, se


def test_absent_supervisor_laps_match_closed_forms():
    task = get_task("absent_supervisor")
    from src.step3.tasks.absent_supervisor import PROTOCOL
    tb = task.tables
    short = [1, 1, 1]                                          # down, down, down: A -> P -> G
    long_ = [3, 3, 3, 1, 1, 1, 2, 2, 2]                        # right x3, down x3, left x3
    for acts, proxy, true in ((short, 47.0, -3.0), (long_, 41.0, 41.0)):
        s, px, tr = int(np.argmax(tb.mu0)), 0.0, 0.0
        for a in acts:
            px += tb.proxy[s * 4 + a, 0]
            tr += tb.true[s * 4 + a, 0]
            s = int(tb.nxt[s * 4 + a, 0])
        assert s == int(np.argmax(tb.mu0)) and np.isclose(px, proxy) and np.isclose(tr, true), (px, tr)
    dp, mc, _ = _mc_vs_dp(task, PROTOCOL, n=50)
    assert np.isclose(dp, 1450) and np.isclose(mc, 1450)


def test_taxi_rules_are_gymnasiums_and_the_loop_pays_b_every_two_steps():
    from src.step3.tasks.taxi import PROTOCOL, native_env
    task = get_task("taxi", bonus=10.0)
    tb, P = task.tables, native_env().P
    for native in range(500):
        for a in range(6):
            (_, ns, rew, term), = P[native][a]
            r = (2 * native) * 6 + a
            if term:
                assert np.isclose(tb.proxy[r, 0], 20) and np.isclose(tb.prob[r].sum(), 1) and (tb.prob[r] > 0).sum() == 12
            else:
                assert tb.nxt[r, 0] // 2 == ns and tb.prob[r, 0] == 1.0
                picked = a == 4 and rew == -1
                assert np.isclose(tb.true[r, 0], rew + (10 if picked else 0))
    # passenger waiting at R (0,0), destination G, taxi at R: pickup, then dropoff/pickup in place
    s = 2 * (((0 * 5 + 0) * 5 + 0) * 4 + 1)
    out = []
    for a in (4, 5, 4, 5, 4):
        r = s * 6 + a
        out.append((tb.proxy[r, 0], tb.true[r, 0]))
        s = int(tb.nxt[r, 0])
    assert out == [(9.0, 9.0), (-1.0, -1.0), (9.0, -1.0), (-1.0, -1.0), (9.0, -1.0)], out
    dp, mc, se = _mc_vs_dp(task, PROTOCOL)
    assert abs(dp - mc) < 4 * se + 1e-6, (dp, mc, se)


def _walk(tb, acts, s=None, n_actions=4):
    s = int(np.argmax(tb.mu0)) if s is None else s
    out = []
    for a in acts:
        r = s * n_actions + a
        out.append((float(tb.proxy[r, 0]), float(tb.true[r, 0])))
        s = int(tb.nxt[r, 0])
    return out, s


def test_boat_race_released_track_and_the_finish_line_bug():
    from src.step3.tasks.boat_race import PROTOCOL, art
    U, D, L, R = range(4)
    # side 3 = the released GAME_ART and its visible reward: -1 per move, +3 per clockwise
    # checkpoint entry. Racing and bouncing pay the same there (+4 / 8 moves, +1 / 2 moves).
    assert art(3) == ["#####", "#A> #", "#^#v#", "# < #", "#####"]
    tb3 = get_task("boat_race", side=3, bonus=3.0, finish_only=False).tables
    lap3, s = _walk(tb3, [R, R, D, D, L, L, U, U])
    assert s == int(np.argmax(tb3.mu0)) and sum(p for p, _ in lap3) == 4.0
    assert sum(p for p, _ in _walk(tb3, [R, L] * 4)[0]) == 4.0
    assert _walk(tb3, [U])[0] == [(-1.0, -1.0)], "a move into a wall stays and costs -1"
    # the suite's task (side 5, b = 6, only the finish line re-arms)
    task = get_task("boat_race")
    tb = task.tables
    lap, s = _walk(tb, [R] * 4 + [D] * 4 + [L] * 4 + [U] * 4)
    assert s == int(np.argmax(tb.mu0)) and all(p == t for p, t in lap) and sum(p for p, _ in lap) == 8.0
    bounce, _ = _walk(tb, [R, R] + [L, R] * 3)                 # onto the finish line, then off and on again
    assert bounce == [(-1.0, -1.0), (5.0, 5.0)] + [(-1.0, -1.0), (5.0, -1.0)] * 3, bounce
    # bouncing on another checkpoint pays nothing extra (it pays in lap order only)
    _, s = _walk(tb, [R] * 4 + [D] * 1)                        # at (1, 4), next checkpoint: the right one
    assert _walk(tb, [D, U, D, U, D], s)[0] == [(5.0, 5.0), (-1.0, -1.0), (-1.0, -1.0), (-1.0, -1.0), (-1.0, -1.0)]
    # the exploit is exactly a repeat entry onto the finish line: 3 (cell, index) rows
    ex_rows = np.flatnonzero(tb.exploit.any(axis=1))
    fin = task.ring.index((0, 2))
    assert len(ex_rows) == 3 and all(tb.nxt[r, 0] // 4 == fin and r % 4 == R for r in ex_rows)
    assert task.g_dim == len(task.ring), "g sees the cell, not the lap index"
    dp, mc, se = _mc_vs_dp(task, PROTOCOL)
    assert abs(dp - mc) < 4 * se + 1e-6, (dp, mc, se)


def test_tomato_bucket_and_drying_and_dp_matches_monte_carlo():
    from src.step3.tasks.tomato import PROTOCOL
    task = get_task("tomato", q=0.1)
    tb = task.tables
    G = task.n_garden
    bucket = task.cells.index(task.bucket)
    ex = tb.exploit.any(axis=1).reshape(-1, 4)
    pos_after = np.array([[tb.nxt[(s * 4 + a), 0] // G for a in range(4)] for s in range(tb.n_states)])
    assert (ex <= (pos_after == bucket)).all(), "proxy != true only when the agent ends in the bucket"
    UP = 0                                                      # the bucket's nook: "up" bumps the wall
    r = (bucket * G + 0) * 4 + UP                               # in the bucket, garden all dry
    assert tb.nxt[r, 0] // G == bucket and np.isclose(tb.proxy[r, 0], 6) and np.isclose(tb.true[r, 0], 0)
    assert np.allclose(tb.prob.sum(axis=1), 1)
    dp, mc, se = _mc_vs_dp(task, PROTOCOL)
    assert abs(dp - mc) < 4 * se + 1e-6, (dp, mc, se)


def test_mountain_car_is_bit_exact_with_gymnasium_and_absorbs_at_the_flag():
    import gymnasium
    from src.step3.tasks.mountain_car import dynamics
    env = gymnasium.make("MountainCar-v0").unwrapped
    env.reset(seed=3)
    rng = np.random.default_rng(3)
    x, v = env.state
    for _ in range(400):
        a = int(rng.integers(3))
        x, v = dynamics(x, v, a)
        env.step(a)
        assert env.state[0] == x and env.state[1] == v
    task = get_task("mountain_car", bonus=10.0, v0=0.05)
    b = task.make_batch(64, seed=0)
    for _ in range(200):
        live = ~b.done
        out = b.step(b.rule())
        assert np.allclose(out.proxy - out.true, 10.0 * (live & (np.abs(b.v) >= 0.05)))
        assert np.allclose(out.true, np.where(live, -1.0, 0.0))
    assert b.done.all(), "the honest rule reaches the flag within one sub-episode"
    o2 = b.step(b.rule())
    assert np.all(o2.proxy == 0) and np.all(o2.true == 0), "the flag is absorbing with 0 reward"


def test_lunar_lander_bonus_rearms_only_after_a_hop_and_terminal_is_absorbing():
    task = get_task("lunar_lander", bonus=100.0, rearm=20)
    b = task.make_batch(8, seed=1)
    tot_p, tot_t, events = np.zeros(8), np.zeros(8), np.zeros(8)
    for _ in range(500):
        out = b.step(b.bounce_rule())
        tot_p += out.proxy
        tot_t += out.true
        events += out.exploit
    assert (events >= 1).mean() > 0.5, "the scripted bouncer re-arms the bonus"
    assert np.allclose(tot_p - tot_t, 100.0 * events), "proxy - true = b per re-armed touchdown"
    h = task.make_batch(8, seed=2)
    for _ in range(500):
        h.step(h.rule())
    assert h.done.mean() > 0.5
    out = h.step(h.rule())
    assert np.all(out.proxy[h.done] == 0) and np.all(out.true[h.done] == 0)


# --- Part 3: protocol invariants and the harness ----------------------------------------


def test_last_audit_never_corrects_and_episode_end_resets():
    env = AuditedVecEnv(GRID, GP, n_envs=4, seed=0)
    env.reset()
    for t in range(GP.t_ep):
        _, _, d, _ = env.step(np.array([_exploit_actions(t)] * 4))
        if t == GP.t_ep - 2:
            assert (env.n_corr == 4).all(), "caught at each of the four non-final audits"
    assert d.all() and env.t == 0 and (env.n_corr == 0).all() and not env.pending.any()
    assert all(h == () for h in env.history) and all(p is None for p in env.g_params)


def test_training_refuses_to_overwrite_a_run():
    from src.step3.train import resolve_config, train_run
    with tempfile.TemporaryDirectory() as d:
        try:
            train_run(d, resolve_config("grid"))
        except FileExistsError:
            return
    raise AssertionError("train_run wrote into an existing directory")


if __name__ == "__main__":
    run_tests(globals(), "Step 3 -- framework regression and suite tasks")
