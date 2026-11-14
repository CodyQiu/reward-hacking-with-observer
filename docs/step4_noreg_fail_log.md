# Step 4 no-regulariser failure campaign (Taxi, Boat Race): decision log

Procedure: `docs/step4_noreg_fail.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=noreg_fail`.

## Flags for the user

- **barley-04.** Every submit still carries `EXCLUDE=barley-04` (your standing instruction from the optimal campaign). On 2026-11-14 at 11:42, `sinfo` shows barley-04 `allocated` with no reason set; say if I should drop the exclusion.
- **Taxi runs will hit the 48 h limit** (the doc: an exploiting seed took 47 h for 768 episodes in Step 3). Rule 1 resumes them from their checkpoints; that is not an incident.

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
