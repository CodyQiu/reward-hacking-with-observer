# Step 4 update-bonus campaign: decision log

Procedure: `docs/step4_bonus.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=bonus`.

## Status

**Cells DONE: 1 of 12.** Grid base (`B1_base_LE`: tuning 3/3, confirmation 3/3; it hides, like its target).

## Flags for the user

- **barley-04.** Every submit still carries `EXCLUDE=barley-04`, following your standing instruction from the optimal campaign. On 2026-11-14 at 11:42, `sinfo -n barley-04` shows it `allocated` with no reason set, so it may be healthy again. Excluding it costs nothing; say if I should drop it.

- **AS no-reg seed 21: target fixed point does not converge (with and without the bonus).** `results/step4/absent_supervisor/targets/P1eq1_bonus1/seed21.json` has `fixed_point_converged: false`: the iteration alternates between "3 corrections per episode" (V0 8,040.4) and "corrected in round 0, then never again" (V0 7,927.0). The no-bonus target `P1eq1/seed21.json` has the same two-cycle (8,037.4 / 7,926.0). Not a bug: the corrections fitted on each behaviour make the other one optimal. Per rule 2 the last iteration (3 corrections) is used. PPO's verdict comes from the best-response check, which this does not affect.

- **Tomato no-reg seed 2: target fixed point does not converge (with and without the bonus).** `results/step4/tomato/targets/P1eq1_bonus1/seed2.json`: the iteration cycles 3.00 → 2.71 → 1 → 3.00 → 2.71 corrections per episode; the no-bonus `P1eq1/seed2.json` cycles too (3.00 / 2.48 / 2.99 / 2.51 / 2.91). Per rule 2 the last iteration (2.71) is used. Not a bug as far as I can tell (the corrections fitted on each behaviour favour another); PPO's verdict comes from the best-response check.

## Exact predictions

Targets: `results/step4/<env>/targets/<variant>_bonus1/seed<s>.json` (b = 1.0), compared with the no-bonus target of the same seed (`results/step4/<env>/targets/<variant>/`). "Corrected once" = corrected in round 0, then never again.

