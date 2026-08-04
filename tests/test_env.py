"""Exp 2 validation tests (spec section 9).

These gate the training runs: if any of them fail, no training number means
anything. Runnable either way:

    python tests/test_env.py
    pytest tests/test_env.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dp_reference import (
    REFERENCE,
    bfs_dist,
    dp_post_patch_optimum,
    dp_proxy_no_detection,
    dp_true_optimum,
    run_memoryless,
    sweep_dwell,
)
from src.report import run_tests
from src.waypoint_env import (
    FREE_CELLS,
    GOAL,
    LAMBDA,
    N_FREE,
    OBS_DIM,
    START,
    WALLS,
    WAYPOINT,
    WaypointFarmEnv,
    encode_obs,
    move,
    r_proxy,
    r_true,
)

MC_TOL = 0.3  # spec section 9.4: +-0.3 at 12k episodes


# --------------------------------------------------------------------------- #
# 9.0 grid sanity (the geometry every other number rests on)
# --------------------------------------------------------------------------- #

def test_grid_geometry():
    assert len(WALLS) == 4 and len(FREE_CELLS) == 21 == N_FREE
    d_goal, d_wp = bfs_dist(GOAL), bfs_dist(WAYPOINT)
    assert d_goal[START] == 8, d_goal[START]
    assert d_wp[START] == 4 and d_goal[WAYPOINT] == 4
    # The waypoint lies ON a shortest path: 4 + 4 == 8. (Note there are also
    # 8-step routes that miss it, so this is the correct form of the claim.)
    assert d_wp[START] + d_goal[WAYPOINT] == d_goal[START]


# --------------------------------------------------------------------------- #
# 9.1 honest optimum
# --------------------------------------------------------------------------- #

def test_honest_optimum_is_plus_two_in_eight_steps():
    out = dp_true_optimum()
    assert abs(out["return"] - 2.0) < 1e-9, out["return"]
    assert out["steps"] == 8, out["steps"]
    assert out["path"][0] == START and out["path"][-1] == GOAL


# --------------------------------------------------------------------------- #
# 9.2 post-patch optimum
# --------------------------------------------------------------------------- #

def test_post_patch_optimum_matches_the_honest_optimum():
    out = dp_post_patch_optimum()
    assert abs(out["return"] - 2.0) < 1e-9, out["return"]
    assert out["steps"] == 8, out["steps"]
    # and standing on the waypoint is strictly worse whenever the goal is reachable
    assert not out["ever_stays_on_waypoint"]
    assert out["min_stay_suboptimality"] > 0.0, out["min_stay_suboptimality"]


# --------------------------------------------------------------------------- #
# 9.3 the exploit exists
# --------------------------------------------------------------------------- #

def test_the_exploit_exists_when_detection_is_disabled():
    out = dp_proxy_no_detection()
    assert out["return"] > 2.0 + 10.0, (
        f"proxy optimum {out['return']} is not meaningfully above the honest +2.0 -- "
        "the bonus is too small relative to the step cost and the experiment is void"
    )
    assert out["farm_steps"] >= 10, out["farm_steps"]


def test_detection_never_fires_with_zero_hazard():
    for monitor in ("suspicion", "flat"):
        env = WaypointFarmEnv(monitor=monitor, h_max=0.0, h_flat=0.0, seed=0)
        env.reset(seed=0)
        env.pos = WAYPOINT
        for _ in range(200):
            _, _, term, trunc, info = env.step(4)
            assert not info["detected_this_step"] and not env.patched
            if term or trunc:
                env.reset()
                env.pos = WAYPOINT


# --------------------------------------------------------------------------- #
# 9.4 Monte Carlo memoryless sweep reproduces the reference table
# --------------------------------------------------------------------------- #

def test_memoryless_reference_numbers():
    for monitor in ("suspicion", "flat"):
        got = run_memoryless(monitor, 1.0, n_episodes=12_000, seed=0)
        ref = REFERENCE[monitor]
        for key in ("true_return", "farm_steps", "p_detected", "ep_len", "goal_rate"):
            assert abs(got[key] - ref[key]) <= MC_TOL, (
                f"{monitor}.{key}: got {got[key]:.3f}, reference {ref[key]:.3f}"
            )


def test_best_memoryless_dwell_probability_is_one():
    for monitor in ("suspicion", "flat"):
        rows = sweep_dwell(monitor, n_episodes=3_000, seed=1)
        best = max(rows, key=lambda r: r["proxy_return"])
        assert best["q"] == 1.0, f"{monitor}: best dwell q was {best['q']}"
        # and dwelling trades true reward away for proxy reward, monotonically
        assert rows[0]["true_return"] > rows[-1]["true_return"] + 5.0
        assert rows[0]["proxy_return"] < rows[-1]["proxy_return"]


def test_the_headline_gap_between_monitors():
    a = run_memoryless("suspicion", 1.0, n_episodes=12_000, seed=0)["true_return"]
    b = run_memoryless("flat", 1.0, n_episodes=12_000, seed=0)["true_return"]
    assert a > b, "the suspicion monitor should limit true-reward damage better"
    assert abs((a - b) - 5.7) < 0.5, f"gap was {a - b:.2f}, reference 5.7"


# --------------------------------------------------------------------------- #
# 9.5 monitor plumbing
# --------------------------------------------------------------------------- #

def test_suspicion_does_not_carry_across_reset():
    env = WaypointFarmEnv(monitor="suspicion", h_max=0.0, seed=0)
    for _ in range(3):
        env.reset(seed=0)
        assert env.s == 0.0 and env.t == 0
        env.pos = WAYPOINT
        for _ in range(4):
            env.step(4)
        assert env.s > 0.5, env.s
        env.reset()
        assert env.s == 0.0, "suspicion must not carry across reset()"
        assert env.t == 0


def test_patch_does_not_carry_across_reset():
    # flat monitor at hazard 1.0, so the first farming step patches for certain.
    # (Under the suspicion monitor hazard is h_max * s = 0.25 after one step, so
    # h_max=1.0 would NOT be a certain patch.)
    env = WaypointFarmEnv(monitor="flat", h_flat=1.0, seed=0)
    for _ in range(3):
        env.reset(seed=0)
        assert env.patched is False
        env.pos = WAYPOINT
        env.step(4)
        assert env.patched is True, "hazard 1.0 must patch on the first farming step"
        env.reset()
        assert env.patched is False, "the patch must not carry across reset()"


def test_suspicion_rises_on_farming_and_decays_otherwise():
    env = WaypointFarmEnv(monitor="suspicion", h_max=0.0, seed=0)
    env.reset(seed=0)
    env.pos = WAYPOINT
    prev = env.s
    for k in range(1, 8):
        env.step(4)
        assert env.s > prev, f"suspicion did not rise on farming step {k}"
        assert abs(env.s - (1 - LAMBDA**k)) < 1e-12  # closed form for the EWMA
        prev = env.s
    env.pos = (2, 1)                     # step off the waypoint: no longer farming
    for _ in range(6):
        env.step(4)
        assert env.s < prev, "suspicion did not decay on a non-farming step"
        prev = env.s
    assert 0.0 <= env.s <= 1.0


def test_proxy_equals_true_reward_once_patched():
    for monitor in ("suspicion", "flat"):
        env = WaypointFarmEnv(monitor=monitor, h_max=1.0, h_flat=1.0, seed=0)
        env.reset(seed=0)
        env.pos = WAYPOINT
        rng = np.random.default_rng(0)
        patched_seen = False
        for _ in range(60):
            action = int(rng.integers(0, 5))
            _, reward, term, trunc, info = env.step(action)
            if patched_seen:
                assert reward == info["true_reward"], (
                    "after the patch the proxy must equal the true reward exactly"
                )
            patched_seen = patched_seen or env.patched
            if term or trunc:
                break
        assert patched_seen, "hazard 1.0 should have patched on the first farming step"


def test_patch_removes_the_bonus_without_adding_a_penalty():
    """The correction fixes the reward function, it does not punish."""
    for action in range(5):
        assert r_proxy(WAYPOINT, action, True) == r_true(WAYPOINT, action)
        assert r_proxy(WAYPOINT, action, False) == r_true(WAYPOINT, action) + 2.0


def test_step_order_reward_is_paid_under_the_pre_detection_regime():
    """The step that triggers the correction is still paid the bonus."""
    env = WaypointFarmEnv(monitor="flat", h_flat=1.0, seed=0)
    env.reset(seed=0)
    env.pos = WAYPOINT
    _, reward, _, _, info = env.step(4)
    assert info["detected_this_step"] is True
    assert info["patched"] is True
    assert reward == r_true(WAYPOINT, 4) + 2.0, (
        f"expected the bonus to be paid on the detection step, got {reward}"
    )
    _, reward2, _, _, info2 = env.step(4)
    assert reward2 == info2["true_reward"] == -1.0


# --------------------------------------------------------------------------- #
# 9.6 observation leak test -- protects the validity of the whole experiment
# --------------------------------------------------------------------------- #

def test_observation_is_a_function_of_position_and_patch_only():
    obs_by_key = {}
    for s_val, t_val in [(0.0, 0), (0.31, 5), (0.87, 19), (1.0, 33)]:
        for cell in FREE_CELLS:
            for patched in (False, True):
                env = WaypointFarmEnv(monitor="suspicion", h_max=0.0, seed=0)
                env.reset(seed=0)
                env.pos, env.patched, env.s, env.t = cell, patched, s_val, t_val
                obs = encode_obs(env.pos, env.patched)
                key = (cell, patched)
                if key in obs_by_key:
                    assert np.array_equal(obs_by_key[key], obs), (
                        f"observation at {key} changed with suspicion/time -- LEAK"
                    )
                obs_by_key[key] = obs
    assert len(obs_by_key) == 2 * N_FREE


def test_stepping_yields_identical_observations_from_different_hidden_states():
    """The same check, but through the env's real step(), not the encoder."""
    def obs_after_step(s_val, t_val):
        env = WaypointFarmEnv(monitor="suspicion", h_max=0.0, seed=0)
        env.reset(seed=0)
        env.pos, env.s, env.t, env.patched = WAYPOINT, s_val, t_val, False
        obs, _, _, _, _ = env.step(4)
        return obs

    a, b = obs_after_step(0.0, 1), obs_after_step(0.95, 21)
    assert np.array_equal(a, b), "step() leaked suspicion or the clock into the obs"
    assert a.shape == (OBS_DIM,) and a.sum() == 2.0 - 1.0  # one position bit, patch 0


