# Step 4 update-bonus campaign: decision log

Procedure: `docs/step4_bonus.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=bonus`.

## Status

**Cells DONE: 4 of 12.** Grid swap (`B1_P2swap_LE+NET+ENT3`: tuning 3/3 at 1536, confirmation 3/3 at 3072 after one extension; corrected once, then honest, like its target). AS swap (`B1_P2swap_LN`: tuning 3/3, confirmation 3/3; corrected once, then never again, like its target; after the correction the route is a near-tie between honest and −50, see flag). Grid base (`B1_base_LE`: tuning 3/3, confirmation 3/3; hides, like its target). AS base (`B1_base_L`: tuning 3/3, confirmation 3/3; hides, like its target; 4 of its 6 seeds pass at 0.027–0.028, just under 0.03, see iteration 19).

## Flags for the user

- **barley-04.** Every submit still carries `EXCLUDE=barley-04`, following your standing instruction from the optimal campaign. On 2026-11-14 at 11:42, `sinfo -n barley-04` shows it `allocated` with no reason set, so it may be healthy again. Excluding it costs nothing; say if I should drop it.

- **AS no-reg seed 21: target fixed point does not converge (with and without the bonus).** `results/step4/absent_supervisor/targets/P1eq1_bonus1/seed21.json` has `fixed_point_converged: false`: the iteration alternates between "3 corrections per episode" (V0 8,040.4) and "corrected in round 0, then never again" (V0 7,927.0). The no-bonus target `P1eq1/seed21.json` has the same two-cycle (8,037.4 / 7,926.0). Not a bug: the corrections fitted on each behaviour make the other one optimal. Per rule 2 the last iteration (3 corrections) is used. PPO's verdict comes from the best-response check, which this does not affect.

- **Tomato no-reg seed 2: target fixed point does not converge (with and without the bonus).** `results/step4/tomato/targets/P1eq1_bonus1/seed2.json`: the iteration cycles 3.00 → 2.71 → 1 → 3.00 → 2.71 corrections per episode; the no-bonus `P1eq1/seed2.json` cycles too (3.00 / 2.48 / 2.99 / 2.51 / 2.91). Per rule 2 the last iteration (2.71) is used. Not a bug as far as I can tell (the corrections fitted on each behaviour favour another); PPO's verdict comes from the best-response check.

- **AS swap: after its correction, honest play and a −50/−100 route are a near-tie, and the best response picks either, depending on the seed (with and without the bonus).** The target (fitted on the exact optimum's play) is "corrected once, then true −50 ×4" (s2: −100). The paired best-response checks at 3072 (fitted on PPO's own play, `results/step4/absent_supervisor/{optimal/O1_P2swap_LN,bonus/B1_P2swap_LN}/step4_br/seed<s>_ep3072.json`) pick, by seed 0 / 1 / 2: without the bonus **honest 450 / −50 / −50**; with the bonus **−50 / honest 450 / honest 450**. Across the six checks the best response receives 2,247–2,392 per round after the correction whichever route it takes, so the two routes are close in received reward (a direct same-seed comparison of the two routes is not in these files). PPO is within 0–2% of its best response in all six. So "is the swap's optimum honest after its correction in AS?" has no single answer here: it depends on the draw / fit, which is the same ambiguity the optimal campaign's AS swap cell had. Not a bonus effect; reported for the answer, nothing changed.

