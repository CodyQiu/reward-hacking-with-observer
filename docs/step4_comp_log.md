# Step 4 compensated-correction campaign: decision log

Procedure: `docs/step4_comp.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`, campaign (C). Append-only below the two summary sections; every driver command runs with `CAMPAIGN=comp`.

## Flags for the user

- **barley-04.** Every submit carries `EXCLUDE=barley-04`, your standing instruction from the optimal campaign, kept in the bonus and noreg_fail campaigns too. On 2026-11-14 `sinfo` showed barley-04 `allocated` with no reason set. Say if I should drop the exclusion.
- **AS (6/6 seeds) and Tomato (5/6): the comp target farms the level; the doc expected one correction, then honest (iterations 2 and 12, 2026-11-15/16).** Tomato's farming seeds take 3–4 corrections, use the bug inside the window in rounds 1–3 (true about 423 against honest 434) and have rising levels; Tomato s0 is corrected once, then honest. Details for AS below.
  - **End state.** All 6 AS comp targets are corrected in every round 0–3. In rounds 1–3 the optimum uses the original bug inside the audit window (true 400 against honest 450), and each correction's level rises (11.8 → 13.5 per step).
  - **Why.** The level formula carries the previous level inside V_before. So each correction adds (R_caught − V_ref,after) / T_sub, and in AS the reference's return under the new correction (about 372) is below the agent's own nearly honest caught play (420–442).
  - **What I am doing.** This is the exact answer for this mechanism. I am not changing anything; wave 1 runs as planned, and PPO's target is this end state. A different level rule would be a mechanism change, which is your call (for example, basing V_ref,after on the agent's own honest play, or not compounding the level).
- **Under comp, the 3% verdict can pass a policy that is not honest after its correction (iteration 4, 2026-11-15).**
  - **Example.** Grid `C1_comp_L` s1 and s2 are CONVERGED (0.012 and 0.011), but PPO's true return is −100 in every round. It is corrected in round 0, keeps the windows clean, then never reaches the goal. The best response and the target are honest after the correction (true 22).
  - **Why the verdict passes it.** The level makes every round worth about 8,690 received, so missing the goal (−122 per round) is only 1.2% of V0 (about 43,500). That is inside the 3% tolerance.
  - **Scope.** The same holds wherever the level dwarfs the honest-vs-exploit difference.
  - **What I am doing.** I apply the criterion as written (never adjust criteria), so these seeds count as CONVERGED, and I report PPO's true return beside every verdict. A behavioural criterion for comp would be your call: for example, PPO's true return by round within x of the best response's, or the gap measured on the true reward.
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

**Absent Supervisor, compensated correction** (job 1989673, 2:39; all 6 fixed points converged; 32 of the 36 draws have the same end state, and 2 seeds each have one draw with 3 corrections):

| Seed | End state | True by round (k = 0..4) | V0 | V_hide | Level per step at corrections 1–4 (all actual) |
|---|---|---|---|---|---|
| 0 | **4 corrections per episode** (rounds 0–3) | −100, 400, 400, 400, 450 | 8,371 | 7,350 | 11.76, 12.46, 13.05, 13.54 |
| 1 | the same | the same | 8,228 | 7,350 | 11.71, 12.22, 12.65, 13.04 |
| 2 | the same | the same | 8,292 | 7,350 | 11.74, 12.35, 12.82, 13.26 |
| 20 | the same | the same | 8,343 | 7,350 | 11.76, 12.44, 12.97, 13.42 |
| 21 | the same | the same | 8,383 | 7,350 | 11.79, 12.46, 13.05, 13.62 |
| 22 | the same | the same | 8,275 | 7,350 | 11.68, 12.29, 12.75, 13.17 |

- **Not the expected end state.** docs/step4_comp.md expected "corrected in round 0, then never again" here. Instead the optimum is **corrected in every round 0–3**:
  - Round 0: the open exploit (true −100).
  - Rounds 1–3: it uses **the original bug inside the audit window** (proxy 550 against true 400, window 1.0) to trigger another correction.
  - Round 4: honest (450).
