# Step 4 update-bonus campaign: decision log

Procedure: `docs/step4_bonus.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=bonus`.

## Flags for the user

- **barley-04.** Every submit still carries `EXCLUDE=barley-04`, following your standing instruction from the optimal campaign. On 2026-11-14 at 11:42, `sinfo -n barley-04` shows it `allocated` with no reason set, so it may be healthy again. Excluding it costs nothing; say if I should drop it.

## Exact predictions

Pending: 12 target jobs (1984510–1984521, seeds 0–2 and 20–22, `results/step4/<env>/targets/<variant>_bonus1/`). For swap and no-reg, each target will be compared with the no-bonus target of the same seed (`results/step4/<env>/targets/<variant>/`): same end state? V0 moved by about 1 × the corrections? corrections per episode changed? For base: does the target hide?

## 2026-11-14, iteration 0 (11:41–11:50): first iteration, targets and wave 1 submitted

- `git pull --no-rebase --no-edit --ff`: fast-forwarded to eb4821a9 (the two new campaigns); then already up to date. The optimal campaign is paused (its log, iteration 185): the queue was empty, no job was cancelled.
- `.venv/bin/python tests/test_step4.py`: **20 tests, 0 failed** (including `test_update_bonus_closed_forms_on_the_step1_grid`, `test_update_bonus_is_paid_where_the_dp_puts_it`, `test_game_key_leaves_out_an_update_bonus_that_is_off`).
- **Targets.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh targets` (dry-run): 12 `run_cmd.sh 36 4 targets_<env>_<variant>_bonus1 ... experiments/step4_targets.py --env <env> --name <variant>_bonus1 --seeds 0 1 2 20 21 22 --set <variant sets> [g.epochs=1000] protocol.update_bonus=1.0` lines (grid without `g.epochs=1000`, as in the optimal campaign). Checked, then `... targets submit` → **1984510–1984521** (grid P2swap / P1eq1 / base, AS P2swap / P1eq1 / base, Tomato P2swap / P1eq1 / base, tomato_large P2swap / P1eq1 / base).
- **Wave 1.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh wave1` (dry-run): 20 `submit.sh 48` lines, seeds 0–2, `results/step4/<env>/bonus/`, each with `protocol.update_bonus=1.0`.
  - Check of the 8 swap / no-reg runs against their reference runs (`.venv/bin/python scripts/farmshare/run_sets.py results/step4/<env>/optimal/<run>`): identical overrides, at the lengths of the doc's table: grid `B1_P2swap_LE+NET+ENT3` 1536, `B1_P1eq1_LN+LR` 6144; AS `B1_P2swap_LN` 3072, `B1_P1eq1_LN+RS` 6144; Tomato `B1_P2swap_LN+ES10+N4` 1536, `B1_P1eq1_LN` 6144; tomato_large `B1_P2swap_LE` 1536, `B1_P1eq1_LN+ES10` 1536 (its reference has since been extended to 3072; the doc's 1536 is used).
  - The 12 base runs: `B1_base_L`, `_LE`, `_LN` per env, the frozen Step 3 config at 1536 episodes (AS 3072), annealed over the last 25%. `LE` lists `ppo.ent_coef` twice (frozen, then 3×); the later one wins, as in the optimal campaign's `LE` runs (e.g. Tomato `O1_P2swap_LE` recorded `ent_coef` 0.1).
  - `... wave1 submit` → **1984522–1984541**: grid 1984522 (`B1_P2swap_LE+NET+ENT3`), 1984523 (`B1_P1eq1_LN+LR`), 1984524–1984526 (`B1_base_L/LE/LN`); AS 1984527 (`B1_P2swap_LN`), 1984528 (`B1_P1eq1_LN+RS`), 1984529–1984531 (base); Tomato 1984532 (`B1_P2swap_LN+ES10+N4`), 1984533 (`B1_P1eq1_LN`), 1984534–1984536 (base); tomato_large 1984537 (`B1_P2swap_LE`), 1984538 (`B1_P1eq1_LN+ES10`), 1984539–1984541 (base).
- Budget: this campaign 32 jobs (≤ 60); with noreg_fail's 8, 40 in all (≤ 110). Cells DONE: 0 of 12.
