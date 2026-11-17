# Step 4 no-regulariser failure campaign (Taxi, Boat Race): decision log

Procedure: `docs/step4_noreg_fail.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=noreg_fail`.

## Flags for the user

- **NEW (2026-11-16): node wheat-06 is down** (`sinfo`: `down*`, "Not responding"). It killed the bonus campaign's Tomato no-reg `LN_confirm` (NODE_FAIL; flagged in docs/step4_bonus_log.md). None of this campaign's jobs were on it. Every submit now carries `EXCLUDE=barley-04,wheat-06` while it is down.

- **barley-04.** Every submit still carries `EXCLUDE=barley-04` (your standing instruction from the optimal campaign). On 2026-11-14 at 11:42, `sinfo` shows barley-04 `allocated` with no reason set; say if I should drop the exclusion.
- **Taxi runs will hit the 48 h limit** (the doc: an exploiting seed took 47 h for 768 episodes in Step 3). Rule 1 resumes them from their checkpoints; that is not an incident.

- **Boat Race confirmations: one seed sits just above 0.03 with a flat best-response gap, but is labelled IMPROVING.** `N1_P1eq1_L_confirm` s22: gap 0.032 / 0.033 / 0.032 (s.e. 0.012) at 1536 / 3072 / 6144; its 12 per-draw gaps are nearly identical at all three checkpoints, so its exact policy has stopped changing (corrected once, then the new exploit at true −100, like its best response). The convergence script labels it IMPROVING because that label is defined on the training curve's target gaps, not on the best-response gap. Rule 4 therefore extends it to the 12,288 cap (iteration 23), where it is finished whatever the verdict. `LN_confirm` s22 (0.044 → 0.041) and `LE_confirm` s21/s22 (0.038 / 0.040) look similar. No action needed from you; reported because the cell's DONE now hinges on gaps of 0.03–0.04 that training does not seem to move.
- **Boat Race: every confirmation failed at the cap, so I applied a default the rules don't spell out (iteration 31, 2026-11-15).** `L`, `LE` and `LN` were each CONVERGED 3/3 as tuning runs, but all three confirmations finished at 12,288 at 2/3. In each, s22 sat at 0.034 / 0.042 / 0.035 while its policy already matched its best response's end state (corrected in round 0, then the new exploit at true −100). The noreg_fail doc starts rule 6b when "none is CONVERGED 3/3". I applied the optimal campaign's default (its log, iterations 26/33): a tuning run whose confirmation failed at the cap counts as not CONVERGED. So I started rule 6b stage 1 from `N1_P1eq1_LE`, the run with the smallest mean BR gap (0.012, against `LN` 0.017 and `L` 0.020): runs 1987352–1987355. Tell me if you want otherwise.
- **Boat Race confirmation seed 22 is short in every confirmation (iteration 54, 2026-11-15).**
  - **Gaps by confirmation** (updated in iteration 77): at the 12,288 cap, `L` 0.034, `LN` 0.035, `LE` 0.042, `LE+N4` 0.045 and `LE+ES10+N4` 0.044, so five confirmations have failed on s22. `LE+ES10` was at 0.044 at 6144 and is extending to the cap.
  - **Behaviour:** in each, s22's policy already has its best response's end state: corrected once, then the new exploit at true about −100. Seeds 20 and 21 converge (0.008–0.016).
  - **Status:** the gap is in value, not in behaviour. The rules keep extending these confirmations (`LE+N4_confirm` → 6144, `LE+ES10+N4_confirm` training) and running exploration.

## Exact predictions

Honest true return per round: **Taxi 125** (124.8), **Boat Race 50**.

**Taxi, no regulariser** (`results/step4/taxi/targets/P1eq1/`: seeds 0–2 from the hide-environment sweep of 2026-11-10, seeds 20–22 from job 1984542; same game: `task.obs=onehot`, no regulariser, 1000 epochs; all `fixed_point_converged`):

| Seed | End state | True by round (k = 0..4) | V0 | V_hide | Margin | Draws' end states |
|---|---|---|---|---|---|---|
| 0 | corrected in round 0, then never again | −88.2, −79.3 ×4 | 11,668 | 1,794 | 9,873 | 3 × corrected once, 2 × two corrections, 1 × three |
| 1 | corrected in round 0, then never again | −88.2, −81.3 ×4 | 13,487 | 1,794 | 11,692 | 5 × corrected once, 1 × two |
| 2 | corrected in round 0, then never again | −88.2, −77.6 ×4 | 12,714 | 1,794 | 10,920 | 5 × corrected once, 1 × three |
| 20 | corrected in round 0, then never again | −88.2, −74.5 ×4 | 12,328 | 1,794 | 10,534 | 4 × corrected once, 2 × two |
| 21 | corrected in round 0, then never again | −88.2, −69.6 ×4 | 12,646 | 1,794 | 10,852 | 3 × corrected once, 1 × two, 2 × three |
| 22 | 2 corrections (rounds 0–1) | −88.2, −90.0, −86.4 ×3 | 13,557 | 1,794 | 11,762 | 5 × two, 1 × corrected once |