- **It is not under-correction.** Within one round after a correction, honest play pays more than the exploit. In s0, the best round after one correction is honest at 1,626, and the exploit round is 1,530.
- **It is farming the level.** Each correction's level rises: 11.8 → 12.5 → 13.0 → 13.5 per step. The level is c_k = [V_before − V_ref,after]⁺ / T_sub, and V_before includes the level in force, so c_k − c_{k−1} = (R_caught − V_ref,after) / T_sub, where R_caught is the caught play's own return excluding the level. In s0:

  | Correction | R_caught | V_ref,after |
  |---|---|---|
  | 2 | about 442 | about 372 |
  | 3 | about 431 | about 372 |
  | 4 | about 420 | about 372 |

  So each correction adds +0.5 to +0.7 per step for the rest of the episode. The reason is that the reference policy earns about 372 under the new correction, less than the agent's nearly honest caught play. On the grid, by contrast, the counterfactual later corrections lower the level (86.8 → 80 → 74 → 68), because the caught play there pays heavy fines.
- **The same seeds under the other mechanisms.**
  - **Swap:** corrected once, then **the new exploit** at true −50 (s2: −100).
  - **Standard PBRR** (`base_bonus1`): **hides** (true −50 ×4, then −100).
- **What this means for the hypothesis.** Comp gets AS corrected at once and it does not hide; its true return after round 0 (400 ×3, 450) is far above the swap's −50. But it is not "corrected once, then behaves": it keeps triggering corrections with the original bug for the level they pay. Flagged at the top.

**Tomato, compensated correction** (job 1989674, 2:12:31; fixed points converged in 5 of 6 seeds, **not in s2**):

| Seed | End state | True by round (k = 0..4) | V0 | V_hide | Level per step at corrections 1–4 |
|---|---|---|---|---|---|
| 0 | corrected in round 0, then never again | 46, 434.1 ×4 | 2,967 | 2,759 | **1.61** / counterfactual 1.56, 1.48, 1.36 |
| 1 | 3.00 corrections (rounds 0–2) | 46, 421.4, 420.9, 433.2, 433.4 | 3,039 | 2,759 | 1.72, 1.84, 1.93 / counterfactual 1.94 |
| 2 | 3.96 corrections (rounds 0–3), fixed point **not converged** | 46, 423.9, 423.2, 423.6, 433.4 | 3,081 | 2,759 | 1.77, 1.93, 2.05, 2.18 |
| 20 | 3.99 corrections (rounds 0–3) | 46, 423.5, 423.3, 423.0, 433.5 | 3,192 | 2,759 | 1.88, 2.14, 2.38, 2.61 |
| 21 | 3.99 corrections (rounds 0–3) | 46, 423.7, 423.3, 423.1, 433.4 | 3,201 | 2,759 | 1.89, 2.17, 2.41, 2.65 |
| 22 | 3.97 corrections (rounds 0–3) | 46, 423.2, 422.8, 423.1, 433.4 | 3,088 | 2,759 | 1.77, 1.93, 2.07, 2.20 |

- **s0: "corrected once, then honest".** It plays honest (434.1) after the correction, with falling counterfactual levels. This is the case the doc expects.
- **The other 5 seeds: the same level-farming as AS.** After round 0 they use **the original bug inside the window** in rounds 1–3 (window 1.0; true 421–424, against honest 434) to trigger another correction each round, then play honest in round 4. Each correction's level is higher than the last. That is not under-correction: in every seed the best single round after one correction is honest (true 434.05).
- **The same seeds under the other mechanisms.**
  - **Swap:** corrected once, then **the new exploit** at true 416.5–424.7 (honest 434).
  - **Standard PBRR** (`base_bonus1`): **hides** (true 59.8 ×4, then 46).
  - So comp's true return after the correction (rounds 1–3 about 423, round 4 433) is about the swap's level in rounds 1–3 and honest in round 4. Comp is corrected at once and does not hide.
- **s2's fixed point did not converge** (3.91–4.00 across iterations). Per rule 2 the last iteration is the target.

Pending: tomato_large, Taxi and Boat Race comp targets (1989675–1989677), and the comparison targets (1989678–1989681).

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

## 2026-11-15, iteration 2 (22:51–23:10): AS target: 4 corrections per episode, farming the level (flagged)

- **AS target.** **1989673** (`targets_absent_supervisor_comp`) COMPLETED 22:27 (2:39). It finished between my ticks, and I noticed it now.
  - In all 6 seeds the optimum is corrected in rounds 0–3: the open exploit in round 0, then the original bug inside the window in rounds 1–3 (true 400), then honest in round 4.
  - The level rises with each correction (11.7 → 13.6 per step).
  - V0 is 8,228–8,383, against V_hide 7,350.
  - Rule 2 table and explanation under "Exact predictions"; flagged at the top. It contradicts the doc's expected end state for AS. Per the prompt, I report it and do not adjust the mechanism.