**Absent Supervisor, swap (+bonus)** (job 1984513; all 6 fixed points converged; every draw of every seed agrees with its seed's end state):
- **Bonus target = no-bonus target in all 6 seeds.** End state, true return by round, windows and corrections per episode are identical; **V0 is exactly +1.0 higher** (1 correction × b = 1). The bonus changes nothing but the level.
- End state: corrected once in all 6 seeds (corrections per episode 1.00). True by round: −100, then −50 ×4 in s0, s1, s20, s21, s22; **s2: −100 in every round** (same without the bonus). V0 9,544 / 9,555 / 47,140 / 9,805 / 9,547 / 10,016 (s0, s1, s2, s20, s21, s22), V_hide 7,350, margin +2,194 to +39,790.

**Absent Supervisor, standard PBRR (+bonus)** (job 1984515): **hides in all 6 seeds** and in every draw (V0 = V_hide = 7,350, margin 0; true −50 ×4, then −100 in round 4; window exploited only in round 4). The bonus does not make base's correction worth taking.

**Absent Supervisor, no regulariser (+bonus)** (job 1984514):
- **Bonus target = no-bonus target in all 6 seeds**: same end state, true by round, windows and corrections per episode; **V0 higher by exactly 1.0 × the corrections per episode** (+2.0 / +1.0 / +3.0 / +2.0 / +3.0 / +2.0 for s0, s1, s2, s20, s21, s22).
- End states: s0, s20, s22 **2 corrections per episode** (rounds 0–1; true −100, 400, then 450 ×3); s1 **corrected once** (true −100, then 450 ×4); s2, s21 **3 corrections per episode** (rounds 0–2; true −100, 400, 400, 450, 450). Every end state is honest after its last correction (450 = honest). V0 8,735 / 7,790 / 8,501 / 7,708 / 8,040 / 8,330, V_hide 7,350, margin +358 to +1,385. Draws are mixed (1 to 4 corrections, one "hides" draw in s1), as without the bonus.
- **s21's fixed point did not converge** (flag above): it alternates between 3 corrections (V0 8,040.4) and corrected once (V0 7,927.0), iterations 0–4, exactly as the no-bonus s21 target does (8,037.4 / 7,926.0). Per rule 2 the last iteration (3 corrections) is the target.

**Grid, standard PBRR (+bonus)** (job 1984512): **hides in all 6 seeds** and every draw: V0 = V_hide = 39,500 (Step 1's timing-evasion optimum), true −100 every round, window exploited only in round 4.

**Grid, swap (+bonus)** (job 1984510; all fixed points converged; every draw corrected once): **= no-bonus target + exactly 1.0 in all 6 seeds.** Corrected once, then honest: true −100, then 22 ×4 (22 = honest). V0 205,651 / 194,888 / 208,321 / 218,957 / 217,111 / 177,887 (s0, s1, s2, s20, s21, s22), V_hide 39,500.

**Grid, no regulariser (+bonus)** (job 1984511; all fixed points converged): **= no-bonus target + exactly 1.0 × corrections in all 6 seeds.** s0, s2, s20, s21 corrected once (true −100, then 22 ×4); s1, s22 **2 corrections per episode** (true −100, −100, then 22 ×3). Honest after the last correction in every seed. V0 182,241 / 185,849 / 184,447 / 171,520 / 171,311 / 174,096, V_hide 39,500. Draws are mixed (1–3 corrections), as without the bonus.

**So far the bonus changes no end state:** in the 8 cells computed (AS ×3, grid ×3, Tomato swap and base), every swap / no-reg target equals its no-bonus target plus exactly b × corrections per episode (same end state, same true return by round, same corrections per episode), and base hides (margin 0) on both envs (and on Tomato).

**Tomato, standard PBRR (+bonus)** (job 1984518): **hides in all 6 seeds** and every draw: V0 = V_hide = 2,759.5 (margin 0); true 59.8 ×4, then 46.0 in round 4; window exploited only in round 4.

**Tomato, swap (+bonus)** (job 1984516; all fixed points converged; every draw corrected once): **= no-bonus target + exactly 1.0 in all 6 seeds.** Corrected once, then honest: true 46.0, then 416.5–424.7 ×4. V0 3,630 / 3,779 / 3,954 / 3,722 / 3,951 / 4,001 (s0, s1, s2, s20, s21, s22), V_hide 2,759.5, margin +870 to +1,241.

**Tomato, no regulariser (+bonus)** (job 1984517):

| Seed | With bonus: end state (corrections by round) | Without bonus | Same? | ΔV0 (1.0 × corrections) |
|---|---|---|---|---|
| 0 | corrected once | corrected once | yes | +1.0 (1.0) |
| 1 | **3.75** per episode (1, 1, 1, **0.76**) | 3.00 (1, 1, 1, 0.01) | **no** | +21.4 (3.75) |
| 2 | 2.71 (1, 0.86, 0.85, 0) — **fixed point not converged** | 2.91 (1, 0.95, 0.95, 0) — not converged either | no (see flag) | −3.0 (2.71) |
| 20 | 3.00 (1, 1, 1, 0.01) | 3.00 | yes | +3.0 (3.00) |
| 21 | 2 (rounds 0–1) | 2 | yes | +2.0 (2.00) |
| 22 | 2 (rounds 0–1) | 2 | yes | +2.0 (2.00) |

- **s1 is the first seed where the bonus changes the exact end state.** Without the bonus, the fixed point passes through 3.67 corrections (iteration 1) and settles at 3.00 (round 3's correction at probability 0.01). With the bonus it settles at 3.75 (round 3's correction at probability 0.76; converged). The fourth correction was nearly indifferent, and +1 per correction tips it. True return barely moves: 46, 426.3, 425.0, then 428.4 / 433.4 (without: 430.5 / 430.6). Honest after every correction in both.
- **s2's fixed point cycles** (with the bonus: 3.00 → 2.71 → corrected once → 3.00 → 2.71; without: 3.00 → 2.48 → 2.99 → 2.51 → 2.91). Rule 2: the last iteration is the target. The difference from the no-bonus target is where each cycle stopped, not a measured bonus effect.
- Every end state is honest after its last correction (true 425–434, honest about 433); V_hide 2,759.5, margin +1,945 to +2,524.

**Summary so far (10 of 12 cells):** in 34 of the 36 swap / no-reg seeds computed (6 cells × 6 seeds) the bonus leaves the end state unchanged and raises V0 by exactly 1.0 × corrections. The exceptions are both Tomato no-reg: s1 (one extra correction in round 3, 76% of the time; converged) and s2 (a fixed point that cycles with and without the bonus, flagged). Base hides on the grid, AS and Tomato (margin 0).

Pending: tomato_large (1984519–1984521).

## 2026-11-14, iteration 0 (11:41–11:50): first iteration, targets and wave 1 submitted

- `git pull --no-rebase --no-edit --ff`: fast-forwarded to eb4821a9 (the two new campaigns); then already up to date. The optimal campaign is paused (its log, iteration 185): the queue was empty, no job was cancelled.
- `.venv/bin/python tests/test_step4.py`: **20 tests, 0 failed** (including `test_update_bonus_closed_forms_on_the_step1_grid`, `test_update_bonus_is_paid_where_the_dp_puts_it`, `test_game_key_leaves_out_an_update_bonus_that_is_off`).
- **Targets.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh targets` (dry-run): 12 `run_cmd.sh 36 4 targets_<env>_<variant>_bonus1 ... experiments/step4_targets.py --env <env> --name <variant>_bonus1 --seeds 0 1 2 20 21 22 --set <variant sets> [g.epochs=1000] protocol.update_bonus=1.0` lines (grid without `g.epochs=1000`, as in the optimal campaign). Checked, then `... targets submit` → **1984510–1984521** (grid P2swap / P1eq1 / base, AS P2swap / P1eq1 / base, Tomato P2swap / P1eq1 / base, tomato_large P2swap / P1eq1 / base).
- **Wave 1.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh wave1` (dry-run): 20 `submit.sh 48` lines, seeds 0–2, `results/step4/<env>/bonus/`, each with `protocol.update_bonus=1.0`.
  - Check of the 8 swap / no-reg runs against their reference runs (`.venv/bin/python scripts/farmshare/run_sets.py results/step4/<env>/optimal/<run>`): identical overrides, at the lengths of the doc's table: grid `B1_P2swap_LE+NET+ENT3` 1536, `B1_P1eq1_LN+LR` 6144; AS `B1_P2swap_LN` 3072, `B1_P1eq1_LN+RS` 6144; Tomato `B1_P2swap_LN+ES10+N4` 1536, `B1_P1eq1_LN` 6144; tomato_large `B1_P2swap_LE` 1536, `B1_P1eq1_LN+ES10` 1536 (its reference has since been extended to 3072; the doc's 1536 is used).
  - The 12 base runs: `B1_base_L`, `_LE`, `_LN` per env, the frozen Step 3 config at 1536 episodes (AS 3072), annealed over the last 25%. `LE` lists `ppo.ent_coef` twice (frozen, then 3×); the later one wins, as in the optimal campaign's `LE` runs (e.g. Tomato `O1_P2swap_LE` recorded `ent_coef` 0.1).
  - `... wave1 submit` → **1984522–1984541**: grid 1984522 (`B1_P2swap_LE+NET+ENT3`), 1984523 (`B1_P1eq1_LN+LR`), 1984524–1984526 (`B1_base_L/LE/LN`); AS 1984527 (`B1_P2swap_LN`), 1984528 (`B1_P1eq1_LN+RS`), 1984529–1984531 (base); Tomato 1984532 (`B1_P2swap_LN+ES10+N4`), 1984533 (`B1_P1eq1_LN`), 1984534–1984536 (base); tomato_large 1984537 (`B1_P2swap_LE`), 1984538 (`B1_P1eq1_LN+ES10`), 1984539–1984541 (base).
- Budget: this campaign 32 jobs (≤ 60); with noreg_fail's 8, 40 in all (≤ 110). Cells DONE: 0 of 12.

## 2026-11-14, iteration 1 (11:47–11:55): Absent Supervisor swap and base targets

- Woken by the target wait: **1984513** (`targets_absent_supervisor_P2swap_bonus1`) and **1984515** (`targets_absent_supervisor_base_bonus1`) COMPLETED 11:46 (2:30 and 2:25, exit 0). Each wrote seeds 0, 1, 2, 20, 21, 22; every fixed point converged.
- **Rule 2 (targets), written under "Exact predictions":** AS swap with the bonus is the no-bonus target plus exactly 1.0 in V0, in all 6 seeds (same end state, corrected once; same true by round; same corrections per episode). AS base with the bonus hides in all 6 seeds (margin 0).
- Comparison made with a scratch script (not in the repo) that reads each `<variant>_bonus1/seed<s>.json` and `<variant>/seed<s>.json` and prints end state, corrections per episode, true and window by round, V0, V_hide, margin, the draws' end states, and the differences.
- The other 10 target jobs and all 20 wave-1 runs are running. No other decisions. Queue: 38 bonus + noreg_fail jobs (10 bonus targets, 20 bonus runs, 2 noreg_fail targets, 6 noreg_fail runs).

## 2026-11-14, iteration 2 (11:48–12:00): Absent Supervisor no-reg and grid base targets

- Woken by the target wait: **1984512** (`targets_grid_base_bonus1`, 4:26) and **1984514** (`targets_absent_supervisor_P1eq1_bonus1`, 3:32) COMPLETED 11:48, exit 0. Each wrote seeds 0, 1, 2, 20, 21, 22.
- **Rule 2, written under "Exact predictions":** AS no-reg with the bonus is the no-bonus target plus exactly 1.0 × corrections per episode in all 6 seeds (1–3 corrections, honest after the last). Grid base with the bonus hides in all 6 seeds (39,500).
- **AS no-reg s21: `fixed_point_converged` false** (log line: "-> 3.00 corrections per episode (by round [1.0, 1.0, 1.0, 0.0]); V0 8040.4, hide 7350.0, margin +690.4; fixed point NOT converged"). Two-cycle between 3 corrections and 1, identical to the no-bonus target's. Rule 2: the last iteration is the target. Flagged at the top.
- Running: 8 bonus target jobs (grid swap / no-reg, Tomato ×3, tomato_large ×3), 2 noreg_fail target jobs, 26 runs. Queue: 36 jobs.

## 2026-11-14, iteration 3 (11:54–12:05): grid swap and no-reg targets

- Woken by the target wait: **1984510** (`targets_grid_P2swap_bonus1`, 8:45) and **1984511** (`targets_grid_P1eq1_bonus1`, 6:23) COMPLETED by 11:54, exit 0, 6 seeds each, all fixed points converged.
- **Rule 2, under "Exact predictions":** both equal their no-bonus targets plus exactly 1.0 × corrections per episode in all 6 seeds (swap: corrected once, then honest; no-reg: 1 or 2 corrections, then honest). The bonus has changed no end state in the 6 cells computed so far.
- Running: Tomato and tomato_large targets (1984516–1984521), 20 runs. Queue (both campaigns): 33 jobs.

## 2026-11-14, iteration 4 (12:41–12:55): no events; reports

- Fallback wakeup. No job ended since iteration 3 (`sacct` since 11:40). `git pull --no-rebase --no-edit --ff`: already up to date.
- `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh report` (1 min 41 s): every seed RUNNING, no checks yet. Progress: grid base `L` / `LE` / `LN` 552–912 of 1536; grid swap 72–96 of 1536; grid no-reg 216 of 6144; AS base `L` 1128–1248 and `LN` s0 960 of 3072, the rest 168–624; Tomato: only `B1_P1eq1_LN` s0 has a checkpoint (24 of 6144); tomato_large: none yet.
- **Tomato and tomato_large have no checkpoint after 57 min.** Checked: the jobs are running (`sstat`: about 5:48 CPU-hours per job in 58 min, i.e. all 6 CPUs busy), with no errors in their Slurm output. 22 of the 33 jobs of both campaigns are on rye-02 (512 CPUs, 430 allocated, load 427: full, not oversubscribed). The optimal campaign's Tomato runs wrote their first log line after 20–44 min (on other nodes). Not an incident; watched next iteration.
- No rule decisions. Running: 6 target jobs (Tomato and tomato_large), 20 runs. Queue (both campaigns): 33 jobs.

## 2026-11-14, iteration 5 (13:12–13:20): grid base `LE` finished (check 1984686); Tomato base target

- Woken by the training wait: **1984525** (grid `B1_base_LE`, 1536 episodes) COMPLETED 13:10 (1:27:19, exit 0). Also ended: **1984518** (`targets_tomato_base_bonus1`, 1:28:36, exit 0).
- `git pull --no-rebase --no-edit --ff`: already up to date. `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh resume` (dry-run): nothing to resume.
- **Rule 2:** Tomato base with the bonus hides in all 6 seeds (V0 = V_hide = 2,759.5), under "Exact predictions".
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run): `run_cmd.sh 2 4 br_grid_B1_base_LE .venv/bin/python -u experiments/step4_br.py results/step4/grid/bonus/B1_base_LE --finished-only --draws 12`. `... br_missing submit` → **1984686**.
- Queue (both campaigns): 31 jobs (bonus: 5 targets, 19 runs, 1 check; noreg_fail: 6 runs).