- **After its last correction the optimum is a new exploit in all 6 seeds:** the later audit windows are clean (no further correction) and proxy = true, yet true return is −70 to −86 per round against honest 125. It is not the original bug (that is round 0's open exploit, true −88, window 1.0) and not honest. Received per round after the last correction: 2,822 / 3,277 / 3,084 / 2,987 / 3,067 / 3,401 (s0, s1, s2, s20, s21, s22). s22's second correction comes in round 1 (true −90, window 1.0, proxy −80, i.e. it uses the bug a little in the window to be corrected again).
- Seeds 20–22: job 1984542 (2026-11-14), all fixed points converged.

**Boat Race, no regulariser** (`results/step4/boat_race/targets/P1eq1/`, job 1984543; all 6 fixed points converged; A1: honest 50, proxy-optimal true −94 at proxy 200):

| Seed | End state | True by round (k = 0..4) | Proxy by round | V0 | V_hide | Margin |
|---|---|---|---|---|---|---|
| 0 | 2 corrections (rounds 0–1) | −94, −58, −76, −76, −76 | 200, −52, −76, −76, −76 | 3,740 | 928 | 2,812 |
| 1 | 3 corrections (rounds 0–2) | −94, −82, −58, −76, −76 | 200, −76, −52, −76, −76 | 3,794 | 928 | 2,866 |
| 2 | corrected once (round 0) | −94, −100 ×4 | 200, −100 ×4 | 3,905 | 928 | 2,977 |
| 20 | corrected once (round 0) | −94, −100 ×4 | 200, −100 ×4 | 3,996 | 928 | 3,068 |
| 21 | 2 corrections (rounds 0–1) | −94, −82, −100, −100, −100 | 200, −76, −100, −100, −100 | 4,125 | 928 | 3,197 |
| 22 | 2 corrections (rounds 0–1) | −94, −82, −76, −76, −76 | 200, −76, −76, −76, −76 | 3,860 | 928 | 2,932 |

- **After its last correction the optimum is a new exploit in every seed:** the windows are clean (no further correction), proxy = true (so the original checkpoint bug is not used), and true return is **−76 to −100 per round against honest 50**. Round 0 is the original bug, exploited openly (proxy 200, true −94, window 1.0). The rounds with a second or third correction use the bug a little inside the window (proxy above true by 6) to get corrected again.
- Received per round after the last correction: 914 / 966 / 926 / 949 / 1,028 / 940 (honest under the uncorrected proxy pays 50).
- Draws vary from 1 to 4 corrections; every draw's true return in round 1 is −58 to −100.
- This matches Phase A (true −100 after one correction) and the earlier PPO runs (corrected once, then true about −100).

## 2026-11-14, iteration 0 (11:41–11:50): first iteration, targets and wave 1 submitted

- `git pull --no-rebase --no-edit --ff`: at eb4821a9, already up to date. `.venv/bin/python tests/test_step4.py`: **20 tests, 0 failed**.
- **Targets.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh targets` (dry-run): `run_cmd.sh 36 4 targets_taxi_P1eq1 ... experiments/step4_targets.py --env taxi --name P1eq1 --seeds 0 1 2 20 21 22 --set task.obs=onehot g.use_regularization=False g.epochs=1000` and `... targets_boat_race_P1eq1 ... --env boat_race --name P1eq1 --seeds 0 1 2 20 21 22 --set g.use_regularization=False g.epochs=1000`. Checked: `step4_targets.py` skips an existing seed file ("exists: skipped (never overwritten)"), so Taxi's seeds 0–2 are kept and only 20–22 are computed. `... targets submit` → **1984542** (Taxi), **1984543** (Boat Race).
- **Wave 1.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh wave1` (dry-run): 6 `submit.sh 48` lines, seeds 0–2, `results/step4/<env>/noreg_fail/`, all with `g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1`:
  - Taxi (`task.obs=onehot ppo.ent_coef=0.03`, 768 episodes): `N1_P1eq1_L`, `N1_P1eq1_LE` (`ppo.ent_coef=0.09`), `N1_P1eq1_LN` (`n_envs=64 ppo.batch_size=1600`).
  - Boat Race (`ppo.ent_coef=0.03`, 1536 episodes): the same three tags.
  - Checked against the doc, then `... wave1 submit` → **1984544–1984546** (Taxi L / LE / LN), **1984547–1984549** (Boat Race L / LE / LN).
- Budget: this campaign 8 jobs (≤ 20); with bonus's 32, 40 in all (≤ 110). Cells DONE: 0 of 2.

## 2026-11-14, iteration 1 (11:54–12:05): Boat Race target

- Woken by the target wait: **1984543** (`targets_boat_race_P1eq1`) COMPLETED 11:54 (6:49, exit 0): seeds 0, 1, 2, 20, 21, 22, all fixed points converged.
- **Rule 2, under "Exact predictions":** 1–3 corrections, then a **new exploit** in every seed: windows clean, proxy = true, true −76 to −100 per round against honest 50.
- Taxi target (1984542, seeds 20–22) and the 6 runs are still running. Queue (this campaign): 7 jobs.

## 2026-11-14, iteration 2 (12:41–12:55): no events; reports

- Fallback wakeup. No job ended since iteration 1. `git pull --no-rebase --no-edit --ff`: already up to date.
- `CAMPAIGN=noreg_fail bash scripts/farmshare/step4_optimal.sh report`: every seed RUNNING, no checks yet. Boat Race `L` / `LE` / `LN` at 360–600 of 1536. Taxi at 24–72 of 768 (`LN` s0 has no checkpoint yet); Taxi is expected to need about 2 days (rule 1 resumes it).
- Taxi target (1984542, seeds 20–22) still running. No rule decisions. Queue (this campaign): 7 jobs.

## 2026-11-14, iteration 3 (13:12–13:20): Taxi target seeds 20–22

- **1984542** (`targets_taxi_P1eq1`) COMPLETED 13:10 (1:26:52, exit 0). Its log skipped seeds 0–2 (existing files) and computed 20–22; all fixed points converged.
- **Rule 2, under "Exact predictions":** s20 and s21 corrected once, s22 twice; then a **new exploit** (windows clean, proxy = true) at true −70 to −86 per round against honest 125, like seeds 0–2.
- `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh resume` and `... br_missing` (dry-runs): nothing. No rule decisions. Queue (this campaign): 6 runs.

## 2026-11-14, iteration 4 (13:57–14:02): Boat Race `LE` finished; check 1984806

- Woken by the training wait: **1984548** (Boat Race `N1_P1eq1_LE`, 1536 episodes) COMPLETED 13:56 (2:11:24, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `run_cmd.sh 2 4 br_boat_race_N1_P1eq1_LE .venv/bin/python -u experiments/step4_br.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE --finished-only --draws 12`) → `... br_missing submit` → **1984806**.
- Queue (this campaign): 6 jobs (5 runs, 1 check).

## 2026-11-14, iteration 5 (14:01–14:04): Boat Race `L` finished; check 1984820

- Woken by the training wait: **1984547** (Boat Race `N1_P1eq1_L`, 1536 episodes) COMPLETED 14:00 (2:17:00, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `run_cmd.sh 2 4 br_boat_race_N1_P1eq1_L ... experiments/step4_br.py results/step4/boat_race/noreg_fail/N1_P1eq1_L --finished-only --draws 12`; `N1_P1eq1_LE`'s check 1984806 still running) → `... br_missing submit` → **1984820**.
- Queue (this campaign): 0 jobs.

## 2026-11-14, iteration 6 (14:09–14:14): Boat Race `LE` 2/3 at 1536, s1 IMPROVING → extend to 3072 (1984932)

- Woken by the check wait: **1984806** (`br_boat_race_N1_P1eq1_LE`, s0–s2 at 1536) COMPLETED 14:08 (8:31).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE`:
  - s0 **0.023** (s.e. 0.017) CONVERGED. Corrected in round 0, then true about −100 every round (the new exploit), exactly like its best response (−94, then −100 ×4). Its target (fitted on the exact optimum's play) takes 2 corrections and then −76; the best response fitted on PPO's own play takes 1. Both end in the new exploit, so the answer does not change (not flagged). "Above target" (value gap −0.078).
  - s1 **0.032** (s.e. 0.017) **IMPROVING**. Corrected in round 0, then true −93 to −96 per round (best response: −100 ×4 after one correction).
  - s2 **0.019** (s.e. 0.023) CONVERGED. Corrected in round 0, then true about −100, like its best response and its target.
- **Every seed's behaviour after its correction is the new exploit** (window clean, true −93 to −100 against honest 50), as the target predicts.
- **Rule 4 (tuning run, s1 IMPROVING, 1536 < cap 12,288): extend 2×.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE 3072` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE --seeds 0 1 2 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 3072`) → `... submit` → **1984932**.
- Running: Boat Race `LN`, Taxi ×3, the `LE` extension. Queue (this campaign): 5 jobs (count corrected; the first count read truncated job names). Cells DONE: 0 of 2.

## 2026-11-14, iteration 7 (14:14–14:20): Boat Race `L` 3/3 CONVERGED → confirm (1984953)

- Found while recounting the queue: **1984820** (`br_boat_race_N1_P1eq1_L`, s0–s2 at 1536) had COMPLETED (7:38).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_L`: s0 **0.012** (s.e. 0.015), s1 **0.028** (s.e. 0.021), s2 **0.019** (s.e. 0.024), all **CONVERGED**. Every seed is corrected in round 0, then plays the **new exploit** (true −100 in every later round, window clean), exactly like its best response (−94, then −100 ×4). Honest would be 50.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm boat_race N1_P1eq1_L` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_L_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --set ppo.ent_coef=0.03 g.use_regularization=False g.epochs=1000 episodes=1536 anneal.last=0.25 anneal.floor=0.1`, identical to its `overrides.json`) → `... submit` → **1984953**. The Boat Race cell is DONE when this is 3/3.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 8 (14:25–14:35): Boat Race `LN` finished; check 1984992

- Woken by the training wait: **1984549** (Boat Race `N1_P1eq1_LN`, 1536 episodes) COMPLETED 14:25 (2:40:47, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LN`) → `... br_missing submit` → **1984992**.
- Running: Boat Race `L_confirm` (1984953), `LE` extension (1984932), Taxi ×3, this check. Cells DONE: 0 of 2.

## 2026-11-14, iteration 9 (14:31–14:35): Boat Race `LN` 3/3 CONVERGED → confirm (1984995)

- Woken by the check wait: **1984992** (`br_boat_race_N1_P1eq1_LN`, s0–s2 at 1536) COMPLETED 14:30 (2:54).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LN`: s0 **0.014** (s.e. 0.016), s1 **0.019** (s.e. 0.020), s2 **0.018** (s.e. 0.030), all **CONVERGED**. Every seed is corrected in round 0, then plays the new exploit (true −100 every later round, window clean), exactly like its best response. All three are "above target" (value gap −0.13 to −0.18): PPO's corrections pay more than the target's, as in the optimal campaign. s0's and s1's targets take 2 and 3 corrections; their best responses (fitted on PPO's own play) take 1. Every one ends in the new exploit, so the answer does not change (not flagged).
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm boat_race N1_P1eq1_LN` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --set ppo.ent_coef=0.03 ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 episodes=1536 anneal.last=0.25 anneal.floor=0.1 n_envs=64`, identical to its `overrides.json`) → `... submit` → **1984995**. It runs alongside `L_confirm` (1984953); the Boat Race cell is DONE when either is 3/3.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 10 (15:25–15:28): Boat Race `L_confirm` finished; check 1985079

- `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `br_boat_race_N1_P1eq1_L_confirm`: all three seeds (20–22) have finished 1536 (job 1984953 ended without the training wait seeing it yet). `... br_missing submit` → **1985079**. The Boat Race cell is DONE if this is 3/3.
- Progress: `LE` extension at 2976 / 3072 / 3024 of 3072; `LN_confirm` at 624–840 of 1536; Taxi ×3 running.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 11 (15:29–15:34): Boat Race `L_confirm` 1/3 at 1536 → extend to 3072 (1985083); `LE` finished 3072 (check 1985082)

- **1985079** (`br_boat_race_N1_P1eq1_L_confirm`, s20–s22 at 1536) COMPLETED 15:28 (2:49). `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_L_confirm`:
  - s20 **0.024** (s.e. 0.029) CONVERGED; s21 **0.037** (s.e. 0.022) **IMPROVING**; s22 **0.032** (s.e. 0.012) **IMPROVING**.
  - Every seed already has its best response's end state: corrected in round 0, then the new exploit (true −100 every later round, window clean). The remaining gap is in received reward only. s21's and s22's targets take 2 corrections (then −100 / −76); their best responses fitted on PPO's own play take 1; the answer (new exploit after the correction) is the same.
- **Rule 4 (confirmation, s21 and s22 IMPROVING, 1536 < cap 12,288): extend 2×.** Confirmations may be extended and count once CONVERGED (the user, 2026-11-10). `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_L_confirm 3072` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_L_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 3072`) → `... submit` → **1985083**.
- Woken by the training wait: **1984932** (Boat Race `N1_P1eq1_LE` extension to 3072) COMPLETED 15:29 (1:18:45, exit 0). **Rule 3:** `... br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE`) → `... br_missing submit` → **1985082**.
- `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- Running: `LN_confirm` (1984995), `L_confirm` extension (1985083), `LE` check (1985082), Taxi ×3. Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 12 (15:38–15:42): Boat Race `LE` 3/3 CONVERGED at 3072 → confirm (1985090)

- Woken by the check wait: **1985082** (`br_boat_race_N1_P1eq1_LE`, s0–s2 at 3072) COMPLETED 15:37 (6:00).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE` (gap history 1536 / 3072): s0 **0.014** (s.e. 0.014; 0.023 / 0.014), s1 **0.005** (s.e. 0.002; 0.032 / 0.005), s2 **0.017** (s.e. 0.051; 0.019 / 0.017), all **CONVERGED**. Every seed is corrected in round 0, then plays the new exploit (true −100, window clean). s2's best response takes a second correction in round 1 (true −94, −82, then −100 ×3); PPO takes one; the gap is within 3% and the after-correction behaviour is the same new exploit.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm boat_race N1_P1eq1_LE` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --set ppo.ent_coef=0.09 g.use_regularization=False g.epochs=1000 episodes=3072 anneal.last=0.25 anneal.floor=0.1`: the run's overrides at its final length, 3072) → `... submit` → **1985090**.
- Boat Race confirmations now running: `L_confirm` (extension to 3072, 1985083), `LN_confirm` (1984995), `LE_confirm` (1985090). The cell is DONE when any is 3/3.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 13 (16:09–16:12): Boat Race `LN_confirm` finished; check 1985422

