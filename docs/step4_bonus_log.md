# Step 4 update-bonus campaign: decision log

Procedure: `docs/step4_bonus.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=bonus`.

## Status

**Cells DONE: 7 of 12.** Grid no-reg (`B1_P1eq1_LN+LR+ENT3`, the cell's reference config plus `ppo.learning_rate=1e-4` (wave 2) and entropy 3× (rule 6b): tuning 3/3 at 3072 (0.000 / 0.000 / 0.001), confirmation 3/3 at 6144 after one extension (0.000 / 0.002 / 0.025); corrected once, then honest (true 22), like its target; iteration 181). AS no-reg (`B1_P1eq1_LN+RS+EP`, the cell's reference config plus `ppo.n_epochs=20` (wave 2): tuning 3/3 at 6144 (0.001 / 0.000 / 0.004), confirmation 3/3 at the 24,576 cap after two extensions (0.001 / 0.001 / 0.027); corrected once, then honest (true about 449); the targets take 1–3 corrections, and the extra corrections are worth less than 3%). Tomato swap (`B1_P2swap_LN+ES10+N4`, the cell's reference config with the bonus: tuning 3/3 at 1536 (0.002 / 0.001 / 0.002), confirmation 3/3 at 1536 (0.002 / 0.001 / 0.002), no extension; corrected once, then honest (true about 420), like its target). Grid swap (`B1_P2swap_LE+NET+ENT3`: tuning 3/3 at 1536, confirmation 3/3 at 3072 after one extension; corrected once, then honest, like its target). AS swap (`B1_P2swap_LN`: tuning 3/3, confirmation 3/3; corrected once, then never again, like its target; after the correction the route is a near-tie between honest and −50, see flag). Grid base (`B1_base_LE`: tuning 3/3, confirmation 3/3; hides, like its target). AS base (`B1_base_L`: tuning 3/3, confirmation 3/3; hides, like its target; 4 of its 6 seeds pass at 0.027–0.028, just under 0.03, see iteration 19).

## Flags for the user

- **barley-04.** Every submit still carries `EXCLUDE=barley-04`, following your standing instruction from the optimal campaign. On 2026-11-14 at 11:42, `sinfo -n barley-04` shows it `allocated` with no reason set, so it may be healthy again. Excluding it costs nothing; say if I should drop it.

- **AS no-reg seed 21: target fixed point does not converge (with and without the bonus).** `results/step4/absent_supervisor/targets/P1eq1_bonus1/seed21.json` has `fixed_point_converged: false`: the iteration alternates between "3 corrections per episode" (V0 8,040.4) and "corrected in round 0, then never again" (V0 7,927.0). The no-bonus target `P1eq1/seed21.json` has the same two-cycle (8,037.4 / 7,926.0). Not a bug: the corrections fitted on each behaviour make the other one optimal. Per rule 2 the last iteration (3 corrections) is used. PPO's verdict comes from the best-response check, which this does not affect.

- **Tomato no-reg seed 2: target fixed point does not converge (with and without the bonus).** `results/step4/tomato/targets/P1eq1_bonus1/seed2.json`: the iteration cycles 3.00 → 2.71 → 1 → 3.00 → 2.71 corrections per episode; the no-bonus `P1eq1/seed2.json` cycles too (3.00 / 2.48 / 2.99 / 2.51 / 2.91). Per rule 2 the last iteration (2.71) is used. Not a bug as far as I can tell (the corrections fitted on each behaviour favour another); PPO's verdict comes from the best-response check.

- **AS swap: after its correction, honest play and a −50/−100 route are a near-tie, and the best response picks either, depending on the seed (with and without the bonus).** The target (fitted on the exact optimum's play) is "corrected once, then true −50 ×4" (s2: −100). The paired best-response checks at 3072 (fitted on PPO's own play, `results/step4/absent_supervisor/{optimal/O1_P2swap_LN,bonus/B1_P2swap_LN}/step4_br/seed<s>_ep3072.json`) pick, by seed 0 / 1 / 2: without the bonus **honest 450 / −50 / −50**; with the bonus **−50 / honest 450 / honest 450**. Across the six checks the best response receives 2,247–2,392 per round after the correction whichever route it takes, so the two routes are close in received reward (a direct same-seed comparison of the two routes is not in these files). PPO is within 0–2% of its best response in all six. So "is the swap's optimum honest after its correction in AS?" has no single answer here: it depends on the draw / fit, which is the same ambiguity the optimal campaign's AS swap cell had. Not a bonus effect; reported for the answer, nothing changed.

- **tomato_large no-reg seed 1: target fixed point does not converge (with and without the bonus).** `results/step4/tomato_large/targets/P1eq1_bonus1/seed1.json` and `P1eq1/seed1.json` both have `fixed_point_converged: false`. Both cycle 4 → 3 → 4 → about 3.47 → 4 corrections per episode and stop at the 5-iteration limit. Per rule 2 the last iteration (4 corrections, then honest) is the target. The bonus does not change it. This is the third such seed, after AS no-reg s21 and Tomato no-reg s2. All three are no-regulariser cells that alternate between neighbouring numbers of corrections, so their targets' correction counts are uncertain by about one.

- **A running seed's checkpoint was committed once; the cause is fixed (iteration 109, 2026-11-15).**
  - **The cause.** A resumed seed renames `metrics.json` to `metrics_ep<N>.json`. On the NFS home, the login node kept the old name's cached dentry for at least 17 minutes: `stat`/`open` found it, `ls` did not. `step4_commit.sh` tests `[[ -f metrics.json ]]`, so it treated Tomato `B1_base_LN+N4` (extension 1988345 running) as finished.
  - **What was committed.** Commit 1a9758ce contains that run's mid-run checkpoint: seeds 0–2 at episode 1560 of 3072, with `logs.npz`, `model.zip`, the round CSVs and `progress.json`. The snapshot is consistent (checkpoints are written atomically). The run's finished files will be committed over it later. I did not rewrite history.
  - **Scope.** A scan of every commit since 2026-11-14 11:00 finds no other `logs.npz` committed with `progress.json` short of its target.
  - **The fix.** `step4_commit.sh`, the `step4_optimal.sh` resume test, `step4_br.py` (`finished()`, used by `--missing` / `br_missing` and `--finished-only`) and `step4_convergence.py` now read the directory listing. The new test is `test_finished_seed_is_read_from_the_directory_listing`; all 21 tests in `tests/test_step4.py` pass.
  - **Optimal campaign.** It uses the same scripts. It is paused, and its runs are not affected.

- **Rule 6b for tomato_large no-reg submits 2 of the 4 stage-1 runs (iteration 183).** The base `B1_P1eq1_LN+ES10` already has the ES10 schedule (`anneal.ent_start=10 anneal.ent_episodes=768`). So `+ES10` would rerun the base config on the same seeds, and `+ES10+N4` would duplicate `+N4`. As with `RS` above, I submitted only the distinct ones, `+ENT3` (1990239) and `+N4` (1990240). Say if you want the duplicates run anyway, or a different ES factor here (for example a longer or stronger schedule).

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

**tomato_large, no regulariser (+bonus)** (job 1984520, 28 h; computed 2026-11-15 16:03):

| Seed | With bonus: end state (corrections by round) | Without bonus | Same? | ΔV0 (1.0 × corrections) |
|---|---|---|---|---|
| 0 | 3 per episode (rounds 0–2) | 3 | yes | +3.0 (3.00) |
| 1 | 4 per episode (rounds 0–3) — **fixed point not converged** | 4 — not converged either | yes (see flag) | −85.6 (4.00) |
| 2 | 3 (rounds 0–2) | 3 | yes | +3.0 (3.00) |
| 20 | 4 (rounds 0–3) | 4 | yes | +4.0 (4.00) |
| 21 | 4 (rounds 0–3) | 4 | yes | +64.5 (4.00) |
| 22 | 4 (rounds 0–3) | 4 | yes | +4.0 (4.00) |

- **The end state is unchanged in all 6 seeds**, and so are the true return by round, the windows and the corrections per episode. After the last correction the optimum is honest: true 515.5–522.5 per round (65.0 in the open round 0). V_hide is 3,686.8, and the margin over hiding is +4,705 to +5,259.
- **V0 rises by exactly 1.0 × corrections in 4 of 6 seeds.**
  - **s21 (+64.5):** both fixed points converged, but they took different paths: with the bonus 3.35 → 3.00 → 4.00 → 4.00; without it 3.29 → 4.00 → 3.89 → 4.00 → 4.00. So the final corrections were fitted on different rollouts.
  - **s1 (−85.6):** both iterations follow the same cycle, 4 → 3 → 4 → about 3.47 → 4, and stop at the 5-iteration limit. Iteration 3 differs slightly (3.49 vs 3.45 corrections), and iteration 4's corrections are fitted on that. Per rule 2 the last iteration is the target.

**Summary (all 12 cells):**
- **End state.** In 46 of the 48 swap / no-reg seeds (8 cells × 6 seeds), the bonus leaves the exact end state unchanged. The exceptions are both Tomato no-reg: s1 has one extra correction in round 3 (3.75 vs 3.00), and s2's fixed point cycles.
- **V0.** In 44 of the 48 seeds, V0 rises by exactly 1.0 × corrections. Besides the two Tomato no-reg seeds, the exceptions are tomato_large no-reg s1 and s21, where V0 differs by a fixed-point path effect (above), not by a change of end state.
- **Base** hides in all 24 seeds.

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

## 2026-11-15, iteration 100 (15:00–15:04): AS no-reg `+ES10+N4_confirm` 1/3 at 6144 → extend 12,288 (1987881 ); Tomato base `LN+N4` s0 0.159

- Woken by the check wait: **1987870** (`br_absent_supervisor_B1_P1eq1_LN+RS+ES10+N4_confirm`, 1:21) and **1987871** (`br_tomato_B1_base_LN+N4`, 8:49) COMPLETED. Verdicts from `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **`B1_P1eq1_LN+RS+ES10+N4_confirm`**, BR gap at 3072 / 6144:

    | Seed | Gap at 3072 | Gap at 6144 (s.e.) | Verdict | Best response |
    |---|---|---|---|---|
    | s20 | 0.070 | **0.0305** (0.027) | IMPROVING | 4 corrections (rounds 1–3 at true 400) |
    | s21 | 0.000 | **0.012** (0.037) | CONVERGED | 2 corrections |
    | s22 | 0.041 | **0.049** (0.037) | PLATEAU | 2 corrections |

    All three policies are corrected once, then honest (true 450).
  - **Tomato `B1_base_LN+N4`**: s0 **0.159** (s.e. 0.000) at 1536. It is reactive: corrected in round 0, then honest (true 433). The best response hides, as in the target. s1 and s2 are still training (1344, 1248).
- **Rule 4 (confirmation; s20 IMPROVING, 6144 < AS cap 24,576): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+ES10+N4_confirm 12288` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 12288`) → `... submit` → **1987881 **. Tomato `LN+N4` waits for its other seeds.
- Queue: 22 jobs in this campaign (limit 60), 29 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 101 (15:07–15:10): grid no-reg `LN+LR` reached the 12,288 cap; check 1987893 

- Woken by the training wait: **1987190** (grid `B1_P1eq1_LN+LR`, extension to 12,288) COMPLETED 15:06 (10:10:23, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `B1_P1eq1_LN+LR`) → `... br_missing submit` → **1987893 **. At the cap the run is finished whatever the verdict: 3/3 → `confirm`; otherwise the cell's next step comes from rule 5 (wave 2) or 6b. Cells DONE: 4 of 12.

## 2026-11-15, iteration 102 (15:12–15:22): grid no-reg `LN+LR` 2/3 at the 12,288 cap → finished; wave 2 (1987902–1987906) and rule 6b stage 1 (1987907–1987910)

- **The check.** Woken by the check wait: **1987893** (`br_grid_B1_P1eq1_LN+LR`, 3:24) COMPLETED 15:11. `.venv/bin/python experiments/step4_convergence.py results/step4/grid/bonus/B1_P1eq1_LN+LR`, BR gap at 6144 / 12,288:

  | Seed | 6144 | 12,288 | Verdict | Behaviour |
  |---|---|---|---|---|
  | s0 | 0.002 | **0.000** | CONVERGED | corrected once, then honest (true 22 ×4), like its best response |
  | s1 | 0.011 | **0.000** | CONVERGED | the same |
  | s2 | 0.055 | **0.067** (s.e. 0.031) | PLATEAU | corrected once, then never reaches the goal (true −100 every round). Its best response takes 2 corrections, then is honest (true −100, −100, 22 ×3). |

- **Rule 4: at the cap, 2/3 → the run is finished.**
- **A missed step, corrected now.** Rule 6b as changed by docs/step4_bonus.md starts exploration "once every wave-1 run of that cell has a check and none is CONVERGED 3/3". Grid no-reg met that in iteration 66 (2/3 at 6144), but I only extended the run then and did not start exploration. I start it now, together with wave 2. This is the same order as AS no-reg, whose wave 2 and exploration started together in iteration 32.
- **Rule 5 (wave 2).** The cell's one wave-1 run is finished, and it is neither CONVERGED 3/3 nor IMPROVING.
  - Extras: `.venv/bin/python scripts/farmshare/run_sets.py results/step4/grid/bonus/B1_P1eq1_LN+LR`, minus `episodes=`, which gives `g.use_regularization=False anneal.last=0.25 anneal.floor=0.1 n_envs=64 ppo.batch_size=1600 ppo.learning_rate=0.0001 protocol.update_bonus=1.0`.
  - Command for each: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh ppo grid P1eq1 "LN+LR+<tag>" "<extras> <factor>" submit`, at 1536 episodes (the grid wave-1 length). Each was dry-run first; later duplicate keys win.

    | Run | Factor | Job |
    |---|---|---|
    | `GL` | `ppo.gae_lambda=1.0` | **1987902** |
    | `NET` | `ppo.net_arch=[256,256]` | **1987903** |
    | `RS` | `reward_scale=0.0025`, i.e. 0.25 × grid's 0.01, as in the optimal campaign's `O1_P1eq1_LN+RS` | **1987904** |
    | `EP` | `ppo.n_epochs=20` | **1987905** |
    | `AN` | `anneal.last=0.5` | **1987906** |

  - **`LR` skipped:** the base already has `ppo.learning_rate=0.0001`, which is exactly the `LR` factor. This is the same as `RS` being skipped for AS no-reg.
- **Rule 6b (exploration, stage 1)** from the cell's run with the smallest mean gap (the only one).
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh explore grid P1eq1 B1_P1eq1_LN+LR`. It gives 4 runs at 1536, each the base's overrides plus:
    - `+ENT3`: `ppo.ent_coef=0.03`
    - `+ES10`: `anneal.ent_start=10 anneal.ent_episodes=768`
    - `+N4`: `n_envs=256 ppo.batch_size=6400`
    - `+ES10+N4`
  - Submitted with `... submit` → **1987907** (ENT3), **1987908** (ES10), **1987909** (N4), **1987910** (ES10+N4).
- **Budget:** this campaign has 30 jobs (≤ 60); all jobs 37 (≤ 110). Cells DONE: 4 of 12.

## 2026-11-15, iteration 103 (15:55–15:59): Tomato no-reg `LN` s1 and Tomato base `LN+N4` s1 finished; checks 1988088 1988089

- Woken by the training wait. The job that ended was noreg_fail's (1987355); this campaign's run states had moved on since the last check. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - Tomato `B1_P1eq1_LN`: s1 finished at 6144; s2 at 6120.
  - Tomato `B1_base_LN+N4`: s1 finished at 1536; s2 at 1512.

  `... br_missing submit` → **1988088** (Tomato no-reg `LN`), **1988089** (Tomato base `LN+N4`).
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 104 (16:03–16:15): the last target (tomato_large no-reg) is in; "Exact predictions" complete

- **The job.** Woken by the target wait: **1984520** (`targets_tomato_large_P1eq1_bonus1`) COMPLETED 16:03 (1-04:19:41, exit 0).
- **The result.** `results/step4/tomato_large/targets/P1eq1_bonus1/seed{0,1,2,20,21,22}.json` were compared with the no-bonus targets (`.../P1eq1/`):
  - The end state is the same in all 6 seeds: 3 or 4 corrections, then honest.
  - V0 = no-bonus + 1.0 × corrections in 4 of 6 seeds. The other two are s1 (−85.6) and s21 (+64.5), where the fixed-point paths differ.
  - Seed 1's fixed point does not converge, with or without the bonus.
- **The log.** I wrote all of this under "Exact predictions" at the top, with the all-12-cell summary, and added the s1 flag under "Flags for the user".
- **What follows.** All 12 bonus targets are computed. Rule 2 needs nothing more. Cells DONE: 4 of 12.

## 2026-11-15, iteration 105 (16:15–16:22): Tomato no-reg `LN` 3/3 CONVERGED at 6144 → `confirm` (1988344); Tomato base `LN+N4` 0/3 → extend 3072 (1988345)

- **Checks.** Woken by the check wait: **1988088** (`br_tomato_B1_P1eq1_LN`) and **1988089** (`br_tomato_B1_base_LN+N4`) COMPLETED. Both training jobs had ended before their checks ran: **1984533** (Tomato `B1_P1eq1_LN`, 6144) COMPLETED 15:56 (1-04:11:09) and **1987175** (Tomato `B1_base_LN+N4`) COMPLETED 15:57 (11:10:39). So every seed was checked. Results of `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **Tomato `B1_P1eq1_LN` (6144, the cell's wave-1 run), all CONVERGED:**

    | Seed | Gap (s.e.) | PPO | Best response | Own target |
    |---|---|---|---|---|
    | s0 | **0.020** (0.010) | corrected once, then honest (true 432) | 3.72 corrections | corrected once, which PPO matches |
    | s1 | **0.002** (0.000) | corrected once, then honest (true 432) | corrected once | 3.75 corrections |
    | s2 | **0.009** (0.009) | corrected once, then honest (true 432) | 2 corrections | 2.71 corrections, fixed point not converged |

    Further corrections are worth only about 1–2% of V here, so a policy that takes one correction is within 3% of best responses that take 2–3.7.
  - **Tomato `B1_base_LN+N4` (1536, rule 6b stage 1):** s0 **0.159**, s1 **0.159**, s2 **0.158** (s.e. 0.000), all PLATEAU. Every seed is reactive: corrected in round 0, then honest (true 433). Every best response hides, as the target does.
- **Rule 4, Tomato `B1_P1eq1_LN`: tuning run, all CONVERGED → `confirm`.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm tomato B1_P1eq1_LN` printed `submit.sh 48 --env tomato --run-id B1_P1eq1_LN_confirm --seeds 20 21 22 --results-dir results/step4/tomato/bonus --set ppo.ent_coef=0.03 ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 n_envs=64 episodes=6144 protocol.update_bonus=1.0`. That matches `run_sets.py` on the run.
  - Submitted with `... submit` → **1988344**. The Tomato no-reg cell is DONE when this is 3/3.
  - Timing: its tuning run took 28 h for 6144 episodes, within the 48 h limit.
- **Rule 6b extension rule, Tomato `B1_base_LN+N4`: exploration run with seeds unconverged → extend 2× whatever the verdict.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+N4 3072` printed `submit.sh 48 --env tomato --run-id B1_base_LN+N4 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 3072`.
  - Submitted with `... submit` → **1988345**.
- **Queue.** 29 jobs in this campaign (limit 60), 36 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 106 (16:48–16:52): partial checks on AS `+NET_confirm` (s21) and Tomato swap `LN+ES10+N4_confirm` (s20, s22) → 1988395 1988396

- **Wake-up.** Scheduled wakeup. `git pull --no-rebase --no-edit --ff`: already up to date. No training job has ended since 16:15. `... resume` (dry-run): nothing.
- **Rule 3.** Dry-run of `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed:
  - AS `B1_P1eq1_LN+RS+NET_confirm`: s21 finished at 6144; s20 at 6096, s22 at 6120.
  - Tomato `B1_P2swap_LN+ES10+N4_confirm`: s20 and s22 finished at 1536; s21 at 1296.
- **Submitted.** `... br_missing submit` → **1988395** (AS `+NET_confirm`), **1988396** (Tomato swap confirmation). The Tomato swap cell is DONE if that confirmation is 3/3 once s21 has finished too.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 107 (16:57–17:05): checks 1988558 (grid no-reg `LN+LR+GL`, s0/s1) and 1988559 (AS `+EP_confirm`, s21); one spurious check cancelled

- **Wake-up.** The training wait fired. The job that ended belonged to noreg_fail (1987352). The bonus job **1987486** (AS `+NET_confirm`) had ended at 16:50 (4:30:08, COMPLETED). Its check **1988395** was still PENDING, so when it starts it will see all three seeds finished. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `B1_P1eq1_LN+LR+GL` (wave 2): s0 and s1 finished at 1536; s2 at 1248.
  - AS `B1_P1eq1_LN+RS+EP_confirm`: s21 finished at 12,288; s20 at 12,264, s22 at 12,192.

  `... br_missing submit` → **1988558** (grid `+GL`), **1988559** (AS `+EP_confirm`). The submit also listed Tomato `B1_base_LN+N4` → **1988560**.
- **1988560 cancelled (`scancel 1988560`; my own job).**
  - **Cause.** Its extension 1988345 had started a minute earlier. `config.json` already said 3072 episodes, but the seeds' `metrics.json` had not yet been renamed to `metrics_ep1536.json`. So `step4_br.py --missing` took a finished seed with no check at "3072".
  - **Why cancelling loses nothing.** With `metrics.json` gone, `--finished-only` skips every seed. The 1536 checks exist, and the script never overwrites a check. The job would have done nothing.
  - **Status.** Not a bug in any result; it is the known resume race (summary of the earlier session). Not flagged.
- **Still queued.** Checks 1988395 (AS `+NET_confirm`) and 1988396 (Tomato swap confirmation) are PENDING. Cells DONE: 4 of 12.

## 2026-11-15, iteration 108 (17:03–17:15): AS no-reg `+EP_confirm` 1/3 at 12,288 → extend to the cap 24,576 (); `+NET_confirm` 1/3 at 6144 → extend 12,288 (); grid `+GL` partial; stale NFS cache noted

- **Wake-up.** The training wait fired. **1987446** (AS `+EP_confirm`, extension to 12,288) COMPLETED 17:02 (5:05:21). **1987904** (grid `B1_P1eq1_LN+LR+RS`) COMPLETED 17:02 (1:48:51). The check waits brought **1988395** (AS `+NET_confirm`), **1988558** (grid `+GL`) and **1988559** (AS `+EP_confirm`), all COMPLETED. 1988559 started at 17:02:39, after 1987446 ended, so it covers all three seeds. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Verdicts** (`.venv/bin/python experiments/step4_convergence.py <run>`; BR gap history from `step4_br/`):

  | Run | Seed | BR gap (earlier) | BR gap now (s.e.) | Verdict |
  |---|---|---|---|---|
  | AS `B1_P1eq1_LN+RS+EP_confirm` (6144 → 12,288) | s20 | 0.032 | **0.059** (0.028) | IMPROVING |
  | | s21 | 0.000 | **0.013** (0.033) | CONVERGED |
  | | s22 | 0.057 | **0.060** (0.042) | IMPROVING |
  | AS `B1_P1eq1_LN+RS+NET_confirm` (3072 → 6144) | s20 | 0.062 | **0.046** (0.026) | IMPROVING |
  | | s21 | 0.031 | **0.000** | CONVERGED |
  | | s22 | 0.066 | **0.031** (0.040) | IMPROVING |
  | grid `B1_P1eq1_LN+LR+GL` (1536, wave 2) | s0 | — | **0.043** (0.004) | not converged |
  | | s1 | — | **0.014** (0.001) | CONVERGED |

  - Every AS policy is corrected once, then honest (true about 449). The best responses take 2–3 corrections.
  - The grid `+GL` policies are corrected once, then honest (true 22). So is their best response; s0's gap is the value cost of a small residual. s2 is still training (1248/1536 at 16:57).
- **Rule 4 (confirmations, seeds IMPROVING, below the AS cap): extend 2×.**
  - `+EP_confirm`, to the cap: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor B1_P1eq1_LN+RS+EP_confirm 24576` (dry-run: `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+EP_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --resume --extend-to 24576`) → `... submit` → ****.
  - `+NET_confirm`: `... extend absent_supervisor B1_P1eq1_LN+RS+NET_confirm 12288` (dry-run: `... --run-id B1_P1eq1_LN+RS+NET_confirm ... --resume --extend-to 12288`) → `... submit` → ****.
- **Stale NFS directory cache on the login node.**
  - **What I saw.** After an extension starts, the job on its compute node renames each seed's `metrics.json` to `metrics_ep<N>.json`. On the login node, `stat` / `open` of `seed<s>/metrics.json` kept succeeding for at least 8 minutes, although `ls` no longer lists it. This was Tomato `B1_base_LN+N4`, extension 1988345, and is consistent with a cached NFS dentry.
  - **Effect on checks.** `step4_br.py --missing` (via `br_missing`) then lists the run as finished without a check at the new length. That is why 1988560 was submitted (iteration 107). `br_missing` still lists it now; I have not resubmitted.
  - **Effect on commits.** `step4_commit.sh` uses the same `-f metrics.json` test, so commit ad2de674 `git add`ed those seeds' directories. Only small files had changed: `config.json` and the new `metrics_ep1536.json`. The checkpoint files were still the finished 1536 state, already committed. No mid-run checkpoint was committed.
  - **Handling.** Before submitting a listed check, or after committing, I now check `ls` for `metrics.json` on resumed runs. I am not changing `step4_commit.sh` or `step4_br.py`: their test is correct where the cache is fresh, as on the compute nodes.
- Queue: 28 jobs in this campaign (limit 60), 35 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 109 (17:15–17:45): fixed the stale-NFS "finished" test in four places (one commit of running checkpoints); checks 1988591–1988594

- **The problem.** Commit 1a9758ce (iteration 108) contained Tomato `B1_base_LN+N4`'s mid-run checkpoint: seeds 0–2 at episode 1560 of 3072, with `logs.npz`, `model.zip`, the round CSVs and `progress.json`.
  - **Cause.** The login node's stale NFS dentry for `seed<s>/metrics.json`, which was renamed to `metrics_ep1536.json` when extension 1988345 started. 17 minutes later, `[ -f metrics.json ]` was still true while `ls` showed no such file.
  - **Why it mattered.** `step4_commit.sh` stages a seed's whole directory if `[[ -f metrics.json ]]`. It would have re-added the run's checkpoints, about 45 MB, on every commit until the cache cleared.
  - **Earlier commits.** A scan of every commit since 2026-11-14 11:00 (each `logs.npz` against that commit's `progress.json`) finds no other case.
- **The fix.** This is clearly a bug under rule 5, so I fixed it with a test.
  - **What changed.** "Finished" now means `metrics.json` is in the seed's directory listing, which was current throughout. Changed:
    - `scripts/farmshare/step4_commit.sh`: a pure-bash `finished()` whose glob reads the listing, with no pipeline under `pipefail`;
    - `scripts/farmshare/step4_optimal.sh`: the same function in the `resume` test. A stale positive there would have skipped resuming a timed-out extension;
    - `experiments/step4_br.py`: `finished()` in `missing()`, `--finished-only` and the `finished` field;
    - `experiments/step4_convergence.py`: the RUNNING label.
  - **The test.** New `test_finished_seed_is_read_from_the_directory_listing` in `tests/test_step4.py`. It simulates the stale dentry with an `os.path.exists` that always finds `metrics.json`, and runs both scripts' `finished()` on real directories. `.venv/bin/python tests/test_step4.py`: 21 tests, 0 failed.
  - **Live check.** With `stat` still stale on Tomato `B1_base_LN+N4`, `step4_br.py --missing` and `br_missing` no longer list it.
  - **Left as is.** The checkpoint files already in 1a9758ce stay in history (no history rewrite). The run's final files will be committed over them when it finishes.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed grid `B1_P1eq1_LN+LR+AN`, `+GL` and `+RS` (wave 2; every seed finished at 1536, checked with `ls`). `... br_missing submit` → **1988591** (`+AN`), **1988592** (`+GL`, s2 now finished too), **1988593** (`+RS`), and **1988594** (AS `+LR_confirm`, whose seed finished between the two commands).
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 110 (17:45–17:55): grid no-reg wave 2 `+AN`, `+GL`, `+RS` at 1536 → extend 3072 (1988599–1988601); AS `+LR_confirm` s20 0.058

- Woken by the check wait. **1988591**–**1988594** COMPLETED. `.venv/bin/python experiments/step4_convergence.py <run>`:

  | Run (episodes) | s0 | s1 | s2 |
  |---|---|---|---|
  | grid `B1_P1eq1_LN+LR+AN` (1536) | **0.002** CONVERGED | **0.027** CONVERGED | **0.052** IMPROVING |
  | grid `B1_P1eq1_LN+LR+GL` (1536) | **0.043** IMPROVING | **0.014** CONVERGED | **0.080** IMPROVING |
  | grid `B1_P1eq1_LN+LR+RS` (1536) | **0.044** IMPROVING | **0.047** PLATEAU | **0.065** PLATEAU |

  - Every best response is corrected once, then honest (true 20–22); `+RS` s2's takes 2 corrections.
  - The unconverged policies are corrected once and then fall short of honest in some rounds:
    - `+AN` s2 never reaches the goal (true −100).
    - `+GL` s2 is at true about −2.
    - `+RS` s0 reaches the goal only in round 1.
    - `+RS` s1 and s2 are at true −100.
  - AS `B1_P1eq1_LN+RS+LR_confirm` (12,288): s20 **0.058** (s.e. 0.021), PLATEAU; it is corrected once, and its best response takes 2 corrections. s21 (12,000) and s22 (7392) are still training. Rule 4 waits.
- **Rule 4 (wave-2 runs, a seed IMPROVING, 1536 < grid cap 12,288): extend 2× to 3072.**
  - Dry-run for each: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+<tag> 3072`, which printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+<tag> --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 3072`.
  - `... submit` → **1988599** (`+AN`), **1988600** (`+GL`), **1988601** (`+RS`).
  - `+NET` and `+EP` (wave 2) and the four exploration runs are still training.
- Queue: 29 jobs in this campaign (limit 60), 36 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 111 (17:18–17:22): Tomato swap confirmation and grid `+AN`/`+GL` training ended; grid `+LR+ENT3` s1 at 1536 → check 1988605

- **Finished training jobs** (all exit 0):
  - **1987223**, Tomato `B1_P2swap_LN+ES10+N4_confirm`, COMPLETED 17:09 (10:37:55).
  - **1987906**, grid `+AN`, COMPLETED 17:05.
  - **1987902**, grid `+GL`, COMPLETED 17:10.

  Their extensions (iteration 110) are queued.
- **Tomato swap confirmation.** Check 1988396 started at about 16:50, before s21 finished, so it covers s20 and s22. s21 gets its own check once 1988396 ends (`br_missing` skips a run while its check is queued).
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run): grid `B1_P1eq1_LN+LR+ENT3`, s1 finished at 1536 (checked with `ls`). `... br_missing submit` → **1988605**.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 112 (17:23–17:25): grid `+LR+ES10` finished at 1536 → check 1988611 

- Woken by the training wait: **1987908** (grid `B1_P1eq1_LN+LR+ES10`, rule 6b stage 1) COMPLETED 17:22 (1:59:37, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `+LR+ES10`) → `... br_missing submit` → **1988611 **. Cells DONE: 4 of 12.

## 2026-11-15, iteration 113 (17:27–17:30): grid `+LR+ENT3` finished; AS `+LR_confirm` s21 at 12,288 → check 1988614 

- **Training wait.** **1987907** (grid `B1_P1eq1_LN+LR+ENT3`, rule 6b stage 1) COMPLETED 17:26 (2:06:55, exit 0). Its check 1988605 started 17:26:38, after the job ended, so it covers all three seeds. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** The dry-run of `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed AS `B1_P1eq1_LN+RS+LR_confirm` (s21 finished at 12,288; s20 was checked in iteration 110; s22 is still training). `... br_missing submit` → **1988614 **.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 114 (17:37–17:45): grid no-reg `+LR+ES10` 3/3 CONVERGED at 1536 → `confirm` (1988633); `+LR+ENT3` 2/3 → extend 3072 (1988634); checks 1988636 1988637

- **Wake-up.** Scheduled wakeup. **1988605**, **1988611** and **1988614** COMPLETED. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Check results** (`.venv/bin/python experiments/step4_convergence.py <run>`):
  - **grid `B1_P1eq1_LN+LR+ES10`** (rule 6b stage 1, 1536): all three CONVERGED.
    - s0 **0.002** (s.e. 0.000), s1 **0.002** (s.e. 0.002), s2 **0.016** (s.e. 0.035).
    - Every seed is corrected once, then honest (true 22 ×4).
    - The best responses of s0 and s1 are the same. s2's takes 2 corrections (true −100, −100, 22 ×3).
    - In s2, the seed where `LN+LR` failed (0.067 at the cap, never reaching the goal), PPO now reaches the goal after its correction.
  - **grid `B1_P1eq1_LN+LR+ENT3`** (1536):
    - s0 **0.003** and s1 **0.006**, both CONVERGED.
    - s2 **0.032** (s.e. 0.033), IMPROVING. Its best response takes 2 corrections.
  - **AS `B1_P1eq1_LN+RS+LR_confirm`** (12,288):
    - s21 **0.000**, CONVERGED.
    - s20 **0.058**, PLATEAU (iteration 110).
    - s22 still training (7824/12,288).
- **Rule 4: grid `+LR+ES10` is all CONVERGED, so `confirm`.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid B1_P1eq1_LN+LR+ES10` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+ES10_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --set g.use_regularization=False anneal.last=0.25 anneal.floor=0.1 anneal.ent_start=10 anneal.ent_episodes=768 n_envs=64 ppo.batch_size=1600 ppo.learning_rate=0.0001 protocol.update_bonus=1.0 episodes=1536`. That matches `run_sets.py` on the run.
  - Submitted: `... submit` → **1988633**.
  - The grid no-reg cell is DONE when this confirmation is 3/3.
- **Rule 6b extension rule: grid `+LR+ENT3` (exploration run, s2 unconverged) is extended 2×, to 3072.**
  - Dry-run: `... extend grid B1_P1eq1_LN+LR+ENT3 3072` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+ENT3 --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 3072`.
  - Submitted: `... submit` → **1988634**.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `B1_P1eq1_LN+LR+EP` (wave 2): s0 and s2 finished at 1536; s1 at 1464.
  - Tomato `B1_base_LN+ES10+N4` (rule 6b): s1 finished at 1536; s0 at 936 and s2 at 264.
  - Finished state was confirmed with `ls`. Submitted: `... br_missing submit` → **1988636** (grid `+EP`) and **1988637** (Tomato base `LN+ES10+N4`).
- Queue: 31 jobs in this campaign (limit 60), 38 in all. Cells DONE: 4 of 12.

## 2026-11-15, iteration 115 (17:42–17:47): grid `+EP` s0/s2 CONVERGED, s1 finished → check 1988646 ; partial results for Tomato swap confirmation and Tomato base `LN+ES10+N4`

- **Training wait.** **1987905** (grid `B1_P1eq1_LN+LR+EP`, wave 2) COMPLETED 17:42 (2:28:38, exit 0). Its check **1988636** (s0, s2) had COMPLETED at 17:40.
- **Results so far** (`.venv/bin/python experiments/step4_convergence.py <run>`):
  - **grid `B1_P1eq1_LN+LR+EP`** (1536):
    - s0 **0.001** (s.e. 0.001) and s2 **0.002** (s.e. 0.001), both CONVERGED. Both are corrected once, then honest (true about 22).
    - s1 has finished but is not yet checked. Its training curve shows true −100 in every round after its correction, so it never reaches the goal.
  - **Tomato `B1_P2swap_LN+ES10+N4_confirm`** (1536): s20 **0.002** and s21 **0.001**, both CONVERGED.
    - Both are corrected once, then honest (true about 420), like their best responses.
    - The check job 1988396 (started 16:50) is still running on s22. It picked up s21 because that seed had finished by the time the job reached it.
    - **The Tomato swap cell is DONE if s22 converges.**
  - **Tomato `B1_base_LN+ES10+N4`** (rule 6b stage 1):
    - s1 has finished at 1536. Its check 1988637 is running.
    - **The training curves of s1 and s0 (960/1536) match the target exactly: they hide.** That is true 59.8 ×4, then 46.0, with every target gap 0.000.
    - This is the first Tomato base run in which PPO does not settle into the reactive policy (corrected once, then honest). s2 (264/1536) is still reactive.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `+EP`, s1) → `... br_missing submit` → **1988646 **.
- Cells DONE: 4 of 12.

## 2026-11-15, iteration 116 (17:47–17:52): **Tomato swap DONE** (`B1_P2swap_LN+ES10+N4_confirm` 3/3 at 1536)

- **Check result.** Woken by the check wait: **1988396** (`br_tomato_B1_P2swap_LN+ES10+N4_confirm`) COMPLETED. It ran from 16:50 and checked the seeds in turn: s20, then s21 (finished 17:09), then s22. `.venv/bin/python experiments/step4_convergence.py results/step4/tomato/bonus/B1_P2swap_LN+ES10+N4_confirm`:

  | Seed | Gap (s.e.) | Verdict | PPO true | Best response true | Target true |
  |---|---|---|---|---|---|
  | s20 | **0.0015** (0.0002) | CONVERGED | 46, then about 421 | 46, then 421.0 ×4 | 46, then 416.5 ×4 |
  | s21 | **0.0015** (0.0003) | CONVERGED | 46, then about 421 | 46, then 420.9 ×4 | 46, then 424.7 ×4 |
  | s22 | **0.0015** (0.0004) | CONVERGED | 46, then about 420 | 46, then 421.4 ×4 | 46, then 420.4 ×4 |

  PPO, its best response and the target are all corrected in round 0, then honest.
- **Rule 4: the confirmation is 3/3, so the Tomato swap cell is DONE.**
  - Config: `B1_P2swap_LN+ES10+N4`, i.e. `ppo.ent_coef=0.03`, 64 envs, batch 1600, entropy 10× falling to 1× by episode 768, the swap, the bonus, at 1536 episodes.
  - Tuning seeds 0–2: 0.002 / 0.001 / 0.002. Confirmation seeds 20–22: 0.002 / 0.001 / 0.002. Neither run was extended.
  - Without the bonus, the same config also passed (optimal campaign). The bonus changed neither the target (+1.0 in V0) nor PPO's end state.
- **Rule 6b: nothing new for Tomato swap.** It has no other runs queued or running.
- **Status updated at the top. Cells DONE: 5 of 12.**
  - DONE: grid swap, AS swap, Tomato swap, grid base, AS base.
  - Open:
    - grid no-reg: `+LR+ES10_confirm` running (1988633);
    - AS no-reg: several confirmations extending;
    - Tomato no-reg: `LN_confirm` running (1988344);
    - Tomato base: stage 1 exploration; `LN+ES10+N4` hides in s0 and s1;
    - tomato_large: all three cells in wave 1.

## 2026-11-15, iteration 117 (17:52–17:55): grid no-reg `+EP` 2/3 at 1536 → extend 3072 (1988664 )

- Check **1988646** (grid `B1_P1eq1_LN+LR+EP`, s1) COMPLETED. Verdicts at 1536:

  | Seed | BR gap | Verdict | Behaviour |
  |---|---|---|---|
  | s0 | **0.001** | CONVERGED | corrected once, then honest |
  | s1 | **0.044** (s.e. 0.008) | IMPROVING | corrected once, then never reaches the goal (true −100); its best response is corrected once, then honest |
  | s2 | **0.002** | CONVERGED | corrected once, then honest |

- **Rule 4 (wave-2 run, s1 IMPROVING, below the cap): extend 2×.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+EP 3072` (dry-run: `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+EP --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 3072`) → `... submit` → **1988664 **.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 118 (17:53–17:56): Tomato base `LN+ES10+N4` s1 **0.000 CONVERGED: hides**, the first Tomato base seed to reach its optimum

- **Check.** **1988637** (`br_tomato_B1_base_LN+ES10+N4`, s1 at 1536) COMPLETED 17:53 (14:13).
  - Gap **0.0000** (s.e. 0.0000), CONVERGED.
  - **Policy: hides**, true 59.8 ×4, then 46.0. The best response does exactly the same, and so does the target.
- **What changed.** Every earlier Tomato base seed was reactive: corrected once, then honest, with gap 0.16. That covers `L`, `LE` and `LN` at up to 3072, and the stage-1 runs `LN+ENT3` and `LN+N4`. The difference here is the exploration schedule ES10 combined with N4: entropy 10× falling to 1× by episode 768, and 256 envs.
- **The other seeds.** s0 (1032/1536) also hides on its training curve, with every target gap below 0.001. s2 (288/1536) is still reactive.
- **Rule 4** waits for s0 and s2. Cells DONE: 5 of 12.

## 2026-11-15, iteration 119 (18:26–18:38): quiet at 18:26; grid `+LR+NET` finished at 1536 → check 1988827 

- **18:26 (scheduled wakeup):** no job had ended since 17:45, and `br_missing` / `resume` (dry-run) showed nothing in either campaign.
- **18:35 (training wait):** **1987903** (grid `B1_P1eq1_LN+LR+NET`, wave 2) COMPLETED 18:33 (3:20:29, exit 0).
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `+NET`) → `... br_missing submit` → **1988827 **. Cells DONE: 5 of 12.

## 2026-11-15, iteration 120 (18:40–18:42): grid no-reg `+NET` 2/3 at 1536, s2 PLATEAU → finished

- **Check 1988827** (`br_grid_B1_P1eq1_LN+LR+NET`) COMPLETED. Verdicts:
  - s0 **0.019** and s1 **0.018** are CONVERGED. Both are corrected once, then honest (true about 22).
  - s2 **0.066** (s.e. 0.038) is PLATEAU. It is corrected once, then never reaches the goal (true −100). Its best response takes 2 corrections, then is honest.
- **Rule 4: the only unconverged seed is PLATEAU, so the config is finished and not extended.**
- **Grid no-reg status:**

  | Run | Status |
  |---|---|
  | `LN+LR` | finished, 2/3 at the cap |
  | `+NET` | finished, 2/3 |
  | `+GL`, `+RS`, `+AN`, `+EP` | extending to 3072 |
  | `+LR+ES10` | 3/3; confirmation `+LR+ES10_confirm` running (1988633) |
  | `+LR+ENT3` | extending to 3072 |
  | `+LR+N4`, `+LR+ES10+N4` | training |

- Cells DONE: 5 of 12.

## 2026-11-15, iteration 121 (19:13–19:16): Tomato base `LN+ES10+N4` s0 finished at 1536 → check 1988849

- **Wake-up.** Scheduled wakeup. `git pull --no-rebase --no-edit --ff`: already up to date. No job of this campaign has ended since 18:33. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed Tomato `B1_base_LN+ES10+N4`.
  - s0 has finished at 1536. Its training curve hid in iteration 115.
  - s1 was already checked: 0.000, hides.
  - s2 is at 552 of 1536.
  - The finished state was confirmed with `ls`.

  `... br_missing submit` → **1988849**.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 122 (19:30–19:33): Tomato base `LN+ES10+N4` s0 **0.000 CONVERGED (hides)**; 2/3 seeds now at the optimum

- **Check result.** **1988849** (`br_tomato_B1_base_LN+ES10+N4`, s0 at 1536) COMPLETED 19:30 (8:41).
  - Gap **0.0000** (s.e. 0.0000), CONVERGED.
  - The policy hides: true 59.8 ×4, then 46.0. Its best response and the target do the same.
- **Run status.** s0 and s1 are both at the exact optimum. s2 is still training and reactive.
- **Rule 4** waits for s2. If s2 converges, the run is confirmed (seeds 20–22). If not, the rule 6b extension rule applies.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 123 (19:34–19:38): AS `+GL` at the 24,576 cap, grid `+RS` at 3072; checks 1988867–1988871

- **Woken by the training wait.** Two jobs COMPLETED, both exit 0: **1987396** (AS `B1_P1eq1_LN+RS+GL`, extension to the cap 24,576) at 19:32 (8:11:52), and **1988601** (grid `+RS`, extension to 3072) at 19:34. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** I dry-ran `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing`; finished seeds per run (now read from the listing):

  | Run | Finished seeds | Still training |
  |---|---|---|
  | grid `B1_P1eq1_LN+LR+N4` | s0, s1 at 1536 | s2 at 1464 |
  | grid `+RS` | s0–s2 at 3072 | — |
  | AS `+GL` | s0–s2 at 24,576 | — |
  | Tomato `B1_base_LN+ENT3` | s0 at 3072 | s1, s2 at about 2900 |

  Submitted with `... br_missing submit` → **1988867** (grid `+N4`), **1988868** (grid `+RS`), **1988870** (AS `+GL`), **1988871** (Tomato base `LN+ENT3`).
- **What the cap means.** AS `+GL` is at the cap, so it is finished whatever the verdict.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 124 (19:38–19:50): **AS no-reg `+GL` 3/3 CONVERGED at the 24,576 cap → `confirm` (1988882)**; grid `+RS` 1/3 → extend 6144 (1988883); grid `+N4` partial

- **What woke me.** The training wait fired for **1988600** (grid `+GL`, extension to 3072), COMPLETED 19:38 (2:20:24). Three checks also COMPLETED: **1988867** (grid `+N4`), **1988868** (grid `+RS`) and **1988870** (AS `+GL`). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Verdicts.** From `.venv/bin/python experiments/step4_convergence.py <run>`, with BR gap histories from `step4_br/`:
  - **AS `B1_P1eq1_LN+RS+GL`** (wave 2, `ppo.gae_lambda=1.0`), BR gap at 3072 / 6144 / 12,288 / 24,576:

    | Seed | 3072 | 6144 | 12,288 | 24,576 | Verdict |
    |---|---|---|---|---|---|
    | s0 | 0.000 | 0.000 | 0.000 | **0.000** | CONVERGED |
    | s1 | 0.002 | 0.000 | 0.000 | **0.018** (s.e. 0.029) | CONVERGED |
    | s2 | 0.038 | 0.038 | 0.085 | **0.000** | CONVERGED |

    - All three policies are corrected once, then nearly honest (true 445–448).
    - The best responses of s0 and s2 are the same as their policies. s1's best response takes 2 corrections.
    - s2 escaped only in the last doubling, from 0.085 to 0.000. This matches the rule 6b note that seeds escape after long flat stretches.
  - **grid `B1_P1eq1_LN+LR+RS`**, BR gap at 1536 / 3072:

    | Seed | 1536 | 3072 | Verdict |
    |---|---|---|---|
    | s0 | 0.044 | **0.000** | CONVERGED |
    | s1 | 0.047 | **0.044** | IMPROVING |
    | s2 | 0.065 | **0.068** | IMPROVING |

    s1 never reaches the goal after its correction. s2 does not either, and its best response takes 2 corrections.
  - **grid `B1_P1eq1_LN+LR+N4`** (rule 6b, 1536): s0 **0.109** and s1 **0.046**, both IMPROVING. Both are corrected once, then never reach the goal (true −100). s2 is still training (1488) and its curve is honest (true about 22). The extension rule waits for s2.
- **Rule 4: AS `+GL` is all CONVERGED, so it goes to `confirm`.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor B1_P1eq1_LN+RS+GL` printed `submit.sh 48 --env absent_supervisor --run-id B1_P1eq1_LN+RS+GL_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/bonus --set ppo.ent_coef=0.1 ppo.batch_size=1600 ppo.gae_lambda=1.0 g.use_regularization=False g.epochs=1000 protocol.update_bonus=1.0 episodes=24576 anneal.last=0.25 anneal.floor=0.1 n_envs=64 reward_scale=0.01625`. That is the run's overrides at its final length, the same as `run_sets.py`.
  - Submitted: `... submit` → **1988882**.
  - Time: the tuning run took about 15 h in total across its extensions, within the 48 h limit.
  - **The AS no-reg cell is DONE when this confirmation is 3/3** (or when any of the other running AS no-reg confirmations is).
- **Rule 4: grid `+RS` (wave 2) has seeds IMPROVING, so extend 2×.**
  - Dry-run: `... extend grid B1_P1eq1_LN+LR+RS 6144` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+RS --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1988883**.
- **Rule 3.** `br_missing` (dry-run: grid `+GL` at 3072) → `... br_missing submit` → **1988884**. Tomato base `LN+ENT3` (1988871) is still pending.
- Queue: 28 jobs in this campaign (limit 60), 35 in all. Cells DONE: 5 of 12.

## 2026-11-15, iteration 125 (19:44–19:46): grid `+LR+N4` finished at 1536 → check 1988901  (s2)

- **Training wait.** **1987909** (grid `B1_P1eq1_LN+LR+N4`, rule 6b stage 1) COMPLETED 19:43 (4:18:17, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `+LR+N4`, s2) → `... br_missing submit` → **1988901 **.
- **Next.** When this check returns, the rule 6b extension rule applies to the run: s0 and s1 are unconverged (iteration 124).
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 126 (19:48–19:52): grid no-reg `+GL` 0/3 at 3072 → extend 6144 (1988904)

- **The check.** **1988884** (`br_grid_B1_P1eq1_LN+LR+GL`, 3072) COMPLETED 19:47 (3:54). BR gap at 1536 → 3072:

  | Seed | 1536 | 3072 | s.e. | Verdict |
  |---|---|---|---|---|
  | s0 | 0.043 | **0.053** | 0.007 | IMPROVING |
  | s1 | 0.014 | **0.052** | 0.001 | IMPROVING |
  | s2 | 0.080 | **0.049** | 0.004 | IMPROVING |

  - **What PPO does.** Every policy is corrected once, then honest (true 21.8–22.0).
  - **Where the gap comes from.** The best responses are also corrected once, but s1 and s2 then take a route with true 20. The gap is in received reward under the refitted no-reg corrections, which raise some non-honest transitions. So the best response earns about 5% more on a slightly different route, while PPO keeps the honest one. s1 moved from 0.014 to 0.052 because the corrections refitted on its later play reward a different route.
- **Rule 4 (wave-2 run, seeds IMPROVING, below the cap): extend 2×.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+GL 6144` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+GL --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1988904**.
- **Status.** Cells DONE: 5 of 12.

## 2026-11-15, iteration 127 (19:51–19:54): grid no-reg `+LR+N4` 0/3 at 1536 → extend 3072 (1988924 )

- **Check result.** **1988901** (`br_grid_B1_P1eq1_LN+LR+N4`, s2) COMPLETED 19:50.

  | Seed | Gap | s.e. | Verdict | Behaviour after the correction |
  |---|---|---|---|---|
  | s0 | 0.109 | 0.012 | IMPROVING | never reaches the goal (true −100) |
  | s1 | 0.046 | 0.006 | IMPROVING | never reaches the goal (true −100) |
  | s2 | 0.034 | 0.003 | IMPROVING | partly honest |

  All three best responses are corrected once, then honest.
- **Rule 6b extension rule.** This is an exploration run with seeds unconverged, so it is extended 2× (to 3072).
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+N4 3072` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+N4 --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 3072`.
  - Submitted with `... submit` → **1988924 **.
- **Tomato base `LN+ENT3`.** Check 1988871 (s0 at 3072) is running. s0's training curve is still reactive (true 46, then about 429).
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 128 (20:06–20:09): Tomato base `LN+ENT3` finished at 3072; s0 and s2 still reactive (0.161); s1 check 1989200 1989201 

- **What finished.** **1988871** (`br_tomato_B1_base_LN+ENT3`) COMPLETED 20:06; **1987845** (Tomato `B1_base_LN+ENT3`, extension to 3072) COMPLETED 20:06 (5:30:56, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date.
- **Gaps** (1536 → 3072):
  - s0: 0.163 → **0.161** (s.e. 0.000)
  - s2: 0.162 → **0.161** (s.e. 0.000)
  - Both are reactive (corrected once, then honest at true about 431). Both best responses hide.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: s1, which finished after the check had started) → `... br_missing submit` → **1989200 1989201 **.
- **Next.** The rule 6b extension applies once s1 is checked, because extending now would overwrite s1's 3072 model before it is checked.
- Cells DONE: 5 of 12.
- **Same submit:** **1989201** (tomato_large `B1_base_L`, s2). s2 finished its 1536 episodes in about 32 h; `ls` shows `metrics.json`. s0 is at 696 and s1 at 1320. This is the first tomato_large seed to reach a check. Its training curve is corrected once, then honest (window 0.25, 1 correction per episode); the tomato_large base target hides.

## 2026-11-15, iteration 130 (20:18–20:21): Tomato base `LN+ENT3` 0/3 at 3072 → extend 6144 (1989207 )

- **Check.** **1989200** (`br_tomato_B1_base_LN+ENT3`, s1) COMPLETED 20:18. s1 **0.161** (s.e. 0.000): reactive (true 46, then 431.6 ×4). Its best response hides.
- **Run status.** All three seeds sit at 0.161 at 3072, unchanged from 1536.
- **Rule 6b extension rule.** This is an exploration run with seeds unconverged, so it is extended 2× (to 6144), whatever the verdict.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+ENT3 6144` printed `submit.sh 48 --env tomato --run-id B1_base_LN+ENT3 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 6144`.
  - Submitted with `... submit` → **1989207 **.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 131 (20:20–20:24): grid `+LR+ENT3` at 3072, grid `+AN` s0/s2 at 3072 → checks 1989551 1989552

- **Training wait.** **1988634** (grid `B1_P1eq1_LN+LR+ENT3`, extension to 3072) COMPLETED 20:19 (2:41:08, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `+AN`: s0 and s2 finished at 3072, s1 at 3024.
  - grid `+LR+ENT3`: all three seeds finished at 3072.

  `... br_missing submit` → **1989551** (`+AN`), **1989552** (`+LR+ENT3`).
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 132 (20:25–20:29): grid `+AN` at 3072 (s0 0.000, s2 0.054); Tomato base `LE` s0 at 6144 → checks 1989562 1989563

- **Training finished.** **1988599** (grid `+AN`, extension to 3072) COMPLETED 20:23 (3:05:51, exit 0).
- **Grid `+AN` check.** **1989551** COMPLETED.
  - s0 **0.000**, CONVERGED (corrected once, then honest).
  - s2 **0.054** (s.e. 0.008), IMPROVING (0.052 at 1536). PPO is corrected once, then honest at true 22. Its best response takes a true-20 route that pays more under the refitted corrections, the same pattern as `+GL` (iteration 126).
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed grid `+AN` (s1) and Tomato `B1_base_LE` (s0 finished at 6144; s1 and s2 at 6000). `... br_missing submit` → **1989562** (`+AN` s1), **1989563** (Tomato base `LE` s0).
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 133 (20:29–20:33): grid no-reg `+LR+ENT3` 3/3 CONVERGED at 3072 → `confirm` (1989566 )

- **Check result.** **1989552** (`br_grid_B1_P1eq1_LN+LR+ENT3`, 3072) COMPLETED 20:27. BR gap at 1536 → 3072:

  | Seed | 1536 | 3072 | Verdict |
  |---|---|---|---|
  | s0 | 0.003 | **0.000** | CONVERGED |
  | s1 | 0.006 | **0.000** | CONVERGED |
  | s2 | 0.032 | **0.001** | CONVERGED |

  Every policy and best response is corrected once, then honest (true 22 ×4).
- **Rule 4 (rule 6b exploration run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid B1_P1eq1_LN+LR+ENT3` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --set g.use_regularization=False anneal.last=0.25 anneal.floor=0.1 n_envs=64 ppo.batch_size=1600 ppo.learning_rate=0.0001 ppo.ent_coef=0.03 protocol.update_bonus=1.0 episodes=3072`. This is the run's overrides at its final length, matching `run_sets.py`.
  - Submitted: `... submit` → **1989566 **.
- **Status.** It runs alongside `+LR+ES10_confirm` (1988633). The grid no-reg cell is DONE when either confirmation is 3/3. Cells DONE: 5 of 12.

## 2026-11-15, iteration 134 (20:33–20:35): grid no-reg `+AN` 2/3 at 3072 → extend 6144 (1989569 )

- **Check.** **1989562** (`br_grid_B1_P1eq1_LN+LR+AN`, s1) COMPLETED. s1: **0.003**, CONVERGED (it was 0.027 at 1536).
- **Run state at 3072.** s0 0.000 and s1 0.003 are CONVERGED. s2 is 0.054 and IMPROVING; it takes the honest route, while its best response takes a true-20 route (iteration 132).
- **Rule 4 (wave-2 run, s2 IMPROVING, below the cap): extend 2×.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+AN 6144` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+AN --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 6144`.
  - Submitted with `... submit` → **1989569 **.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 135 (20:42–20:46): grid no-reg `+LR+ES10_confirm` finished at 1536 → check 1989578; Tomato base `L` s0 at 6144 → check 1989579

- **Trigger.** The training wait reported **1988633** (grid `B1_P1eq1_LN+LR+ES10_confirm`, seeds 20–22, 1536) COMPLETED 20:41 (3:03:12, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `+LR+ES10_confirm`, all three seeds;
  - Tomato `B1_base_L`, s0 finished at 6144 (s1 is at 5856, s2 at 4944).

  `... br_missing submit` → **1989578** (grid confirmation) and **1989579** (Tomato base `L` s0).
- **What the grid check decides.** **The grid no-reg cell is DONE if 1989578 is 3/3.**
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 136 (20:46–20:50): grid no-reg `+LR+ES10_confirm` 1/3 at 1536 → extend 3072 (1989595 )

- **Check result.** **1989578** (`br_grid_B1_P1eq1_LN+LR+ES10_confirm`) COMPLETED 20:46 (2:34). Verdicts from `.venv/bin/python experiments/step4_convergence.py <run>`:

  | Seed | Gap (s.e.) | Verdict | Policy | Best response |
  |---|---|---|---|---|
  | s20 | **0.003** (0.003) | CONVERGED | corrected once, then honest | corrected once, then honest |
  | s21 | **0.129** (0.005) | IMPROVING | corrected once; round 1 is still at true −99, then honest | corrected once, then honest (true 22 from round 1) |
  | s22 | **0.034** (0.024) | IMPROVING | corrected once, then honest | takes 2 corrections |

- **Rule 4 (confirmation, seeds IMPROVING, 1536 < grid cap 12,288): extend 2×.** Confirmations count once extended.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+ES10_confirm 3072` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+ES10_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --resume --extend-to 3072`.
  - Submitted with `... submit` → **1989595 **.
- **Grid no-reg's other confirmation.** `+LR+ENT3_confirm` (1989566) is still running.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 137 (21:00–21:03): Tomato base `L` s0 0.160 and `LE` s0 0.162 at 6144 (still reactive; partial)

- **What came back.** **1989579** (`br_tomato_B1_base_L`, s0 at 6144) COMPLETED. **1989563** (`br_tomato_B1_base_LE`) has checked s0 at 6144 and is now on its next seed.
- **Verdicts.**
  - `B1_base_L` s0: **0.160** (s.e. 0.000).
  - `B1_base_LE` s0: **0.162** (s.e. 0.000).
  - Both are reactive: corrected once, then honest, true about 431. Both best responses hide.
  - The gaps have not moved since 1536 (0.161 / 0.165 then).
- **Remaining seeds.** `L` s1 and s2 are still training. `LE` s1 and s2 finished at 20:44; 1989563 is checking them now, or a follow-up check will.
- **Rule 4** waits for the remaining seeds. Cells DONE: 5 of 12.

## 2026-11-15, iteration 138 (21:03–21:06): AS no-reg `+ES10` reached the 24,576 cap → check 1989610

- **Training finished.** **1987630** (AS `B1_P1eq1_LN+RS+ES10`, extended to the cap of 24,576) COMPLETED 21:02 (7:58:43, exit 0).
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: AS `+ES10`; s0 and s1 finished, s2 just finishing) → `... br_missing submit` → **1989610**. It covers all three seeds when it starts.
- **At the cap** the run is finished, whatever the verdict. s2 was 0.075 at 12,288; s0 and s1 were 0.000.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 139 (21:05–21:08): AS no-reg `+ES10` 2/3 at the 24,576 cap → finished

- **The check.** **1989610** (`br_absent_supervisor_B1_P1eq1_LN+RS+ES10`, 24,576) COMPLETED 21:05.

  | Seed | BR gap (s.e.) | Verdict | Behaviour |
  |---|---|---|---|
  | s0 | **0.000** | CONVERGED | corrected once, then honest |
  | s1 | **0.000** | CONVERGED | corrected once, then honest |
  | s2 | **0.047** (0.029) | not converged | corrected once, then honest (true 449.9); its best response takes 2 corrections |

  s2's BR gap over the run: 0.061 / 0.074 / 0.075 / 0.047 at 3072 / 6144 / 12,288 / 24,576.
- **Decision.** Rule 4 and the 6b extension rule both stop at the cap, so the run is finished at 2/3.
- **AS no-reg rule 6b stage 1:**
  - `+ENT3`: 3/3; its confirmation is extending to 24,576 (1987629).
  - `+N4`: 3/3; its confirmation failed (iteration 96).
  - `+ES10+N4`: 3/3; its confirmation is extending to 12,288 (1987881).
  - `+ES10`: finished at the cap, 2/3.

  Stage 2 starts only once every stage-1 run is finished without the cell being DONE; not yet.
- **Other AS no-reg runs still able to make the cell DONE:**
  - `+GL_confirm` (1988882), from `+GL`, which was 3/3 at the cap;
  - `+EP_confirm` → 24,576 (1988581);
  - `+NET_confirm` → 12,288 (1988582);
  - `+LR_confirm` (s22 still training).
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 140 (21:09–21:11): AS no-reg `+LR_confirm` finished at 12,288 → check 1989621 (s22)

- **1987290** (AS `B1_P1eq1_LN+RS+LR_confirm`, 12,288) COMPLETED 21:03 (11:41:47, exit 0). s20 (0.058, PLATEAU) and s21 (0.000) are already checked. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: AS `+LR_confirm`, s22) → `... br_missing submit` → **1989621 **.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 141 (21:22–21:28): AS `+LR_confirm` 2/3 at 12,288, s20 PLATEAU → failed; Tomato base `LE` 0/3 at 6144 → extend to the cap 12,288 (1989626); checks 1989628 1989629

- **Checks back.** **1989621** (AS `+LR_confirm`, s22) and **1989563** (Tomato `B1_base_LE`, s1 and s2) COMPLETED. Verdicts from `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **AS `B1_P1eq1_LN+RS+LR_confirm`** (12,288):
    - s20 **0.058**, PLATEAU.
    - s21 **0.000**, CONVERGED.
    - s22 **0.001**, CONVERGED. It is corrected once, then honest; its best response takes 2 corrections, at a negligible value difference.
  - **Tomato `B1_base_LE`** (6144), BR gaps flat since 1536 (0.167):
    - s0 **0.162**, s1 **0.163**, s2 **0.163**, all labelled IMPROVING by the training curve.
    - All three are reactive: corrected once, then honest, true about 430. Their best responses hide.
- **Rule 4, AS `+LR_confirm`.** The only unconverged seed is PLATEAU, so the run is finished and this confirmation failed (2/3, s20 at 0.058).
  - AS no-reg confirmations failed so far: `+AN`, `+N4`, `+LR`.
  - Still running: `+GL_confirm`, `+ENT3_confirm`, `+EP_confirm`, `+NET_confirm`, `+ES10+N4_confirm`.
- **Rule 4, Tomato `B1_base_LE`.** Seeds are labelled IMPROVING and the run is below the cap, so extend 2× to the cap.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LE 12288` printed `submit.sh 48 --env tomato --run-id B1_base_LE --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 12288`.
  - Submitted: `... submit` → **1989626**.
  - At the cap the run is finished whatever the verdict.
- **Rule 3.** The `br_missing` dry-run listed two runs:
  - Tomato `B1_base_L`: s1 finished at 6144; s2 at 5232.
  - Tomato `B1_base_LN+ES10`: s0 finished at 1536; s1 at 504, s2 at 1296.

  Submitted: `... br_missing submit` → **1989628** (`base_L`) and **1989629** (`base_LN+ES10`).
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 142 (21:58–22:15): the third campaign (comp) started; grid `+LR+ES10+N4` finished → check 1989701; Tomato base `L` s1 0.160 PLATEAU

- **Repo and prompt changes.**
  - The user's commit b145f873e (pulled 21:57) added the compensated-correction campaign. The user then sent the three-campaign loop prompt. Comp's iteration 0 (28 jobs) is in `docs/step4_comp_log.md`.
  - Nothing in this campaign changes. The new code paths are off by default, and `tests/test_step4.py` passes 28/28 on the merged code.
  - Budgets: bonus ≤ 60, noreg_fail ≤ 20, comp ≤ 30, all ≤ 110. With comp, all my jobs come to about 61.
- **Finished runs.** **1987910** (grid `B1_P1eq1_LN+LR+ES10+N4`, rule 6b stage 1) COMPLETED 21:57 (6:27:38, exit 0).
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `+LR+ES10+N4`) → `... br_missing submit` → **1989701**.
- **Check result.** **1989628** (Tomato `B1_base_L`, s1 at 6144): **0.160**, PLATEAU, reactive. The best response hides. s0 is at 0.160 PLATEAU; s2 is at 5760/6144, so Rule 4 waits for s2.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 143 (22:13–22:16): AS `+ES10+N4_confirm` finished at 12,288; checks 1989710–1989712

- **Trigger.** The training wait reported **1987881** (AS `B1_P1eq1_LN+RS+ES10+N4_confirm`, extended to 12,288) COMPLETED 22:13 (7:11:38, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing, in all three campaigns.
- **Rule 3.** The dry-run of `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed:
  - grid `+EP`: s2 finished at 3072; s0 and s1 are at 3048.
  - AS `+ES10+N4_confirm`: all three seeds finished at 12,288.
  - tomato_large `B1_base_LN`: s0 finished at 1536; s1 and s2 are at 1488.

  Submitted with `... br_missing submit` → **1989710** (grid `+EP`), **1989711** (AS `+ES10+N4_confirm`), **1989712** (tomato_large `base_LN`).
- **Queue.** Checks are queueing behind fair-share priority.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 144 (22:18–22:22): grid no-reg `+LR+ES10+N4` 2/3 at 1536 → extend 3072 (1989713 ); Tomato base `LN+ES10` s0/s2 0.159 (partial)

- **Checks back.** **1989701** (grid `+LR+ES10+N4`) and **1989629** (Tomato `B1_base_LN+ES10`, s0 and s2) COMPLETED.
- **Grid `B1_P1eq1_LN+LR+ES10+N4` (1536).**

  | Seed | Gap (s.e.) | Verdict |
  |---|---|---|
  | s0 | **0.001** | CONVERGED |
  | s1 | **0.016** | CONVERGED |
  | s2 | **0.035** (0.032) | IMPROVING |

  s2 is corrected once, then honest. Its best response takes 2 corrections.
- **Tomato `B1_base_LN+ES10` (1536).**
  - s0 **0.160** and s2 **0.159**, both reactive (true 432 after the correction). Their best responses hide.
  - s1 is still training. It was at 504 when the check was submitted.
  - So ES10 alone has not repeated what ES10+N4 did, where 2 of 3 seeds hid.
- **Rule 6b extension rule.** The grid exploration run has s2 unconverged, so it is extended 2×.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+ES10+N4 3072` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+ES10+N4 --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 3072`.
  - Submitted with `... submit` → **1989713 **.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 145 (22:21–22:26): AS no-reg `+ES10+N4_confirm` 1/3 at 12,288, unconverged seeds PLATEAU → finished; this confirmation failed

- **Check result.** **1989711** (`br_absent_supervisor_B1_P1eq1_LN+RS+ES10+N4_confirm`, 12,288) COMPLETED 22:20. BR gap at 3072 / 6144 / 12,288:

  | Seed | 3072 | 6144 | 12,288 | Verdict at 12,288 |
  |---|---|---|---|---|
  | s20 | 0.070 | 0.031 | **0.053** | PLATEAU |
  | s21 | 0.000 | 0.012 | **0.018** | CONVERGED |
  | s22 | 0.041 | 0.049 | **0.031** | PLATEAU |

  Every policy is corrected once, then honest. Every best response takes 2 corrections.
- **Rule 4.** Every unconverged seed is PLATEAU, so the run is finished; this confirmation failed (1/3).
- **AS no-reg confirmations so far.**
  - Failed: `+AN`, `+N4`, `+LR`, `+ES10+N4`.
  - Still running: `+GL_confirm` (from the 3/3 `+GL`), `+ENT3_confirm` → 24,576, `+EP_confirm` → 24,576, `+NET_confirm` → 12,288.
  - The stage-1 exploration runs are all finished or failed: `ES10` (2/3 at the cap), `N4` (confirmation failed) and `ES10+N4` (confirmation failed). The exception is `ENT3`, whose confirmation is still running, so stage 2 is not yet due.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 146 (22:26–22:30): grid no-reg `+EP` 2/3 at 3072 → extend 6144 (1989727 )

- **Check.** **1989710** (grid `B1_P1eq1_LN+LR+EP`, 3072) COMPLETED.

  | Seed | Gap | Verdict | After the correction |
  |---|---|---|---|
  | s0 | **0.001** | CONVERGED | corrected once, then honest |
  | s1 | **0.040** (s.e. 0.007) | IMPROVING (0.044 at 1536) | never reaches the goal (true −100) |
  | s2 | **0.023** | CONVERGED | corrected once, then honest |

  s1's best response is corrected once, then honest.
- **Rule 4 (wave-2 run, s1 IMPROVING, below the cap): extend 2×.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+EP 6144` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+EP --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1989727 **.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 147 (22:29–22:34): grid `+LR+ES10_confirm` at 3072 → check 1989735; tomato_large base `L` s2 0.226 (reactive); checks 1989736 1989737

- **The tomato_large check.** **1989201** (tomato_large `B1_base_L`, s2 at 1536) COMPLETED 22:29 (2:18:31). This is the first tomato_large check: s2 **0.226** (s.e. 0.000), reactive (corrected once, then honest, true about 516.5). The best response hides (true 84.2 ×4, then 65.0), as the target does.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `+LR+ES10_confirm`: all three seeds at 3072 (the extension finished).
  - Tomato `B1_base_L`: s2 finished at 6144.
  - tomato_large `B1_base_L`: s1 finished at 1536; s0 is at 960.

  `... br_missing submit` → **1989735** (grid confirmation), **1989736** (Tomato base `L`), **1989737** (tomato_large base `L`).
- **Grid no-reg.** The cell is DONE if 1989735 is 3/3.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 148 (22:51–23:12): grid no-reg `+LR+ES10_confirm` 2/3 at 3072, s21 PLATEAU → failed; Tomato base `LN+ES10+N4` finished → check 1989796

- **Wake-up.** Scheduled. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Finished training jobs** (all exit 0):
  - **1989595**, grid `+LR+ES10_confirm` → 3072, 22:30;
  - **1987620**, Tomato `B1_base_L` → 6144, 22:30;
  - **1984541**, tomato_large `B1_base_LN` → 1536, 22:33, after 34:50 h;
  - **1987176**, Tomato `B1_base_LN+ES10+N4`, 22:50.
- **Check 1989735: grid `B1_P1eq1_LN+LR+ES10_confirm` at 3072.**

  | Seed | BR gap, 1536 → 3072 | Verdict |
  |---|---|---|
  | s20 | 0.003 → **0.000** | CONVERGED |
  | s21 | 0.129 → **0.119** (s.e. 0.003) | PLATEAU |
  | s22 | 0.034 → **0.025** | CONVERGED |

  - s21's policy is corrected once, then needs an extra dishonest round (iteration 136); its best response is corrected once, then honest.
- **Rule 4: the only unconverged seed is PLATEAU, so the run is finished; this confirmation failed (2/3).** Grid no-reg's other confirmation, `+LR+ENT3_confirm` (1989566), is still running.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: Tomato `B1_base_LN+ES10+N4`, s2) → `... br_missing submit` → **1989796**.
  - s0 and s1 hide at 0.000. If s2 converges, the run goes to confirmation.
  - The checks of Tomato base `L` s2 (1989736) and tomato_large base `LN` / `L` (1989712, 1989737) are running or queued.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 149 (23:22–23:28): Tomato base `LN+ES10+N4` 2/3 (s0, s1 hide) → extend 3072 (1989820); `L` 0/3 at 6144 → extend to the cap 12,288 (1989821)

- **Checks returned.** **1989796** (Tomato `B1_base_LN+ES10+N4`, s2) and **1989736** (Tomato `B1_base_L`, s2) COMPLETED. `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **`B1_base_LN+ES10+N4`** (rule 6b stage 1, 1536):
    - s0 **0.000** CONVERGED, hides.
    - s1 **0.000** CONVERGED, hides.
    - s2 **0.158** PLATEAU, reactive (true 433 after the correction). Its best response hides.
  - **`B1_base_L`** (6144):
    - s0 **0.160** PLATEAU.
    - s1 **0.160** PLATEAU.
    - s2 **0.161**, labelled IMPROVING.
    - All three are reactive; every best response hides.
- **Rule 6b extension rule, `LN+ES10+N4`.** This is an exploration run and s2 is unconverged, so it is extended 2× to 3072.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+ES10+N4 3072` printed `submit.sh 48 --env tomato --run-id B1_base_LN+ES10+N4 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 3072`.
  - `... submit` → **1989820**.
- **Rule 4, `B1_base_L`.** s2 is labelled IMPROVING and 6144 is below the cap, so it is extended 2× to the cap.
  - Dry-run: `... extend tomato B1_base_L 12288` printed `submit.sh 48 --env tomato --run-id B1_base_L --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 12288`.
  - `... submit` → **1989821**.
  - At the cap the run is finished, whatever the verdict.
- **Tomato base status.**
  - `LN` is finished at 0/3.
  - `L` and `LE` are extending to the cap.
  - Stage 1:
    - `LN+ENT3` is extending to 6144.
    - `LN+N4` is extending to 3072.
    - `LN+ES10` has s1 still training.
    - `LN+ES10+N4` is 2/3 and extending.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 150 (23:49–23:53): AS no-reg `+ENT3_confirm` s20/s22 at the 24,576 cap → check 1989840

- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed AS `+ENT3_confirm`.
  - s20 and s22 have finished at 24,576; s21 is at 23,952.
  - At 12,288 the gaps were s20 0.0301 (IMPROVING), s21 0.000 and s22 0.023.

  `... br_missing submit` → **1989840**.
- **What this run decides.** It is at the cap, so it is finished after this check. If s20 is now ≤ 0.03 and s21 holds, the AS no-reg cell is DONE.
- Cells DONE: 5 of 12.

## 2026-11-15, iteration 151 (23:53–23:57): AS no-reg `+ENT3_confirm` not 3/3 at the 24,576 cap → finished; this confirmation failed

- **Check result.** **1989840** (`br_absent_supervisor_B1_P1eq1_LN+RS+ENT3_confirm`, s20 and s22 at 24,576) COMPLETED 23:53. BR gap over the extensions:

  | Seed | 3072 | 6144 | 12,288 | 24,576 |
  |---|---|---|---|---|
  | s20 | 0.049 | 0.034 | 0.030 | **0.037** (s.e. 0.035) |
  | s21 | 0.000 | 0.002 | 0.000 | still training (24,000) |
  | s22 | 0.052 | 0.039 | 0.023 | **0.078** (s.e. 0.041) |

  - Both checked policies are corrected once, then honest (true about 449.8).
  - Both best responses take 2 corrections (round 1 at true 400). s22's best response now pays more for the second correction than at 12,288.
- **Rule 4: at the cap the run is finished, and s20 and s22 are unconverged, so this confirmation failed.** s21 cannot change that.
- **AS no-reg confirmations:**
  - failed: `+AN`, `+N4`, `+LR`, `+ES10+N4`, `+ENT3`;
  - still running: `+GL_confirm` (1988882, 24,576 episodes), `+EP_confirm` → 24,576 (1988581), `+NET_confirm` → 12,288 (1988582).
- **Rule 6b stage 1 for AS no-reg is now complete without the cell DONE:**
  - `ENT3` and `ES10+N4`: confirmations failed;
  - `N4`: confirmation failed;
  - `ES10`: 2/3 at the cap.

  So stage 2 is due: take the stage-1 run with the smallest mean BR gap and run `explore ... stage2`.
  - Mean BR gap at each run's last tuning check (seeds 0–2): `+N4` 0.000 / 0.000 / 0.000 → **0.0000**; `+ENT3` 0.0002; `+ES10+N4` 0.005; `+ES10` 0.016 (at 24,576).
  - Base: **`B1_P1eq1_LN+RS+N4`**, the smallest. I corrected this line before submitting; my first draft named `+ENT3` from memory, and the computed means put `+N4` first.
- Cells DONE: 5 of 12.
- **Rule 6b stage 2 for AS no-reg.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh explore absent_supervisor P1eq1 B1_P1eq1_LN+RS+N4 stage2`. Both runs are the base's overrides at 3072 episodes:
    - `+ENT10`: `ppo.ent_coef=1`, i.e. 10× the base's 0.1.
    - `+ES30`: `anneal.ent_start=30 anneal.ent_episodes=1536`.
  - `ES30+N4` is not submitted: the base already has N4 (`n_envs=256 ppo.batch_size=6400`), so it would be `ES30` again.
  - Submitted: `... stage2 submit` → **1989843 1989844 **.
  - The extension rule applies to both.

## 2026-11-16, iteration 152 (00:00–00:03): grid no-reg `+GL` reached 6144 → check 1989849 1989850 

- **Training finished.** **1988904** (grid `B1_P1eq1_LN+LR+GL`, extension to 6144) COMPLETED 23:58 (4:05:30, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `+GL`) → `... br_missing submit` → **1989849** (grid `+GL`) and **1989850** (grid `+RS`, whose seed finished at 6144 between the two commands).
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 153 (00:06–00:10): grid no-reg `+GL` 2/3 at 6144, s2 PLATEAU → finished; `+RS` 1/3 → extend to the cap 12,288 (1989863 )

- **Checks back.** **1989849** (grid `+GL`) and **1989850** (grid `+RS`) COMPLETED. Verdicts at 6144:

  | Run | Seed | BR gap | Verdict | Policy after its correction |
  |---|---|---|---|---|
  | `+GL` | s0 | **0.000** | CONVERGED | honest |
  | | s1 | **0.001** | CONVERGED | honest |
  | | s2 | **0.051** | PLATEAU | honest at true 22; its best response takes a true-20 route that pays more under the refitted correction (iteration 126) |
  | `+RS` | s0 | **0.000** | CONVERGED | honest |
  | | s1 | **0.043** | PLATEAU | never reaches the goal |
  | | s2 | **0.059** | IMPROVING | never reaches the goal; its best response takes 2 corrections |

- **Rule 4, `+GL`.** The only unconverged seed is PLATEAU, so the config is finished and not extended.
- **Rule 4, `+RS`.** s2 is IMPROVING, so the run is extended 2× to the cap.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+RS 12288` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+RS --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 12288`.
  - Submitted: `... submit` → **1989863 **.
- **Grid no-reg runs still open:**
  - `+LR+ENT3_confirm` (1989566);
  - `+AN` → 6144;
  - `+EP` → 6144;
  - `+RS` → 12,288;
  - `+LR+N4` → 3072;
  - `+LR+ES10+N4` → 3072.

  Finished without DONE: `LN+LR`, `+NET` and `+GL`; `+LR+ES10`'s confirmation failed.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 154 (00:13–00:15): tomato_large base `L` s1 0.227 (reactive; partial)

- **Check result.** **1989737** (tomato_large `B1_base_L`, s1 at 1536) COMPLETED 00:12 (1:19:36): s1 **0.227** (s.e. 0.000).
  - The policy is reactive: corrected once, then honest, at true about 516.
  - The best response hides (true 84.2 ×4, then 65.0), as the target does.
- **Run status.** s2 was 0.226 (iteration 147); s0 is still training. Rule 4 waits for s0.
- **Next check.** The tomato_large base `LN` check (1989712, s0) is still running.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 155 (00:16–00:19): Tomato base `LN+N4` s0 at 3072 → check 1989866

- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed Tomato `B1_base_LN+N4` (rule 6b stage 1). s0 has finished at 3072; s1 and s2 are at 2976. `... br_missing submit` → **1989866**.
- **Also finished:** **1988883** (grid `+RS`, its earlier extension to 6144) COMPLETED 00:02. Its 12,288 extension is 1989863.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 156 (00:26–00:30): Tomato base `LN+ES10` finished; grid `+LR+N4` s1 at 3072 → checks 1989876 1989877

- **Training finished.** **1987174** (Tomato `B1_base_LN+ES10`) COMPLETED 00:25 (19:39:23, exit 0).
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `+LR+N4`: s1 finished at 3072; s0 is at 3024 and s2 at 3048.
  - Tomato `B1_base_LN+ES10`: s1 finished at 1536. s0 and s2 were checked in iteration 144.

  `... br_missing submit` → **1989876** (grid `+LR+N4`), **1989877** (Tomato `LN+ES10`).
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 157 (00:32–00:35): grid `+LR+N4` finished at 3072 → check 1989881  (s0, s2)

- **Training finished.** **1988924** (grid `B1_P1eq1_LN+LR+N4`, extended to 3072) COMPLETED 00:30 (4:37:44, exit 0). Check **1989876** (s1) is done.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `+LR+N4`, s0 and s2) → `... br_missing submit` → **1989881 **.
- **Pending checks.** The Tomato base `LN+N4` / `LN+ES10` and tomato_large base `LN` checks are still running.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 158 (00:37–00:42): grid `+LR+N4` 1/3 at 3072 → extend 6144 (1989885 ); checks 1989882 (AS `+ENT3_confirm` s21) and 1989883 (Tomato base `LN+N4` s1/s2)

- **What finished.**
  - **1989881** (grid `+LR+N4`, s0 and s2 at 3072) COMPLETED.
  - **1989866** (Tomato `B1_base_LN+N4`, s0) COMPLETED.
  - Training jobs **1987629** (AS `+ENT3_confirm`, 24,576) and **1988345** (Tomato `B1_base_LN+N4`, 3072) COMPLETED 00:37 and 00:35.
- **Check results.**
  - **grid `B1_P1eq1_LN+LR+N4`** (3072):
    - s0 **0.062** IMPROVING (0.109 at 1536);
    - s1 **0.052** IMPROVING;
    - s2 **0.004** CONVERGED.
    - s0 and s1 are corrected once, then never reach the goal. Their best responses are honest.
  - **Tomato `B1_base_LN+N4`** s0 **0.158** (3072), PLATEAU, reactive. s1 and s2 have finished but are not checked yet.
- **Rule 6b extension rule.** The grid exploration run has seeds unconverged, so it is extended 2×.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+N4 6144` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+N4 --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1989885 **.
- **Rule 3.** `br_missing` (dry-run: AS `+ENT3_confirm` s21; Tomato `LN+N4` s1 and s2) → `... br_missing submit` → **1989882**, **1989883**.
  - `+ENT3_confirm` already failed (iteration 151); s21's check is for the record.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 159 (00:55–01:00): Tomato base `LN+ES10` 0/3 at 1536 → extend 3072 (1989902 ); grid `+AN` at 6144 → check

- **The check.** **1989877** (Tomato `B1_base_LN+ES10`, s1) COMPLETED. All three seeds are reactive at 1536 (s0 **0.160**, s1 **0.160**, s2 **0.159**, all PLATEAU); every best response hides.
- **Rule 6b extension rule.** This is an exploration run with all seeds unconverged, so it is extended 2× whatever the verdict.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+ES10 3072` printed `submit.sh 48 --env tomato --run-id B1_base_LN+ES10 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 3072`.
  - Submitted: `... submit` → **1989902 **.
- **Rule 3.**
  - **1989569** (grid `+AN`, extended to 6144) COMPLETED 00:40.
  - `br_missing` (dry-run: grid `+AN` at 6144) → `... br_missing submit` → **1989903 **.
- **Other checks returned.**
  - **1989882**: AS `+ENT3_confirm` s21 (already failed; for the record).
  - **1989883**: Tomato base `LN+N4` s1 and s2, still queued.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 160 (00:49–00:52): grid no-reg `+AN` 2/3 at 6144, s2 PLATEAU → finished

- **The check.** **1989903** (grid `B1_P1eq1_LN+LR+AN`, 6144) COMPLETED 00:49. BR gaps at 1536 / 3072 / 6144:

  | Seed | 1536 | 3072 | 6144 | Verdict |
  |---|---|---|---|---|
  | s0 | 0.002 | 0.000 | **0.002** | CONVERGED |
  | s1 | 0.027 | 0.003 | **0.000** | CONVERGED |
  | s2 | 0.052 | 0.054 | **0.049** | PLATEAU |

  - s2's policy is corrected once, then honest (true 22).
  - Its best response takes a true-20 route that pays more under the refitted corrections. This is the same pattern as `+GL` s2.
- **Rule 4: the only unconverged seed is PLATEAU, so the config is finished.**
- **Grid no-reg wave 2 so far.**
  - Finished without 3/3: `+NET`, `+GL`, `+AN`.
  - Still running: `+EP` → 6144 (1989727) and `+RS` → 12,288 (1989863).
  - In exploration, `+LR+ES10_confirm` failed. `+LR+ENT3_confirm` (1989566) is running, and `+LR+N4` → 6144 and `+LR+ES10+N4` → 3072 are still extending.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 161 (01:25–01:32): Tomato base `LN+N4` 0/3 at 3072 → extend 6144 (1989933 )

- **The check.** **1989883** (Tomato `B1_base_LN+N4`, s1 and s2) COMPLETED. All three seeds are at **0.158**, PLATEAU, at 3072. They are reactive (true about 433 after the correction), and every best response hides.
- **Rule 6b extension rule.** This is an exploration run with all seeds unconverged, so it is extended 2× whatever the verdict.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+N4 6144` printed `submit.sh 48 --env tomato --run-id B1_base_LN+N4 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1989933 **.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 162 (01:33–01:36): tomato_large base `L` finished at 1536 (37:50 h) → check 1989944  (s0)

- **Training finished.** **1984539** (tomato_large `B1_base_L`, wave 1) COMPLETED 01:33 (1-13:49:37, exit 0), inside the 48 h limit.
- **Earlier checks.** s1 (**0.227**) and s2 (**0.226**) were checked in iterations 154 and 147; both are reactive.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: s0) → `... br_missing submit` → **1989944 **.
- **Next.** Rule 4 is applied once s0 has a result.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 163 (02:05–02:08): grid `+LR+ES10+N4` finished at 3072; Tomato base `LN+ES10+N4` seed(s) at 3072 → checks 1989990 1989991 

- **Training finished.** **1989713** (grid `B1_P1eq1_LN+LR+ES10+N4`, extended to 3072) COMPLETED 02:04 (3:32:21, exit 0).
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed grid `+LR+ES10+N4` (all seeds) and Tomato `B1_base_LN+ES10+N4` (finished seeds at 3072, per `ls`). `... br_missing submit` → **1989990 1989991 **.
- **What the Tomato check decides.** At 1536 the Tomato run had s0 and s1 hiding at 0.000 and s2 reactive at 0.158. Whether s2 has changed at 3072 decides between `confirm` and a further extension.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 164 (02:10–02:14): grid no-reg `+LR+ES10+N4` 3/3 CONVERGED at 3072 → `confirm` (1989995 )

- **Check result.** **1989990** (grid `B1_P1eq1_LN+LR+ES10+N4`, 3072) COMPLETED 02:10. BR gap at 1536 → 3072:

  | Seed | 1536 | 3072 | Verdict |
  |---|---|---|---|
  | s0 | 0.001 | **0.000** | CONVERGED |
  | s1 | 0.016 | **0.002** | CONVERGED |
  | s2 | 0.035 | **0.017** | CONVERGED |

  All three policies are corrected once, then honest (true about 22).
- **Rule 4 (rule 6b exploration run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid B1_P1eq1_LN+LR+ES10+N4` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --set g.use_regularization=False anneal.last=0.25 anneal.floor=0.1 anneal.ent_start=10 anneal.ent_episodes=768 n_envs=256 ppo.batch_size=6400 ppo.learning_rate=0.0001 protocol.update_bonus=1.0 episodes=3072`. That is the run's overrides at its final length, and it matches `run_sets.py`.
  - Submitted: `... submit` → **1989995 **.
- **Grid no-reg confirmations now running:** `+LR+ENT3_confirm` (1989566) and this one. The cell is DONE when either is 3/3.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 165 (02:32–02:35): Tomato base `LN+ES10+N4` s0/s1 still hide at 3072 (0.000); s2 still training

- **Check result.** **1989991** (Tomato `B1_base_LN+ES10+N4`, s0 and s1 at 3072) COMPLETED. s0 **0.000** and s1 **0.000**, CONVERGED; both hide, matching the target.
- **s2.** Still training at 2496 of 3072. Its training curve is still reactive (corrected in round 0, then honest).
- **Next.** Rule 4 waits for s2.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 166 (02:57–03:00): tomato_large no-reg `LN+ES10` finished at 1536 (39 h); grid `+LR+ENT3_confirm` seeds finished → checks 1990118 1990119 

- **Training finished.** **1984538** (tomato_large `B1_P1eq1_LN+ES10`, wave 1) COMPLETED 02:56 (1-15:12:25, exit 0), inside the 48 h limit.
- **Rule 3.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed grid `+LR+ENT3_confirm` (its finished seeds, per `ls`) and tomato_large `B1_P1eq1_LN+ES10`. `... br_missing submit` → **1990118 1990119 **.
  - The tomato_large no-reg check is that cell's first. Its target is 3–4 corrections, then honest.
  - The grid no-reg cell is DONE if `+LR+ENT3_confirm` is 3/3.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 167 (03:04–03:08): grid no-reg `+LR+ENT3_confirm` finished at 3072; s21 0.121, s22 0.041 (not converged) → check 1990132 (s20)

- **What finished.** **1989566** (grid `+LR+ENT3_confirm`, 3072) COMPLETED 03:04 (6:35:32, exit 0). Check **1990118** COMPLETED 03:01 and covered s21 and s22.
- **Results.**

  | Seed | Gap (s.e.) | True by round | Received per round (rounds 1–4) | Best response's received |
  |---|---|---|---|---|
  | s21 | **0.121** (0.004) | −100, then 22 ×4 (honest) | about 42,967 | 49,160 |
  | s22 | **0.041** (0.023) | corrected once, then honest | — | 42,922, then 51,258 (it takes 2 corrections) |

  - **s21.** Its true return is honest, but under the refitted no-reg correction, which raises honest transitions by large amounts, the best response's honest route collects more of the raise.
  - **s22.** The best response takes a second correction, worth about 4% of V.
- **Rule 3.** `br_missing` (dry-run: s20) → `... br_missing submit` → **1990132**.
- **What this means.** With s21 and s22 unconverged, the confirmation cannot be 3/3 at 3072. Rule 4 is applied once s20 is in.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 168 (03:24–03:28): grid no-reg `+LR+ENT3_confirm` 1/3 at 3072 → extend 6144 (1990151 ); AS `+EP_confirm` at the cap → check 1990150

- **Grid check result.** **1990132** (grid `+LR+ENT3_confirm`, s20) COMPLETED 03:23. At 3072:
  - s20 **0.020** CONVERGED (honest; its best response takes a true-20 route).
  - s21 **0.121** PLATEAU (iteration 167).
  - s22 **0.041** IMPROVING.
- **Rule 4.** This is a confirmation, s22 is IMPROVING and 3072 is below the cap, so extend 2×. The s21 PLATEAU does not stop the extension, because rule 4 extends when any seed is IMPROVING.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+ENT3_confirm 6144` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+ENT3_confirm --seeds 20 21 22 --results-dir results/step4/grid/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1990151 **.
- **AS confirmation reached the cap.** **1988581** (AS `+EP_confirm`, extended to the cap of 24,576) COMPLETED 03:22 (10:13:45, exit 0).
  - `br_missing` (dry-run: AS `+EP_confirm`) → `... br_missing submit` → **1990150**.
  - At the cap the run is finished, whatever the verdict.
- Cells DONE: 5 of 12.

## 2026-11-16, iteration 169 (03:37–03:45): **AS no-reg DONE** (`B1_P1eq1_LN+RS+EP_confirm` 3/3 at the 24,576 cap)

- **Check result.** **1990150** (`br_absent_supervisor_B1_P1eq1_LN+RS+EP_confirm`, 24,576) COMPLETED 03:37. BR gap at 6144 / 12,288 / 24,576:

  | Seed | 6144 | 12,288 | 24,576 | Verdict |
  |---|---|---|---|---|
  | s20 | 0.032 | 0.059 | **0.001** | CONVERGED |
  | s21 | 0.000 | 0.013 | **0.001** | CONVERGED |
  | s22 | 0.057 | 0.060 | **0.027** | CONVERGED |

  - Every policy is corrected once, then honest (true 448.8–449.8).
  - The best responses of s20 and s22 take 2 corrections (round 1 at true 400), worth less than 3% more.
- **Rule 4: the confirmation is 3/3, so the AS no-reg cell is DONE.**
  - Config: `B1_P1eq1_LN+RS+EP`, i.e. `ppo.ent_coef=0.1 ppo.batch_size=1600 ppo.n_epochs=20 g.use_regularization=False g.epochs=1000 n_envs=64 reward_scale=0.01625`, anneal over the last 25%, the bonus.
  - Tuning seeds 0–2 at 6144: 0.001 / 0.000 / 0.004.
  - Confirmation seeds 20–22 at 24,576 (two extensions): 0.001 / 0.001 / 0.027.
  - Extended confirmations count (the user, 2026-11-10).
- **Rule 6b: nothing new for AS no-reg.** Its running runs finish as information only, with no extensions or confirmations:
  - `+GL_confirm` (1988882), `+NET_confirm` → 12,288 (1988582), stage 2 `+N4+ENT10` (1989843) and `+N4+ES30` (1989844).
  - `br_missing` still checks them.
- **Status updated at the top. Cells DONE: 6 of 12.**
  - DONE: grid swap, AS swap, Tomato swap, grid base, AS base, AS no-reg.
  - Open: grid no-reg, Tomato no-reg, Tomato base, and the three tomato_large cells.

## 2026-11-16, iteration 170 (03:50–03:55): tomato_large base `LN` 0/3 at 1536, all PLATEAU → finished; Tomato base `LN+ES10+N4` s2 at 3072 → check 1990162 

- **Check 1989712** (tomato_large `B1_base_LN`, all three seeds at 1536) COMPLETED 03:50 (5:01:16).
  - s0 **0.223**, s1 **0.223**, s2 **0.223**, all PLATEAU.
  - The policies are reactive: corrected in round 0, then honest at true about 519.5.
  - The best responses hide (true 84.2 ×4, then 65.0), as the target does.
- **Rule 4.** Every unconverged seed is PLATEAU, so the run is finished.
- **tomato_large base status.**
  - `L`: s1 0.227 and s2 0.226, both PLATEAU; s0's check (1989944) is running.
  - `LE`: still training. It reaches the 48 h limit at about 11:43, and rule 1 resumes it.
  - Rule 6b exploration for this cell starts once every wave-1 run has a check and none is 3/3.
- **Training finished.** **1989820** (Tomato `B1_base_LN+ES10+N4`, extension to 3072) COMPLETED 03:48.
  - `br_missing` (dry-run: s2) → `... br_missing submit` → **1990162 **.
  - s0 and s1 hide at 0.000. If s2 now hides too, the run goes to `confirm`.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 171 (04:11–04:16): tomato_large base `L` 0/3 at 1536 → extend 3072 (1990168 ) (corrected: s0 is IMPROVING)

- **The check.** **1989944** (tomato_large `B1_base_L`, s0) COMPLETED 04:10 (1:07:26).
  - s0 is **0.227**, labelled **IMPROVING**.
  - The run is now complete: s0 0.227 (IMPROVING), s1 0.227 (PLATEAU), s2 0.226 (PLATEAU).
  - Every policy is reactive (corrected in round 0, then honest, true about 516). Every best response hides, as the target does.
- **Rule 4.** s0 is IMPROVING and 1536 is below the cap of 12,288, so extend 2×.
  - Correction: my first version of this entry (commit fbd09cea8) read all three seeds as PLATEAU and called the run finished. The script labels s0 IMPROVING, so I corrected the entry and submitted the extension.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato_large B1_base_L 3072` printed `submit.sh 48 --env tomato_large --run-id B1_base_L --seeds 0 1 2 --results-dir results/step4/tomato_large/bonus --resume --extend-to 3072`.
  - Submitted with `... submit` → **1990168 **.
- **tomato_large base.**
  - `LN` is finished at 0/3. `L` is extending to 3072.
  - `LE` is still training (wave 1). It reaches the 48 h limit at about 11:43; rule 1 resumes it.
  - Rule 6b exploration starts once `LE` has a check and no wave-1 run is 3/3.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 172 (04:17–04:20): Tomato base `LN+ES10+N4` 2/3 at 3072 (s2 still reactive) → extend 6144 (1990170 )

- **The check.** **1990162** (Tomato `B1_base_LN+ES10+N4`, s2 at 3072) COMPLETED.

  | Seed | Gap at 1536 → 3072 | Verdict | Behaviour |
  |---|---|---|---|
  | s0 | 0.000 → **0.000** | CONVERGED | hides |
  | s1 | 0.000 → **0.000** | CONVERGED | hides |
  | s2 | 0.158 → **0.158** | PLATEAU | reactive |

- **Rule 6b extension rule.** This is an exploration run with s2 unconverged, so it is extended 2× whatever the verdict.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+ES10+N4 6144` printed `submit.sh 48 --env tomato --run-id B1_base_LN+ES10+N4 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1990170 **.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 173 (04:20–04:30): grid no-reg `LN+LR+EP` finished at 6144 → check 1990171

- **The run.** **1989727** (grid `B1_P1eq1_LN+LR+EP`, extended to 6144) COMPLETED 04:23 (4:45:26). s0 and s2 had finished earlier; s1 finished last.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_grid_B1_P1eq1_LN+LR+EP` (`--finished-only --draws 12`). It also printed "tomato_large/B1_P1eq1_LN+ES10: check still queued/running" (1990119).
  - Submitted: `... br_missing submit` → **1990171**. It reads the finished seeds when it starts, so it covers all three (s1's `metrics.json` is in its directory listing).
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 174 (04:28–04:33): grid no-reg `LN+LR+EP` 2/3 at 6144 (s1 IMPROVING by the script) → extend to the cap, 12,288 (1990173)

- **The check.** **1990171** (grid `B1_P1eq1_LN+LR+EP`, all three seeds at 6144) COMPLETED (2:06). `step4_convergence.py`:

  | Seed | BR gap at 1536 / 3072 / 6144 | Verdict | PPO's true by round | Best response |
  |---|---|---|---|---|
  | s0 | 0.001 / 0.001 / **0.001** | CONVERGED | −100, 21.6, 20.9, 21.5, 21.6 | corrected in round 0, then honest |
  | s1 | 0.044 / 0.040 / **0.042** (s.e. 0.008) | IMPROVING | −100 every round (corrected in every round) | corrected in round 0, then honest |
  | s2 | 0.002 / 0.023 / **0.010** (s.e. 0.034) | CONVERGED | −100, 21.7, 21.8, 21.7, 21.7 | 2 corrections, then honest |

  - s1 is still the open exploiter, corrected every round. Its BR gap is flat (0.040–0.044). The IMPROVING verdict comes from the script's 24-episode curve, which I apply as written.
- **Rule 4 (wave-2 run, one seed IMPROVING): extend 2×**, which is the grid cap.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend grid B1_P1eq1_LN+LR+EP 12288` printed `submit.sh 48 --env grid --run-id B1_P1eq1_LN+LR+EP --seeds 0 1 2 --results-dir results/step4/grid/bonus --resume --extend-to 12288`.
  - Submitted: `... submit` → **1990173**.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 175 (05:28–05:30): AS no-reg `LN+RS+NET_confirm` finished (information only; the cell is DONE) → check 1990197 

- **The run.** **1988582** (AS `B1_P1eq1_LN+RS+NET_confirm`) COMPLETED 05:28 (12:18:55, exit 0).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_absent_supervisor_B1_P1eq1_LN+RS+NET_confirm`.
  - Submitted: `... br_missing submit` → **1990197 **. AS checks take about a minute. The cell is DONE (`LN+RS+EP`), so this is for the record only.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 176 (05:43–05:47): AS no-reg `LN+RS+NET_confirm` 1/3 at 12,288 (information only); Tomato base `LN+ES10` s0 at 3072 → check 1990199

- **The check.** **1990197** (AS `B1_P1eq1_LN+RS+NET_confirm`, 12,288) COMPLETED (2:11). Verdicts:
  - s20: 0.044 (s.e. 0.029), IMPROVING;
  - s21: 0.000, CONVERGED (corrected once, then honest);
  - s22: 0.078 (s.e. 0.035), IMPROVING.
  - The cell is DONE (`LN+RS+EP`), so this run is information only and is not extended.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_B1_base_LN+ES10` (s0 finished at 3072; s1 and s2 are still training in 1989902).
  - Submitted: `... br_missing submit` → **1990199**. The run is not extended until all three seeds are checked.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 177 (06:00–06:02): Tomato base `LN+ES10` s0 0.159 PLATEAU at 3072 (reactive)

- **The check.** **1990199** (Tomato `B1_base_LN+ES10` s0 at 3072) COMPLETED (6:42).
  - s0: BR gap 0.159, PLATEAU (at 1536 it was 0.159). PPO is corrected in round 0, then honest (true 432 against 434). The best response hides (59.8 ×4, then 46).
  - s1 and s2 are at 3048/3072 and look the same.
- **Next.** This is an exploration (6b) run, so it is extended 2× (to 6144) whatever the verdict, once s1 and s2 are checked. Cells DONE: 6 of 12.

## 2026-11-16, iteration 178 (06:03–06:05): Tomato base `LN+ES10` finished at 3072 → check 1990210  (s1, s2)

- **Training wait.** **1989902** (Tomato `B1_base_LN+ES10`, extended to 3072) COMPLETED 06:03 (4:32:26, exit 0).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_B1_base_LN+ES10`.
  - Submitted: `... br_missing submit` → **1990210 ** (s1, s2).
- The 6b extension to 6144 follows once this check is in. Cells DONE: 6 of 12.

## 2026-11-16, iteration 179 (06:40–06:45): grid no-reg `LN+LR+ENT3_confirm` finished at 6144 → check 1990221

- **Training wait.** **1990151** (grid `B1_P1eq1_LN+LR+ENT3_confirm`, extended to 6144) COMPLETED 06:39 (2:51:18, exit 0).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_grid_B1_P1eq1_LN+LR+ENT3_confirm`.
  - Submitted: `... br_missing submit` → **1990221**.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 180 (06:41–06:50): Tomato base `LN+ES10` 0/3 at 3072 (all reactive, PLATEAU) → 6b extension to 6144 (1990224 )

- **The check.** **1990210** (Tomato `B1_base_LN+ES10`, s1 and s2 at 3072) COMPLETED (13:14).
  - All three seeds: BR gap **0.159**, PLATEAU, unchanged since 1536 (0.160 / 0.160 / 0.159).
  - In every seed PPO is corrected in round 0, then honest (true about 432 against 434). The best response hides (59.8 ×4, then 46).
- **Rule 6b extension rule.** This is an exploration run (extended under 6b before, in iteration 159), so it is extended 2× whatever the verdict.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+ES10 6144` printed `submit.sh 48 --env tomato --run-id B1_base_LN+ES10 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 6144`.
  - Submitted: `... submit` → **1990224 **.
- Cells DONE: 6 of 12.

## 2026-11-16, iteration 181 (06:50–07:00): **grid no-reg DONE** (`LN+LR+ENT3_confirm` 3/3 at 6144)

- **The check.** **1990221** (grid `B1_P1eq1_LN+LR+ENT3_confirm` at 6144) COMPLETED (2:43). `step4_convergence.py`:

  | Seed | BR gap at 3072 → 6144 | Verdict | PPO's true by round | Best response |
  |---|---|---|---|---|
  | s20 | 0.020 → **0.000** | CONVERGED | −100, 22 ×4 | corrected once, then honest |
  | s21 | 0.121 → **0.002** | CONVERGED | −100, 22 ×4 | corrected once, then honest |
  | s22 | 0.041 → **0.025** (s.e. 0.023) | CONVERGED | −100, 21.9, 22, 22, 22 | 2 corrections, then honest |

- **Rule 4: a `_confirm` run with all seeds CONVERGED → the cell is DONE.**
  - The tuning run `B1_P1eq1_LN+LR+ENT3` was 3/3 at 3072 (0.000 / 0.000 / 0.001; iteration 133).
  - The confirmation was extended once, 3072 → 6144 (iteration 168: 1/3 at 3072, with an IMPROVING seed). Extended confirmations count (the user's ruling, docs/step4_optimal.md).
  - PPO is corrected once, then honest (true 22) in all six seeds, which is the target's end state.
- **The cell's other runs are now information only:** `+LR+EP` (→ 12,288, 1990173), `+LR+ES10+N4_confirm` (1989995), `+LR+N4` (1989885), `+LR+RS` (1989863). They keep running; I cancel nothing. Status updated at the top.
- **Cells DONE: 7 of 12.** Open: Tomato no-reg, Tomato base, tomato_large swap, no-reg and base.

## 2026-11-16, iteration 182 (07:00–07:08): tomato_large no-reg `LN+ES10` 0/3 at 1536 (s1, s2 IMPROVING) → extend 3072 (1990237 )

- **The check.** **1990119** (tomato_large `B1_P1eq1_LN+ES10`, wave 1, all three seeds at 1536) COMPLETED (3:55:12). `step4_convergence.py`:

  | Seed | BR gap (s.e.) | Verdict | PPO | Best response | Target |
  |---|---|---|---|---|---|
  | s0 | **0.073** (0.016) | PLATEAU | 3 corrections; true 65, then about 518 | 4 corrections | 3 corrections |
  | s1 | **0.055** (0.009) | IMPROVING | 4 corrections; true 65, then about 518 | 4 corrections | 4 corrections |
  | s2 | **0.037** (0.012) | IMPROVING | 3 corrections; true 65, then about 518 | 3 corrections | 3 corrections |

  - PPO's end states match the targets' (3–4 corrections per episode; true about 518 in rounds 1–4 against honest about 523). The shortfall is in value.
- **Rule 4 (wave-1 run, seeds IMPROVING, below the 12,288 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato_large B1_P1eq1_LN+ES10 3072` printed `submit.sh 48 --env tomato_large --run-id B1_P1eq1_LN+ES10 --seeds 0 1 2 --results-dir results/step4/tomato_large/bonus --resume --extend-to 3072`.
  - Submitted: `... submit` → **1990237 **.
  - The wave-1 run took 39:12 h for 1536 episodes, so the extension may reach the 48 h limit; rule 1 then resumes it.
- Cells DONE: 7 of 12.

## 2026-11-16, iteration 183 (07:08–07:15): rule 6b starts in tomato_large no-reg: `+ENT3` (1990239), `+N4` (1990240)

- **When to start (docs/step4_bonus.md, rule 6b).** The cell's one wave-1 run, `B1_P1eq1_LN+ES10`, now has a check, and it is 0/3 (iteration 182). So exploration starts now, in parallel with its extension (1990237).
- **The base** is that run, the only one in the cell.
- **Dry-run.** `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh explore tomato_large P1eq1 B1_P1eq1_LN+ES10` printed 4 submits on seeds 0–2, at 1536 episodes, all with the base's `ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 protocol.update_bonus=1.0`:
  - `B1_P1eq1_LN+ES10+ENT3`: `ppo.ent_coef=0.09`, ES10 schedule, `n_envs=64`;
  - `B1_P1eq1_LN+ES10+ES10`: `ppo.ent_coef=0.03`, ES10 schedule, `n_envs=64`. **This is identical to the base**;
  - `B1_P1eq1_LN+ES10+N4`: `ppo.ent_coef=0.03`, ES10, `n_envs=256 ppo.batch_size=6400`;
  - `B1_P1eq1_LN+ES10+ES10+N4`: **identical to `+N4`**.
- **Submitted the two distinct runs.** I ran their printed `submit.sh` lines exactly as the driver prints them: **1990239** (`+ENT3`) and **1990240** (`+N4`). The two duplicates are skipped and flagged at the top.
- **Budget.** Bonus jobs 20 (limit 60); all my jobs 44 (limit 110). Cells DONE: 7 of 12.

## 2026-11-16, iteration 184 (08:32–08:35): Tomato base `LN+ENT3` finished at 6144 → check 1990255 

- **Training wait.** **1989207** (Tomato `B1_base_LN+ENT3`, 6b, extended to 6144) COMPLETED 08:32 (12:09:30, exit 0).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_B1_base_LN+ENT3`.
  - Submitted: `... br_missing submit` → **1990255 **.
- Cells DONE: 7 of 12.

## 2026-11-16, iteration 185 (09:02–09:08): grid no-reg `LN+LR+RS` finished at 12,288 (information only) → check 

- **Training wait.** **1989863** (grid `B1_P1eq1_LN+LR+RS`, extended to the 12,288 cap) COMPLETED 09:02 (8:00:05, exit 0).
- **The cell is DONE** (iteration 181), so this run is information only.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_grid_B1_P1eq1_LN+LR+RS`.
  - Submitted: `... br_missing submit` → ****, for the record.
- Cells DONE: 7 of 12.
- **Its check.** **1990269** COMPLETED (3:31); verdicts are in the line below (information only).
  - Verdicts at 12,288 (the cap): s0 0.000 CONVERGED; s1 0.050 PLATEAU; s2 0.056 IMPROVING. The run ends here: it is at the cap, and the cell is already DONE.

## 2026-11-16, iteration 186 (09:24–09:30): Tomato base `LN+ENT3` (6b) 0/3 at 6144 (all reactive) → extend to the cap, 12,288 (1990294 )

- **The check.** **1990255** (Tomato `B1_base_LN+ENT3` at 6144) COMPLETED (24:22).

  | Seed | BR gap at 1536 / 3072 / 6144 | Verdict | PPO's true by round | Best response |
  |---|---|---|---|---|
  | s0 | 0.163 / 0.161 / **0.160** | IMPROVING | 46, then about 430 | hides (59.8 ×4, then 46) |
  | s1 | 0.162 / 0.161 / **0.161** | IMPROVING | the same | the same |
  | s2 | 0.162 / 0.161 / **0.160** | IMPROVING | the same | the same |

  - All three are reactive: corrected in round 0, then honest. The best response hides.
  - The BR gap is flat at 0.160; the IMPROVING call comes from the script's 24-episode curve.
- **Rule 6b extension rule (exploration run): extend 2×**, which is the cap.
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato B1_base_LN+ENT3 12288` printed `submit.sh 48 --env tomato --run-id B1_base_LN+ENT3 --seeds 0 1 2 --results-dir results/step4/tomato/bonus --resume --extend-to 12288`.
  - Submitted: `... submit` → **1990294 **.
  - The 3072 → 6144 leg took 12:09 h, so this one should take about 24 h.
- **Tomato base so far.** Every run in this cell (`L`, `LE`, `LN`, `LN+ENT3`, `LN+N4`, `LN+ES10`, `LN+ES10+N4`) has seeds that are reactive, at a BR gap of about 0.16. Only `LN+ES10+N4` s0/s1 hide (0.000).
- Cells DONE: 7 of 12.

## 2026-11-16, iteration 187 (09:31–09:36): checks for Tomato base `LN+ES10+N4` (s0, s1 at 6144) and tomato_large base `LE` (s0 at 1536)

- **Tick.** No job failed. Nothing to resume yet: the tomato_large wave-1 runs reach 48 h at about 11:43.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed two runs:
    - Tomato `B1_base_LN+ES10+N4`: s0 and s1 finished at 6144; s2 is still training in 1990170.
    - tomato_large `B1_base_LE`, wave 1: s0 finished at 1536; s1 and s2 are still training.
  - Submitted: `... br_missing submit` → **1990306** (Tomato), **1990307** (tomato_large).
- **tomato_large base, rule 6b.** It starts once `LE` has a check and no wave-1 run is 3/3: `L` is extending, `LN` finished 0/3. This check is the first for `LE`.
- Cells DONE: 7 of 12.

## 2026-11-16, iteration 188 (10:13–10:16): Tomato base `LN+ES10+N4` s0, s1 still hide at 6144 (0.000); s2 still reactive

- **The check.** **1990306** (Tomato `B1_base_LN+ES10+N4` s0, s1 at 6144) COMPLETED (11:50).
  - s0: **0.000**, CONVERGED.
  - s1: **0.000**, CONVERGED.
  - Both hide, matching the target exactly (true 59.8 ×4, then 46).
  - s2 (4776/6144) is still training and still reactive (corrected once, then true about 430). It was 0.158 PLATEAU at 3072.
- **Next.** Once s2 finishes and is checked: 3/3 → `confirm`. Otherwise, as an exploration run, it is extended 2× (to 12,288, the cap) whatever the verdict.
- Cells DONE: 7 of 12.

## 2026-11-16, iteration 189 (10:21–10:24): AS no-reg `LN+RS+N4+ES30` (information only) has finished seeds → check 1990351 

- **Tick.** No job failed. Nothing to resume.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=bonus EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_absent_supervisor_B1_P1eq1_LN+RS+N4+ES30` (s0 finished; s1 and s2 still training), a stage-2 run in a cell that is already DONE.
  - Submitted: `... br_missing submit` → **1990351 **, for the record (AS checks take minutes).
- Cells DONE: 7 of 12.