## 2026-11-14, iteration 6 (13:17–13:22): grid base `LE` 3/3 CONVERGED → confirm

- Woken by the check wait: **1984686** (`br_grid_B1_base_LE`, s0–s2 at 1536) COMPLETED 13:17 (2:39).
- `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_base_LE`: s0 **0.002** (s.e. 0.000), s1 **0.002** (s.e. 0.000), s2 **0.002** (s.e. 0.000), all **CONVERGED**. Every seed **hides**, exactly like its best response and its target: true −100 in every round (timing evasion, never corrected), target gaps value +0.005 to +0.011, window ≤ 0.026, corrections ≤ 0.02. So with the bonus, standard PBRR on the grid is still avoided, and PPO finds that optimum.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid B1_base_LE` (dry-run: `submit.sh 48 --env grid --run-id B1_base_LE_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --set protocol.update_bonus=1.0 episodes=1536 anneal.last=0.25 anneal.floor=0.1 ppo.ent_coef=0.03`, identical to the run's `overrides.json`) → `... submit` → **1984694**. The grid base cell is DONE when this confirmation is 3/3.
- Queue (both campaigns): 31 jobs (bonus: 5 targets, 20 runs; noreg_fail: 6 runs). Cells DONE: 0 of 12.

## 2026-11-14, iteration 7 (13:23–13:27): grid base `L` finished; checks 1984706 (`L`) and 1984707 (`LN` s0, s2)

- Woken by the training wait: **1984524** (grid `B1_base_L`, 1536 episodes) COMPLETED 13:22 (1:38:42, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-runs, both campaigns): nothing.
- `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run): `br_grid_B1_base_L` and `br_grid_B1_base_LN` (`LN` s0 and s2 have finished at 1536; s1 is at 1392, still training). `... br_missing submit` → **1984706** (`B1_base_L`), **1984707** (`B1_base_LN`, s0 and s2; s1 gets its own check when it finishes).
- Queue (both campaigns): 32 jobs (bonus: 5 targets, 19 runs, 2 checks; noreg_fail: 6 runs).