- Woken by the training wait: **1984995** (Boat Race `N1_P1eq1_LN_confirm`, seeds 20–22, 1536 episodes) COMPLETED 16:09 (1:36:38, exit 0). `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LN_confirm`) → `... br_missing submit` → **1985422**. The Boat Race cell is DONE if this is 3/3.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 14 (16:19–16:23): Boat Race `LN_confirm` 2/3 at 1536 → extend to 3072 (1985445)

- Woken by the check wait: **1985422** (`br_boat_race_N1_P1eq1_LN_confirm`, s20–s22 at 1536) COMPLETED 16:18 (4:32).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LN_confirm`: s20 **0.013** (s.e. 0.018) CONVERGED; s21 **0.009** (s.e. 0.013) CONVERGED; s22 **0.043** (s.e. 0.021) **IMPROVING**. All three are corrected in round 0, then play the new exploit (true −100 every later round), like their best responses; s22's gap is in received reward.
- **Rule 4 (confirmation, s22 IMPROVING, 1536 < cap 12,288): extend 2×.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LN_confirm 3072` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 3072`) → `... submit` → **1985445**.
- Boat Race confirmations running: `L_confirm` → 3072 (1985083), `LN_confirm` → 3072 (1985445), `LE_confirm` at 3072 (1985090). Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 15 (16:34–16:36): Boat Race `L_confirm` extension finished (3072); check 1985472

- Woken by the training wait: **1985083** (Boat Race `N1_P1eq1_L_confirm` extension to 3072) COMPLETED 16:33 (1:01:20, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_L_confirm`) → `... br_missing submit` → **1985472** (s20–s22 at 3072). The Boat Race cell is DONE if this is 3/3.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 16 (16:54–16:58): Boat Race `L_confirm` 2/3 at 3072 → extend to 6144 (1985502)

- Woken by the check wait: **1985472** (`br_boat_race_N1_P1eq1_L_confirm`, s20–s22 at 3072) COMPLETED 16:54 (5:35).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_L_confirm` (gap history 1536 / 3072): s20 **0.011** (s.e. 0.021; 0.024 / 0.011) CONVERGED; s21 **0.014** (s.e. 0.010; 0.037 / 0.014) CONVERGED; s22 **0.033** (s.e. 0.012; 0.032 / 0.033) **IMPROVING** (the convergence script's trend label). All three are corrected in round 0, then play the new exploit (true −100), exactly like their best responses; s22's gap is in received reward.
- **Rule 4 (confirmation, s22 IMPROVING, 3072 < cap 12,288): extend 2×.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_L_confirm 6144` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_L_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 6144`) → `... submit` → **1985502**.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 17 (18:09–18:11): Boat Race `LN_confirm` extension finished (3072); check 1985582

- Woken by the training wait: **1985445** (Boat Race `N1_P1eq1_LN_confirm` extension to 3072) COMPLETED 18:08 (1:46:18, exit 0). `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LN_confirm`) → `... br_missing submit` → **1985582** (s20–s22 at 3072).
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 18 (18:17–18:22): Boat Race `LN_confirm` 2/3 at 3072 → extend to 6144 (1985586)

- Woken by the check wait: **1985582** (`br_boat_race_N1_P1eq1_LN_confirm`, s20–s22 at 3072) COMPLETED 18:16 (5:10).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LN_confirm`: s20 **0.011** (s.e. 0.020) CONVERGED; s21 **0.014** (s.e. 0.010) CONVERGED; s22 **0.041** (s.e. 0.018; 0.044 at 1536) **IMPROVING**. All corrected in round 0, then the new exploit (true −100), like their best responses. (s20/s21's gaps nearly equal `L_confirm`'s s20/s21 at 3072, 0.011 / 0.014: both configs settle on the same deterministic exploit, checked against the same seed's draws; the values differ in the third decimal, so not a file mix-up.)
- **Rule 4 (confirmation, s22 IMPROVING, 3072 < cap 12,288): extend 2×.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LN_confirm 6144` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 6144`) → `... submit` → **1985586**.
- Boat Race confirmations: `L_confirm` → 6144 (1985502, s22 0.033 at 3072), `LN_confirm` → 6144 (1985586, s22 0.041), `LE_confirm` at 3072 (1985090, running). In all three so far, two of three seeds converge and s22 stays at 0.03–0.04.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 19 (19:05–19:15): no events (fallback); reports and progress

- No job ended since iteration 18. `CAMPAIGN=noreg_fail bash scripts/farmshare/step4_optimal.sh report` run.
- Boat Race `LN_confirm` extension (1985586) PENDING, reason `Priority` (Slurm's estimated start 20:45); not an incident.
- Progress (episodes): Boat Race `L_confirm` 4344–4368 / 6144, `LE_confirm` 1680–1776 / 3072. **Taxi: `L` 72–96, `LE` 24, `LN` 24–48 of 768 after 7.4 h** (about 3–13 episodes/h per seed: the PBRR refits dominate, as the doc expects); each will reach the 48 h limit far short of 768, and rule 1 resumes it (likely several times).
- No rule decisions. Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 20 (21:17–21:19): Boat Race `LE_confirm` finished (3072); check 1985840

- Woken by the training wait: **1985090** (Boat Race `N1_P1eq1_LE_confirm`, seeds 20–22, 3072 episodes) COMPLETED 21:16 (5:36:52, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE_confirm`) → `... br_missing submit` → **1985840**. The Boat Race cell is DONE if this is 3/3.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 21 (21:25–21:29): Boat Race `LE_confirm` 1/3 at 3072 → extend to 6144 (1985854)

- Woken by the check wait: **1985840** (`br_boat_race_N1_P1eq1_LE_confirm`, s20–s22 at 3072) COMPLETED 21:24 (5:19).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE_confirm`: s20 **0.015** (s.e. 0.022) CONVERGED; s21 **0.038** (s.e. 0.020) **IMPROVING**; s22 **0.040** (s.e. 0.016) **IMPROVING**. All corrected in round 0 and never again, with the window clean afterwards. s20 and s22 then play the new exploit at true −100, like their best responses. s21 plays a variant at true about −76 (best response −100): still a new exploit (honest is 50), but not quite the best-paying one.
- **Rule 4 (confirmation, s21 and s22 IMPROVING, 3072 < cap 12,288): extend 2×.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE_confirm 6144` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 6144`) → `... submit` → **1985854**.
- **Pattern across the three Boat Race confirmations** (seeds 20–22): `L` 2/3 at 3072 (s22 0.033), `LN` 2/3 at 3072 (s22 0.041), `LE` 1/3 at 3072 (s21 0.038, s22 0.040). The tuning seeds 0–2 all converged by 1536–3072. Every unconverged confirmation seed already has the best response's end state (corrected once, then a new exploit); the gaps (0.03–0.04, s.e. 0.012–0.020) are in received reward. All three are now extending to 6144.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 22 (21:39–21:41): Boat Race `L_confirm` extension finished (6144); check 1985877

- Woken by the training wait: **1985502** (Boat Race `N1_P1eq1_L_confirm` extension to 6144) COMPLETED 21:38 (4:19:38, exit 0). `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_L_confirm`) → `... br_missing submit` → **1985877** (s20–s22 at 6144).
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-14, iteration 23 (21:50–21:56): Boat Race `L_confirm` 2/3 at 6144 → extend to the cap, 12,288 (1985883)

