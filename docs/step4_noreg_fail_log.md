# Step 4 no-regulariser failure campaign (Taxi, Boat Race): decision log

Procedure: `docs/step4_noreg_fail.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`. Append-only below the two summary sections; every driver command runs with `CAMPAIGN=noreg_fail`.

## Flags for the user

- **barley-04.** Every submit still carries `EXCLUDE=barley-04` (your standing instruction from the optimal campaign). On 2026-11-14 at 11:42, `sinfo` shows barley-04 `allocated` with no reason set; say if I should drop the exclusion.
- **Taxi runs will hit the 48 h limit** (the doc: an exploiting seed took 47 h for 768 episodes in Step 3). Rule 1 resumes them from their checkpoints; that is not an incident.

## Exact predictions

Honest true return per round: **Taxi 125** (124.8), **Boat Race 50**.

**Taxi, no regulariser** (`results/step4/taxi/targets/P1eq1/`, seeds 0–2 from the hide-environment sweep of 2026-11-10, same game: `task.obs=onehot`, no regulariser, 1000 epochs; all `fixed_point_converged`):

| Seed | End state | True by round (k = 0..4) | V0 | V_hide | Margin | Draws' end states |
|---|---|---|---|---|---|---|
| 0 | corrected in round 0, then never again | −88.2, −79.3 ×4 | 11,668 | 1,794 | 9,873 | 3 × corrected once, 2 × two corrections, 1 × three |
| 1 | corrected in round 0, then never again | −88.2, −81.3 ×4 | 13,487 | 1,794 | 11,692 | 5 × corrected once, 1 × two |
| 2 | corrected in round 0, then never again | −88.2, −77.6 ×4 | 12,714 | 1,794 | 10,920 | 5 × corrected once, 1 × three |

- **After its correction the optimum is a new exploit:** the audit windows of rounds 1–4 are clean (window 0.0, no further correction), yet true return is −78 to −81 per round against honest 125. It is not the original bug (that is round 0's open exploit, true −88, window 1.0) and not honest. Received per round after the correction: 2,822 / 3,277 / 3,084.
- Seeds 20–22: pending (job 1984542).

**Boat Race, no regulariser:** pending (job 1984543, seeds 0–2 and 20–22).

## 2026-11-14, iteration 0 (11:41–11:50): first iteration, targets and wave 1 submitted

- `git pull --no-rebase --no-edit --ff`: at eb4821a9, already up to date. `.venv/bin/python tests/test_step4.py`: **20 tests, 0 failed**.
- **Targets.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh targets` (dry-run): `run_cmd.sh 36 4 targets_taxi_P1eq1 ... experiments/step4_targets.py --env taxi --name P1eq1 --seeds 0 1 2 20 21 22 --set task.obs=onehot g.use_regularization=False g.epochs=1000` and `... targets_boat_race_P1eq1 ... --env boat_race --name P1eq1 --seeds 0 1 2 20 21 22 --set g.use_regularization=False g.epochs=1000`. Checked: `step4_targets.py` skips an existing seed file ("exists: skipped (never overwritten)"), so Taxi's seeds 0–2 are kept and only 20–22 are computed. `... targets submit` → **1984542** (Taxi), **1984543** (Boat Race).
- **Wave 1.** `CAMPAIGN=noreg_fail EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh wave1` (dry-run): 6 `submit.sh 48` lines, seeds 0–2, `results/step4/<env>/noreg_fail/`, all with `g.use_regularization=False g.epochs=1000 anneal.last=0.25 anneal.floor=0.1`:
  - Taxi (`task.obs=onehot ppo.ent_coef=0.03`, 768 episodes): `N1_P1eq1_L`, `N1_P1eq1_LE` (`ppo.ent_coef=0.09`), `N1_P1eq1_LN` (`n_envs=64 ppo.batch_size=1600`).
  - Boat Race (`ppo.ent_coef=0.03`, 1536 episodes): the same three tags.
  - Checked against the doc, then `... wave1 submit` → **1984544–1984546** (Taxi L / LE / LN), **1984547–1984549** (Boat Race L / LE / LN).
- Budget: this campaign 8 jobs (≤ 20); with bonus's 32, 40 in all (≤ 110). Cells DONE: 0 of 2.