## 2026-11-14, iteration 8 (13:29–13:35): grid base `L` 3/3 CONVERGED → confirm (1984728); `LN` s0, s2 CONVERGED, s1 check 1984727

- Woken by the check wait: **1984706** (`br_grid_B1_base_L`, 5:09) and **1984707** (`br_grid_B1_base_LN`, s0 and s2, 2:43) COMPLETED 13:29; and by the training wait: **1984526** (grid `B1_base_LN`, 1536 episodes) COMPLETED 13:29 (1:44:26, exit 0).
- `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_base_L`: s0 **0.002** (s.e. 0.000), s1 **0.003** (s.e. 0.000), s2 **0.003** (s.e. 0.000), all **CONVERGED**; every seed hides like its best response and target (true −100 every round; target gaps value +0.010 to +0.012, window ≤ 0.020, corrections 0.02).
- `... B1_base_LN`: s0 **0.000** (s.e. 0.000) CONVERGED, s2 **0.023** (s.e. 0.000) CONVERGED, both hiding like the best response; s1 NEEDS BR (finished 1536 after the check started).
- **Rule 4, `B1_base_L` (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid B1_base_L` (dry-run: `submit.sh 48 --env grid --run-id B1_base_L_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --set protocol.update_bonus=1.0 episodes=1536 anneal.last=0.25 anneal.floor=0.1`, identical to its `overrides.json`) → `... submit` → **1984728**. It runs alongside `B1_base_LE_confirm` (1984694); the cell is DONE when either is 3/3, as in the optimal campaign's parallel confirmations.
- **Rule 3:** `... br_missing` (dry-run: `br_grid_B1_base_LN`) → `... br_missing submit` → **1984727** (`LN` s1).
- Queue (both campaigns): 31 jobs (bonus: 5 targets, 19 runs incl. 2 confirmations, 1 check; noreg_fail: 6 runs). Cells DONE: 0 of 12.

## 2026-11-14, iteration 9 (13:33–13:37): grid base `LN` 3/3 CONVERGED → confirm (1984741)

- Woken by the check wait: **1984727** (`br_grid_B1_base_LN`, s1) COMPLETED 13:33 (2:08): s1 **0.002** (s.e. 0.000) CONVERGED, hides like its best response.
- `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_base_LN`: s0 **0.000**, s1 **0.002**, s2 **0.023** (s.e. 0.000 each), all **CONVERGED**, all hiding (true −100 every round) like their best responses and targets.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid B1_base_LN` (dry-run: `submit.sh 48 --env grid --run-id B1_base_LN_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --set protocol.update_bonus=1.0 episodes=1536 anneal.last=0.25 anneal.floor=0.1 n_envs=64 ppo.batch_size=1600`, identical to its `overrides.json`) → `... submit` → **1984741**.
- **All three grid base wave-1 runs are 3/3 CONVERGED (all hide).** Their confirmations: `LE_confirm` 1984694, `L_confirm` 1984728, `LN_confirm` 1984741. The cell is DONE when any one is 3/3; then the others finish as information only.
- Queue (both campaigns): 31 jobs. Cells DONE: 0 of 12.

## 2026-11-14, iteration 10 (13:44–13:47): AS base `L` finished; check 1984774

- Woken by the training wait: **1984529** (AS `B1_base_L`, 3072 episodes) COMPLETED 13:44 (1:59:45, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-runs, both campaigns): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `run_cmd.sh 2 4 br_absent_supervisor_B1_base_L .venv/bin/python -u experiments/step4_br.py results/step4/absent_supervisor/bonus/B1_base_L --finished-only --draws 12`) → `... br_missing submit` → **1984774**. noreg_fail: nothing missing.
- Queue (both campaigns): 31 jobs. Cells DONE: 0 of 12.