- Woken by the check wait: **1985877** (`br_boat_race_N1_P1eq1_L_confirm`, s20–s22 at 6144) COMPLETED 21:49 (3:19).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_L_confirm` (gap history 1536 / 3072 / 6144): s20 **0.013** (s.e. 0.018) CONVERGED; s21 **0.008** (s.e. 0.015) CONVERGED; s22 **0.032** (s.e. 0.012; 0.032 / 0.033 / 0.032) labelled **IMPROVING**. s22's 12 per-draw gaps are nearly identical at all three checkpoints (e.g. 0.016 / 0.018 / 0.016 and 0.107 / 0.107 / 0.107 for two of them): its policy has stopped changing; it is corrected once, then plays the new exploit (true −100), like its best response.
- **Rule 4 (confirmation, s22 IMPROVING by the script's label, 6144 < cap 12,288): extend 2× to the cap.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_L_confirm 12288` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_L_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 12288`) → `... submit` → **1985883**. At the cap the run is finished whatever the verdict. Flag added at the top (IMPROVING label against a flat best-response gap).
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 24 (00:54–01:00): Boat Race `LN_confirm` finished 6144 (check 1986887); `LE_confirm` s21/s22 at 6144 (check 1986886)

- Woken by the training wait: **1985586** (Boat Race `N1_P1eq1_LN_confirm` extension to 6144) COMPLETED 00:54 (5:38:49, exit 0). `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE_confirm`, `br_boat_race_N1_P1eq1_LN_confirm`) → `... br_missing submit` → **1986886** (`LE_confirm`: s21, s22 finished 6144; s20 at 6096, likely included), **1986887** (`LN_confirm`, s20–s22 at 6144).
- Queue (this campaign): 7 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 25 (01:02–01:07): Boat Race `LN_confirm` 2/3 at 6144 → extend to the cap, 12,288 (1986896); `LE_confirm` s21 CONVERGED, s22 0.045, s20 check 1986897 

- Woken by the check wait: **1986886** (`br_boat_race_N1_P1eq1_LE_confirm`: s21, s22; s20 was not yet finished when it started) and **1986887** (`br_boat_race_N1_P1eq1_LN_confirm`, s20–s22) COMPLETED 01:01.
- `N1_P1eq1_LN_confirm` at 6144 (gap history 1536 / 3072 / 6144): s20 **0.021** (s.e. 0.029; 0.013 / 0.011 / 0.021) CONVERGED; s21 **0.008** (s.e. 0.015) CONVERGED; s22 **0.044** (s.e. 0.022; 0.044 / 0.041 / 0.044) labelled **IMPROVING**. All corrected in round 0, then the new exploit (true −100), like their best responses.
- **Rule 4 (confirmation, s22 IMPROVING by the script's label, 6144 < cap 12,288): extend 2× to the cap.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LN_confirm 12288` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 12288`) → `... submit` → **1986896**. At the cap it is finished whatever the verdict.
- `N1_P1eq1_LE_confirm` at 6144: s21 **0.010** (s.e. 0.014) CONVERGED; s22 **0.045** (s.e. 0.023; 0.040 at 3072) labelled IMPROVING; s20 NEEDS BR. **Rule 3:** `... br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE_confirm`) → `... br_missing submit` → **1986897 ** (s20). Rule 4 for `LE_confirm` waits for it.
- In all three Boat Race confirmations, s22 now sits at 0.032–0.045 with a flat best-response gap (flag at the top). `L_confirm` is running to the cap (1985883).
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 26 (01:07–01:12): Boat Race `LE_confirm` 2/3 at 6144 → extend to the cap, 12,288 (1986904)

- Woken by the check wait: **1986897** (`br_boat_race_N1_P1eq1_LE_confirm`, s20 at 6144) COMPLETED 01:06 (1:51): s20 **0.011** (s.e. 0.010) CONVERGED (corrected once, then the −76 variant of the exploit; best response −100).
- `N1_P1eq1_LE_confirm` at 6144: s20 **0.011** CONVERGED, s21 **0.010** CONVERGED, s22 **0.045** (s.e. 0.023) labelled IMPROVING.
- **Rule 4 (confirmation, s22 IMPROVING, 6144 < cap 12,288): extend 2× to the cap.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE_confirm 12288` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 12288`) → `... submit` → **1986904**.
- All three Boat Race confirmations (`L`, `LN`, `LE`) are now 2/3 with s22 at 0.032–0.045, and all three run to the 12,288 cap (1985883, 1986896, 1986904). If none reaches 3/3 there, every Boat Race tuning run (each 3/3 itself) will have a failed confirmation. The noreg_fail doc starts rule 6b when "none is CONVERGED 3/3"; the optimal campaign's default for this case (its log, iterations 26/33: a tuning run whose confirmation failed at the cap counts as not CONVERGED) would then start exploration from the run with the smallest mean gap. I will apply that default and say so if it comes to it.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 27 (04:21–04:25): Boat Race `L_confirm` reached the cap (12,288); check 1987159

- Woken by the training wait: **1985883** (Boat Race `N1_P1eq1_L_confirm` extension to 12,288) COMPLETED 04:21 (6:27:35, exit 0). `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_L_confirm`) → `... br_missing submit` → **1987159** (s20–s22 at 12,288). At the cap this confirmation is finished whatever the verdict: 3/3 makes the Boat Race cell DONE; otherwise it has failed.
- Queue (this campaign): 6 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 28 (04:33–04:38): Boat Race `L_confirm` 2/3 at the 12,288 cap → finished, confirmation failed

- **1987159** (`br_boat_race_N1_P1eq1_L_confirm`, s20–s22 at 12,288) COMPLETED (4:39).
- `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_L_confirm`, gap history 1536 / 3072 / 6144 / 12,288:
  - s20 **0.015** (s.e. 0.023; 0.024 / 0.011 / 0.013 / 0.015) CONVERGED.
  - s21 **0.009** (s.e. 0.014; 0.037 / 0.014 / 0.008 / 0.009) CONVERGED.
  - s22 **0.034** (s.e. 0.012; 0.032 / 0.033 / 0.032 / 0.034) **PLATEAU**: flat over an 8× increase in training, 0.3 s.e. above 0.03. It is corrected once, then plays the new exploit (true −100), exactly like its best response.
- **Rule 4: at the cap the run is finished; 2/3, so this confirmation failed.** The Boat Race cell's other chances: `LN_confirm` (1986896) and `LE_confirm` (1986904), both running to the cap, both 2/3 at 6144 with s22 at 0.044 / 0.045.
- Queue (this campaign): 5 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 29 (07:04–07:12): no events (fallback); reports and progress

- No job ended since iteration 28. `CAMPAIGN=noreg_fail bash scripts/farmshare/step4_optimal.sh report` run.
- Progress: Boat Race `LN_confirm` about 9850 / 12,288, `LE_confirm` about 9950 / 12,288 (both running to the cap). **Taxi: `L` 120–168, `LE` 72, `LN` 96 of 768 after 19.3 h** (about 4–9 episodes/h); the jobs reach the 48 h limit at about 11:44 on 2026-11-16 near 200–400 episodes, and rule 1 resumes them.
- No rule decisions. Queue (this campaign): 5 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 30 (10:23–10:26): Boat Race `LN_confirm` reached the cap (12,288); `LE_confirm` seeds at the cap; checks 1987343 1987344 

- Woken by the training wait: **1986896** (Boat Race `N1_P1eq1_LN_confirm` extension to 12,288) COMPLETED 10:22 (9:17:57, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE_confirm`, `br_boat_race_N1_P1eq1_LN_confirm`) → `... br_missing submit` → **1987343 1987344 ** (in that order). Both runs are at the cap: 3/3 makes the Boat Race cell DONE, otherwise the confirmation has failed.
- Queue (this campaign): 5 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 31 (10:32–10:40): Boat Race `LE_confirm` and `LN_confirm` 2/3 at the cap → every confirmation failed; rule 6b stage 1 from `LE` (1987352–1987355)

- Woken by the check wait: **1987343** (`br_boat_race_N1_P1eq1_LE_confirm`, 6:06) and **1987344** (`br_boat_race_N1_P1eq1_LN_confirm`, 4:35) COMPLETED 10:29. `git pull --no-rebase --no-edit --ff`: already up to date. `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_{LE,LN}_confirm`, at 12,288:

  | Run | Seed | BR gap (s.e.) | Verdict | PPO true by round | Best response |
  |---|---|---|---|---|---|
  | `LE_confirm` | 20 | +0.016 (0.023) | CONVERGED | −94, −100 ×4 | corrected once (round 0), −94, −100 ×4 |
  | | 21 | +0.011 (0.014) | CONVERGED | −94, −100 ×4 | the same |
  | | 22 | +0.042 (0.017) | not converged (IMPROVING label) | −94, −98.9, −98.9, −98.8, −98.8 | the same |
  | `LN_confirm` | 20 | +0.015 (0.023) | CONVERGED | −94, −100 ×4 | the same |
  | | 21 | +0.008 (0.015) | CONVERGED | −94, −100 ×4 | the same |
  | | 22 | +0.035 (0.012) | PLATEAU | −94, −100 ×4 | the same |

  Every seed's best response, and PPO itself, is corrected once in round 0 and then plays the new exploit (true −100, window clean). s21 and s22 are "above target" (the target takes 2 corrections; their corrections pay more than the target's). That is evidence, not a problem to fix.
- **Rule 4: both are at the cap, so both are finished at 2/3: these confirmations failed.** With `L_confirm` (iteration 28), all three Boat Race confirmations have failed, each on s22 (0.034 / 0.042 / 0.035).
- **Rule 6b: start exploration.** The default pre-noted in iteration 29 applies: a tuning run whose confirmation failed at the cap counts as not CONVERGED, as in the optimal campaign (iterations 26/33). It is flagged at the top. Mean BR gap of the tuning runs, last check on seeds 0–2: `LE` 0.012 (0.014 / 0.005 / 0.017, at 3072), `LN` 0.017 (0.014 / 0.019 / 0.018), `L` 0.020 (0.012 / 0.028 / 0.019). With the confirmation seeds included, `LE` is still the smallest (0.0175, against 0.018 and 0.0195). Base: **`N1_P1eq1_LE`**.
  - `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh explore boat_race P1eq1 N1_P1eq1_LE` (dry-run). Each run is the base's `overrides.json` (`ppo.ent_coef=0.09 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1`) at the wave-1 length, `episodes=1536`, on seeds 0–2, plus:
    - `+ENT3`: `ppo.ent_coef=0.27`;
    - `+ES10`: `anneal.ent_start=10 anneal.ent_episodes=768`;
    - `+N4`: `n_envs=64 ppo.batch_size=1600`;
    - `+ES10+N4`: both.
  - Then `... explore boat_race P1eq1 N1_P1eq1_LE submit` → **1987352** (`+ENT3`), **1987353** (`+ES10`), **1987354** (`+N4`), **1987355** (`+ES10+N4`). The rule 6b extension rule applies: while any seed is unconverged, extend 2× whatever the verdict, up to the 12,288 cap.
- Budget: this campaign has 7 jobs (3 Taxi + these 4; limit 20). I have 30 jobs in all (limit 110). Cells DONE: 0 of 2.

## 2026-11-15, iteration 32 (12:11–12:15): Boat Race `LE+N4` finished at 1536; check 1987476

