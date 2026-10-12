"""Step 2 validation: Eq 3 / the neural correction, the PBRR environment and
overseer, the idealised DP, and the no-overwrite guard.

Run as ``.venv/bin/python tests/test_step2.py`` (or under pytest).
"""

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audit_grid import BASE, build_tables
from src.audit_pbrr import N_LEVELS, PBRRAuditEnv, PBRROverseer, encode_obs2, obs_dim2
from src.pbrr_core import GConfig, Traj, _reg_coef, build_design, fit_correction, loss_numpy
from src.pbrr_grid import make_traj, rollout_subepisode, train_bc_reference, transition_features
from src.report import run_tests
from src.step2_dp import evaluate_levels, solve_levels

STAY, UP, DOWN, LEFT, RIGHT = range(5)
SMALL_G = GConfig(n_layers=3, width=64, epochs=50, lr=1e-3)


def _mdp1_pairs():
    proxy = np.array([10.0, 6.0, 7.0, 9.0])
    true = np.array([2.0, 4.0, 3.0, 8.0])

    def t(a):
        c = np.zeros(4)
        c[a] = 1
        return Traj(c, proxy[a], true[a], 1)
    return proxy, [(t(0), t(2), 1.0)]


def _exploit_path_actions():
    E = BASE.exploit
    return [DOWN] * E[0] + [RIGHT] * E[1]


# --- Eq 3 -----------------------------------------------------------------------------


def test_fit_reports_the_eq3_objective_it_minimised():
    rng = np.random.default_rng(0)
    trajs = [Traj(rng.integers(0, 4, 12).astype(float), float(rng.normal() * 5),
                  float(rng.normal()), 12) for _ in range(8)]
    pairs = [(trajs[i], trajs[j], float(rng.random() < 0.5)) for i in range(4) for j in range(4, 8)]
    X = np.eye(12, dtype=np.float32)
    g, info = fit_correction(pairs, X, SMALL_G, seed=0)
    assert abs(info["loss"] - info["loss_eq3_check"]) < 1e-3 * max(1.0, abs(info["loss"])), info


def test_partition_and_lambda_follow_e6_and_the_code():
    def t(proxy, true):
        return Traj(np.array([1.0, 0.0]), proxy, true, 1)
    agree = (t(5.0, 0.0), t(1.0, 0.0), 0.0)        # proxy prefers tau1, label says tau1
    disagree = (t(5.0, 0.0), t(1.0, 0.0), 1.0)     # proxy prefers tau1, label says tau2
    d = build_design([agree, agree, disagree])
    assert d.n_agree == 2
    assert np.isclose(_reg_coef(d, GConfig()), 10.0 / 2)
    d0 = build_design([disagree])
    assert _reg_coef(d0, GConfig(no_agree="skip")) == 0.0          # released code
    assert _reg_coef(d0, GConfig(no_agree="max1")) == 10.0         # lambda = 10 / max(1, |D+|)
    assert _reg_coef(d, GConfig(use_regularization=False)) == 0.0   # Eq 1
    # D-: only the PREFERRED trajectory (tau2) is regularised
    c = np.array([1.0, 0.0])
    t1, t2 = Traj(c, 5.0, 0.0, 1), Traj(np.array([0.0, 1.0]), 1.0, 0.0, 1)
    dd = build_design([(t1, t2, 1.0)])
    assert np.allclose(dd.reg, [0.0, 1.0])


def test_numpy_loss_is_bce_plus_ridge():
    proxy, pairs = _mdp1_pairs()
    d = build_design(pairs)
    g = np.zeros(len(d.present))
    expected = np.log(1 + np.exp(-(7.0 - 10.0)))   # BCE with label 1 on logit r(s3) - r(s1)
    assert np.isclose(loss_numpy(g, d, GConfig()), expected)


def test_l_minus_mechanism_on_the_papers_minimal_mdp():
    proxy, pairs = _mdp1_pairs()
    X = np.eye(4, dtype=np.float32)
    g_max1, _ = fit_correction(pairs, X, GConfig(no_agree="max1"), seed=0)
    g_skip, _ = fit_correction(pairs, X, GConfig(no_agree="skip"), seed=0)
    assert abs(g_max1[2]) < 0.5 and proxy[0] + g_max1[0] < proxy[2] + g_max1[2]
    assert g_skip[2] > 1.0     # unregularised: the fix comes partly from raising the preferred


def test_counts_dot_g_equals_the_per_step_sum():
    rng = np.random.default_rng(1)
    g = rng.normal(size=BASE.n_pos * 5)
    P, A = rollout_subepisode(lambda t, p, f: np.full((len(p), 5), 0.2), 4, rng)
    for p, a in zip(P, A):
        tr = make_traj(p, a)
        assert np.isclose(tr.counts @ g, g[p * 5 + a].sum())
        tb = build_tables(BASE)
        assert np.isclose(tr.proxy, tb.reward[p, a, 0].sum()) and np.isclose(tr.true, tb.true[p, a].sum())


