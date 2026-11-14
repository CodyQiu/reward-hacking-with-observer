# Step 4 update-bonus campaign: decision log

Procedure: `docs/step4_bonus.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=bonus`.

## Flags for the user

- **barley-04.** Every submit still carries `EXCLUDE=barley-04`, following your standing instruction from the optimal campaign. On 2026-11-14 at 11:42, `sinfo -n barley-04` shows it `allocated` with no reason set, so it may be healthy again. Excluding it costs nothing; say if I should drop it.

- **AS no-reg seed 21: target fixed point does not converge (with and without the bonus).** `results/step4/absent_supervisor/targets/P1eq1_bonus1/seed21.json` has `fixed_point_converged: false`: the iteration alternates between "3 corrections per episode" (V0 8,040.4) and "corrected in round 0, then never again" (V0 7,927.0). The no-bonus target `P1eq1/seed21.json` has the same two-cycle (8,037.4 / 7,926.0). Not a bug: the corrections fitted on each behaviour make the other one optimal. Per rule 2 the last iteration (3 corrections) is used. PPO's verdict comes from the best-response check, which this does not affect.

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

**So far the bonus changes no end state:** in the 6 cells computed (AS ×3, grid ×3), every swap / no-reg target equals its no-bonus target plus exactly b × corrections per episode (same end state, same true return by round, same corrections per episode), and base hides (margin 0) on both envs.

Pending: Tomato (1984516–1984518); tomato_large (1984519–1984521).

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