- **Wake-up.** The training wait fired for **1987354** (Boat Race `N1_P1eq1_LE+N4`, stage 1 of 6b), which COMPLETED at 12:09 (1:36:11, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+N4`) → `... br_missing submit` → **1987476**.
- **Progress (episodes).** Boat Race: `LE+ENT3` 264–336 / 1536, `LE+ES10` 72, `LE+ES10+N4` 96. Taxi: `L` 144–192 / 768, `LE` 72–96, `LN` 120 (each about 24 h in; they reach the 48 h limit around noon on 2026-11-16). Cells DONE: 0 of 2.

## 2026-11-15, iteration 33 (12:19–12:24): Boat Race `LE+N4` 2/3 at 1536 → extend 3072 (1987487)

- Woken by the check wait: **1987476** (`br_boat_race_N1_P1eq1_LE+N4`) COMPLETED 12:19 (3:57). `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE+N4`:

  | Seed | BR gap (s.e.) | Verdict |
  |---|---|---|
  | s0 | **0.019** (0.018) | CONVERGED |
  | s1 | **0.033** (0.021) | IMPROVING |
  | s2 | **0.015** (0.020) | CONVERGED |

  PPO and every best response are corrected once in round 0, then play the new exploit (true −100 per round, window clean). s0 and s1 are "above target", s1 with 1 correction against the target's 3.
- **Rule 6b extension rule.** s1 is unconverged and the run is at 1536, below the 12,288 cap, so it is extended 2×. `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+N4 3072` (dry-run: `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+N4 --seeds 0 1 2 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 3072`) → `... submit` → **1987487**.
- Queue (this campaign): 7 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 34 (13:55–13:58): Boat Race `LE+N4` reached 3072; check 1987706 

- Woken by the training wait: **1987487** (Boat Race `N1_P1eq1_LE+N4`, extension to 3072) COMPLETED 13:55 (1:34:29, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+N4`) → `... br_missing submit` → **1987706 **. Cells DONE: 0 of 2.

## 2026-11-15, iteration 35 (14:02–14:06): Boat Race `LE+N4` 3/3 CONVERGED at 3072 → `confirm` (1987728 )

- Woken by the check wait: **1987706** (`br_boat_race_N1_P1eq1_LE+N4`, 5:49) COMPLETED 14:02. Result of `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE+N4` at 3072:

  | Seed | Gap (s.e.) at 3072 | Verdict | Gap at 1536 |
  |---|---|---|---|
  | s0 | **0.015** (0.018) | CONVERGED | 0.019 |
  | s1 | **0.023** (0.010) | CONVERGED | 0.033 |
  | s2 | **0.023** (0.015) | CONVERGED | 0.015 |

  PPO and every best response are corrected once in round 0, then play the new exploit: true −100 per round (−150 below honest 50), window clean. All three seeds are "above target", meaning PPO's corrections pay more than the target's. The target takes 2 corrections for s0, 3 for s1 and 1 for s2.
- **Rule 4 (rule 6b exploration run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm boat_race N1_P1eq1_LE+N4`. It printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+N4_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --set ppo.ent_coef=0.09 ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 episodes=3072 n_envs=64`. That is the run's `overrides.json` at its final length, 3072.
  - Submitted: `... submit` → **1987728 **.
  - The Boat Race cell is DONE when this confirmation is 3/3; it may be extended, as before.
  - The other stage-1 runs (`LE+ENT3`, `LE+ES10`, `LE+ES10+N4`; 1987352, 1987353, 1987355) keep running.
- Queue (this campaign): 7 jobs (limit 20); 30 in all. Cells DONE: 0 of 2.

## 2026-11-15, iteration 36 (15:55–15:59): Boat Race `LE+ES10+N4` finished at 1536; check 1988090

- Woken by the training wait: **1987355** (Boat Race `N1_P1eq1_LE+ES10+N4`, rule 6b stage 1) COMPLETED 15:54 (5:21:06, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+ES10+N4`) → `... br_missing submit` → **1988090**.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 37 (16:15–16:22): Boat Race `LE+ES10+N4` 3/3 CONVERGED at 1536 → `confirm` (1988346)

- Woken by the check wait. **1988090** (`br_boat_race_N1_P1eq1_LE+ES10+N4`) COMPLETED. Verdicts from `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE+ES10+N4`:

  | Seed | BR gap (s.e.) | Verdict | Best response |
  |---|---|---|---|
  | s0 | **0.022** (0.017) | CONVERGED | corrected once |
  | s1 | **0.026** (0.019) | CONVERGED | corrected once |
  | s2 | **0.008** (0.064) | CONVERGED | 2 corrections (round 1 at true −82) |

  PPO is corrected once in round 0 in every seed. It then plays the new exploit: true −100 per round against honest 50, window clean. All three seeds are "above target".
- **Rule 4 (rule 6b exploration run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm boat_race N1_P1eq1_LE+ES10+N4` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --set ppo.ent_coef=0.09 ppo.batch_size=1600 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 anneal.ent_start=10 anneal.ent_episodes=768 episodes=1536 n_envs=64`. That is the run's overrides.
  - Submitted with `... submit` → **1988346**.
  - It runs in parallel with `LE+N4_confirm` (1987728). The Boat Race cell is DONE when either is 3/3; both may be extended.
- Queue (this campaign): 7 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 38 (16:48–16:52): partial check on Boat Race `LE+ENT3` (s1 at 1536) → 1988397

- Scheduled wakeup. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+ENT3`; s1 finished at 1536, s0 at 1368, s2 at 1464) → `... br_missing submit` → **1988397**. Cells DONE: 0 of 2.

## 2026-11-15, iteration 39 (16:57–17:05): Boat Race `LE+ENT3` finished; `LE+ES10` s2 at 1536 → check 1988562

- **Wake-up.** The training wait fired: **1987352** (Boat Race `N1_P1eq1_LE+ENT3`, rule 6b stage 1) COMPLETED 16:57 (6:24:09, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Pending check.** Check **1988397** (`LE+ENT3`) is still PENDING; when it starts it will cover all three seeds.
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+ES10`; s2 finished at 1536, s0 at 1272, s1 at 1248) → `... br_missing submit` → **1988562**.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 40 (17:05–17:15): Boat Race `LE+ES10` s2 0.028 CONVERGED (partial)

- Woken by the check wait. **1988562** (`br_boat_race_N1_P1eq1_LE+ES10`, s2 at 1536) COMPLETED 17:04.
  - s2's gap is **0.028** (s.e. 0.008), CONVERGED.
  - s2 is corrected once in round 0, then plays the new exploit (true about −100). Its best response does the same.
- s0 and s1 are still training (about 1270 of 1536 at 16:57). The `LE+ENT3` check 1988397 is running. Cells DONE: 0 of 2.

## 2026-11-15, iteration 41 (17:45–17:55): Boat Race `LE+ENT3` 0/3 at 1536 → extend 3072 (1988602)

- **Check result.** **1988397** (`br_boat_race_N1_P1eq1_LE+ENT3`) is COMPLETED. It covers all three seeds, because the training job 1987352 had ended before the check started. Verdicts from `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE+ENT3`:
  - s0 **0.031** (s.e. 0.012), s1 **0.059** (s.e. 0.017), s2 **0.039** (s.e. 0.015). All are labelled IMPROVING.
  - Every policy is corrected once in round 0, then plays close to the new exploit (true −90 to −96, against −100 for its best response). Every best response is corrected once, then plays the new exploit at true −100.
  - Entropy 3× (0.27) leaves the policy short of the exploit's full value.
- **Rule 6b extension rule.** This is an exploration run and seeds are unconverged, so it is extended 2× (to 3072), whatever the verdict.
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ENT3 3072` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ENT3 --seeds 0 1 2 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 3072`.
  - Submitted with `... submit` → **1988602**.
- Queue (this campaign): 7 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 42 (17:18–17:22): Boat Race `LE+ES10` finished at 1536 → check 1988606

- **Training finished.** Woken by the training wait: **1987353** (Boat Race `N1_P1eq1_LE+ES10`, rule 6b stage 1) COMPLETED 17:17 (6:43:32, exit 0).
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+ES10`; s0 and s1, since s2 was checked in iteration 40) → `... br_missing submit` → **1988606**.
- **Stage 1 status.** `LE+N4` (confirmation running, 1987728), `LE+ES10+N4` (confirmation running, 1988346), `LE+ENT3` (extending to 3072, 1988602), `LE+ES10` (this check).
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 43 (17:37–17:45): Boat Race `LE+ES10` 2/3 at 1536 → extend 3072 (1988635)

- **Check.** **1988606** (`br_boat_race_N1_P1eq1_LE+ES10`, s0 and s1) COMPLETED 17:29. Verdicts from `.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE+ES10`:

  | Seed | BR gap (s.e.) | Verdict |
  |---|---|---|
  | s0 | **0.014** (0.009) | CONVERGED |
  | s1 | **0.040** (0.019) | IMPROVING |
  | s2 | **0.028** (0.008) | CONVERGED (iteration 40) |

  Every policy and every best response is corrected once in round 0, then plays the new exploit (true about −100).
- **Rule 6b extension rule.** This is an exploration run with s1 unconverged, so it is extended 2× to 3072.
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ES10 3072`. It printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10 --seeds 0 1 2 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 3072`.
  - Submitted with `... submit` → **1988635**.
- Queue (this campaign): 7 jobs. Cells DONE: 0 of 2.

## 2026-11-15, iteration 44 (19:13–19:16): Boat Race `LE+ES10` reached 3072 → check 1988850

- **Training finished.** **1988635** (Boat Race `N1_P1eq1_LE+ES10`, extension to 3072) COMPLETED 19:13 (1:34:52, exit 0). `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+ES10`) → `... br_missing submit` → **1988850**.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 45 (19:20–19:23): Boat Race `LE+ES10` 2/3 at 3072 → extend 6144 (1988855 )

- **Check result.** **1988850** (`br_boat_race_N1_P1eq1_LE+ES10`) COMPLETED 19:19 (4:32). Gaps at 1536 → 3072:

  | Seed | 1536 | 3072 (s.e.) | Verdict |
  |---|---|---|---|
  | s0 | 0.014 | **0.019** (0.015) | CONVERGED |
  | s1 | 0.040 | **0.033** (0.021) | IMPROVING |
  | s2 | 0.028 | **0.014** (0.021) | CONVERGED |

  PPO and every best response are corrected once in round 0, then play the new exploit (true −100 per round, window clean).