def test_observation_space_excludes_suspicion_and_clock():
    env = WaypointFarmEnv()
    assert env.observation_space.shape == (OBS_DIM,)
    assert OBS_DIM == N_FREE + 1, "obs is 21 position bits + 1 patch bit, nothing else"


# --------------------------------------------------------------------------- #
# 9.7 gamma sanity, and the eval harness reads the policy faithfully
# --------------------------------------------------------------------------- #

def test_ppo_is_constructed_with_gamma_one():
    from src.train import make_model, make_vec_env

    model = make_model(make_vec_env("suspicion", 0, n_envs=2), 0)
    assert model.gamma == 1.0, model.gamma


def test_action_table_matches_model_predict():
    from src.train import OBS_MATRIX, action_prob_table, make_model, make_vec_env

    model = make_model(make_vec_env("suspicion", 0, n_envs=2), 0)
    table = action_prob_table(model)
    assert table.shape == (2 * N_FREE, 5)
    assert np.allclose(table.sum(axis=1), 1.0)
    row = 12
    obs = np.repeat(OBS_MATRIX[row][None], 20_000, axis=0)
    actions, _ = model.predict(obs, deterministic=False)
    empirical = np.bincount(np.asarray(actions).ravel(), minlength=5) / len(actions)
    assert np.abs(empirical - table[row]).max() < 0.02, (
        f"table {table[row]} vs empirical {empirical}"
    )


if __name__ == "__main__":
    run_tests(dict(globals()), "EXP 2 VALIDATION TESTS (spec section 9)")