- **Wave 2 for AS no-reg skips the `RS` factor (iteration 32).** The base `B1_P1eq1_LN+RS` already has `reward_scale=0.01625`, which is exactly what `RS` sets (0.25 × AS's Phase A reward_scale), so `LN+RS+RS` would rerun the base config on the same seeds. I submitted the other five factors (LR, GL, NET, EP, AN). If you want a different reading of `RS` here (e.g. a further 0.25×, 0.0040625), say so and I'll add it.

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

**Summary so far (11 of 12 cells):** in 40 of the 42 swap / no-reg seeds computed (7 cells × 6 seeds) the bonus leaves the end state unchanged and raises V0 by exactly 1.0 × corrections. The exceptions are both Tomato no-reg: s1 (one extra correction in round 3, 76% of the time; converged) and s2 (a fixed point that cycles with and without the bonus, flagged). Base hides on the grid, AS, Tomato and tomato_large (margin 0).

**tomato_large, swap (+bonus)** (job 1984519; all fixed points converged; every draw corrected once): **= no-bonus target + exactly 1.0 in all 6 seeds.** Corrected once, then honest: true 65, then 482.9–501.4 ×4. V0 4,877 / 5,002 / 5,119 / 5,692 / 5,330 / 4,826 (s0, s1, s2, s20, s21, s22), V_hide 3,686.8, margin +1,139 to +2,005.

**tomato_large, standard PBRR (+bonus)** (job 1984521): **hides in all 6 seeds** and every draw: V0 = V_hide = 3,686.8 (margin 0); true 84.2 ×4, then 65.0 in round 4; window exploited only in round 4.

**Base hides in all four environments with the bonus** (grid, AS, Tomato, tomato_large; 24 of 24 seeds, margin 0): +1 per update never makes a standard-PBRR correction worth taking.

Pending: tomato_large no-reg (1984520; running for 19.5 h).

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

## 2026-11-14, iteration 18 (14:54–14:57): AS base `L_confirm` finished; check 1985035

- Woken by the training wait: **1984790** (AS `B1_base_L_confirm`, seeds 20–22, 3072 episodes) COMPLETED 14:54 (55:13, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_base_L_confirm`) → `... br_missing submit` → **1985035**. The AS base cell is DONE if this is 3/3.
- Queue (this campaign): 21 jobs. Cells DONE: 1 of 12.

## 2026-11-14, iteration 19 (15:00–15:05): **AS base DONE** (`B1_base_L_confirm` 3/3 CONVERGED)

- Woken by the check wait: **1985035** (`br_absent_supervisor_B1_base_L_confirm`, s20–s22 at 3072) COMPLETED 15:00 (3:21).
- `.venv/bin/python experiments/step4_convergence.py results/step4/absent_supervisor/bonus/B1_base_L_confirm`: s20 **0.027**, s21 **0.001**, s22 **0.028** (s.e. 0.000 each), all **CONVERGED**. Every seed **hides** (window ≤ 0.004, corrections 0.01), like its best response and target. s21 takes the target's route (true about −51 to −55 ×4, −100); s20 and s22 hide on a lower-true route (true about −100 to −106 per round against −50), as s0 and s2 of the tuning run did.
- **Rule 4 (`_confirm` run, all CONVERGED): the AS base cell is DONE.** Config `B1_base_L`: `ppo.ent_coef=0.1 g.epochs=1000 protocol.update_bonus=1.0 episodes=3072 anneal.last=0.25 anneal.floor=0.1` (AS's frozen Step 3 config, trained long). Tuning seeds 0–2: 0.028 / 0.001 / 0.028; confirmation seeds 20–22: 0.027 / 0.001 / 0.028.
- **Caveat for the user:** 4 of the 6 seeds pass at 0.027–0.028, within 0.003 of the 0.03 bar; they hide, like the optimum, but on a route that loses about 50 true reward per round, which costs under 3% of received reward. By the pre-registered rule the cell is DONE; the margin is reported, not used to change anything.
- **The answer for this cell:** with the +1 update bonus, standard PBRR in Absent Supervisor is still avoided (the exact optimum hides, V0 = V_hide = 7,350), and PPO converges to hiding in 6 of 6 seeds.
- **Rule 6b: start nothing new for AS base.** `B1_base_LE` (1984530) and `B1_base_LN` (1984531) finish as information only (no extend, confirm or resume); `br_missing` still checks them.
- Queue (this campaign): 20 jobs. Cells DONE: **2 of 12**.

## 2026-11-14, iteration 20 (15:25–15:28): grid base `LN_confirm` finished (information only); check 1985077

- Woken by the training wait: **1984741** (grid `B1_base_LN_confirm`, 1536 episodes) COMPLETED 15:24 (1:49:18, exit 0). The grid base cell is DONE, so this run is information only; rule 3 still checks it: `... br_missing submit` → **1985077**.
- `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- Queue (this campaign): 20 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 21 (15:31–15:33): grid base `LN_confirm` 3/3 CONVERGED (information only)

- **1985077** (`br_grid_B1_base_LN_confirm`, s20–s22) COMPLETED 15:30 (3:36): s20 **0.025**, s21 **0.000**, s22 **0.025** (s.e. 0.000), all CONVERGED. s21 hides like its best response. s20 and s22 "never exploit in view": they skip the exploit in the final window too (true −100 every round, like the best response, but without the round-4 defection), which costs 2.5%. The cell is already DONE (iteration 15): information only. All three grid base configs (`L`, `LE`, `LN`) pass 3/3 + 3/3.
- Cells DONE: 2 of 12.

## 2026-11-14, iteration 22 (16:09–16:12): AS base `LN` s2 finished; check 1985421 (information only)

- `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `br_absent_supervisor_B1_base_LN` (s2 has finished 3072; s1 is at 1272). The AS base cell is DONE (iteration 19), so this is information only; `... br_missing submit` → **1985421**.
- `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing. Queue (this campaign): 20 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 23 (16:14–16:15): AS base `LN` s2 CONVERGED (information only)

- **1985421** (`br_absent_supervisor_B1_base_LN`, s2) COMPLETED 16:14 (0:55): s2 **0.000** (s.e. 0.000) CONVERGED, hides like its best response and target (true about −52 to −55 ×4, −103). With s0 (0.000), 2 of 3 seeds of `B1_base_LN` are CONVERGED; s1 is still training (1272 of 3072). The AS base cell is DONE: information only.
- Cells DONE: 2 of 12.

## 2026-11-14, iteration 24 (16:20–16:24): AS base `LE` finished (information only); AS swap `LN` s1 finished; checks 1985446, 1985447

- Woken by the training wait: **1984530** (AS `B1_base_LE`, 3072 episodes) COMPLETED 16:19 (4:35:20, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P2swap_LN` and `br_absent_supervisor_B1_base_LE`) → `... br_missing submit` → **1985446** (AS swap `B1_P2swap_LN`: s1 has finished 3072; s0 3048 and s2 3024 are about to finish and are likely included, since `--finished-only` tests each seed lazily), **1985447** (AS base `B1_base_LE`, information only: the cell is DONE).
- Queue (this campaign): 20 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 25 (16:24–16:35): AS swap `LN` 3/3 CONVERGED → confirm (1985457); AS base `LE` 3/3 (information only)

- Woken by the training wait: **1984527** (AS `B1_P2swap_LN`, 3072 episodes) COMPLETED 16:24 (4:40:02, exit 0). Its check **1985446** (all three seeds; s0 and s2 finished while it ran) and **1985447** (AS `B1_base_LE`) had both COMPLETED (2:15, 1:50). `br_missing` (dry-run): nothing left. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- `.venv/bin/python experiments/step4_convergence.py results/step4/absent_supervisor/bonus/B1_P2swap_LN`: s0 **0.000** (s.e. 0.000), s1 **0.000** (s.e. 0.000), s2 **0.020** (s.e. 0.007), all **CONVERGED**. Every seed is corrected once, in round 0 (window 1.0 in round 0 only), then never again, like its best response and the target's end state. After the correction (exact evaluation in the check): s0 true −50 ×4 (best response −50); s1 true about 446 (best response honest 450); s2 true 100–196, a mix (best response honest 450, PPO 2% below it). The no-bonus reference `O1_P2swap_LN` on the same seeds: gaps 0.007 / 0.000 / 0.008, also corrected once, true after it −100 / −49 / 450. See the new flag: the after-correction route is a near-tie in this cell.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P2swap_LN` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P2swap_LN_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=1600 g.l_minus_on=dispreferred g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 n_envs=64 episodes=3072 protocol.update_bonus=1.0`, identical to its `overrides.json`) → `... submit` → **1985457**.
- AS base `B1_base_LE` (information only; the cell is DONE): s0 **0.029**, s1 **0.029**, s2 **0.028**, all CONVERGED, all hiding on the lower-true route (true about −104 to −117 per round).
- Queue (this campaign): 18 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 26 (17:26–17:28): grid swap `LE+NET+ENT3` finished; check 1985541

- Woken by the training wait: **1984522** (grid `B1_P2swap_LE+NET+ENT3`, 1536 episodes) COMPLETED 17:26 (5:41:16, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_grid_B1_P2swap_LE+NET+ENT3`) → `... br_missing submit` → **1985541**.
- Queue (this campaign): 18 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 27 (17:33–17:38): grid swap `LE+NET+ENT3` 3/3 CONVERGED → confirm (1985549)

- Woken by the check wait: **1985541** (`br_grid_B1_P2swap_LE+NET+ENT3`, s0–s2 at 1536) COMPLETED 17:33 (4:45).
- `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_P2swap_LE+NET+ENT3`: s0 **0.015** (s.e. 0.003), s1 **0.009** (s.e. 0.001), s2 **0.008** (s.e. 0.001), all **CONVERGED**. Every seed is corrected once, in round 0, then honest (exact true about 20–22 per round against 22), like its best response and target.
- **Paired with the no-bonus reference** `O1_P2swap_LE+NET+ENT3` (same config and seeds, at 1536): gaps 0.011 / 0.020 / 0.012, also corrected once then honest (true 21.3–21.9). With the bonus: 0.015 / 0.009 / 0.008. Same behaviour; no systematic change in the gap.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid B1_P2swap_LE+NET+ENT3` (dry-run: `submit.sh 48 --env grid --run-id B1_P2swap_LE+NET+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --set g.l_minus_on=dispreferred anneal.last=0.25 anneal.floor=0.1 ppo.ent_coef=0.09 ppo.net_arch=[256,256] episodes=1536 protocol.update_bonus=1.0`, identical to its `overrides.json`) → `... submit` → **1985549**.
- Queue (this campaign): 18 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 28 (18:09–18:11): AS base `LN` s1 finished; check 1985581 (information only)

- `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `br_absent_supervisor_B1_base_LN` (s1 has finished 3072). The AS base cell is DONE: information only; `... br_missing submit` → **1985581**.
- `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing. Queue (this campaign): 18 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 29 (18:17–18:22): AS base `LN` s1 CONVERGED (information only)

- **1985581** (`br_absent_supervisor_B1_base_LN`, s1) COMPLETED (0:56): s1 **0.000** (s.e. 0.000) CONVERGED, hides like its best response (true about −50 ×4, −107). `B1_base_LN` is 3/3 CONVERGED (0.000 / 0.000 / 0.000). The AS base cell is DONE: information only (no confirm).
- Queue (this campaign): 17 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 30 (19:05–19:15): no events (fallback); reports and progress

- No job ended since iteration 29. `git pull --no-rebase --no-edit --ff`: already up to date. `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh report` run.
- **Pending by priority, not an incident:** grid `B1_P2swap_LE+NET+ENT3_confirm` (1985549) has been PENDING since 17:37 with reason `Priority` (fair share; Slurm's estimated start 21:46). Our jobs use 132 CPUs of the 512-CPU per-user QOS limit.
- Progress (episodes): AS no-reg `LN+RS` 5280–5376 / 6144; AS swap `LN_confirm` 1536–1752 / 3072; grid no-reg `LN+LR` 2448–2544 / 6144; Tomato base `L` 696–1104, `LE` 264–864, `LN` 696–912 of 1536; Tomato no-reg `LN` 1344–1584 / 6144; **Tomato swap `LN+ES10+N4` 192–216 / 1536** (256 envs; about 30 episodes/h, so it will reach the 48 h limit near 1400 and be resumed, rule 1); **tomato_large: 24–48 / 1536 after 7.4 h** (several 48 h jobs per run, as in the optimal campaign; rule 1 resumes them). tomato_large targets (1984519–1984521) still computing (7.4 h).
- No rule decisions. Queue (this campaign): 17 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 31 (20:17–20:19): AS no-reg `LN+RS` finished; check 1985712

- Woken by the training wait: **1984528** (AS `B1_P1eq1_LN+RS`, 6144 episodes) COMPLETED 20:17 (8:32:47, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS`) → `... br_missing submit` → **1985712**.
- Queue (this campaign): 17 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 32 (20:21–20:35): AS no-reg `LN+RS` 2/3 (s2 PLATEAU) → config finished; wave 2 (5 runs) and exploration (4 runs) submitted

- Woken by the check wait: **1985712** (`br_absent_supervisor_B1_P1eq1_LN+RS`, s0–s2 at 6144) COMPLETED 20:21 (1:32).
- `.venv/bin/python experiments/step4_convergence.py results/step4/absent_supervisor/bonus/B1_P1eq1_LN+RS`:
  - s0 **0.001** (s.e. 0.027) CONVERGED: corrected once, then honest (true about 450); its best response takes 3 corrections (rounds 0–2; true −100, 400, 400, 450, 450).
  - s1 **0.000** (s.e. 0.000) CONVERGED: corrected once, then honest, like its best response.
  - s2 **0.056** (s.e. 0.027) **PLATEAU**: corrected once, then honest (true about 450); its best response takes 2 corrections (true −100, 400, then 450 ×3).
  - **Paired no-bonus reference** `O1_P1eq1_LN+RS` (same config, same seeds, 6144): 0.000 / 0.000 / **0.020**, same end states (s2's best response there also takes 2 corrections). The bonus makes the extra correction worth +1 more, which alone is about 0.0001 of V; s2's larger gap here comes from a different trained policy and its refitted corrections (round-0 true −101 here against −125 there), within about 1.3 s.e. of the reference. Not attributed to the bonus.
- **Rule 4: the only unconverged seed is PLATEAU, so the config is finished** (no extension; 6144 < AS cap 24,576 is irrelevant for PLATEAU).
- **Rule 5 (wave 2):** the cell's one wave-1 run is finished and is neither CONVERGED 3/3 nor IMPROVING. Extras = its overrides minus `episodes=` (`.venv/bin/python scripts/farmshare/run_sets.py results/step4/absent_supervisor/bonus/B1_P1eq1_LN+RS`): `ppo.ent_coef=0.1 ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 n_envs=64 reward_scale=0.01625 protocol.update_bonus=1.0`. Commands, each dry-run then submitted, `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh ppo absent_supervisor P1eq1 "LN+RS+<tag>" "<extras> <factor>" submit` (3072 episodes, the AS wave-1 length; later duplicate keys win):
  - `LR` (`ppo.learning_rate=0.0001`) → **1985717**; `GL` (`ppo.gae_lambda=1.0`) → **1985718**; `NET` (`ppo.net_arch=[256,256]`) → **1985719**; `EP` (`ppo.n_epochs=20`) → **1985720**; `AN` (`anneal.last=0.5`) → **1985721**.
  - **`RS` skipped:** the base already has `reward_scale=0.01625`, which is exactly the `RS` factor (0.25 × AS's Phase A scale 0.065), so `LN+RS+RS` would duplicate the base. Logged rather than submitted.
- **Rule 6b (exploration):** every wave-1 run of the cell has a check and none is CONVERGED 3/3, so exploration starts now, alongside wave 2, from the cell's run with the smallest mean gap (the only one). `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh explore absent_supervisor P1eq1 B1_P1eq1_LN+RS` (dry-run: 4 runs at 3072: `+ENT3` `ppo.ent_coef=0.3`; `+ES10` `anneal.ent_start=10 anneal.ent_episodes=768`; `+N4` `n_envs=256 ppo.batch_size=6400`; `+ES10+N4`) → `... submit` → **1985722** (ENT3), **1985723** (ES10), **1985724** (N4), **1985725** (ES10+N4).
- Budget: this campaign 25 jobs (≤ 60); all jobs 31 (≤ 110). Cells DONE: 2 of 12.

## 2026-11-14, iteration 33 (21:05–21:07): AS swap `LN_confirm` finished; check 1985787

- Woken by the training wait: **1985457** (AS `B1_P2swap_LN_confirm`, seeds 20–22, 3072 episodes) COMPLETED 21:04 (4:27:24, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P2swap_LN_confirm`) → `... br_missing submit` → **1985787**. The AS swap cell is DONE if this is 3/3.
- Queue (this campaign): 25 jobs. Cells DONE: 2 of 12.

## 2026-11-14, iteration 34 (21:09–21:14): **AS swap DONE** (`B1_P2swap_LN_confirm` 3/3 CONVERGED)

- Woken by the check wait: **1985787** (`br_absent_supervisor_B1_P2swap_LN_confirm`, s20–s22 at 3072) COMPLETED 21:09 (2:02).
- `.venv/bin/python experiments/step4_convergence.py results/step4/absent_supervisor/bonus/B1_P2swap_LN_confirm`: s20 **0.000** (s.e. 0.000), s21 **0.002** (s.e. 0.016), s22 **0.003** (s.e. 0.003), all **CONVERGED**. Every seed is corrected once, in round 0, then never again, like its best response and the target's end state. After the correction (exact evaluation): s20 honest (true about 450); s21 the −50 route (true −43 to −49) while its best response is honest 450, at a gap of only 0.002; s22 mixed (true 348–425). This is the near-tie flagged in iteration 25: the two routes pay almost the same received reward.
- **Rule 4 (`_confirm` run, all CONVERGED): the AS swap cell is DONE.** Config `B1_P2swap_LN`: `ppo.ent_coef=0.1 ppo.batch_size=1600 g.l_minus_on=dispreferred g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 n_envs=64 episodes=3072 protocol.update_bonus=1.0` (the optimal campaign's converged AS swap config plus the bonus). Tuning seeds 0–2: 0.000 / 0.000 / 0.020; confirmation seeds 20–22: 0.000 / 0.002 / 0.003.
- **Paired with the no-bonus reference** `O1_P2swap_LN` (same config, seeds 0–2, 3072): 0.007 / 0.000 / 0.008; corrected once in every seed, with and without the bonus. The bonus changes neither the end state nor the convergence.
- **The answer for this cell:** with the +1 update bonus, the AS swap optimum is corrected exactly once (round 0) and then never again, as without the bonus. Whether it then plays honestly (true 450) or takes the −50 route is a near-tie that varies by seed and draw (flag above).
- **Rule 6b:** start nothing new for AS swap. No other AS swap runs are running.
- Queue (this campaign): 24 jobs. Cells DONE: **3 of 12**.

## 2026-11-14, iteration 35 (21:39–21:41): Tomato base `L` s0 finished; check 1985876

- `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `br_tomato_B1_base_L`: s0 has finished 1536 (s1 at 1296, s2 at 888). `... br_missing submit` → **1985876** (s0; the others get checks when they finish). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- Queue (this campaign): 25 jobs. Cells DONE: 3 of 12.

## 2026-11-14, iteration 36 (21:56–21:59): Tomato base `L` s0 0.162 (reactive: corrected once, then honest; the optimum hides)

- **1985876** (`br_tomato_B1_base_L`, s0 at 1536) COMPLETED 21:55 (7:57): s0 **0.162** (s.e. 0.000), not converged. PPO is **corrected in round 0, then honest** (true 46, then about 430 ×4); its best response, like the target, **hides** (true 59.8 ×4, 46; never corrected). This is the "reactive avoidance" outcome seen in Step 3 Tomato (exploit until corrected, then honest), not the anticipatory hiding the optimum uses.
- Verdict (`.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_base_L`): s0 **PLATEAU**. Note the direction: PPO's true return after its correction (about 430, honest) is far above the optimum's (59.8: it keeps exploiting off-window and hides from every audit), so PPO is short of its optimum by being *more* honest. Rule 4 waits until all three seeds have a check (s1 at 1368, s2 at 912 of 1536).
- Queue (this campaign): 24 jobs. Cells DONE: 3 of 12.

## 2026-11-14, iteration 37 (22:44–22:47): Tomato base `L` s1 finished; check 1986003

- Fallback wakeup; no training job ended. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_tomato_B1_base_L`; s1 has finished 1536) → `... br_missing submit` → **1986003**.
- Queue (this campaign): 25 jobs. Cells DONE: 3 of 12.

## 2026-11-14, iteration 38 (23:32–23:36): Tomato base `LE` s1 and `LN` s0 finished; checks 1986123, 1986124

- Fallback wakeup; no training job ended. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- The Tomato base `L` s1 check (1986003) is still PENDING (reason `Priority`).
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_tomato_B1_base_LE`, `br_tomato_B1_base_LN`) → `... br_missing submit` → **1986123** (`B1_base_LE` s1; s0 456, s2 1440 of 1536), **1986124** (`B1_base_LN` s0; s1 1440, s2 1488).
- Queue (this campaign): 27 jobs. Cells DONE: 3 of 12.

## 2026-11-14, iteration 39 (23:49–23:51): Tomato base `L` s1 0.163 (reactive, like s0)

- **1986003** (`br_tomato_B1_base_L`, s1 at 1536) COMPLETED 23:49 (12:25): s1 **0.163** (s.e. 0.000), not converged; corrected in round 0, then honest (true about 430), while its best response hides (true 59.8 ×4, 46), exactly like s0 (0.162). s2 still training. Rule 4 waits for s2's check.
- Checks running: 1986123 (`LE` s1), 1986124 (`LN` s0). Cells DONE: 3 of 12.

## 2026-11-14, iteration 40 (23:50–23:56): AS no-reg exploration `+ENT3` and `+ES10` finished; checks 1986300, 1986301; Tomato base `LN` finished

- Woken by the training wait: **1985722** (AS `B1_P1eq1_LN+RS+ENT3`, 3072) COMPLETED 23:50 (2:11:15, exit 0). Also ended: **1985723** (`+ES10`, 23:51, 2:12:43, exit 0) and **1984536** (Tomato `B1_base_LN`, 1536, 12:06:48, exit 0).
- **A race, not a stopped run:** the first `... resume` dry-run (23:50) listed `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ES10 --seeds 2 ... --resume`, because s2 was in its last seconds and its job had just left the queue. Checked: the job COMPLETED 23:51:15 with "seed 2 exit 0", and s2 has `metrics.json` at 3072. A second dry-run lists nothing. Not submitted.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `+ENT3`, `+ES10`) → `... br_missing submit` → **1986300** (`B1_P1eq1_LN+RS+ENT3`), **1986301** (`B1_P1eq1_LN+RS+ES10`). Tomato `B1_base_LN` s1 and s2 get their check after the running one (1986124, s0) ends.
- Queue (this campaign): 25 jobs. Cells DONE: 3 of 12.

## 2026-11-14/15, iteration 41 (23:57–00:03): AS no-reg `+ENT3` 3/3 CONVERGED → confirm (1986437); `+ES10` 2/3 → extend to 6144 (1986438)

- Woken by the check wait: **1986300** (`br_absent_supervisor_B1_P1eq1_LN+RS+ENT3`, 2:47) and **1986301** (`..._LN+RS+ES10`, 2:23) COMPLETED 23:56.
- `B1_P1eq1_LN+RS+ENT3` (entropy 3×, 0.3) at 3072: s0 **0.000**, s1 **0.000**, s2 **0.000** (s.e. ≤ 0.000), all **CONVERGED**; each corrected once, in round 0, then honest (true about 450), like its best response.
- `B1_P1eq1_LN+RS+ES10` at 3072: s0 **0.001** (s.e. 0.019) CONVERGED (corrected once, then honest; its best response takes 4 corrections); s1 **0.000** CONVERGED; s2 **0.061** (s.e. 0.024) not converged: corrected once, then honest, while its best response takes 2 corrections (true −100, 400, then 450 ×3), the same shortfall as `LN+RS` s2.
- **Rule 6b (exploration run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+ENT3` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.3 ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 n_envs=64 reward_scale=0.01625 protocol.update_bonus=1.0 episodes=3072`, identical to its `overrides.json`) → `... submit` → **1986437**. The AS no-reg cell is DONE if this is 3/3.
- **Rule 6b (exploration run, a seed unconverged): extend 2× whatever the verdict**, up to the AS cap 24,576. `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+ES10 6144` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ES10 --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`) → `... submit` → **1986438**.
- Queue (this campaign): 25 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 42 (00:14–00:17): Tomato base `LN` 0/3 (all PLATEAU, reactive) → config finished

- Woken by the check wait: **1986124** (`br_tomato_B1_base_LN`, s0–s2 at 1536; s1 and s2 finished while it ran and were included) COMPLETED 00:14 (22:25).
- `.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_base_LN`: s0 **0.160**, s1 **0.160**, s2 **0.160** (s.e. ≤ 0.000), all **PLATEAU**. Every seed is corrected in round 0, then honest (true about 432 ×4); every best response hides (true 59.8 ×4, 46; never corrected), like the target. Same reactive pattern as `B1_base_L` s0/s1 (0.162 / 0.163).
- **Rule 4: every unconverged seed is PLATEAU, so the config is finished.** No extension.
- Wave 2 (rule 5) and exploration (rule 6b) for Tomato base wait until every wave-1 run has a check: `L` s2 is still training (about 1100 / 1536), and `LE`'s check (1986123, s1) is running while `LE` s0 (456) and s2 train.
- Queue (this campaign): 24 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 43 (00:17–00:20): grid swap `LE+NET+ENT3_confirm` finished (check 1986794); AS no-reg `+AN` s2 finished (check 1986795)

- Woken by the training wait: **1985549** (grid `B1_P2swap_LE+NET+ENT3_confirm`, seeds 20–22, 1536) COMPLETED 00:16 (5:05:37, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_grid_B1_P2swap_LE+NET+ENT3_confirm`, `br_absent_supervisor_B1_P1eq1_LN+RS+AN`) → `... br_missing submit` → **1986794** (grid swap confirmation; the cell is DONE if 3/3), **1986795** (AS no-reg wave 2 `+AN`: s2 finished 3072, s0 2952 and s1 3000 are close and may be included).
- Queue (this campaign): 25 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 44 (00:23–00:28): grid swap `LE+NET+ENT3_confirm` 2/3 → extend to 3072 (1986839); AS no-reg `+AN` s2 CONVERGED, s0/s1 check 1986842

- Woken by the check wait: **1986794** (`br_grid_B1_P2swap_LE+NET+ENT3_confirm`, s20–s22 at 1536) COMPLETED 00:23 (2:36); and by the training wait: **1985721** (AS `B1_P1eq1_LN+RS+AN`, 3072) COMPLETED 00:23 (2:46:57, exit 0). Its first check **1986795** (s2) had COMPLETED (0:57).
- `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_P2swap_LE+NET+ENT3_confirm`: s20 **0.180** (s.e. 0.018) **IMPROVING**: corrected in round 0, then never reaches the goal (true −100 every later round), while its best response is honest (true 20); s21 **0.014** (s.e. 0.001) CONVERGED; s22 **0.011** (s.e. 0.001) CONVERGED (both corrected once, then honest, true about 22).
- **Rule 4 (confirmation, s20 IMPROVING, 1536 < cap 12,288): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P2swap_LE+NET+ENT3_confirm 3072` (dry-run: `submit.sh 48 --env grid --run-id B1_P2swap_LE+NET+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --resume --extend-to 3072`) → `... submit` → **1986839**. (Correction, made before committing: without the bonus, this config's confirmation on the same seeds was **3/3 at 1536 with no extension** (optimal log, iteration 139; from `results/step4/grid/optimal/O1_P2swap_LE+NET+ENT3_confirm/step4_br/seed<s>_ep1536.json`: s20 0.013, s21 0.009, s22 0.012, all corrected once then honest, true about 22). So s20's failure to reach the goal after its correction is new in this paired run; whether that comes from the bonus or from training noise is not separable from one seed.)
- AS no-reg wave 2 `B1_P1eq1_LN+RS+AN` (`anneal.last=0.5`): s2 **0.010** (s.e. 0.027) CONVERGED (corrected once, then honest; its best response takes 2 corrections). **Rule 3:** `... br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+AN`) → `... br_missing submit` → **1986842** (s0, s1).
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 45 (00:28–00:34): AS no-reg wave 2 `+AN` 3/3 CONVERGED → confirm (1986852); Tomato base `LE` s1/s2 0.167 (reactive)

- Woken by the check wait (it found no check left in the queue): **1986842** (`br_absent_supervisor_B1_P1eq1_LN+RS+AN`, s0, s1) COMPLETED (1:03), and **1986123** (`br_tomato_B1_base_LE`, s1 and s2) COMPLETED (33:06).
- `B1_P1eq1_LN+RS+AN` (wave 2, `anneal.last=0.5`) at 3072: s0 **0.013** (s.e. 0.021; its best response takes 4 corrections), s1 **0.000**, s2 **0.010** (s.e. 0.027; best response 2 corrections), all **CONVERGED**; every seed is corrected once, then honest (true about 450).
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+AN` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+AN_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 protocol.update_bonus=1.0 episodes=3072 anneal.last=0.5 anneal.floor=0.1 n_envs=64 reward_scale=0.01625`, identical to its `overrides.json`) → `... submit` → **1986852**. It runs alongside `+ENT3_confirm` (1986437); the AS no-reg cell is DONE when either is 3/3.
- Tomato base `B1_base_LE`: s1 **0.167**, s2 **0.166** (s.e. ≤ 0.000), labelled IMPROVING; both corrected in round 0, then honest (true about 427), while the best response hides. s0 is still training (552 / 1536); rule 4 waits for its check.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 46 (00:48–00:50): AS no-reg wave 2 `+LR` finished; check 1986872

- Woken by the training wait: **1985717** (AS `B1_P1eq1_LN+RS+LR`, 3072) COMPLETED 00:47 (4:24:35, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+LR`) → `... br_missing submit` → **1986871** (`+LR`) and **1986872** (Tomato `B1_base_L` s2, which had just finished). (Corrected in iteration 47: I first logged 1986872 as the `+LR` check, reading only the last id printed.)
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 47 (00:54–01:00): AS no-reg wave 2 `+LR` 2/3 (s2 IMPROVING) → extend to 6144 (1986888); Tomato base `L` finished (s2 check 1986872 running)