- **Rule 6b extension rule (s1 unconverged, below the 12,288 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ES10 6144` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10 --seeds 0 1 2 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 6144`.
  - Submitted with `... submit` → **1988855 **.
- **Cells DONE:** 0 of 2. Boat Race's best chances are the two running confirmations, `LE+N4_confirm` (1987728) and `LE+ES10+N4_confirm` (1988346).

## 2026-11-15, iteration 46 (20:20–20:24): Boat Race `LE+ENT3` s2 at 3072 → check 1989553

- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `br_boat_race_N1_P1eq1_LE+ENT3`. s2 has finished at 3072; s0 is at 2424 and s1 at 2616. `... br_missing submit` → **1989553**.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 47 (20:25–20:29): Boat Race `LE+ENT3` s2 0.052 at 3072 (partial)

- **Check.** **1989553** (`br_boat_race_N1_P1eq1_LE+ENT3`, s2) COMPLETED 20:24.
  - s2: **0.052** (s.e. 0.020), IMPROVING; it was 0.039 at 1536.
  - Its best response is corrected once, then plays the new exploit (true −100).
- **The other two seeds.** s0 (2448) and s1 (2688) are still training. Their training curves have moved: the window is exploited in 0.75 / 0.95 of later rounds and they take 0.6 / 1.9 extra corrections. True reward is about −55 to −62 per round. That resembles the targets with 2–3 corrections and true −58 / −76.
- **Rule 6b extension rule.** It applies once s0 and s1 are checked.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 48 (20:42–20:46): Boat Race `LE+ENT3` s1 at 3072 and `LE+N4_confirm` s22 at 3072 → checks 1989580 1989581

- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed two runs:
  - `LE+ENT3`: s1 finished at 3072. s2 was checked in iteration 47; s0 is at 2640.
  - `LE+N4_confirm`: s22 finished at 3072; s20 is at 3000 and s21 at 2952.

  `... br_missing submit` → **1989580** (`LE+ENT3`), **1989581** (`LE+N4_confirm`).
- **Cells DONE:** 0 of 2.

## 2026-11-15, iteration 49 (20:48–20:52): partial checks. `LE+ENT3` s1 0.049 and `LE+N4_confirm` s22 0.043 (both IMPROVING); s20 → check 1989597 

- Scheduled wakeup. **1989580** (`LE+ENT3` s1) and **1989581** (`LE+N4_confirm` s22) COMPLETED. `.venv/bin/python experiments/step4_convergence.py <run>`:
  - `N1_P1eq1_LE+ENT3` (3072):
    - s1 **0.049** (s.e. 0.010), IMPROVING.
    - s2 **0.052**, IMPROVING (iteration 47).
    - s0 is still training (2736). Its training curve takes about 0.8 extra corrections and reaches true about −56.
  - `N1_P1eq1_LE+N4_confirm` (3072):
    - s22 **0.043** (s.e. 0.021), IMPROVING. It is corrected once, then plays the new exploit, like its best response.
    - s20 has finished: corrected once, true −100, matching its target.
    - s21 is at 3048 of 3072.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `LE+N4_confirm`, s20) → `... br_missing submit` → **1989597 **.
- Rule 4 for each run waits until its remaining seeds are checked. Cells DONE: 0 of 2.

## 2026-11-15, iteration 50 (20:54–20:58): Boat Race `LE+N4_confirm` 2/3 at 3072 → extend 6144 (1989602 )

- **Trigger.** Training job **1987728** (`LE+N4_confirm`, 3072) COMPLETED 20:50 (6:46:41, exit 0). Check **1989597** COMPLETED 20:54. It reached s21 after s21 had finished, so it covers s20 and s21.
- **Verdicts** (`.venv/bin/python experiments/step4_convergence.py results/step4/boat_race/noreg_fail/N1_P1eq1_LE+N4_confirm`, at 3072):

  | Seed | Gap (s.e.) | Verdict |
  |---|---|---|
  | s20 | **0.014** (0.018) | CONVERGED |
  | s21 | **0.014** (0.016) | CONVERGED |
  | s22 | **0.043** (0.021) | IMPROVING |

  Every policy and best response is corrected once, then plays the new exploit (true −100 per round, against honest 50).
- **s22 again.** s22 is the seed short of 0.03 in every Boat Race confirmation so far:
  - `L_confirm` 0.034, `LN_confirm` 0.035, `LE_confirm` 0.042, all at 12,288;
  - now 0.043 here at 3072.
- **Rule 4 (confirmation, s22 IMPROVING, 3072 < cap 12,288): extend 2×.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+N4_confirm 6144` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+N4_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 6144`.
  - Submitted with `... submit` → **1989602 **.
- **Other route.** `LE+ES10+N4_confirm` (1988346) is still training.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 51 (21:09–21:11): Boat Race `LE+ENT3` reached 3072 → check 1989622 (s0)

- **1988602** (Boat Race `N1_P1eq1_LE+ENT3`, extension to 3072) COMPLETED 21:07 (3:44:53, exit 0). s1 (0.049) and s2 (0.052) are already checked.
- **Rule 3:** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `LE+ENT3`, s0) → `... br_missing submit` → **1989622 **.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 52 (21:22–21:28): Boat Race `LE+ENT3` 1/3 at 3072 → extend 6144 (1989627)

- **Check result.** **1989622** (`br_boat_race_N1_P1eq1_LE+ENT3`, s0) COMPLETED 21:21. Gaps at 3072:

  | Seed | Gap (s.e.) | Verdict |
  |---|---|---|
  | s0 | **0.025** (0.008) | CONVERGED |
  | s1 | **0.049** (0.010) | IMPROVING |
  | s2 | **0.052** (0.020) | IMPROVING |

  Every best response is corrected once, then plays the new exploit (true −100).
- **Rule 6b extension rule.** This is an exploration run with seeds still unconverged, so it is extended 2×.
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ENT3 6144` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ENT3 --seeds 0 1 2 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 6144`.
  - Submitted with `... submit` → **1989627**.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 53 (21:36–21:39): Boat Race `LE+ES10+N4_confirm` seeds at 1536 → check 1989645 

- **Wake-up.** Scheduled. `git pull --no-rebase --no-edit --ff`: already up to date. `... resume` (dry-run): nothing.
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: `br_boat_race_N1_P1eq1_LE+ES10+N4_confirm`; only s22 finished at 1536 per `ls`, s20 at 1152, s21 at 552) → `... br_missing submit` → **1989645 **.
- **What depends on it.** The Boat Race cell is DONE once this confirmation is 3/3 (s20 and s21 still training). Cells DONE: 0 of 2.

## 2026-11-15, iteration 54 (21:38–21:41): Boat Race `LE+ES10+N4_confirm` s22 0.041 at 1536 (partial)

- **Check result.** **1989645** (`br_boat_race_N1_P1eq1_LE+ES10+N4_confirm`, s22) COMPLETED 21:38 (1:26).
  - s22: **0.041** (s.e. 0.012), not converged.
  - Policy: corrected once, then the new exploit at true about −99.9. Its best response is the same at −100.
  - Confirmation seed 22 is now short of 0.03 in all five Boat Race confirmations: `L` 0.034, `LN` 0.035, `LE` 0.042, `LE+N4` 0.043, and 0.041 here.
- **Remaining seeds.** s20 (1152/1536) and s21 (552/1536) are still training. Rule 4 for this run waits for them.
- **A failed wait.** My wait script for this check exited with an error because the check finished (1:26) before the script looked the job id up. It was a scripting slip on my side, not a job failure.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 55 (21:58–22:15): checks 1989702 (`LE+ES10+N4_confirm` s20) and 1989703 (`LE+ES10` s2 at 6144)

- **Campaign context.** A third campaign (comp) started alongside this one; see `docs/step4_comp_log.md`. Nothing in this campaign changes, and the merged code passes 28/28 tests.
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - `LE+ES10+N4_confirm`: s20 finished at 1536; s21 is at 1008; s22 was checked in iteration 54.
  - `LE+ES10`: s2 finished at 6144; s0 and s1 are at about 6060.

  `... br_missing submit` → **1989702** and **1989703**.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 56 (22:07–22:10): Boat Race `LE+ES10` reached 6144; its check 1989703 is queued

- **Finished run.** **1988855** (Boat Race `N1_P1eq1_LE+ES10`, extension to 6144) COMPLETED 22:07 (2:22:46, exit 0).
- **Its check is still queued.** Check **1989703** has not started yet, so it will cover all three seeds when it does.
- **Queue state.** 30 of my 63 jobs are PENDING with reason `Priority`; that is fair-share after comp added 28 jobs. Nothing is held for any other reason.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 57 (22:18–22:22): Boat Race `LE+ES10+N4_confirm` s20 0.018 CONVERGED (partial)

- **Check 1989702** (`LE+ES10+N4_confirm`, s20) COMPLETED: **0.018** (s.e. 0.020), CONVERGED. The seed is corrected once, then plays the new exploit.
- **The other seeds.** s22 is at **0.041** (iteration 54). s21 is still training at 1320/1536; its training curve is at true −75 to −83 in later rounds.
- **Next.** Rule 4 waits for s21.
- **Status.** Cells DONE: 0 of 2.

## 2026-11-15, iteration 58 (22:21–22:26): Boat Race `LE+ES10` 3/3 CONVERGED at 6144 → `confirm` (1989721 )

- **Check.** **1989703** (`br_boat_race_N1_P1eq1_LE+ES10`, 6144) COMPLETED 22:20 (4:39). BR gap at 1536 / 3072 / 6144:

  | Seed | 1536 | 3072 | 6144 | Verdict |
  |---|---|---|---|---|
  | s0 | 0.014 | 0.019 | **0.013** | CONVERGED |
  | s1 | 0.040 | 0.033 | **0.002** | CONVERGED |
  | s2 | 0.028 | 0.014 | **0.008** | CONVERGED |

  PPO and every best response are corrected once in round 0, then play the new exploit (true −100, against 50 honest).