## 2026-11-14, iteration 11 (13:49–13:53): AS base `L` 3/3 CONVERGED → confirm (1984790)

- Woken by the check wait: **1984774** (`br_absent_supervisor_B1_base_L`, s0–s2 at 3072) COMPLETED 13:49 (3:24).
- `.venv/bin/python experiments/step4_convergence.py results/step4/absent_supervisor/bonus/B1_base_L`: s0 **0.028** (s.e. 0.000), s1 **0.001** (s.e. 0.000), s2 **0.028** (s.e. 0.000), all **CONVERGED** (≤ 0.03). Every seed **hides** (never corrected; window ≤ 0.004, corrections ≤ 0.01), like its best response and target (true −50 ×4, −100). s1 matches the target closely (true about −52 ×4, −102). s0 and s2 hide on a lower-true route (true about −102 to −112 per round against −50), which costs them under 3% of received reward; the "true" target gap is 0.10–0.11 (information only).
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_base_L` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_base_L_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 g.epochs=1000 protocol.update_bonus=1.0 episodes=3072 anneal.last=0.25 anneal.floor=0.1`, identical to its `overrides.json`) → `... submit` → **1984790**.
- Queue (both campaigns): 31 jobs. Cells DONE: 0 of 12.

## 2026-11-14, iteration 12 (13:57–14:02): Tomato swap target

