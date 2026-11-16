# Step 4 compensated-correction campaign: decision log

Procedure: `docs/step4_comp.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`, campaign (C). Append-only below the two summary sections; every driver command runs with `CAMPAIGN=comp`.

## Flags for the user

- **barley-04.** Every submit carries `EXCLUDE=barley-04`, your standing instruction from the optimal campaign, kept in the bonus and noreg_fail campaigns too. On 2026-11-14 `sinfo` showed barley-04 `allocated` with no reason set. Say if I should drop the exclusion.
- **Taxi runs will hit the 48 h limit** (docs/step4_comp.md, wave 1). Rule 1 resumes them from their checkpoints; that is not an incident.

## Exact predictions

Honest true return per round: grid 22, AS 450, Tomato about 434, tomato_large about 523, Taxi 125, Boat Race 50. Targets: `results/step4/<env>/targets/comp/seed<s>.json`. Comparison targets:
- **Swap:** `P2swap/`, from the optimal campaign; for Taxi and Boat Race, the `compare` jobs.
- **Standard PBRR:** `base_bonus1/` for grid, AS, Tomato and tomato_large; `base/` for Taxi and Boat Race.

**Grid, compensated correction** (job 1989672, 3:51; all 6 fixed points converged; every draw of every seed has the same end state):

| Seed | End state | True by round (k = 0..4) | V0 | V_hide | Level per step: actual 1st / counterfactual 2nd–4th |
|---|---|---|---|---|---|
| 0 | corrected in round 0, then never again | −100, 22 ×4 | 43,518 | 39,500 | **86.8** / 80.5, 74.2, 67.8 |
| 1 | the same | −100, 22 ×4 | 43,519 | 39,500 | **86.8** / 80.5, 74.2, 67.8 |
| 2 | the same | −100, 22 ×4 | 43,522 | 39,500 | **86.8** / 79.5, 72.2, 64.9 |
| 20 | the same | −100, 22 ×4 | 43,520 | 39,500 | **86.8** / 81.1, 75.4, 69.7 |
| 21 | the same | −100, 22 ×4 | 43,514 | 39,500 | **86.8** / 81.2, 75.5, 69.9 |
| 22 | the same | −100, 22 ×4 | 43,506 | 39,500 | **86.8** / 80.6, 74.5, 68.3 |

- **What the optimum does.** In all 6 seeds it exploits in view in round 0, is corrected, and is **honest** after (true 22 = honest; the best round after one correction has true 22.0). That is neither the original bug nor a new exploit.
- **Margin over hiding.** It beats hiding by about 4,010. Hiding is standard PBRR's own optimum here (39,500).
- **The level.** The actual correction's level is 86.8 per step: V_before 8,700, the open exploiter's round, and V_ref,after about 17.4. The counterfactual later corrections pay less and less, from about 80 to about 68 per step. So re-triggering a correction is never worth it (no farming), as docs/step4_comp.md predicts.
- **The same seeds under the other mechanisms.**
  - **Swap** (optimal campaign targets): corrected once, then honest (true 22) in all 6 seeds. On the grid, comp matches the swap.
  - **Standard PBRR** (`base_bonus1`): **hides** in all 6 seeds, with true −100 every round. The bonus adds value only to corrections, so without it standard PBRR hides too.

Pending: AS, Tomato, tomato_large, Taxi and Boat Race comp targets (1989673–1989677), and the comparison targets (1989678–1989681).

## 2026-11-15, iteration 0 (21:58–22:10): first iteration; targets, comparison targets and wave 1 submitted

- **Starting point.**
  - The user's commit b145f873e (21:48) added this campaign: `docs/step4_comp.md`, the code, 8 new tests, and the three-campaign loop prompt. It arrived with `git pull --no-rebase --no-edit --ff` during the bonus / noreg_fail loop. The user then sent the new prompt in the session.
  - `.venv/bin/python tests/test_step4.py`: **28 tests, 0 failed**. That includes the 8 compensated-correction tests and my stale-NFS test from earlier today (5481e0b3), which the user's commit keeps.
- **Targets (pipeline 1).**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh targets`. It listed 6 jobs, each `step4_targets.py --env <env> --name comp --seeds 0 1 2 20 21 22 --set g.fine_only=True g.offset=True g.offset_margin=0.0`, plus `g.epochs=1000` outside the grid and `task.obs=onehot` for Taxi.
  - Submitted: `... targets submit` → **1989672** (grid), **1989673** (AS), **1989674** (Tomato), **1989675** (tomato_large), **1989676** (Taxi), **1989677** (Boat Race).
- **Comparison targets (pipeline 2).**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh compare`. It listed `P2swap` (`g.l_minus_on=dispreferred`) and `base` in Taxi (`task.obs=onehot`) and Boat Race, `g.epochs=1000`, seeds 0–2 and 20–22.
  - Taxi's existing `P2swap` seed 0–2 files are skipped by `step4_targets.py`, which never overwrites.
  - Submitted: `... compare submit` → **1989678** (Taxi swap), **1989679** (Taxi base), **1989680** (Boat Race swap), **1989681** (Boat Race base).
- **Wave 1 (pipeline 3).**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh wave1`. It listed 18 runs: `C1_comp_L`, `_LE` and `_LN` per env on seeds 0–2, each with `g.fine_only=True g.offset=True g.offset_margin=0.0 anneal.last=0.25 anneal.floor=0.1` on the env's frozen Step 3 config.
    - Lengths: grid, Tomato, tomato_large and Boat Race 1536; AS 3072; Taxi 768.
    - `LE` is entropy 3×. `LN` is `n_envs=64 ppo.batch_size=1600`.
  - Submitted: `... wave1 submit` → **1989682–1989684** (grid L/LE/LN), **1989685–1989687** (AS), **1989688–1989690** (Tomato), **1989691–1989693** (tomato_large), **1989694–1989696** (Taxi), **1989697–1989699** (Boat Race).
- **Budget.** This campaign has 28 jobs (limit 30); all my jobs come to 61 (limit 110). Cells DONE: 0 of 6.

## 2026-11-15, iteration 1 (22:25–22:35): grid target (all 6 seeds: corrected once, then honest)

- **Target job.** **1989672** (`targets_grid_comp`) COMPLETED 22:25 (3:51). Every fixed point converged in 2 iterations.
- **Rule 2.** Entered under "Exact predictions" at the top.
  - **End state.** In all 6 seeds the optimum is "corrected in round 0, then never again", then honest (true 22 ×4). V0 is about 43,515 against V_hide 39,500.
  - **Level.** The actual correction's level is 86.8 per step. The counterfactual later corrections pay less, from about 80 down to about 68.
  - **Comparison.** On the grid this matches the swap's targets. Standard PBRR hides.
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run): nothing; no wave-1 seed has finished.
- **Queue.** The other target jobs and the wave-1 runs are queued or running behind fair-share priority. Cells DONE: 0 of 6.