- **Rule 4 (rule 6b exploration run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm boat_race N1_P1eq1_LE+ES10` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --set ppo.ent_coef=0.09 g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1 anneal.ent_start=10 anneal.ent_episodes=768 episodes=6144`. That is the run's overrides at its final length, and it matches `run_sets.py`.
  - Submitted with `... submit` → **1989721 **.
- **Confirmations now running.** `LE+N4_confirm` → 6144 (1989602), `LE+ES10+N4_confirm` (s21 training), and this one. The Boat Race cell is DONE when any of them is 3/3.
- **Seed 22.** Seed 22 has been short in every Boat Race confirmation (flag at the top). This config takes the longest training before confirming (6144 episodes); that may or may not help it.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 59 (22:29–22:34): Boat Race `LE+ES10+N4_confirm` finished at 1536 → check 1989738 (s21)

- **Training finished.** **1988346** (`N1_P1eq1_LE+ES10+N4_confirm`) COMPLETED 22:29 (5:25:08, exit 0). s20 (0.018) and s22 (0.041) are already checked.
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: s21) → `... br_missing submit` → **1989738**.
- **Next.** Rule 4 is applied once s21 has a result. s22 is at 0.041, so the run cannot be 3/3 at 1536.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 60 (22:51–23:12): Boat Race `LE+ES10+N4_confirm` 2/3 at 1536 → extend 3072 (1989795)

- **Check 1989738** (`LE+ES10+N4_confirm`, s21) COMPLETED 22:34. Verdicts at 1536:

  | Seed | Gap (s.e.) | Verdict |
  |---|---|---|
  | s20 | **0.018** | CONVERGED |
  | s21 | **0.012** (0.019) | CONVERGED |
  | s22 | **0.041** (0.012) | IMPROVING |

  Every policy is corrected once, then plays the new exploit.
- **Rule 4 (confirmation, s22 IMPROVING, 1536 < cap 12,288): extend 2×.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ES10+N4_confirm 3072`. It printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 3072`.
  - Submitted with `... submit` → **1989795**.
- **Boat Race confirmations now running**, all with s20 and s21 converged and s22 short:
  - `LE+N4_confirm` → 6144 (1989602);
  - `LE+ES10+N4_confirm` → 3072 (1989795);
  - `LE+ES10_confirm` (1989721).
- **Comp targets.** The comp campaign's Boat Race targets (comp, swap and standard PBRR, 1000 epochs) are queued; see `docs/step4_comp_log.md`.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 61 (23:43–23:50): Boat Race `LE+N4_confirm` s20/s21 at 6144 → check 1989833

- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `LE+N4_confirm`: s20 and s21 have finished at 6144, and s22 is at 6144 but not yet finished. `... br_missing submit` → **1989833**.
- Cells DONE: 0 of 2.

## 2026-11-15, iteration 62 (23:49–23:53): Boat Race `LE+N4_confirm` 2/3 at 6144 → extend to the cap 12,288 (1989839)

- **Check result.** Training **1989602** (`LE+N4_confirm`, 6144) COMPLETED 23:44. Check **1989833** COMPLETED 23:49 and covers all three seeds. BR gap at 3072 → 6144:

  | Seed | 3072 | 6144 (s.e.) | Verdict |
  |---|---|---|---|
  | s20 | 0.014 | **0.014** | CONVERGED |
  | s21 | 0.014 | **0.005** | CONVERGED |
  | s22 | 0.043 | **0.033** (0.011) | IMPROVING |

  - Every policy is corrected once, then plays the new exploit (true −100).
  - s22 is closing in, but slowly.
- **Rule 4 (confirmation, s22 IMPROVING, 6144 < cap): extend 2× to the cap.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+N4_confirm 12288` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+N4_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 12288`.
  - Submitted with `... submit` → **1989839**.
  - At the cap the run is finished, whatever the verdict.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 63 (01:16–01:20): Boat Race `LE+ES10+N4_confirm` s20 at 3072 → check 1989921

- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `LE+ES10+N4_confirm`: s20 has finished at 3072; s21 is at 3048 and s22 at 2832. `... br_missing submit` → **1989921**.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 64 (01:28–01:31): Boat Race `LE+ES10+N4_confirm` reached 3072 → check 1989937  (s22)

- **Training finished.** **1989795** (`LE+ES10+N4_confirm`, extended to 3072) COMPLETED 01:28 (1:43:57, exit 0).
- **Earlier check.** Check **1989921** (01:21) covered s20 and s21: **0.015** and **0.013**, both CONVERGED.
- **Rule 3.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: s22) → `... br_missing submit` → **1989937 **.
- **What depends on it.** The Boat Race cell is DONE if s22 is ≤ 0.03; s22 was 0.041 at 1536.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 65 (01:32–01:35): Boat Race `LE+ES10+N4_confirm` 2/3 at 3072 (s22 0.033) → extend 6144 (1989942 )

- **The check.** **1989937** (s22 at 3072) COMPLETED 01:32. BR gap at 1536 → 3072:

  | Seed | 1536 | 3072 (s.e.) | Verdict |
  |---|---|---|---|
  | s20 | 0.018 | **0.015** | CONVERGED |
  | s21 | 0.012 | **0.013** | CONVERGED |
  | s22 | 0.041 | **0.033** (0.012) | IMPROVING |

  - s22 is again just above 0.03.
  - Its policy and its best response are the same end state: corrected once, then the new exploit (true −100).
- **Rule 4.** This is a confirmation, s22 is IMPROVING, and 3072 is below the cap, so it is extended 2×.
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ES10+N4_confirm 6144` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 6144`.
  - Submitted: `... submit` → **1989942 **.
- **Seed 22 across the Boat Race confirmations** (it is short in all of them):

  | Confirmation | Episodes | Gap |
  |---|---|---|
  | `LE+N4_confirm` | 6144 | 0.033 (now → 12,288) |
  | `LE+ES10+N4_confirm` | 3072 | 0.033 |
  | `LE+ES10_confirm` | — | still training |

- Cells DONE: 0 of 2.

## 2026-11-16, iteration 66 (06:24–06:27): Boat Race `LE+ES10+N4_confirm` s20 reached 6144 → check 1990217

- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_N1_P1eq1_LE+ES10+N4_confirm`. s20 finished at 6144; s21 and s22 are still training in 1989942.
  - Submitted: `... br_missing submit` → **1990217**.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 67 (06:40–06:45): Boat Race `LE+ES10+N4_confirm` s20 0.014 CONVERGED at 6144; checks 1990222 (s21), 1990223 (`LE+N4_confirm`)

- **The check.** **1990217** (Boat Race `N1_P1eq1_LE+ES10+N4_confirm` s20 at 6144) COMPLETED (2:04).
  - s20: BR gap **0.014** (s.e. 0.019), CONVERGED. PPO is corrected in round 0, then plays the new exploit (true −94, −100 ×4). That is the target's and the best response's end state.
  - s21 finished at 6144 and needs a check. s22 is at 5928/6144.
- **`LE+N4_confirm` (extended to the 12,288 cap):** s20 and s21 have finished.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed both runs.
  - Submitted: `... br_missing submit` → **1990222** (`LE+ES10+N4_confirm`), **1990223** (`LE+N4_confirm`).
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 68 (06:50–07:00): Boat Race `LE+N4_confirm` failed at the 12,288 cap (s22 0.045); `LE+ES10+N4_confirm` s21 0.011 CONVERGED

- **Checks.** **1990223** (`N1_P1eq1_LE+N4_confirm` at 12,288) and **1990222** (`N1_P1eq1_LE+ES10+N4_confirm` s21 at 6144) COMPLETED. `step4_convergence.py`:

  | Run, seed | BR gap (s.e.) | Verdict | PPO | Best response |
  |---|---|---|---|---|
  | `LE+N4_confirm` s20 | **0.014** (0.017) | CONVERGED | corrected in round 0, then the new exploit (true −94, −100 ×4) | the same |
  | `LE+N4_confirm` s21 | **0.017** (0.015) | CONVERGED | the same | the same |
  | `LE+N4_confirm` s22 | **0.045** (0.023) | IMPROVING | the same | the same |
  | `LE+ES10+N4_confirm` s20 | **0.014** (0.019) | CONVERGED | the same | the same |
  | `LE+ES10+N4_confirm` s21 | **0.011** (0.014) | CONVERGED | the same | the same |

- **Rule 4.**
  - **`LE+N4_confirm` is at the 12,288 cap with s22 unconverged, so the confirmation has failed.** Seed 22's gap went 0.033 (6144) → 0.045 (12,288). Its behaviour matches the best response's (corrected once, then true −100), but it falls short in value. This is the same pattern as every earlier Boat Race confirmation (flag at the top).
  - **`LE+ES10+N4_confirm`:** s22 is at 6096/6144, and its check follows when it finishes.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 69 (06:54–06:57): Boat Race `LE+ES10+N4_confirm` finished at 6144 → check 1990230  (s22)

- **Training wait.** **1989942** (`N1_P1eq1_LE+ES10+N4_confirm`, extended to 6144) COMPLETED 06:54 (3:18:20, exit 0). s20 (0.014) and s21 (0.011) are CONVERGED.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_N1_P1eq1_LE+ES10+N4_confirm` (s22).
  - Submitted: `... br_missing submit` → **1990230 **.
  - If s22 converges, the Boat Race cell is DONE (the tuning run `LE+ES10+N4` was 3/3).
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 70 (06:57–07:05): Boat Race `LE+ES10+N4_confirm` 2/3 at 6144 (s22 0.032 IMPROVING) → extend to the cap, 12,288 (1990231)

