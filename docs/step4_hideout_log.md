# Step 4 hideout grid (CAMPAIGN=hideout): decision log

Procedure: `docs/step4_hideout.md`. The env is `grid_hideout`, the Step 1 grid where the audit flags every window step that does not end at the goal or at the hideout H.
- **The exact sweep:** `scripts/farmshare/step4_hideout.sh`. Hideout {near, mid, start} × b {100, 400, 1600} × {base, P1eq1, P2swap, indiff_twin}, seeds 0–2 (and 20–22 at start, b = 100). 4 target jobs. Targets go to `results/step4/grid_hideout/targets/h<hideout>_b<b>_<variant>/`. The map is `bash scripts/farmshare/step4_hideout.sh report`.
- **PPO:** `CAMPAIGN=hideout`, runs `H1_<variant>_<tag>` in `results/step4/grid_hideout/hideout/`.
  - Wave 1 is the default setting (start, b = 100): base, P1eq1, P2swap and indiff_twin2 × L/LE/LN, seeds 0–2, 12 runs.
  - The verdict and rules are those of `docs/step4_optimal.md`. Caps as the grid: 12,288 episodes.
  - Wave 2 is automatic: no-regulariser PPO at each setting where no regulariser does poorly (at most 3).
- **Budget:** at most 24 jobs. Every submit carries `EXCLUDE=barley-04,wheat-06`.

This log is append-only below the three summary sections.

## Status

- **Sweep:** 4 target jobs submitted 2026-11-21 (iteration 0).
- **PPO wave 1:** 12 runs submitted 2026-11-21 (iteration 0).
- Cells DONE: 0 of 4 (base, P1eq1, P2swap, indiff_twin2 at the default setting).

## Flags for the user

- None yet.

## Exact predictions

Pre-registered in `docs/step4_hideout.md` (2026-11-21, before any target):
- **Standard PBRR hides at every setting.**
- **No regulariser and the swap:** corrected once or twice, then honest, at every setting. So the expectation is **no setting where no regulariser does poorly**.
- **The twin:** corrected in round 0, then honest, at every setting (V0 = 5 × the open round; level error 0).

"No regulariser does poorly" at a setting iff at least one seed is not honest by the end: rounds 3 and 4 do not both reach true ≥ honest − 5% of (honest − exploit).

The map (`bash scripts/farmshare/step4_hideout.sh report`) goes here once the targets are in.

## 2026-11-21, iteration 0 (15:30–16:35): the sweep (4 target jobs) and PPO wave 1 (12 runs) submitted

- **Setup.** `git pull --no-rebase --no-edit --ff`: already up to date (`5fb1619`). `.venv/bin/python tests/test_step4.py` 50/50 (including `test_hideout_grid_flags_everything_but_the_goal_and_the_hideout`). `tests/test_step3.py` 13/13.
- **The sweep.** `EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_hideout.sh submit_all` (dry-run, checked: 4 jobs of 6 h, one per variant, each `step4_hideout.sh run <variant>`). With `submit`:
  - base → **2003925**;
  - P1eq1 → **2003926**;
  - P2swap → **2003927**;
  - indiff_twin → **2003928**.
- **PPO wave 1.** `CAMPAIGN=hideout EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh wave1` (dry-run, checked).
  - 12 lines: env `grid_hideout` at its default (hideout START, b = 100), 1536 episodes, `anneal.last=0.25 anneal.floor=0.1`, seeds 0–2, into `results/step4/grid_hideout/hideout/`.
  - Variant settings: none for base; `g.use_regularization=False` for P1eq1; `g.l_minus_on=dispreferred` for P2swap; `g.fine_only=True g.offset=True g.offset_rule=twin twin.all_levels=True` for indiff_twin2.
  - Config settings: `LE` adds `ppo.ent_coef=0.03`, `LN` adds `n_envs=64 ppo.batch_size=1600`.
  - Lines run verbatim. Job ids:
    - `H1_base_L` / `LE` / `LN` → **2003929 / 2003930 / 2003931**;
    - `H1_P1eq1_L` / `LE` / `LN` → **2003932 / 2003933 / 2003934**;
    - `H1_P2swap_L` / `LE` / `LN` → **2003935 / 2003936 / 2003937**;
    - `H1_indiff_twin2_L` / `LE` / `LN` → **2003938 / 2003939 / 2003940**.
- Jobs: hideout 16 (cap 24); 76 in all.
