# Step 4 exact-indifference campaigns (indiff, indiff_pool): decision log

Procedure: `docs/step4_indiff.md`. Two campaigns, one log:
- `CAMPAIGN=indiff`: the exact rule, `g.fine_only=True g.offset=True g.offset_rule=exact`;
- `CAMPAIGN=indiff_pool`: M estimated from a pool of plays, `g.offset_rule=pool`.

**Targets only.** No PPO for either campaign until the user says so (the user, 2026-11-17).

This log is append-only below the three summary sections. Every driver command runs with `CAMPAIGN=indiff` or `CAMPAIGN=indiff_pool`, and the jobs count toward the 110 total.

## Status

**Targets submitted 2026-11-17 01:41: 11 jobs per campaign (iteration 0). None has finished yet.**
- grid, AS, Tomato, Taxi and Boat Race: one job each, seeds 0–2 and 20–22.
- tomato_large: one job per seed.

The verdict per seed (A1–A3, level errors) comes from `experiments/step4_indiff_check.py`. It goes under "Exact predictions" as targets finish.

## Flags for the user

- **Excluded nodes.** Every submit carries `EXCLUDE=barley-04,wheat-06`.
  - barley-04 is your standing instruction from the optimal campaign.
  - wheat-06 went down on 2026-11-16 (`sinfo`: "Not responding"). That killed the bonus campaign's Tomato no-reg `LN_confirm` (NODE_FAIL; flagged in `docs/step4_bonus_log.md` and held for you). wheat-06 shows `mixed-` again now; say if I should drop the exclusion.

## Exact predictions

The pre-registered predictions are in `docs/step4_indiff.md` ("Predictions"):
- grid, AS and Tomato: corrected in round 0, then honest, in 6/6 seeds.
- Taxi: the same in 4/6 (not s21, s22).
- Boat Race: the same in 5/6 (not s20).
- tomato_large: corrected again in round 1; after that unknown.

The criteria are A1 (no hiding), A2 (honest after the last correction) and A3 (a best round every round).

Verdicts: none yet. Targets go to `results/step4/<env>/targets/indiff/` and `results/step4/<env>/targets/indiff_pool/`.

## 2026-11-17, iteration 0 (01:35–01:42): both campaigns' targets submitted

- **Starting point.**
  - `git pull --no-rebase --no-edit --ff`: already up to date. The campaign's code and doc arrived in 40c7f94c2 ("Step 4 indiff, third review"), merged in d44cbe30d.
  - `.venv/bin/python tests/test_step4.py`: **38 tests, 0 failed**.
- **indiff (the exact rule).**
  - Dry-run: `CAMPAIGN=indiff EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh targets`. It listed 11 jobs, each `run_cmd.sh 36 4 targets_<env>_indiff[_s<seed>] … step4_targets.py --env <env> --name indiff --seeds … --set g.fine_only=True g.offset=True g.offset_rule=exact`, plus `g.epochs=1000` outside the grid and `task.obs=onehot` for Taxi:
    - grid, AS, Tomato, Taxi and Boat Race: one job each, seeds 0 1 2 20 21 22;
    - tomato_large: seeds 0, 1, 2, 20, 21 and 22, one job each.
  - Submitted: `... targets submit` →
    - **1992072** (grid), **1992073** (AS), **1992074** (Tomato);
    - **1992075–1992080** (tomato_large s0, s1, s2, s20, s21, s22);
    - **1992081** (Taxi), **1992082** (Boat Race).
- **indiff_pool (M estimated).**
  - Dry-run: `CAMPAIGN=indiff_pool EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh targets`. It listed the same 11 jobs with `--name indiff_pool` and `g.offset_rule=pool`.
  - Submitted: `... targets submit` →
    - **1992083** (grid), **1992084** (AS), **1992085** (Tomato);
    - **1992086–1992091** (tomato_large s0, s1, s2, s20, s21, s22);
    - **1992092** (Taxi), **1992093** (Boat Race).
- **Budget.** 22 jobs for these two campaigns; all my jobs 56 (limit 110).
- **Next.** As targets finish, run `.venv/bin/python experiments/step4_indiff_check.py results/step4/*/targets/indiff/ results/step4/*/targets/indiff_pool/` and record every seed's verdict under "Exact predictions". No PPO.