- **Other target jobs.** Tomato (1989674) and tomato_large (1989675) are running. Taxi, Boat Race and the 4 comparison targets are pending (Priority).
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run): nothing; no wave-1 seed has finished. `... resume` (dry-run): nothing.
- **Cells DONE:** 0 of 6.

## 2026-11-15, iteration 3 (23:31–23:36): first wave-1 seeds finished; AS `LE` hides on its training curve; checks 1989826–1989829

- **AS `LE` finished.** **1989686** (AS `C1_comp_LE`, 3072 episodes) COMPLETED 23:30 (1:17:26, exit 0), much faster than other AS runs.
  - Its seeds' training logs show **hiding**: windows 0–3 exploited 0.00, off-window 1.00, final window 1.00, 0.01–0.02 corrections per episode, proxy over rounds 0–3 about 1,400.
  - With so few corrections there are almost no PBRR refits, which is why it was fast.
  - The exact target is 4 corrections per episode (iteration 2), so the check should show a large gap. Hiding is worth 7,350, against 8,228–8,383 for the target.
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed four runs; finished seeds were confirmed with `ls`:

  | Run | Finished | Still training |
  |---|---|---|
  | grid `C1_comp_L` | s1, s2 at 1536 | s0 at 1392 |
  | AS `C1_comp_L` | s1 at 3072 | s0 at 744, s2 at 2616 |
  | AS `C1_comp_LE` | all three | — |
  | Boat Race `C1_comp_L` | s2 at 1536 | s0 at 1440, s1 at 1368 |

  `... br_missing submit` → **1989826** (grid `L`), **1989827** (AS `L`), **1989828** (AS `LE`), **1989829** (Boat Race `L`).
- **Budget.** This campaign has 29 jobs (limit 30); all my jobs come to 60. Cells DONE: 0 of 6.

## 2026-11-15, iteration 4 (23:37–23:50): first comp verdicts. Grid `L` passes 2/2 (but not honest, flagged); AS mostly hides; AS `LE` → extend 6144 (1989830)

- **Checks back.** **1989826–1989829** COMPLETED; **1989682** (grid `C1_comp_L`) COMPLETED 23:37. Verdicts from `.venv/bin/python experiments/step4_convergence.py <run>`:
  - **grid `C1_comp_L`** (1536):
    - s1 **0.012** CONVERGED; s2 **0.011** CONVERGED.
    - Both policies are corrected in round 0, then **true −100** every round: they never reach the goal. They receive about 8,565–8,583 per round, against the best response's 8,692–8,705, which is honest after the correction (true 22). Flagged at the top: the 3% gap is loose under the level.
    - s0 finished after the check started → check **1989831**.
  - **AS `C1_comp_L`** (3072):
    - s1 **0.107** PLATEAU. It **hides**: 0 corrections, true about −62 per round. The best response and target take 4 corrections.
    - s0 (768) and s2 (2736) are still training. Their curves already take 1.6 and 3.2 corrections per episode, with true 320–410 and 220–303 per round.
  - **AS `C1_comp_LE`** (3072):
    - s0 **0.146** IMPROVING; s2 **0.143** IMPROVING. Both hide: 0 corrections, true about −108.
    - s1 **0.015** CONVERGED. It takes about 3.5 corrections with mixed rounds (true −72, 45, 168, 174, 148). Its best response takes 3 corrections.
  - **Boat Race `C1_comp_L`:** `NO TARGET`. The Boat Race comp target (1989677) is still queued, so its checks cannot be judged yet.
- **Rule 4, AS `C1_comp_LE`.** Seeds are labelled IMPROVING and 3072 is below the AS cap of 24,576, so extend 2×.
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor C1_comp_LE 6144` printed `submit.sh 48 --env absent_supervisor --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/absent_supervisor/comp --resume --extend-to 6144`.
  - Submitted: `... submit` → **1989830**.
- **Rule 3.** `br_missing` (dry-run: grid `C1_comp_L` s0; Boat Race `C1_comp_L` s0/s1, now finished) → `... br_missing submit` → **1989831**, **1989832**.
- **Budget.** This campaign has 26 jobs. Cells DONE: 0 of 6.

## 2026-11-15, iteration 5 (23:43–23:50): grid `C1_comp_L` 3/3 by the verdict (but true −100 after the correction) → `confirm` (1989835 ); Boat Race `LE` s0 → check 1989834

- **Grid result.** **1989831** (grid `C1_comp_L`, s0) COMPLETED 23:40.
  - s0 is **0.011**, CONVERGED. The run is **3/3 CONVERGED** (0.011 / 0.012 / 0.011).
  - In every seed PPO is corrected in round 0, then has **true −100** in every round, while the best response and the target are honest (22).
  - So the cell passes the 3% verdict without the honest behaviour (flag at the top, iteration 4).
- **Rule 4 (tuning run, all CONVERGED): `confirm`.** I apply the criterion as written and do not adjust it.
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid C1_comp_L` printed `submit.sh 48 --env grid --run-id C1_comp_L_confirm --seeds 20 21 22 --results-dir results/step4/grid/comp --set g.fine_only=True g.offset=True g.offset_margin=0.0 episodes=1536 anneal.last=0.25 anneal.floor=0.1`. That matches `run_sets.py`.
  - Submitted: `... submit` → **1989835 **.
  - If it is 3/3, the grid comp cell is DONE by the rules, with PPO's true return reported beside it. You may want to override that (flag).