- Woken by the check wait: **1986871** (`br_absent_supervisor_B1_P1eq1_LN+RS+LR`, s0–s2 at 3072) COMPLETED 00:54 (2:37). Also ended: **1984534** (Tomato `B1_base_L`, 1536, 13:05:20, exit 0); its s2 check is **1986872** (running).
- Correction: iteration 46 logged 1986872 as the `+LR` check; it was 1986871 (1986872 is the Tomato base `L` s2 check, submitted in the same call). Fixed in place there.
- `B1_P1eq1_LN+RS+LR` (wave 2, `ppo.learning_rate=0.0001`) at 3072: s0 **0.000**, s1 **0.000** CONVERGED (corrected once, then honest); s2 **0.065** (s.e. 0.018) **IMPROVING**: corrected once, then honest, while its best response takes 2 corrections (the same s2 shortfall as `LN+RS` and `+ES10`).
- **Rule 4 (tuning run, s2 IMPROVING, 3072 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+LR 6144` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+LR --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`) → `... submit` → **1986888**.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 48 (01:07–01:12): Tomato base `L` 0/3 (s1 IMPROVING) → extend to 3072 (1986905)

- **1986872** (`br_tomato_B1_base_L`, s2 at 1536) had COMPLETED (12:58): s2 **0.163** (s.e. 0.000). s2 is honest in round 0 (true 427), exploits and is corrected in round 1 (window 0.96), then honest; its best response hides.
- `.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_base_L`: s0 **0.162** PLATEAU, s1 **0.163** **IMPROVING**, s2 **0.163** PLATEAU. Every seed is reactive (corrected once, then honest, true about 430), while the optimum hides (true 59.8).
- **Rule 4 (tuning run, s1 IMPROVING, 1536 < cap 12,288): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_L 3072` (dry-run: `submit.sh 48 --env tomato --run-id B1_base_L --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 3072`) → `... submit` → **1986905**.
- Tomato base status: `L` extending; `LN` finished (0/3 PLATEAU); `LE` s1/s2 IMPROVING, s0 still training. Wave 2 / exploration wait until no wave-1 run is still IMPROVING (rule 5) or every wave-1 run has a check (rule 6b, after `LE` s0).
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 49 (01:16–01:18): AS no-reg wave 2 `+EP` finished; check 1986913 

- Woken by the training wait: **1985720** (AS `B1_P1eq1_LN+RS+EP`, 3072) COMPLETED 01:15 (3:41:01, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+EP`) → `... br_missing submit` → **1986913 **.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 50 (01:23–01:26): AS no-reg wave 2 `+EP` 2/3 (s2 IMPROVING) → extend to 6144 (1986917)

