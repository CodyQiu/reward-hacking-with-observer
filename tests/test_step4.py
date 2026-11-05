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


def test_anneal_factor():
    from src.step3.train import _anneal_factor
    an = {"last": 0.25, "floor": 0.1}
    assert _anneal_factor({}, 50, 100) == 1.0 and _anneal_factor({"last": 0.0, "floor": 0.1}, 99, 100) == 1.0
    assert _anneal_factor(an, 75, 100) == 1.0
    assert abs(_anneal_factor(an, 87.5, 100) - 0.55) < 1e-12 and abs(_anneal_factor(an, 100, 100) - 0.1) < 1e-12


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
    results/step3/tomato_large does not exist yet (one missing path used to fail the whole git add), and a
    modified tracked file (a running job's runs.csv) does not block the pull."""
    import shutil, subprocess, tempfile
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git = lambda cwd, *a: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout
    with tempfile.TemporaryDirectory() as tmp:
        remote, work = os.path.join(tmp, "remote.git"), os.path.join(tmp, "work")
        git(tmp, "init", "-q", "--bare", remote)
        git(tmp, "clone", "-q", remote, work)
        for k, v in (("user.name", "t"), ("user.email", "t@t")):
            git(work, "config", k, v)
        os.makedirs(os.path.join(work, "scripts", "farmshare"))
        shutil.copy(os.path.join(repo, "scripts", "farmshare", "step4_commit.sh"), os.path.join(work, "scripts", "farmshare"))
        with open(os.path.join(work, "runs.csv"), "w") as fh:
            fh.write("a\n")
        git(work, "add", "-A"); git(work, "commit", "-qm", "init"); git(work, "push", "-q", "origin", "HEAD")
        os.makedirs(os.path.join(work, "docs"))
        with open(os.path.join(work, "docs", "step4_optimal_log.md"), "w") as fh:
            fh.write("log\n")
        with open(os.path.join(work, "runs.csv"), "a") as fh:
            fh.write("b\n")                                   # modified, not to be committed
        out = subprocess.run(["bash", "scripts/farmshare/step4_commit.sh", "msg"], cwd=work, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        assert "docs/step4_optimal_log.md" in git(remote, "ls-tree", "-r", "--name-only", "HEAD")
        assert git(work, "status", "--porcelain").strip() == "M runs.csv"


if __name__ == "__main__":
    run_tests(globals(), "Step 4 -- PBRR variants and the tabular fit")