- **Boat Race.** **1989697** (Boat Race `C1_comp_L`) COMPLETED 23:38. Check **1989832** (s0, s1) is done, but its verdicts wait for the Boat Race comp target (1989677, queued).
- **Rule 3.** `br_missing` (dry-run: Boat Race `C1_comp_LE`, s0 at 1536) → `... br_missing submit` → **1989834**.
- Cells DONE: 0 of 6.

## 2026-11-15, iteration 6 (23:49–23:53): Boat Race `C1_comp_LE` finished → check 1989841

- **Boat Race `LE` finished.** **1989698** (Boat Race `C1_comp_LE`) COMPLETED 23:48 (1:18:12, exit 0). Its s0 check **1989834** is done.
- **Rule 3.** `br_missing` (dry-run: Boat Race `C1_comp_LE`, s1 and s2) → `... br_missing submit` → **1989841**.
- **Boat Race verdicts are on hold.** They need the Boat Race comp target, 1989677, which is still queued.
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 7 (00:00–00:03): AS `C1_comp_L` s2 finished → check 1989851 

- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed AS `C1_comp_L`. s2 has finished at 3072; s0 is still training. Submitted with `... br_missing submit` → **1989851 **.
- **Boat Race `C1_comp_LE`.** Check **1989841** (s1, s2) is done. Its verdicts wait for the Boat Race comp target (1989677, still queued).
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 8 (00:06–00:10): AS `C1_comp_L` s2 0.001 CONVERGED (corrected once, then honest)

- **Check 1989851** (AS `C1_comp_L`, s2 at 3072) COMPLETED.
  - Gap **0.001**, CONVERGED.
  - PPO is corrected in round 0, then **honest** (true 443–448 per round).
  - Its best response takes 2 corrections (round 1 at true 400).
  - That is still the farming direction the target takes (4 corrections), but at this point a second correction is worth little.
- **The other seeds.** s1 **0.107**, PLATEAU, hides. s0 is still training (960/3072); its curve takes about 1.5 corrections per episode, with true about 315–405 per round.
- **Rule 4** waits for s0.
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 9 (00:16–00:19): grid `C1_comp_LE` finished → check 1989867; Boat Race `C1_comp_LN` s0/s1 → check 1989868

- **Training finished.** **1989683** (grid `C1_comp_LE`) COMPLETED 00:15 (2:06:26, exit 0).
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `C1_comp_LE`: all three seeds at 1536.
  - Boat Race `C1_comp_LN`: s0 and s1 at 1536; s2 at 528.

  `... br_missing submit` → **1989867** (grid `LE`), **1989868** (Boat Race `LN`).
- **Boat Race verdicts.** They are still waiting for the Boat Race comp target.
- **Tomato comp target.** The job (1989674) has written 5 of its 6 seed files; I will tabulate it once the job finishes.
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 10 (00:26–00:30): grid `C1_comp_LE` 3/3 by the verdict (true −100 after the correction) → `confirm` (1989878 )