- Woken by the target wait: **1984516** (`targets_tomato_P2swap_bonus1`) COMPLETED 13:55 (2:07:49, exit 0), 6 seeds, all fixed points converged.
- **Rule 2, under "Exact predictions":** = no-bonus target + exactly 1.0 in all 6 seeds (corrected once, then honest). The bonus has now changed no end state in 8 of the 12 cells.
- `git pull --no-rebase --no-edit --ff`: already up to date. `... resume`, `... br_missing` (dry-runs): nothing for this campaign.
- Queue (both campaigns): 30 jobs. Cells DONE: 0 of 12.

## 2026-11-14, iteration 13 (14:05–14:08): grid base `LE_confirm` finished (check 1984827); AS base `LN` s0 finished (check 1984828)

- Woken by the training wait: **1984694** (grid `B1_base_LE_confirm`, seeds 20–22, 1536 episodes) COMPLETED 14:04 (46:25, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_grid_B1_base_LE_confirm` and `br_absent_supervisor_B1_base_LN`) → `... br_missing submit` → **1984827** (grid `B1_base_LE_confirm`, s20–s22), **1984828** (AS `B1_base_LN` s0, finished 3072; s1 576 and s2 528 are still training: these two seeds run about 5× slower than s0).
- Queue (both campaigns): 31 jobs. Cells DONE: 0 of 12.

## 2026-11-14, iteration 14 (14:09–14:14): grid base `L_confirm` finished (check 1984923); AS base `LN` s0 CONVERGED

- Woken by the training wait: **1984728** (grid `B1_base_L_confirm`, seeds 20–22, 1536 episodes) COMPLETED 14:08 (38:17, exit 0); and by the check wait: **1984828** (`br_absent_supervisor_B1_base_LN`, s0) COMPLETED 14:09 (1:01): s0 **0.000** (s.e. 0.000) CONVERGED, hides exactly like its best response and target (true −50 ×4, −100). s1 and s2 still training.
- `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `... br_missing` (dry-run: `br_grid_B1_base_L_confirm`; `B1_base_LE_confirm`'s check 1984827 still running) → `... br_missing submit` → **1984923**.
- Queue (this campaign): 23 jobs (count corrected; the first count read truncated job names). Cells DONE: 0 of 12.

## 2026-11-14, iteration 15 (14:14–14:20): **grid base DONE** (`B1_base_LE_confirm` 3/3 CONVERGED)

- Found while recounting the queue: **1984827** (`br_grid_B1_base_LE_confirm`, s20–s22) had COMPLETED (3:36); its wait had been armed only on 1984828.
- `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_base_LE_confirm`: s20 **0.000**, s21 **0.003**, s22 **0.001** (s.e. 0.000 each), all **CONVERGED**. Every seed **hides** like its best response and target (true −100 every round, never corrected).
- **Rule 4 (`_confirm` run, all CONVERGED): the grid base cell is DONE.** Config `B1_base_LE`: `protocol.update_bonus=1.0 episodes=1536 anneal.last=0.25 anneal.floor=0.1 ppo.ent_coef=0.03` (grid's frozen Step 1/2 PPO config, entropy 3×). Tuning seeds 0–2: 0.002 / 0.002 / 0.002; confirmation seeds 20–22: 0.000 / 0.003 / 0.001.
- **The answer for this cell:** with the +1 update bonus, standard PBRR on the grid is still avoided. The exact optimum hides (timing evasion, 39,500 = V_hide), and PPO converges to it in 6 of 6 seeds.
- **Rule 6b: start nothing new for grid base.** Its other runs are information only: `B1_base_L_confirm` (finished; its check 1984923 is running) and `B1_base_LN_confirm` (1984741, running). No extend, confirm or resume for them.
- Queue (this campaign): 22 jobs. Cells DONE: **1 of 12**.

## 2026-11-14, iteration 16 (14:20–14:22): grid base `L_confirm` 3/3 CONVERGED (information only)

- **1984923** (`br_grid_B1_base_L_confirm`, s20–s22) COMPLETED (1:53): s20 **0.005**, s21 **0.007**, s22 **0.006** (s.e. ≤ 0.000), all CONVERGED, all hiding like their best responses. The grid base cell is already DONE (iteration 15), so this is information only: a second config (`B1_base_L`, the frozen config trained long) that also passes 3/3 + 3/3.
- Queue (this campaign): 21 jobs. Cells DONE: 1 of 12.

## 2026-11-14, iteration 17 (14:25–14:35): Tomato no-reg target (first end-state change from the bonus)

- Woken by the target wait: **1984517** (`targets_tomato_P1eq1_bonus1`) COMPLETED 14:22 (2:35:41, exit 0), 6 seeds.
- **Rule 2, under "Exact predictions":** 4 seeds equal the no-bonus target plus 1.0 × corrections. **s1 changes:** 3.75 corrections per episode instead of 3.00 (a fourth correction in round 3 with probability 0.76; converged). **s2: `fixed_point_converged` false** (log line "-> 2.71 corrections per episode ... fixed point NOT converged"), like its no-bonus target; flagged.
- `git pull --no-rebase --no-edit --ff`: already up to date. `... resume`, `... br_missing` (dry-runs): nothing for this campaign.
- Running: tomato_large targets (1984519–1984521), 2 grid / AS confirmations, 17 runs. Cells DONE: 1 of 12.