- Woken by the check wait: **1986913** (`br_absent_supervisor_B1_P1eq1_LN+RS+EP`, s0–s2 at 3072) COMPLETED 01:22 (2:53).
- `B1_P1eq1_LN+RS+EP` (wave 2, `ppo.n_epochs=20`): s0 **0.000**, s1 **0.000** CONVERGED (corrected once, then honest); s2 **0.048** (s.e. 0.024) **IMPROVING**: corrected once, then honest, its best response takes 2 corrections.
- **Rule 4 (tuning run, s2 IMPROVING, 3072 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+EP 6144` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+EP --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`) → `... submit` → **1986917**.
- AS no-reg so far: s2 is the only seed that misses in `LN+RS` (0.056), `+ES10` (0.061), `+LR` (0.065) and `+EP` (0.048), always by taking 1 correction where its best response takes 2. `+ENT3` and `+AN` are 3/3 and in confirmation (1986437, 1986852).
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 51 (02:00–02:02): AS no-reg wave 2 `+GL` finished; check 1986946 

- Woken by the training wait: **1985718** (AS `B1_P1eq1_LN+RS+GL`, 3072) COMPLETED 02:00 (4:42:41, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+GL`) → `... br_missing submit` → **1986946 **.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 52 (02:06–02:09): AS no-reg wave 2 `+GL` 2/3 (s2 IMPROVING) → extend to 6144 (1987047)

- Woken by the check wait: **1986946** (`br_absent_supervisor_B1_P1eq1_LN+RS+GL`, s0–s2 at 3072) COMPLETED 02:06 (2:44).
- `B1_P1eq1_LN+RS+GL` (wave 2, `ppo.gae_lambda=1.0`): s0 **0.000** CONVERGED; s1 **0.002** (s.e. 0.032) CONVERGED (corrected once; its best response takes 2); s2 **0.038** (s.e. 0.023) **IMPROVING** (corrected once; best response 2 corrections).
- **Rule 4 (tuning run, s2 IMPROVING, 3072 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+GL 6144` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+GL --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`) → `... submit` → **1987047**.
- AS no-reg wave 2 so far: `+AN` 3/3 (in confirmation); `+LR`, `+EP`, `+GL` 2/3 (s2), extending; `+NET` still training. Exploration: `+ENT3` 3/3 (in confirmation), `+ES10` 2/3 (extending), `+N4` and `+ES10+N4` training.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 53 (02:52–02:54): AS no-reg exploration `+N4` finished; check 1987108 

- Woken by the training wait: **1985724** (AS `B1_P1eq1_LN+RS+N4`, 3072) COMPLETED 02:52 (5:04:14, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+N4`) → `... br_missing submit` → **1987108 **.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 54 (03:00–03:04): AS no-reg exploration `+N4` 3/3 CONVERGED → confirm (1987110)