- **The check.** **1989867** (grid `C1_comp_LE`, 1536) COMPLETED 00:21.
  - s0 **0.011**, s1 **0.011**, s2 **0.011**, all CONVERGED.
  - As with `C1_comp_L`, every policy is corrected in round 0 and then has true −100 in every round (it never reaches the goal), while the best response and the target are honest (22). This is the flag at the top.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid C1_comp_LE` printed `submit.sh 48 --env grid --run-id C1_comp_LE_confirm --seeds 20 21 22 --results-dir results/step4/grid/comp --set g.fine_only=True g.offset=True g.offset_margin=0.0 episodes=1536 anneal.last=0.25 anneal.floor=0.1 ppo.ent_coef=0.03`. That matches `run_sets.py`.
  - Submitted: `... submit` → **1989878 **.
  - It runs alongside `C1_comp_L_confirm` (1989835).
- **Boat Race.** Check **1989868** (Boat Race `C1_comp_LN`, s0 and s1) is done; its verdicts wait for the target.
- **Budget.** This campaign has 24 jobs. Cells DONE: 0 of 6.

## 2026-11-16, iteration 11 (00:37–00:42): grid `C1_comp_LN` finished → check 1989884

- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed grid `C1_comp_LN`, the last grid wave-1 run. `... br_missing submit` → **1989884**.
- **Targets still pending.**
  - The comp targets for Tomato (1989674) and tomato_large (1989675) are still running, about 2 h in.
  - Taxi, Boat Race and the comparison targets are queued.
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 12 (00:42–00:55): Tomato target (5 of 6 seeds farm the level, s0 corrected once then honest); grid `C1_comp_LN` s2 0.011

- **Tomato target.** **1989674** (`targets_tomato_comp`) COMPLETED 00:40 (2:12:31).
  - s0 is "corrected once, then honest" (434.1).
  - s1, s2, s20, s21 and s22 take 3–4 corrections, using the bug inside the window in rounds 1–3 (true about 423), with rising levels.
  - s2's fixed point did not converge.
  - Entered under "Exact predictions"; the farming flag at the top now covers Tomato too.
- **Grid check.** **1989884** (grid `C1_comp_LN`) COMPLETED. s2 **0.011** CONVERGED; it is corrected once, then true −100, like `L` and `LE`. s0 (1128) and s1 (1056) are still training, so rule 4 waits.
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 13 (01:16–01:20): AS `C1_comp_LE` reached 6144; checks 1989922–1989924

- **Training finished.** **1989830** (AS `C1_comp_LE`, extension to 6144) COMPLETED 01:14 (1:09:42, exit 0).
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - grid `C1_comp_LN`: s0 finished at 1536; s1 is at 1488.
  - AS `C1_comp_LE`: all three seeds at 6144.
  - Tomato `C1_comp_L`: s1 finished at 1536; s0 is at 648 and s2 at 672.

  `... br_missing submit` → **1989922** (grid `LN`), **1989923** (AS `LE`), **1989924** (Tomato `L`). The Tomato check is the first Tomato comp check.
- **Budget.** This campaign has 25 jobs. Cells DONE: 0 of 6.

## 2026-11-16, iteration 14 (01:25–01:32): grid `C1_comp_LN` 3/3 by the verdict (true −100 after the correction) → `confirm` (1989931 ); AS `C1_comp_LE` 1/3 at 6144 → extend 12,288 (1989932 )

- **Checks returned.** **1989922** (grid `C1_comp_LN`) and **1989923** (AS `C1_comp_LE`, 6144) COMPLETED. **1989684** (grid `C1_comp_LN` training) COMPLETED 01:20.
- **Grid `C1_comp_LN`** (1536): s0, s1, s2 are each **0.011**, all CONVERGED.
  - Every seed is corrected in round 0, then has true −100 (flag at the top).
  - All three grid comp configs (`L`, `LE`, `LN`) now pass the verdict this way.
- **AS `C1_comp_LE`**, BR gap at 3072 → 6144:

  | Seed | 3072 | 6144 | Verdict | Behaviour |
  |---|---|---|---|---|
  | s0 | 0.146 | **0.139** | IMPROVING | hides |
  | s1 | 0.015 | **0.013** | CONVERGED | corrected once, then honest |
  | s2 | 0.143 | **0.143** | IMPROVING | hides |

  The best responses of s0 and s2 take 4 corrections (the farming end state); s1's best response takes 3.
- **Rule 4, grid `C1_comp_LN`: all CONVERGED, so `confirm`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm grid C1_comp_LN` printed `submit.sh 48 --env grid --run-id C1_comp_LN_confirm --seeds 20 21 22 --results-dir results/step4/grid/comp --set g.fine_only=True g.offset=True g.offset_margin=0.0 episodes=1536 anneal.last=0.25 anneal.floor=0.1 n_envs=64 ppo.batch_size=1600`. That matches `run_sets.py`.
  - Submitted: `... submit` → **1989931 **.
- **Rule 4, AS `C1_comp_LE`: seeds IMPROVING, below the cap, so extend 2×.**
  - Dry-run: `... extend absent_supervisor C1_comp_LE 12288` printed `submit.sh 48 --env absent_supervisor --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/absent_supervisor/comp --resume --extend-to 12288`.
  - Submitted: `... submit` → **1989932 **.
- Cells DONE: 0 of 6.