def test_transition_features_are_s_next_s_action_one_hots():
    X = transition_features(BASE)
    tb = build_tables(BASE)
    assert X.shape == (BASE.n_pos * 5, 2 * BASE.n_pos + 5)
    assert (X.sum(axis=1) == 3).all()
    s, a = BASE.idx((4, 8)), RIGHT
    row = X[s * 5 + a]
    assert row[s] == 1 and row[BASE.n_pos + tb.next_pos[s, a]] == 1 and row[2 * BASE.n_pos + a] == 1


# --- environment and overseer ---------------------------------------------------------


def test_correction_lands_next_sub_episode_and_resets_at_episode_end():
    env = PBRRAuditEnv(BASE, seed=0)
    env.reset()
    path = _exploit_path_actions()
    E = BASE.idx(BASE.exploit)
    for t in range(BASE.t_sub):                       # dwell through the window of k = 0
        _, r, _, _, info = env.step(path[t] if t < len(path) else STAY)
    assert info["detected"] and env.n_corr == 1 and env.pending and env.history == (0,)
    assert r == 99.0                                  # the step that triggered it still pays the proxy
    g = np.zeros((BASE.n_pos, 5))
    g[E, STAY] = -500.0
    env.set_correction(g)
    assert not env.pending
    for t in range(len(path)):
        env.step(path[t])
    _, r, _, _, info = env.step(STAY)
    assert r == 99.0 - 500.0 and info["proxy_reward"] == 99.0 and info["received_reward"] == r
    for t in range(BASE.t_sub * 3 + (BASE.t_sub - len(path) - 1)):
        _, _, term, _, _ = env.step(STAY)
    assert term and env.n_corr <= N_LEVELS - 1
    env.reset()
    assert env.t == 0 and env.n_corr == 0 and env.history == () and not env.g.any()


def test_the_last_audit_never_triggers_a_correction():
    env = PBRRAuditEnv(BASE, seed=0)
    env.reset()
    env.t = BASE.t_ep - BASE.t_sub                  # jump to the last sub-episode
    path = _exploit_path_actions()
    for t in range(BASE.t_sub):
        _, _, term, _, info = env.step(path[t] if t < len(path) else STAY)
    assert term and info["detected"] and env.n_corr == 0 and not env.pending


def test_observation_encoding():
    o = encode_obs2(BASE, t=237, pos=BASE.idx((4, 9)), n_corr=2, flagged=1)
    assert o.shape == (obs_dim2(BASE),) == (225 + 100 + 5 + 5 + 1,)
    assert o[:225].sum() == 1 and o[225:325].sum() == 1 and o[225 + 37] == 1
    assert o[325 + 2] == 1 and o[330 + 2] == 1 and o[335] == 1


def test_reference_policy_is_safe_and_reaches_goal():
    ref, _ = train_bc_reference(seed=0)
    rng = np.random.default_rng(0)
    P, A = rollout_subepisode(ref, 400, rng)
    tb = build_tables(BASE)
    touches = np.mean([tb.bonus[p, a, 0].any() for p, a in zip(P, A)])
    goal = np.mean([make_traj(p, a).true > -100 for p, a in zip(P, A)])
    assert touches < 0.01 and goal > 0.9, (touches, goal)


def test_overseer_round_fits_and_pushes_a_correction_to_the_caught_envs():
    from sbx import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv

    env = DummyVecEnv([lambda: PBRRAuditEnv(BASE, 0.01, seed=0), lambda: PBRRAuditEnv(BASE, 0.01, seed=1)])
    model = PPO("MlpPolicy", env, n_steps=BASE.t_sub, batch_size=100, seed=0, gamma=1.0)
    ref, _ = train_bc_reference(seed=0)
    P, A = rollout_subepisode(ref, 3, np.random.default_rng(0))
    over = PBRROverseer(BASE, [make_traj(p, a) for p, a in zip(P, A)], SMALL_G.with_(no_agree="max1"), k=3)
    model.learn(total_timesteps=2 * BASE.t_sub, callback=over)
    env.set_attr("pending", True, indices=[0])            # pretend env 0 was caught in sub-episode 0
    env.set_attr("history", (0,), indices=[0])
    env.set_attr("n_corr", 1, indices=[0])
    over._run_pending_rounds()
    g0, g1 = env.get_attr("g")
    assert np.abs(g0).sum() > 0 and not np.abs(g1).any()
    assert not env.get_attr("pending")[0]
    assert len(over.rounds) == 1 and over.rounds[0]["n_pairs"] == 9


# --- idealised DP and bookkeeping -----------------------------------------------------


def test_level_dp_reproduces_step1_with_the_oracle_patch():
    tb = build_tables(BASE)
    R = np.stack([tb.reward[:, :, 0]] + [tb.reward[:, :, 1]] * 4)
    V, pol = solve_levels(BASE, R)
    assert V[0, tb.start, 0, 0] == 39500.0
    ev = evaluate_levels(BASE, R, pol)
    assert ev["received"].tolist() == [7700.0] * 4 + [8700.0] and ev["levels"].max() == 0


def test_training_refuses_to_overwrite_a_run():
    from src.step2_train import resolve_config, train_run

    d = tempfile.mkdtemp()
    try:
        train_run(d, resolve_config({"timesteps": 1}))
    except FileExistsError:
        return
    raise AssertionError("an existing run directory was not protected")


if __name__ == "__main__":
    run_tests(globals(), "Step 2 -- PBRR core, environment, overseer, idealised DP")