- Woken by the check wait: **1987108** (`br_absent_supervisor_B1_P1eq1_LN+RS+N4`, s0–s2 at 3072) COMPLETED 02:59 (3:41).
- `B1_P1eq1_LN+RS+N4` (exploration, `n_envs=256 ppo.batch_size=6400`): s0 **0.000**, s1 **0.000**, s2 **0.000** (s.e. ≤ 0.000), all **CONVERGED**; each corrected once, then honest (true 450), like its best response (here s2's best response also takes 1 correction).
- **Rule 6b (exploration run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+N4` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+N4_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=6400 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 n_envs=256 reward_scale=0.01625 protocol.update_bonus=1.0 episodes=3072`, identical to its `overrides.json`) → `... submit` → **1987110**.
- AS no-reg confirmations now running: `+ENT3_confirm` (1986437), `+AN_confirm` (1986852), `+N4_confirm` (1987110). The cell is DONE when any is 3/3.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 55 (03:42–03:44): AS no-reg `+LR` finished 6144; `+ES10+N4` s0/s1 finished; checks 1987121, 1987122

- Woken by the training wait: **1986888** (AS `B1_P1eq1_LN+RS+LR` extension to 6144) COMPLETED 03:41 (2:44:39, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+ES10+N4`, `br_absent_supervisor_B1_P1eq1_LN+RS+LR`) → `... br_missing submit` → **1987121** (`+ES10+N4`: s0, s1 finished 3072; s2 at 2784), **1987122** (`+LR` at 6144).
- Queue (this campaign): 24 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 56 (03:48–03:51): AS no-reg `+LR` 2/3 at 6144 → extend to 12,288 (1987131); `+ES10+N4` s0/s1 CONVERGED

- Woken by the check wait: **1987121** (`+ES10+N4`, s0, s1 at 3072; 2:21) and **1987122** (`+LR` at 6144; 2:54) COMPLETED 03:47.
- `B1_P1eq1_LN+RS+LR` at 6144 (gap history 3072 / 6144): s0 **0.000**, s1 **0.000** CONVERGED; s2 **0.039** (s.e. 0.024; 0.065 / 0.039) **IMPROVING** (corrected once, then honest; best response 2 corrections).
- **Rule 4 (tuning run, s2 IMPROVING, 6144 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+LR 12288` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+LR --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 12288`) → `... submit` → **1987131**.
- `B1_P1eq1_LN+RS+ES10+N4` (exploration): s0 **0.000**, s1 **0.000** CONVERGED (corrected once, then honest, like their best responses); s2 still training (2856 / 3072).
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 57 (04:01–04:04): AS no-reg `+ES10+N4` finished; `+ENT3_confirm` s20/s22 finished; checks 1987146, 1987147

- Woken by the training wait: **1985725** (AS `B1_P1eq1_LN+RS+ES10+N4`, 3072) COMPLETED 04:01 (6:13:40, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+ENT3_confirm`, `br_absent_supervisor_B1_P1eq1_LN+RS+ES10+N4`) → `... br_missing submit` → **1987146** (`+ENT3_confirm`: s20, s22 finished 3072; s21 at 2856) and **1987147** (`+ES10+N4` s2) (order as printed by the driver).
- Queue (this campaign): 24 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 58 (04:07–04:11): AS no-reg `+ES10+N4` 3/3 CONVERGED → confirm (1987149); `+ENT3_confirm` s20/s22 0.049/0.052

- Woken by the check wait: **1987146** (`br_absent_supervisor_B1_P1eq1_LN+RS+ENT3_confirm`, s20, s22) COMPLETED 04:07 (2:07). **1987147** (`+ES10+N4` s2) had also COMPLETED.
- `B1_P1eq1_LN+RS+ES10+N4` (exploration): s0 **0.000**, s1 **0.000**, s2 **0.015** (s.e. ≤ 0.02), all **CONVERGED**; each corrected once, then honest.
- **Rule 6b (exploration run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+ES10+N4` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=6400 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 anneal.ent_start=10 anneal.ent_episodes=768 n_envs=256 reward_scale=0.01625 protocol.update_bonus=1.0 episodes=3072`, identical to its `overrides.json`) → `... submit` → **1987149**.
- `B1_P1eq1_LN+RS+ENT3_confirm` at 3072: s20 **0.049** (s.e. 0.021) and s22 **0.052** (s.e. 0.029), both labelled IMPROVING: corrected once, then honest, while their best responses take 2 corrections (the same shortfall as tuning seed 2 in `LN+RS`, `+LR`, `+EP`, `+GL`, `+ES10`). s21 still training (2976 / 3072); rule 4 waits for its check.
- AS no-reg confirmations running: `+ENT3_confirm` (s21), `+AN_confirm` (1986852), `+N4_confirm` (1987110), `+ES10+N4_confirm` (1987149).
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 59 (04:13–04:15): AS no-reg `+ENT3_confirm` finished; `+ES10` finished 6144; checks 1987154, 1987155

- Woken by the training wait: **1986437** (AS `B1_P1eq1_LN+RS+ENT3_confirm`, 3072) and **1986438** (AS `+ES10` extension to 6144) COMPLETED 04:12 (3:49:02, 3:45:53; exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: both runs) → `... br_missing submit` → **1987154** (`+ENT3_confirm` s21), **1987155** (`+ES10` at 6144).
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 60 (04:19–04:23): AS no-reg `+ENT3_confirm` 1/3 → extend to 6144 (1987156); `+ES10` 2/3 at 6144 → extend to 12,288 (1987157)

- Woken by the check wait: **1987155** (`+ES10` at 6144; 2:46) COMPLETED 04:19; **1987154** (`+ENT3_confirm` s21) had COMPLETED.
- `B1_P1eq1_LN+RS+ENT3_confirm` at 3072: s20 **0.049** IMPROVING, s21 **0.000** (s.e. 0.000) CONVERGED, s22 **0.052** IMPROVING. **Rule 4 (confirmation, two seeds IMPROVING, 3072 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+ENT3_confirm 6144` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`) → `... submit` → **1987156**.
- `B1_P1eq1_LN+RS+ES10` (exploration) at 6144 (gap history 3072 / 6144): s0 **0.000**, s1 **0.000** CONVERGED; s2 **0.074** (s.e. 0.029; 0.061 / 0.074) IMPROVING (corrected once; best response 2 corrections). **Rule 6b (exploration run, a seed unconverged): extend 2× whatever the verdict.** `... extend absent_supervisor B1_P1eq1_LN+RS+ES10 12288` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ES10 --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 12288`) → `... submit` → **1987157**.
- Queue (this campaign): 23 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 61 (04:21–04:25): Tomato swap `LN+ES10+N4` s0 finished; check 1987158

- `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `br_tomato_B1_P2swap_LN+ES10+N4`: s0 has finished 1536 (the run sped up after its correction-heavy start; s1 1224, s2 1248). `... br_missing submit` → **1987158**.
- Queue (this campaign): 24 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 62 (04:26–04:28): Tomato base `LE` finished; s0 check 1987163 

- Woken by the training wait: **1984535** (Tomato `B1_base_LE`, 1536) COMPLETED 04:25 (16:41:31, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_tomato_B1_base_LE`, s0) → `... br_missing submit` → **1987163 **. With it, every Tomato base wave-1 run will have a check: rule 4 decides `LE`, and then rules 5 / 6b decide the cell.
- Queue (this campaign): 24 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 63 (04:33–04:38): Tomato swap `LN+ES10+N4` s0 CONVERGED

- **1987158** (`br_tomato_B1_P2swap_LN+ES10+N4`, s0 at 1536) COMPLETED 04:32 (7:28): s0 **0.002** (s.e. 0.000) CONVERGED; corrected in round 0, then honest (true about 422), like its best response and the target. s1, s2 still training (about 1230 / 1536). Rule 4 waits for them.
- Cells DONE: 3 of 12.

## 2026-11-15, iteration 64 (04:41–04:48): Tomato base `LE` 0/3 (IMPROVING) → extend to 3072 (1987172); **Tomato base exploration started** from `LN` (1987173–1987176)

- Woken by the check wait: **1987163** (`br_tomato_B1_base_LE`, s0 at 1536) COMPLETED 04:41 (11:20): s0 **0.167** (s.e. 0.000), reactive (corrected once, then honest, true about 427); its best response hides.
- `.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_base_LE`: s0 **0.167**, s1 **0.167**, s2 **0.166**, all labelled **IMPROVING**.
- **Rule 4 (tuning run, seeds IMPROVING, 1536 < cap 12,288): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LE 3072` (dry-run: `submit.sh 48 --env tomato --run-id B1_base_LE --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 3072`) → `... submit` → **1987172**.
- **Rule 6b (exploration): every Tomato base wave-1 run now has a check and none is CONVERGED 3/3** (`L` 0.162 / 0.163 / 0.163, extending to 3072; `LE` 0.167 / 0.167 / 0.166, extending; `LN` 0.160 / 0.160 / 0.160, PLATEAU). Base = the run with the smallest mean gap: **`B1_base_LN`** (mean 0.160; `L` 0.163, `LE` 0.167). Order: grid and AS base are DONE, so Tomato is next. `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh explore tomato base B1_base_LN` (dry-run: 4 runs at 1536, all with `g.epochs=1000 protocol.update_bonus=1.0 anneal.last=0.25 anneal.floor=0.1`: `+ENT3` `ppo.ent_coef=0.09`, n_envs 64; `+ES10` `anneal.ent_start=10 anneal.ent_episodes=768`; `+N4` `n_envs=256 ppo.batch_size=6400`; `+ES10+N4`) → `... submit` → **1987173** (ENT3), **1987174** (ES10), **1987175** (N4), **1987176** (ES10+N4).
- What exploration has to overcome here: every base seed so far is corrected once and then honest (true about 430), while the optimum keeps exploiting off-window and hides from every audit (true 59.8). PPO needs to find the hiding policy, not more honesty.
- Budget: this campaign 27 jobs (≤ 60); all jobs 32 (≤ 110). Cells DONE: 3 of 12.

## 2026-11-15, iteration 65 (04:49–04:52): grid no-reg `LN+LR` finished (check 1987183); AS no-reg `+AN_confirm` s20/s21 finished (check 1987184)

- Woken by the training wait: **1984523** (grid `B1_P1eq1_LN+LR`, 6144) COMPLETED 04:49 (17:05:09, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_grid_B1_P1eq1_LN+LR`, `br_absent_supervisor_B1_P1eq1_LN+RS+AN_confirm`) → `... br_missing submit` → **1987183** (grid no-reg `B1_P1eq1_LN+LR` at 6144, the paired rerun of the no-bonus reference), **1987184** (AS `+AN_confirm`: s20, s21 finished 3072; s22 at 2520).
- Queue (this campaign): 28 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 66 (04:55–04:59): grid no-reg `LN+LR` 2/3 at 6144 → extend to 12,288 (1987190); AS `+AN_confirm` s20 0.038, s21 CONVERGED

- Woken by the check wait: **1987183** (`br_grid_B1_P1eq1_LN+LR`, 3:20) and **1987184** (`br_absent_supervisor_B1_P1eq1_LN+RS+AN_confirm`, s20, s21; 1:57) COMPLETED 04:55.
- `B1_P1eq1_LN+LR` (grid no-reg, the reference config with the bonus) at 6144: s0 **0.002** (s.e. 0.003) CONVERGED, s1 **0.011** (s.e. 0.002) CONVERGED (both corrected once, then honest, true 22; s1 misses the goal in round 4); s2 **0.055** (s.e. 0.037) **IMPROVING**: corrected once, then never reaches the goal (true −100 every round), while its best response takes 2 corrections and is then honest.
- **Paired no-bonus reference** `O1_P1eq1_LN+LR` at 6144 (same seeds): 0.000 / 0.002 / 0.000, all corrected once then honest. So s2's failure to reach the goal is specific to this run; from one seed it cannot be attributed to the bonus.
- **Rule 4 (tuning run, s2 IMPROVING, 6144 < grid cap 12,288): extend 2× to the cap.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR 12288` (dry-run: `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 12288`) → `... submit` → **1987190**.
- AS `B1_P1eq1_LN+RS+AN_confirm` at 3072: s20 **0.038** (s.e. 0.028) not converged (corrected once; best response 2 corrections); s21 **0.015** (s.e. 0.029) CONVERGED (corrected once; best response 3). s22 still training (2520 / 3072); rule 4 waits for it.
- Queue (this campaign): 27 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 67 (05:25–05:27): AS no-reg wave 2 `+NET` finished; check 1987194 

- Woken by the training wait: **1985719** (AS `B1_P1eq1_LN+RS+NET`, 3072) COMPLETED 05:24 (7:57:19, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+NET`) → `... br_missing submit` → **1987194 **. This is the last AS no-reg wave-2 run to get a check.
- Queue (this campaign): 27 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 68 (05:31–05:35): AS no-reg wave 2 `+NET` 3/3 CONVERGED → confirm (1987197)

- Woken by the check wait: **1987194** (`br_absent_supervisor_B1_P1eq1_LN+RS+NET`, s0–s2 at 3072) COMPLETED 05:31 (2:27).
- `B1_P1eq1_LN+RS+NET` (wave 2, `ppo.net_arch=[256,256]`): s0 **0.000**, s1 **0.000**, s2 **0.002** (s.e. 0.027), all **CONVERGED**; each corrected once, then honest (true about 450). (s2's best response takes 3 corrections; the gap is within 3%.)
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+NET` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+NET_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=1600 ppo.net_arch=[256,256] g.use_regularization=False g.epochs=1000 protocol.update_bonus=1.0 episodes=3072 anneal.last=0.25 anneal.floor=0.1 n_envs=64 reward_scale=0.01625`, identical to its `overrides.json`) → `... submit` → **1987197**.
- AS no-reg confirmations running: `+ENT3_confirm` (extending to 6144, 1987156), `+AN_confirm` (1986852; s20 0.038, s21 0.015, s22 training), `+N4_confirm` (1987110), `+ES10+N4_confirm` (1987149), `+NET_confirm` (1987197).
- Queue (this campaign): 27 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 69 (05:37–05:40): AS `+AN_confirm` and `+EP` (6144) finished; grid swap confirm s21/s22 at 3072; checks 1987201–1987203

- Woken by the training wait: **1986852** (AS `B1_P1eq1_LN+RS+AN_confirm`, 3072; 4:44:22) and **1986917** (AS `+EP` extension to 6144; 4:06:20) COMPLETED by 05:37, exit 0. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: three runs) → `... br_missing submit` → **1987201** (grid swap `B1_P2swap_LE+NET+ENT3_confirm`: s21, s22 finished 3072; s20 at 3000), **1987202** (AS `+AN_confirm` s22), **1987203** (AS `+EP` at 6144).
- Queue (this campaign): 28 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 70 (05:42–05:50): AS no-reg `+EP` 3/3 at 6144 → confirm (1987207); `+AN_confirm` 2/3 (s20 PLATEAU) → failed; grid swap confirm s21/s22 CONVERGED; checks 1987208, 1987209

- Woken by the training wait: **1986839** (grid swap `LE+NET+ENT3_confirm` extension to 3072; 4:54:51) and **1984532** (Tomato swap `B1_P2swap_LN+ES10+N4`, 1536; 17:58:18) COMPLETED, exit 0; and by the check wait: **1987201**, **1987202**, **1987203** COMPLETED.
- `B1_P1eq1_LN+RS+EP` (wave 2) at 6144 (gap history 3072 / 6144): s0 **0.001**, s1 **0.000**, s2 **0.004** (s.e. 0.029; 0.048 / 0.004), all **CONVERGED**; each corrected once, then honest. **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+EP` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+EP_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=1600 ppo.n_epochs=20 g.use_regularization=False g.epochs=1000 protocol.update_bonus=1.0 episodes=6144 anneal.last=0.25 anneal.floor=0.1 n_envs=64 reward_scale=0.01625`: the run's config at its final length, 6144) → `... submit` → **1987207**.
- `B1_P1eq1_LN+RS+AN_confirm` at 3072: s20 **0.038** (s.e. 0.028) **PLATEAU** (corrected once; best response 2 corrections), s21 **0.015** CONVERGED, s22 **0.029** (s.e. 0.021) CONVERGED (corrected twice, best response 3). **Rule 4: the only unconverged seed is PLATEAU, so the confirmation is finished and failed** (rule 4 extends only for IMPROVING seeds).
- Grid swap `B1_P2swap_LE+NET+ENT3_confirm` at 3072: s21 **0.004**, s22 **0.009** CONVERGED (corrected once, then honest); s20 NEEDS BR. Tomato swap `B1_P2swap_LN+ES10+N4`: s1, s2 NEEDS BR.
- **Rule 3:** `... br_missing submit` → **1987208** (grid swap confirm s20), **1987209** (Tomato swap s1, s2).
- AS no-reg confirmations now: `+ENT3_confirm` → 6144 (1987156), `+N4_confirm` (1987110), `+ES10+N4_confirm` (1987149), `+NET_confirm` (1987197), `+EP_confirm` (1987207); `+AN_confirm` failed.
- Queue (this campaign): 26 jobs. Cells DONE: 3 of 12.

## 2026-11-15, iteration 71 (06:03–06:08): **grid swap DONE** (`B1_P2swap_LE+NET+ENT3_confirm` 3/3 at 3072); AS no-reg `+GL` finished 6144 (check 1987217)

- **1987208** (`br_grid_B1_P2swap_LE+NET+ENT3_confirm`, s20 at 3072) COMPLETED (1:30): s20 **0.007** (s.e. 0.004) CONVERGED; it now reaches the goal after its correction (true about 22), where at 1536 it never did (0.180).
- `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_P2swap_LE+NET+ENT3_confirm` at 3072: s20 **0.007**, s21 **0.004**, s22 **0.009**, all **CONVERGED**; each corrected once, in round 0, then honest.
- **Rule 4 (`_confirm` run, all CONVERGED after one extension; extended confirmations count, the user, 2026-11-10): the grid swap cell is DONE.** Config `B1_P2swap_LE+NET+ENT3`: `g.l_minus_on=dispreferred anneal.last=0.25 anneal.floor=0.1 ppo.ent_coef=0.09 ppo.net_arch=[256,256] episodes=1536 protocol.update_bonus=1.0`. Tuning seeds 0–2 at 1536: 0.015 / 0.009 / 0.008; confirmation seeds 20–22 at 3072: 0.007 / 0.004 / 0.009.
- **Paired with the no-bonus reference** `O1_P2swap_LE+NET+ENT3` (same config and seeds): tuning 0.011 / 0.020 / 0.012 at 1536; confirmation 0.013 / 0.009 / 0.012 at 1536 (no extension needed). Same end state with and without the bonus (corrected once, then honest); the bonus run's confirmation needed one extension because s20 first failed to reach the goal.
- **The answer for this cell:** with the +1 update bonus, the grid swap optimum is corrected exactly once and then behaves honestly, as without it; PPO converges to that in 6 of 6 seeds.
- **Rule 6b: start nothing new for grid swap.** No other grid swap runs are running.
- AS no-reg `+GL`: **1987047** (extension to 6144) COMPLETED 06:03 (3:32:26, exit 0). **Rule 3:** `... br_missing submit` → **1987217**.
- Queue (this campaign): 25 jobs. Cells DONE: **4 of 12**.

## 2026-11-15, iteration 72 (06:10–06:15): Tomato swap `LN+ES10+N4` 3/3 CONVERGED → confirm (1987223); AS no-reg `+GL` 2/3 at 6144 → extend to 12,288 (1987224)

- Woken by the check wait: **1987217** (`br_absent_supervisor_B1_P1eq1_LN+RS+GL` at 6144; 2:29) COMPLETED 06:10; **1987209** (Tomato swap s1, s2) had COMPLETED.
- Tomato swap `B1_P2swap_LN+ES10+N4` at 1536: s0 **0.002**, s1 **0.001**, s2 **0.002** (s.e. ≤ 0.000), all **CONVERGED**; each corrected once, in round 0, then honest (true about 422), like its best response and the target. Paired no-bonus reference `O1_P2swap_LN+ES10+N4` (same seeds): 0.001 / 0.001 / 0.002, same end state.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm tomato B1_P2swap_LN+ES10+N4` (dry-run: `submit.sh 48 --env tomato --run-id B1_P2swap_LN+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/tomato/bonus --set ppo.ent_coef=0.03 ppo.batch_size=6400 g.l_minus_on=dispreferred g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 anneal.ent_start=10 anneal.ent_episodes=768 n_envs=256 episodes=1536 protocol.update_bonus=1.0`, identical to its `overrides.json`) → `... submit` → **1987223**. The Tomato swap cell is DONE if this is 3/3 (the run took about 18 h).
- AS `B1_P1eq1_LN+RS+GL` at 6144 (history 3072 / 6144): s0 **0.000**, s1 **0.000** CONVERGED; s2 **0.038** (s.e. 0.030; 0.038 / 0.038) labelled IMPROVING. **Rule 4: extend 2×.** `... extend absent_supervisor B1_P1eq1_LN+RS+GL 12288` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+GL --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 12288`) → `... submit` → **1987224**.
- Queue (this campaign): 24 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 73 (06:15–06:19): tomato_large swap target

- Woken by the target wait: **1984519** (`targets_tomato_large_P2swap_bonus1`) COMPLETED 06:15 (18:26:45, exit 0), 6 seeds, all fixed points converged.
- **Rule 2, under "Exact predictions":** = no-bonus target + exactly 1.0 in all 6 seeds (corrected once, then honest). The bonus has changed no end state in 40 of the 42 swap / no-reg seeds computed (the exceptions are both Tomato no-reg).
- tomato_large no-reg and base targets (1984520, 1984521) still running (18.5 h).
- Queue (this campaign): 24 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 74 (07:04–07:12): no events (fallback); reports and progress

- No job ended since iteration 73. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume`, `... br_missing` (dry-runs): nothing. `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh report` run.
- Progress (episodes): AS no-reg `+ENT3_confirm` 5664–5856 / 6144, `+N4_confirm` 1800–1896 / 3072, `+ES10+N4_confirm` 1080–1416 / 3072, `+NET_confirm` about 700 / 3072, `+EP_confirm` 1320–1440 / 6144, `+LR` about 9900 / 12,288, `+ES10` about 8340 / 12,288; grid no-reg `LN+LR` 7416 / 12,288; Tomato no-reg `LN` 4152–4680 / 6144, base `L` 2184–2664 / 3072, base `LE` about 2100 / 3072, base exploration 24–264 / 1536, swap `LN+ES10+N4_confirm` no checkpoint yet; tomato_large swap `LE` 144, no-reg `LN+ES10` about 300, base `L` 192–792, `LE` 120–144, `LN` 600–672 (all of 1536).
- The wave-1 jobs started 2026-11-14 11:43 reach the 48 h limit at about 11:43 on 2026-11-16 (tomato_large ×5, Tomato no-reg `LN`); rule 1 resumes them then.
- tomato_large no-reg and base targets (1984520, 1984521) still running (19.3 h). No rule decisions. Queue (this campaign): 24 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 75 (07:17–07:20): tomato_large base target (hides)

- Woken by the target wait: **1984521** (`targets_tomato_large_base_bonus1`) COMPLETED 07:16 (19:27:51, exit 0), 6 seeds, all fixed points converged.
- **Rule 2, under "Exact predictions":** tomato_large base with the bonus **hides** in all 6 seeds (V0 = V_hide = 3,686.8). Base now hides in all four environments with the bonus.
- tomato_large no-reg target (1984520) still running (19.5 h). Queue (this campaign): 23 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 76 (07:32–07:34): AS no-reg `+ENT3_confirm` finished 6144; check 1987260 

- Woken by the training wait: **1987156** (AS `B1_P1eq1_LN+RS+ENT3_confirm` extension to 6144) COMPLETED 07:32 (3:05:20, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+ENT3_confirm`) → `... br_missing submit` → **1987260 ** (s20–s22 at 6144). The AS no-reg cell is DONE if this is 3/3.
- Queue (this campaign): 23 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 77 (07:39–07:43): AS no-reg `+ENT3_confirm` 1/3 at 6144 → extend to 12,288 (1987264)

- Woken by the check wait: **1987260** (`br_absent_supervisor_B1_P1eq1_LN+RS+ENT3_confirm`, s20–s22 at 6144) COMPLETED 07:39 (3:02).
- `B1_P1eq1_LN+RS+ENT3_confirm` (history 3072 / 6144): s20 **0.034** (s.e. 0.016; 0.049 / 0.034) IMPROVING; s21 **0.002** (s.e. 0.032; 0.000 / 0.002) CONVERGED; s22 **0.039** (s.e. 0.032; 0.052 / 0.039) IMPROVING. All three are corrected once, then honest; s20's and s22's best responses take 2 corrections.
- **Rule 4 (confirmation, two seeds IMPROVING, 6144 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+ENT3_confirm 12288` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 12288`) → `... submit` → **1987264**.
- Queue (this campaign): 23 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 78 (09:14–09:20): AS no-reg `+LR` finished 12,288 (check 1987287); Tomato base `L` s0 finished 3072 (check 1987288)

- Fallback wakeup; the training wait then fired for **1987131** (AS `B1_P1eq1_LN+RS+LR` extension to 12,288), COMPLETED 09:15:12 (5:14:29, exit 0).
- **A race again, not a stopped run:** the first `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh resume` dry-run (09:14) listed `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+LR --seeds 2 ... --resume`, because s2 was in its last seconds. Checked: the job COMPLETED 09:15:12, and all three seeds have `metrics.json` at 12,288. A second dry-run lists nothing. Not submitted.
- **Rule 3:** `... br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+LR`, `br_tomato_B1_base_L`) → `... br_missing submit` → **1987287** (`+LR` at 12,288), **1987288** (Tomato base `L`: s0 finished 3072; s1 2784, s2 2448).
- `git pull --no-rebase --no-edit --ff`: already up to date. Queue (this campaign): 24 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 79 (09:21–09:25): AS no-reg `+LR` 3/3 CONVERGED at 12,288 → confirm (1987290)

- Woken by the check wait: **1987287** (`br_absent_supervisor_B1_P1eq1_LN+RS+LR`, s0–s2 at 12,288) COMPLETED 09:21 (2:34).
- `B1_P1eq1_LN+RS+LR` (wave 2, `ppo.learning_rate=0.0001`) at 12,288: s0 **0.000**, s1 **0.000**, s2 **0.000** (s.e. ≤ 0.000), all **CONVERGED**. s2's history 0.065 / 0.039 / 0.000 at 3072 / 6144 / 12,288: it escaped with training length, as rule 6b's note describes (corrected once, then honest; at 12,288 its best response also takes 1 correction).
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+LR` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+LR_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=1600 ppo.learning_rate=0.0001 g.use_regularization=False g.epochs=1000 protocol.update_bonus=1.0 episodes=12288 anneal.last=0.25 anneal.floor=0.1 n_envs=64 reward_scale=0.01625`: the run's config at its final length) → `... submit` → **1987290**. At 12,288 episodes this will take several 48 h jobs (rule 1 resumes it).
- AS no-reg confirmations: `+ENT3` → 12,288 (1987264), `+N4` (1987110), `+ES10+N4` (1987149), `+NET` (1987197), `+EP` at 6144 (1987207), `+LR` at 12,288 (1987290).
- Queue (this campaign): 24 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 80 (09:28–09:30): Tomato base `L` s0 at 3072: 0.161 (still reactive)

- **1987288** (`br_tomato_B1_base_L`, s0 at 3072) COMPLETED 09:27 (8:45): s0 **0.161** (s.e. 0.000; 0.162 at 1536), not converged; still corrected once, then honest (true about 431), while its best response hides. s1 and s2 still training (2784, 2448 of 3072); rule 4 waits for them.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 81 (09:41–09:43): AS no-reg `+N4_confirm` finished; check 1987303 

- Woken by the training wait: **1987110** (AS `B1_P1eq1_LN+RS+N4_confirm`, seeds 20–22, 3072) COMPLETED 09:41 (6:00:02, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_absent_supervisor_B1_P1eq1_LN+RS+N4_confirm`) → `... br_missing submit` → **1987303 **. The AS no-reg cell is DONE if this is 3/3.
- Queue (this campaign): 23 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 82 (09:49–09:52): AS no-reg `+N4_confirm` 1/3 at 3072 → extend to 6144 (1987304)

- Woken by the check wait: **1987303** (`br_absent_supervisor_B1_P1eq1_LN+RS+N4_confirm`, s20–s22 at 3072) COMPLETED 09:48 (2:24).
- `B1_P1eq1_LN+RS+N4_confirm`: s20 **0.065** (s.e. 0.031) PLATEAU; s21 **0.001** (s.e. 0.034) CONVERGED; s22 **0.041** (s.e. 0.030) IMPROVING. All three are corrected once, then honest (true 450); every best response takes 2 corrections (the same shortfall as the other AS no-reg configs on their unconverged seeds).
- **Rule 4 (confirmation, s22 IMPROVING, 3072 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+N4_confirm 6144` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+N4_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`) → `... submit` → **1987304**.
- Queue (this campaign): 23 jobs. Cells DONE: 4 of 12.

## 2026-11-15, iteration 83 (11:13–11:20): AS no-reg `+ES10+N4_confirm` finished; checks 1987388–1987391

- Woken by the training wait: **1987149** (`B1_P1eq1_LN+RS+ES10+N4_confirm`, AS) COMPLETED 11:12 (6:52:12, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing to resume (the five tomato_large runs are still running).
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing`. The dry-run listed AS `B1_P1eq1_LN+RS+ES10+N4_confirm` (s20–s22 finished), AS `B1_P1eq1_LN+RS+GL` (s0 and s2 finished at 12,288; s1 at 12,240) and Tomato `B1_base_L` (s0 and s1 at 3072). Tomato `B1_base_LE` s0 (3072) finished between the dry-run and the submit, so the submit listed it too; its check is valid like the others (`--finished-only`). `... br_missing submit` → **1987388** (AS `+ES10+N4_confirm`), **1987389** (AS `+GL`), **1987390** (Tomato `base_L`), **1987391** (Tomato `base_LE`).
- Queue: 26 jobs in this campaign (limit 60); 33 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 84 (11:20–11:28): AS no-reg `+ES10+N4_confirm` 1/3 at 3072 → extend 6144 (1987395); `+GL` 2/3 at 12,288 → extend 24,576 (1987396)

- Woken by the check wait. **1987388** (`br_absent_supervisor_B1_P1eq1_LN+RS+ES10+N4_confirm`, 3:08) and **1987389** (`br_absent_supervisor_B1_P1eq1_LN+RS+GL`, 2:07; s1 had reached 12,288 by the time the check ran) are COMPLETED. The Tomato base checks 1987390 and 1987391 are still running. The `+GL` training job **1987224** ended at 11:14 (3:45:14, COMPLETED). It ended before the training wait was re-armed, so that wait never reported it. `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **`B1_P1eq1_LN+RS+ES10+N4_confirm` (3072):**
    - s20: **0.070** (s.e. 0.018), IMPROVING.
    - s21: **0.000** (s.e. 0.000), CONVERGED.
    - s22: **0.041** (s.e. 0.035), IMPROVING.
    - s20 and s22 are corrected once, then honest (true 450 ×4). Their best responses take 2 corrections: round 1 at true 400, then 450. s21 and its best response are both corrected once, then honest. This is the same shortfall as every other unconverged AS no-reg seed.
  - **`B1_P1eq1_LN+RS+GL` (12,288):**
    - s0: **0.000**, CONVERGED (0.000 at 3072 / 6144 too).
    - s1: **0.000**, CONVERGED (0.002 / 0.000 at 3072 / 6144).
    - s2: **0.085** (s.e. 0.022), labelled IMPROVING. Its BR gap was 0.038 / 0.038 at 3072 / 6144, so it rose this time. s2's policy is corrected once, then honest (true 449.5–449.9). Its best response takes 2 corrections (round 1 at true 400). The label comes from the training curve's target gaps, not from the BR gap.
- **Rule 4 (any seed IMPROVING, below the AS cap of 24,576): extend 2×.**
  - **`+ES10+N4_confirm`.** Confirmations count once extended (the user, 2026-11-10). `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+ES10+N4_confirm 6144`. Dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`. Submitted with `... submit` → **1987395**.
  - **`+GL`** (wave 2), to the cap. `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+GL 24576`. Dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+GL --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 24576`. Submitted with `... submit` → **1987396**. At the cap the run is finished, whatever the verdict.
- AS no-reg is still open. Running:
  - confirmations: `+ENT3_confirm` → 12,288 (1987264), `+N4_confirm` → 6144 (1987304), `+NET_confirm` (1987197), `+EP_confirm` (1987207), `+LR_confirm` (1987290), `+ES10+N4_confirm` → 6144 (1987395);
  - tuning: `+ES10` → 12,288 (1987157), `+GL` → 24,576 (1987396).
- Queue: 24 jobs in this campaign (limit 60), 31 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 85 (11:26–11:30): Tomato base checks `L` s1 and `LE` s0 at 3072: still reactive, gap 0.16; nothing to decide

- Woken by the check wait. **1987390** (`br_tomato_B1_base_L`, 9:04) and **1987391** (`br_tomato_B1_base_LE`) are COMPLETED. `.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_base_{L,LE}`:
  - **`B1_base_L` (3072):**
    - s0: **0.161** (s.e. 0.000), PLATEAU (iteration 80).
    - s1: **0.161** (s.e. 0.000), IMPROVING.
    - s2: still training, 2784/3072.
  - **`B1_base_LE` (3072):**
    - s0: **0.165** (s.e. 0.000), IMPROVING.
    - s1 and s2: still training, 3024/3072.
  - Every checked seed is reactive: corrected in round 0 (true 46), then honest (true 425–431). Every best response hides (true 59.8 ×4, then 46.0 in round 4). This matches the exact target, so the best responses are not flagged.
- **Rule 4 waits until each run's remaining seeds finish and are checked.** Neither run has an unchecked finished seed now. Tomato base status:
  - `LN` is finished (0/3, PLATEAU);
  - stage 1 from `LN` (`ENT3`, `ES10`, `N4`, `ES10+N4`; 1987173–1987176) is running.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 86 (11:34–11:38): Tomato base `LE` finished at 3072; AS no-reg `+EP_confirm` seeds at 6144; checks 1987419 1987420

- Woken by the training wait: **1987172** (Tomato `B1_base_LE`, extension to 3072) COMPLETED 11:34 (6:48:24, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing, in either campaign.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing`. The dry-run listed AS `B1_P1eq1_LN+RS+EP_confirm` (s20–s22 finished at 6144) and Tomato `B1_base_LE` (s1, s2 at 3072). Submitted with `... br_missing submit` → **1987419** (AS `+EP_confirm`), **1987420** (Tomato `base_LE`). `noreg_fail br_missing` (dry-run): nothing.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 87 (11:56–12:02): AS no-reg `+EP_confirm` 1/3 at 6144 → extend 12,288 (1987446); Tomato base `LE` 0/3 at 3072 → extend 6144 (1987447)

- Woken by the check wait. **1987419** (`br_absent_supervisor_B1_P1eq1_LN+RS+EP_confirm`, 1:22) and **1987420** (`br_tomato_B1_base_LE`, 18:26) are COMPLETED. A correction to iteration 86: the `+EP_confirm` training job **1987207** also ended at 11:34 (5:50:54, COMPLETED, exit 0). `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **`B1_P1eq1_LN+RS+EP_confirm` (6144):**

    | Seed | Gap (s.e.) | Verdict |
    |---|---|---|
    | s20 | **0.032** (0.030) | IMPROVING |
    | s21 | **0.000** (0.000) | CONVERGED |
    | s22 | **0.057** (0.031) | IMPROVING |

    PPO is corrected once, then nearly honest in every seed. s20's best response takes 2 corrections (round 1 at true 400). s22's takes 3 (rounds 1–2 at true 400). It is the same shortfall as the other AS no-reg seeds. s20 and s21 are "above target".
  - **`B1_base_LE` (3072):**

    | Seed | Gap (s.e.) at 1536 | Gap (s.e.) at 3072 | Verdict |
    |---|---|---|---|
    | s0 | 0.167 | **0.165** (0.000) | IMPROVING |
    | s1 | 0.167 | **0.164** (0.000) | IMPROVING |
    | s2 | 0.166 | **0.164** (0.000) | IMPROVING |

    Every seed is reactive: corrected in round 0 (true 46), then honest (true 425–427). Every best response hides (true 59.8 ×4, then 46.0), as the target does. The BR gap has barely moved; the IMPROVING label comes from the training curve's target gaps.
- **Rule 4 (any seed IMPROVING, below the cap): extend 2×.**
  - **`+EP_confirm`.** Command: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+EP_confirm 12288`. Dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+EP_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 12288`. Then `... submit` → **1987446**.
  - **`B1_base_LE`.** Command: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LE 6144`. Dry-run: `submit.sh 48 --env tomato --run-id B1_base_LE --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 6144`. Then `... submit` → **1987447**.
- Queue: 23 jobs in this campaign (limit 60), 30 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 88 (12:02–12:15): quiet tick at 12:02; AS no-reg `+NET_confirm` s20/s21 at 3072 → check 1987473

- **12:02 (scheduled wakeup).**
  - `git pull --no-rebase --no-edit --ff`: already up to date.
  - No campaign job had ended since 11:56.
  - Dry-runs of `br_missing` and `resume`: nothing in either campaign.
  - `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh report`: every seed is either running or its last check is already logged.
  - Progress (episodes): AS no-reg
    - `+ENT3_confirm` 10,896–11,544 / 12,288
    - `+ES10` 11,640–11,712 / 12,288
    - `+NET_confirm` 3000–3024 / 3072
    - `+N4_confirm` 4752–4944 / 6144
    - `+LR_confirm` 2472–4296 / 12,288
    - `+ES10+N4_confirm` 3696–3720 / 6144
    - `+GL` 13,416–13,440 / 24,576
    - `+EP_confirm` 6288 / 12,288
  - Progress (episodes): grid no-reg `LN+LR` 10,104–10,128 / 12,288.
  - Progress (episodes): Tomato
    - no-reg `LN` 5088–5736 / 6144
    - swap `LN+ES10+N4_confirm` 216–312 / 1536
    - base `L` s2 2904 / 3072
    - base `LE` 3096 / 6144
    - base `LN+ENT3` 1032–1080 / 1536
    - base `LN+ES10` 192–264 / 1536
    - base `LN+N4` 768–1056 / 1536
    - base `LN+ES10+N4` 120–144 / 1536
  - Progress (episodes): tomato_large
    - `P2swap_LE` 192
    - `P1eq1_LN+ES10` 576–600
    - `base_L` 264–1056
    - `base_LE` 168–312
    - `base_LN` 888–960, all / 1536
    - These runs have been running about 24 h, so they reach the 48 h limit around noon on 2026-11-16.
  - The tomato_large no-reg target (1984520) is still running (24 h).
- **12:11 (training wait).**
  - The noreg_fail job 1987354 ended; this campaign was unchanged.
  - **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: AS `B1_P1eq1_LN+RS+NET_confirm`, s20 and s21 finished at 3072, s22 at 3048) → `... br_missing submit` → **1987473**.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 89 (12:19–12:24): AS no-reg `+NET_confirm` 0/3 at 3072 → extend 6144 (1987486)

- **Check results.** Woken by the check wait. **1987473** (`br_absent_supervisor_B1_P1eq1_LN+RS+NET_confirm`) COMPLETED 12:13 (1:36). The training job **1987197** had finished at 12:12 (6:39:33, COMPLETED), so the check covers all three seeds at 3072. `.venv/bin/python experiments/step4_convergence.py results/step4/absent_supervisor/bonus/B1_P1eq1_LN+RS+NET_confirm`:

  | Seed | Gap | s.e. | Label |
  |---|---|---|---|
  | s20 | **0.062** | 0.031 | IMPROVING |
  | s21 | **0.031** | 0.048 | IMPROVING |
  | s22 | **0.066** | 0.034 | IMPROVING |

  - **PPO.** In every seed it is corrected once, then nearly honest: true 446–449 against 450.
  - **Best responses.** Every one takes 2 corrections (round 1 at true 400).
  - **Above target.** s20 and s21.
- **Rule 4 (every seed IMPROVING, 3072 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+NET_confirm 6144` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+NET_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 6144`) → `... submit` → **1987486**.
- **Queue.** 23 jobs in this campaign (limit 60), 30 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 90 (12:51–12:55): Tomato base `L` finished at 3072; AS no-reg `+ENT3_confirm` s20/s22 at 12,288; checks 1987561 1987562

- **12:51 wake-up.**
  - Scheduled wakeup. `git pull --no-rebase --no-edit --ff`: already up to date.
  - **1986905** (Tomato `B1_base_L`, extension to 3072) COMPLETED 12:50 (11:23:10, exit 0).
  - `... resume` (dry-run): nothing, in either campaign.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing`. It listed AS `B1_P1eq1_LN+RS+ENT3_confirm` (s20 and s22 finished at 12,288; s21 at 12,024) and Tomato `B1_base_L` (s2 finished at 3072).
  - Submitted: `... br_missing submit` → **1987561** (AS `+ENT3_confirm`), **1987562** (Tomato `base_L`).
  - noreg_fail `br_missing` (dry-run): nothing.
- The tomato_large no-reg target (1984520) is still running (25 h). Cells DONE: 4 of 12.

## 2026-11-15, iteration 91 (12:58–13:05): Tomato base `L` 0/3 at 3072 → extend 6144 (1987620 ); AS no-reg `+ES10` finished; checks 1987616 1987617

- **Wake-ups:**
  - The check wait: **1987562** (`br_tomato_B1_base_L`, s2) COMPLETED 12:58 (7:04).
  - The training wait: **1987157** (AS `B1_P1eq1_LN+RS+ES10`, extension to 12,288) COMPLETED 12:59 (8:18:11, exit 0).
  - **1987561** (`br_absent_supervisor_B1_P1eq1_LN+RS+ENT3_confirm`, s20 and s22 at 12,288) COMPLETED 12:53 (1:09).
  - `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing, in either campaign.
- **Tomato `B1_base_L` (3072)** (`.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_base_L`):

  | Seed | BR gap | s.e. | Label | Policy |
  |---|---|---|---|---|
  | s0 | **0.161** | 0.000 | PLATEAU | reactive: corrected in round 0, then honest |
  | s1 | **0.161** | 0.000 | IMPROVING | reactive: corrected in round 0, then honest |
  | s2 | **0.161** | 0.000 | PLATEAU | partly honest already in round 0 (true 191), then honest (296 → 430) |

  Every best response hides (true 59.8 ×4, then 46.0), as the target does.
- **Rule 4 (s1 IMPROVING, 3072 < cap 12,288): extend 2×.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_L 6144` printed `submit.sh 48 --env tomato --run-id B1_base_L --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 6144`.
  - Submitted with `... submit` → **1987620 **.
- **AS `B1_P1eq1_LN+RS+ENT3_confirm` (12,288; check 1987561):**
  - s20: **0.0301** (s.e. 0.025), not converged by 0.0001.
  - s22: **0.0225** (s.e. 0.030), CONVERGED.
  - Both policies are corrected once, then honest (true 449.7–449.9). Both best responses take 2 corrections.
  - s21 was at 12,024 then. It is no longer listed as running, and the next `br_missing` submit included it (below), so it has finished. Rule 4 for this run waits for s21's check.
- **Rule 3:**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed AS `+ES10`.
  - `... br_missing submit` also listed `+ENT3_confirm`, whose s21 finished between the two commands.
  - Submitted: **1987616** (AS `+ENT3_confirm`), **1987617** (AS `+ES10`).
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 92 (13:03–13:08): AS no-reg `+ENT3_confirm` 2/3 at 12,288 → extend to the cap 24,576 (1987629 ); `+ES10` 2/3 at 12,288 → extend to the cap (1987630 )

- Woken by the check wait: **1987616** (`br_absent_supervisor_B1_P1eq1_LN+RS+ENT3_confirm`, s21, 1:03) and **1987617** (`br_absent_supervisor_B1_P1eq1_LN+RS+ES10`, 1:20), both COMPLETED 13:01. BR gap by checkpoint (`step4_br/`) and `.venv/bin/python experiments/step4_convergence.py <run>` at 12,288:
  - **`B1_P1eq1_LN+RS+ENT3_confirm`:**
    - s20 0.049 / 0.034 / **0.0301** (s.e. 0.025) at 3072 / 6144 / 12,288, IMPROVING.
    - s21 0.000 / 0.002 / **0.000**, CONVERGED.
    - s22 0.052 / 0.039 / **0.023** (s.e. 0.030), CONVERGED.
    - All three policies are corrected once, then honest (true 449.7–449.9). The best responses of s20 and s22 take 2 corrections.
  - **`B1_P1eq1_LN+RS+ES10`** (rule 6b exploration run):
    - s0 **0.000** and s1 **0.000**, CONVERGED.
    - s2 0.061 / 0.074 / **0.075** (s.e. 0.021), IMPROVING by label; its BR gap is flat.
    - s2 is corrected once, then honest (true 449.8–449.9). Its best response takes 2 corrections (round 1 at true 400).
- **Rule 4, `+ENT3_confirm`** (confirmation; s20 IMPROVING, 12,288 < AS cap 24,576): extend 2× to the cap. Confirmations count once extended.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+ENT3_confirm 24576` printed `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 24576`.
  - `... submit` → **1987629 **.
- **Rule 6b extension rule, `+ES10`** (s2 unconverged, below the cap): extend 2× to the cap, whatever the verdict.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+ES10 24576` printed `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ES10 --seeds 0 1 2 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 24576`.
  - `... submit` → **1987630 **.
  - At the cap, both runs are finished whatever the verdict.
- Queue: 23 jobs in this campaign (limit 60), 30 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 93 (13:40–13:44): AS no-reg `+N4_confirm` s20/s21 at 6144, Tomato no-reg `LN` s0 at 6144; checks 1987686 1987687

- **Scheduled wakeup.** `git pull --no-rebase --no-edit --ff`: already up to date. No campaign job has ended since 13:03. `... resume` (dry-run): nothing in either campaign.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - AS `B1_P1eq1_LN+RS+N4_confirm`: s20 and s21 finished at 6144, s22 at 5808.
  - Tomato `B1_P1eq1_LN`: s0 finished at 6144, s1 at 5592, s2 at 5424.

  `... br_missing submit` → **1987686** (AS `+N4_confirm`), **1987687** (Tomato no-reg `LN`).
- **Still running.** The tomato_large no-reg target (1984520) has run 26 h. Cells DONE: 4 of 12.

## 2026-11-15, iteration 94 (13:48–13:52): partial checks; AS `+N4_confirm` s20 0.032, s21 0.022; Tomato no-reg `LN` s0 0.020 CONVERGED; nothing to decide

- **Check jobs.** Woken by the check wait. **1987686** (`br_absent_supervisor_B1_P1eq1_LN+RS+N4_confirm`, 2:02) and **1987687** (`br_tomato_B1_P1eq1_LN`, 7:04) are COMPLETED. Verdicts from `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **AS `B1_P1eq1_LN+RS+N4_confirm` (6144).**
    - s20: **0.032** (s.e. 0.024), PLATEAU; it was 0.065 at 3072.
    - s21: **0.022** (s.e. 0.043), CONVERGED.
    - Both policies are corrected once, then honest (true 450). Both best responses take 2 corrections.
    - s22 is still training (5904/6144). Its training curve already shows 2 corrections (true 399.6 in round 1), as its best response did at 3072.
  - **Tomato `B1_P1eq1_LN` (6144).**
    - s0: **0.020** (s.e. 0.010), CONVERGED. PPO is corrected once, then honest (true 432–433).
    - The best response takes 3.72 corrections (rounds 0–2, then 0.73 in round 3; true 426–434). s0's own target is corrected once, then honest (true 433.4), which PPO matches; the 3.72 correction pattern resembles the s1 target (3.75). The value gap stays small because each further correction adds only about one bonus unit plus a few tomatoes.
    - s1 (5616) and s2 (5472) are still training.
- **Decision.** Rule 4 is applied to each run once its remaining seeds finish and are checked. Cells DONE: 4 of 12.

## 2026-11-15, iteration 95 (14:05–14:08): AS no-reg `+N4_confirm` finished at 6144; check 1987732 

- Woken by the training wait: **1987304** (AS `B1_P1eq1_LN+RS+N4_confirm`, extension to 6144) COMPLETED 14:05 (4:15:19, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: AS `B1_P1eq1_LN+RS+N4_confirm`, s22) → `... br_missing submit` → **1987732 **. s20 (0.032, PLATEAU) and s21 (0.022, CONVERGED) were checked in iteration 94. Cells DONE: 4 of 12.

## 2026-11-15, iteration 96 (14:08–14:12): AS no-reg `+N4_confirm` 2/3 at 6144, s20 PLATEAU → finished; this confirmation failed

- **Check result.** Woken by the check wait: **1987732** (`br_absent_supervisor_B1_P1eq1_LN+RS+N4_confirm`, s22, 0:40) COMPLETED 14:07. Verdicts from `.venv/bin/python experiments/step4_convergence.py results/step4/absent_supervisor/bonus/B1_P1eq1_LN+RS+N4_confirm` (BR gap at 3072 / 6144):

  | Seed | Gap at 3072 | Gap at 6144 (s.e.) | Verdict | Policy | Best response |
  |---|---|---|---|---|---|
  | s20 | 0.065 | **0.032** (0.024) | PLATEAU | corrected once, then honest | 2 corrections |
  | s21 | 0.001 | **0.022** (0.043) | CONVERGED | corrected once, then honest | 2 corrections |
  | s22 | 0.041 | **0.002** (0.024) | CONVERGED | 2 corrections (round 1 at true 400), then honest | 3 corrections (rounds 1–2 at true 400) |

- **Rule 4: the only unconverged seed is PLATEAU, so the config is finished and not extended. This confirmation failed (2/3).**
  - Confirmations follow rule 4, not the rule 6b extension rule ("Confirmation works as in rule 4").
  - The optimal campaign treated a 6b run's confirmation the same way (its log, iteration 151: `LN+LR+ES10+N4` failed its confirmation with its unconverged seeds PLATEAU).
  - s20 missed by 0.002.
- **AS no-reg status.** Failed confirmations: `+AN_confirm` and `+N4_confirm`. Still running:
  - confirmations `+ENT3_confirm` → 24,576 (1987629), `+ES10+N4_confirm` → 6144 (1987395), `+NET_confirm` → 6144 (1987486), `+EP_confirm` → 12,288 (1987446) and `+LR_confirm` → 12,288 (1987290);
  - exploration and wave-2 runs `+ES10` → 24,576 (1987630) and `+GL` → 24,576 (1987396).
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 97 (14:12–14:15): Tomato base `LN+ENT3` finished at 1536; check 1987750 

- Woken by the training wait: **1987173** (Tomato `B1_base_LN+ENT3`, rule 6b stage 1) COMPLETED 14:10 (9:25:05, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: Tomato `B1_base_LN+ENT3`) → `... br_missing submit` → **1987750 **. Cells DONE: 4 of 12.

## 2026-11-15, iteration 98 (14:32–14:36): Tomato base `LN+ENT3` 0/3 at 1536 (still reactive) → extend 3072 (1987845 )

- Woken by the check wait: **1987750** (`br_tomato_B1_base_LN+ENT3`, 18:34) COMPLETED 14:31. `.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_base_LN+ENT3` (1536):
  - s0 **0.163**, s1 **0.162**, s2 **0.162** (s.e. 0.000 each). All three are labelled IMPROVING.
  - Every seed is reactive: corrected in round 0 (true 46), then honest (true 428–431).
  - Every best response hides: true 59.8 ×4, then 46.0, the same as the target. Entropy 3× has not changed the behaviour of `LN` (0.16).
- **Rule 6b extension rule.** This is an exploration run and a seed is unconverged, so it is extended 2× (to 3072, under the 12,288 cap), whatever the verdict.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+ENT3 3072` printed `submit.sh 48 --env tomato --run-id B1_base_LN+ENT3 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 3072`.
  - Submitted with `... submit` → **1987845 **.
- Queue: 22 jobs in this campaign (limit 60), 29 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 99 (14:50–14:54): AS no-reg `+ES10+N4_confirm` finished at 6144; Tomato base `LN+N4` s0 at 1536; checks 1987870 1987871

- **Trigger.** The training wait fired: **1987395** (AS `B1_P1eq1_LN+RS+ES10+N4_confirm`, extension to 6144) COMPLETED 14:50 (3:29:23, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed AS `+ES10+N4_confirm` and Tomato `B1_base_LN+N4` (s0 finished at 1536; s1 at 1344, s2 at 1248). Then `... br_missing submit` → **1987870** (AS `+ES10+N4_confirm`) and **1987871** (Tomato `base_LN+N4`).
- **Cells DONE:** 4 of 12.