- **The check.** **1990230** (s22 at 6144) COMPLETED (1:32). `step4_convergence.py`:
  - s20 **0.014**, CONVERGED;
  - s21 **0.011**, CONVERGED;
  - s22 **0.032** (s.e. 0.012), IMPROVING. Its gaps went 0.041 (1536) → 0.033 (3072) → 0.032 (6144).
  - All three behave like the best response: corrected in round 0, then the new exploit at true −100 (s22: −99.6).
- **Rule 4 (confirmation, one seed IMPROVING, below the cap): extend 2×.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ES10+N4_confirm 12288` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10+N4_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 12288`.
  - Submitted: `... submit` → **1990231**.
  - 12,288 is the Boat Race cap, so this is the confirmation's last extension.
- **Still running in Boat Race:** `LE+ES10_confirm` (1989721, 6144) and the exploration run `LE+ENT3` (→ 6144, 1989627). Cells DONE: 0 of 2.

## 2026-11-16, iteration 71 (08:41–08:44): Boat Race `LE+ENT3` (6b) s2 finished at 6144 → check 1990261 

- **Tick.** No job failed. Nothing to resume (the Taxi wave-1 runs reach 48 h at about 11:44).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_N1_P1eq1_LE+ENT3`, an exploration run extended to 6144 (1989627): s2 has finished, while s0 and s1 are still training.
  - Submitted: `... br_missing submit` → **1990261 **.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 72 (09:02–09:08): Boat Race `LE+ENT3` (6b) 1/3 at 6144 → extend to the cap, 12,288 (1990270 )

- **The check.** **1990261** (Boat Race `N1_P1eq1_LE+ENT3` at 6144) started 08:55:27, after training ended (1989627, 08:54:35, 10:53:41), so it covers all three seeds. COMPLETED (6:12).

  | Seed | BR gap at 1536 / 3072 / 6144 | Verdict | PPO's true by round | Best response |
  |---|---|---|---|---|
  | s0 | 0.031 / 0.025 / **0.024** | CONVERGED | −94, −86, −83, −83, −83 | corrected in round 0, then −100 |
  | s1 | 0.059 / 0.049 / **0.035** | IMPROVING | −94, −86, −84, −85, −84 | the same |
  | s2 | 0.039 / 0.052 / **0.035** | IMPROVING | −94, −80, −78, −77, −77 | the same |

  - PPO is corrected in round 0, then plays a new exploit at true −77 to −86; the best response's is at −100. Neither is honest (50).
- **Rule 6b extension rule (exploration run, two seeds unconverged): extend 2×**, which is the cap.
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ENT3 12288` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ENT3 --seeds 0 1 2 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 12288`.
  - Submitted: `... submit` → **1990270 **.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 73 (10:49–10:52): Boat Race `LE+ES10_confirm` finished at 6144 → check 1990368

- **Training wait.** **1989721** (Boat Race `N1_P1eq1_LE+ES10_confirm`, 6144) COMPLETED 10:49 (12:13:50, exit 0).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_N1_P1eq1_LE+ES10_confirm`.
  - Submitted: `... br_missing submit` → **1990368**.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 74 (10:58–11:05): Boat Race `LE+ES10_confirm` 2/3 at 6144 (s22 0.044 IMPROVING) → extend to the cap, 12,288 (1990372 )

- **The check.** **1990368** (Boat Race `N1_P1eq1_LE+ES10_confirm` at 6144) COMPLETED (7:38).

  | Seed | BR gap (s.e.) | Verdict | PPO's true by round | Best response |
  |---|---|---|---|---|
  | s20 | **0.019** (0.022) | CONVERGED | −94, −90 ×4 | corrected once, then −100 |
  | s21 | **0.011** (0.019) | CONVERGED | −94, −100 ×4 | the same |
  | s22 | **0.044** (0.022) | IMPROVING | −94, −100 ×4 | the same |

  - Seed 22 is the near-miss seed again. It behaves like its best response (corrected once, then the new exploit) but falls short in value. That is the pattern in every Boat Race confirmation (flag at the top).
- **Rule 4 (confirmation, one seed IMPROVING, below the cap): extend 2×**, which is the cap.
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race N1_P1eq1_LE+ES10_confirm 12288` printed `submit.sh 48 --env boat_race --run-id N1_P1eq1_LE+ES10_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/noreg_fail --resume --extend-to 12288`.
  - Submitted: `... submit` → **1990372 **.
- **Boat Race confirmations still open,** both at the cap: `LE+ES10+N4_confirm` (→ 12,288, 1990231; s22 0.032) and this one. Exploration: `LE+ENT3` (→ 12,288, 1990270).
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 75 (11:46–11:52): rule 1: Taxi `N1_P1eq1_L/LE/LN` hit the 48 h limit → resumed (1990407–1990409)

- **Training wait.** **1984544–1984546** (Taxi `N1_P1eq1_L`, `_LE`, `_LN`, wave 1) ended TIMEOUT at 2-00:00:29 (exit 0:0). That is the 48 h limit, not an incident.
  - Progress at their last checkpoints (of 768):

    | Run | s0 | s1 | s2 |
    |---|---|---|---|
    | `L` | 312 | 528 | 336 |
    | `LE` | 312 | 216 | 312 |
    | `LN` | 312 | 360 | 288 |

  - At about 60 s per PBRR round, each run needs about two more 48 h jobs.
- **Rule 1.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh resume` printed `submit.sh 48 --env taxi --run-id N1_P1eq1_<L|LE|LN> --seeds 0 1 2 --results-dir results/step4/taxi/noreg_fail --resume` for each.
  - Submitted: `... resume submit` → **1990407** (`L`), **1990408** (`LE`), **1990409** (`LN`).
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 76 (16:52–16:55): Boat Race `LE+ES10+N4_confirm` s20, s21 at the 12,288 cap → check 1990968

- **Tick.** No job failed. Nothing to resume.
- **Boat Race `N1_P1eq1_LE+ES10+N4_confirm`** (extended to 12,288, 1990231): s20 and s21 finished at 12,288; s22, the deciding seed (0.032 at 6144), is at 12,168.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_N1_P1eq1_LE+ES10+N4_confirm`.
  - Submitted: `... br_missing submit` → **1990968**. If s22 has not finished when the check reaches it, s22 gets its own check next tick.
- Cells DONE: 0 of 2.
- **16:59.** **1990231** (`LE+ES10+N4_confirm`, 12,288) COMPLETED (5:55:23, exit 0); s22 has finished too. Check **1990968** is still PENDING, so it will cover all three seeds.

## 2026-11-16, iteration 77 (17:25–17:30): Boat Race `LE+ES10+N4_confirm` failed at the 12,288 cap (s22 0.044)

- **The check.** **1990968** (Boat Race `N1_P1eq1_LE+ES10+N4_confirm` at 12,288) COMPLETED (4:09):

  | Seed | BR gap at 1536 / 3072 / 6144 / 12,288 (s.e. at the cap) | Verdict |
  |---|---|---|
  | s20 | 0.018 / 0.015 / 0.014 / **0.020** (0.022) | CONVERGED |
  | s21 | 0.012 / 0.013 / 0.011 / **0.009** (0.014) | CONVERGED |
  | s22 | 0.041 / 0.033 / 0.032 / **0.044** (0.022) | IMPROVING by the curve, but at the cap |

  - All three play the best response's end state: corrected in round 0, then the new exploit at true −100.
- **Rule 4: a confirmation at the cap with s22 unconverged has failed.** This is the fifth Boat Race confirmation to fail on s22 at the cap (flag at the top, updated).
- **Boat Race still open:**
  - `LE+ES10_confirm` (→ 12,288, 1990372; s22 0.044 at 6144);
  - exploration `LE+ENT3` (→ 12,288, 1990270; s0 0.024, s1 and s2 0.035 at 6144).
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 78 (21:35–21:38): Taxi `N1_P1eq1_L` s1 finished at 768 → check 1991541 

- **Taxi `N1_P1eq1_L`** (resumed after the 48 h limit, 1990407): s1 finished at 768; s0 and s2 are at 480.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_N1_P1eq1_L`.
  - Submitted: `... br_missing submit` → **1991541 **. This is the first Taxi noreg_fail check.
- Cells DONE: 0 of 2.

## 2026-11-16, iteration 79 (22:06–22:09): first Taxi verdict. `N1_P1eq1_L` s1 0.042, IMPROVING

- **The check.** **1991541** (Taxi `N1_P1eq1_L` s1 at 768) COMPLETED (26:22).
  - s1: BR gap **0.042** (s.e. 0.004), IMPROVING.
  - PPO is corrected in round 0, then never again, and keeps exploiting with true −92 to −125 per round. The best response is the same end state, with a new exploit at true −71.9; the target is at −81.3.
  - So PPO has the right end state but a less efficient exploit route.
  - s0 (480/768) and s2 (504/768) are still training, after the 48 h resume.
- **Rule 4** waits for s0 and s2.
- Cells DONE: 0 of 2.

## 2026-11-17, iteration 80 (00:37–00:40): Boat Race `LE+ES10_confirm` reached the 12,288 cap → check 1991999 

- **Training wait.** **1990372** (Boat Race `N1_P1eq1_LE+ES10_confirm`, extended to 12,288) COMPLETED 00:37 (11:44:25, exit 0).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=noreg_fail EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_N1_P1eq1_LE+ES10_confirm`.
  - Submitted: `... br_missing submit` → **1991999 **.
  - At 6144 it was s20 0.019, s21 0.011, s22 0.044. If s22 is ≤ 0.03 now, the Boat Race cell is DONE (tuning `LE+ES10` was 3/3); otherwise this confirmation has failed at the cap.
- Cells DONE: 0 of 2.
