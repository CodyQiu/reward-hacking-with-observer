# Step 4 compensated-correction campaign: decision log

Procedure: `docs/step4_comp.md` (with the criteria, rules and commands of `docs/step4_optimal.md` as changed there). Loop prompt: `docs/step4_loop_prompt.md`, campaign (C). Append-only below the two summary sections; every driver command runs with `CAMPAIGN=comp`.

## Status

**Cells DONE: 3 of 6.**

**Tomato: DONE (iteration 59). PPO is corrected once, then nearly honest; the target farms the level.**
- **The config.** `C1_comp_LN` (the frozen Step 3 config with the comp settings, `n_envs=64 ppo.batch_size=1600`), at 1536 episodes.
  - Tuning seeds 0–2: 0.002 / 0.002 / 0.006.
  - Confirmation seeds 20–22: 0.025 / 0.025 / 0.005.
  - Neither run was extended.
- **Behaviour.** In all six seeds PPO is corrected in round 0, then plays nearly honest: true about 432 against honest 434.1.
  - The targets of 5 of these 6 seeds farm the level instead: 3–4 corrections, true about 423 in rounds 1–3.
  - The best responses under PPO's own corrections farm in s20 and s21 (3.98 corrections, true about 426), but not much: PPO is within 2.5% of them.
  - So PPO's true return after its correction (about 432) is higher than the target's (about 423), and PPO does not farm.
- **Other Tomato runs.** `C1_comp_L` 3/3 (its confirmation 1990357 is information only now). `C1_comp_LE` 3/3; its confirmation's check at 3072 (1991014) is information only.

**Absent Supervisor: DONE (iteration 43). PPO matches the target's end state: it farms the level.**
- **The config.** `C1_comp_LN` (the frozen Step 3 config with the comp settings, `n_envs=64 ppo.batch_size=1600`), at 3072 episodes.
  - Tuning seeds 0–2: 0.001 / 0.001 / 0.002.
  - Confirmation seeds 20–22: 0.001 / 0.003 / 0.002.
  - Neither run was extended.
- **Behaviour.** In all six seeds PPO takes about 4 corrections per episode: the open exploit in round 0, then the bug inside the window in rounds 1–3 (true about 400), then honest in round 4 (about 449). That is the target's end state.
  - The best response under PPO's own corrections takes 2–4 corrections.
  - So PPO behaves as comp's exact optimum does: it farms the level (flag below). It is not "corrected once, then honest".
- **Other AS runs.** `C1_comp_L` finished 2/3 (s1 hides). `C1_comp_LE` reached the 24,576 cap with s2 hiding (0.143); its s0/s1 checks (1990449) are information only.

**Grid: DONE by the verdict, but PPO is not honest after its correction.**
- **The config.** `C1_comp_L`, the env's frozen Step 3 config with the comp settings, at 1536 episodes.
  - Tuning seeds 0–2: 0.011 / 0.012 / 0.011.
  - Confirmation seeds 20–22: 0.011 / 0.011 / 0.011.
  - Neither run was extended.
- **The caveat.** In all six seeds PPO is corrected in round 0 and then never reaches the goal (true −100 every round). The target and the best response are honest (true 22). The 3% verdict passes it because the level makes missing the goal only about 1.2% of V (flag below).
- **By a behavioural criterion this cell is not DONE.**
- **Other grid runs.** `C1_comp_LE` and `C1_comp_LN` show the same thing. Their confirmations (1989878, 1989931) are information only now.

## Flags for the user

- **NEW (2026-11-16): node wheat-06 is down** (`sinfo`: `down*`, "Not responding"). It killed the bonus campaign's Tomato no-reg `LN_confirm` (NODE_FAIL; flagged in docs/step4_bonus_log.md). None of this campaign's jobs were on it. Every submit now carries `EXCLUDE=barley-04,wheat-06` while it is down.

- **barley-04.** Every submit carries `EXCLUDE=barley-04`, your standing instruction from the optimal campaign, kept in the bonus and noreg_fail campaigns too. On 2026-11-14 `sinfo` showed barley-04 `allocated` with no reason set. Say if I should drop the exclusion.
- **AS (6/6 seeds), Tomato (5/6), tomato_large (4/6), Taxi (2/6) and Boat Race (6/6): the comp target farms the level; the doc expected one correction, then honest (iterations 2, 12, 24, 35 and 68, 2026-11-15/17).** In tomato_large the target's fixed point did not converge in s1, s2 and s21 (the last iteration is the target, per rule 2). In Boat Race, 5 of 6 seeds farm while honest by the true reward. In Taxi's two farming seeds the first correction also under-corrects (iteration 24); the other 4 Taxi seeds are corrected once, then honest. Tomato's farming seeds take 3–4 corrections, use the bug inside the window in rounds 1–3 (true about 423 against honest 434) and have rising levels; Tomato s0 is corrected once, then honest. Details for AS below.
  - **End state.** All 6 AS comp targets are corrected in every round 0–3. In rounds 1–3 the optimum uses the original bug inside the audit window (true 400 against honest 450), and each correction's level rises (11.8 → 13.5 per step).
  - **Why.** The level formula carries the previous level inside V_before. So each correction adds (R_caught − V_ref,after) / T_sub, and in AS the reference's return under the new correction (about 372) is below the agent's own nearly honest caught play (420–442).
  - **What I am doing.** This is the exact answer for this mechanism. I am not changing anything; wave 1 runs as planned, and PPO's target is this end state. A different level rule would be a mechanism change, which is your call (for example, basing V_ref,after on the agent's own honest play, or not compounding the level).
- **Under comp, the 3% verdict can pass a policy that is not honest after its correction (iteration 4, 2026-11-15).**
  - **Example.** Grid `C1_comp_L` s1 and s2 are CONVERGED (0.012 and 0.011), but PPO's true return is −100 in every round. It is corrected in round 0, keeps the windows clean, then never reaches the goal. The best response and the target are honest after the correction (true 22).
  - **Why the verdict passes it.** The level makes every round worth about 8,690 received, so missing the goal (−122 per round) is only 1.2% of V0 (about 43,500). That is inside the 3% tolerance.
  - **Scope.** The same holds wherever the level dwarfs the honest-vs-exploit difference.
  - **What I am doing.** I apply the criterion as written (never adjust criteria), so these seeds count as CONVERGED, and I report PPO's true return beside every verdict. A behavioural criterion for comp would be your call: for example, PPO's true return by round within x of the best response's, or the gap measured on the true reward.
- **Boat Race `C1_comp_LN` was confirmed before its target existed (iteration 31, 2026-11-16).** The Boat Race comp target (1989677) has been queued at low priority since 21:58. `step4_convergence.py` prints NO TARGET for every Boat Race seed, but its CONVERGED verdict uses only the best-response gap (`br["gap"] <= TOL_BR`, 0.03); the target matters only for IMPROVING / PLATEAU and the report. All three `LN` seeds have gaps ≤ 0.03 (0.021, 0.022, 0.000), so I submitted `confirm` (1990212) without waiting. Say if you would rather I wait for targets in future.
- **Taxi runs will hit the 48 h limit** (docs/step4_comp.md, wave 1). Rule 1 resumes them from their checkpoints; that is not an incident. **Measured (iteration 24):** a Taxi PBRR round at 1000 epochs takes about 60 s, and once PPO is corrected in most episodes, 24 episodes take 3–6 h (`C1_comp_L` s1: 204 rounds in 12,000 s). The noreg_fail Taxi runs show the same. At that rate a 768-episode run needs about 3–4 jobs of 48 h. The seeds are computing (full CPU), not stuck.

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

**Taxi, compensated correction** (job 1989676; all 6 fixed points converged; the mean-table optimum differs from most single draws: in s0, for example, 1 of 6 draws is "corrected once, then honest" and the others take 2–4 corrections):

| Seed | End state | True by round (k = 0..4) | Windows k = 0..4 | V0 | V_hide | Level per step at corrections 1–4 |
|---|---|---|---|---|---|---|
| 0 | corrected in round 0, then never again | −88.2, 124.8 ×4 | 1, 0, 0, 0, 0 | 1,941 | 1,794 | **2.68** / counterfactual 2.69, 2.53, 2.34 |
| 1 | the same | −88.2, 124.7 ×4 | 1, 0, 0, 0, 0 | 1,951 | 1,794 | **2.69** / counterfactual 2.71, 2.60, 2.45 |
| 2 | the same | −88.2, 124.7 ×3, 124.6 | 1, 0, 0, 0, 0.2 | 1,871 | 1,794 | **2.48** / counterfactual 2.35, 2.09, 1.80 |
| 20 | the same | −88.2, 124.7 ×4 | 1, 0, 0, 0, 0 | 1,925 | 1,794 | **2.63** / counterfactual 2.56, 2.39, 2.14 |
| 21 | **2.86 corrections** (by round 1.0, 0.88, 0.70, 0.28) | −88.2, −1.3, 14.7, 50.3, 64.4 | 1, 0.9, 0.7, 0.3, 0.5 | 2,492 | 1,794 | 2.69, 3.81, 4.26 / counterfactual 3.90 |
| 22 | **3.56 corrections** (by round 1.0, 1.0, 0.82, 0.75) | −88.2, −53.9, 1.4, 19.6, 22.7 | 1, 1.0, 0.8, 0.7, 0.7 | 2,788 | 1,794 | 2.62, 4.13, 4.87, 5.22 |

- **4 of 6 seeds (s0, s1, s2, s20): corrected in round 0, then honest.** True 124.6–124.8 after the correction (honest 125). This is the behaviour the doc wants, with V0 beating hiding by 77–157.
  - The best single round after one correction is honest in all four (true 124.6–124.8). The counterfactual second correction's level is about equal to the first (s0 2.69 vs 2.68, s1 2.71 vs 2.69) or lower, so a second caught round does not pay.
- **2 of 6 seeds (s21, s22): the original bug, under-corrected, plus level farming.** After round 0 they keep using the bug inside the window (rounds 1–3) and are corrected 2.86 / 3.56 times per episode. Each correction's level is higher than the last (s22: 2.62 → 4.13 → 4.87 → 5.22).
  - **Unlike AS and Tomato, the first correction under-corrects here.** The best single round after it is *not* honest: true 1.2 (s21) and −51.8 (s22), received 495 / 531 against honest's 352 / 310. The fines also spill onto honest play (honest after one correction earns 42 / 77 less than honest true + level). So part of the bug stays profitable, and the rising level adds to it.
- **The same seeds under the other mechanisms.**
  - **Swap** (seeds 0–2, the existing 1000-epoch targets; seeds 20–22 from 1989678, all fixed points converged): corrected once, then **a new exploit** in all 6 seeds, at true −66.5 / −65.7 / −56.9 / −48.1 / −65.7 / −50.3 (s0, s1, s2, s20, s21, s22). V0 3,677–5,985 against V_hide 1,794.
  - **Standard PBRR** (`base`): s0 hides (true −65.9 ×4, then −88.2). The other seeds were not computed: the job was cancelled at the user's request (iteration 70).
  - **No regulariser** (noreg_fail's targets, for information): corrected once, then a new exploit at true −70 to −81 in 5 seeds; s22 takes 2 corrections, true −86 to −90.
  - So in Taxi comp is the only one of the three mechanisms whose optimum is honest after the correction, in 4 of 6 seeds.

**Boat Race, compensated correction** (job 1989677, 4:52; all 6 fixed points converged; 34 of 36 draws have the seed's end state, and s0 has 2 draws with 3 corrections):

| Seed | End state | True by round (k = 0..4) | Windows k = 0..4 | Received by round | V0 | V_hide | Level per step at corrections 1–4 (all actual) |
|---|---|---|---|---|---|---|---|
| 0 | **4 corrections** (rounds 0–3) | −94, 50 ×4 | 1, 1, 1, 1, 0 | 200, 207, 213, 220, 231 | 1,071 | 928 | 1.61, 1.69, 1.75, 1.82 |
| 1 | the same | −94, 50 ×4 | 1, 1, 1, 1, 0 | 200, 213, 226, 240, 253 | 1,132 | 928 | 1.63, 1.77, 1.90, 2.04 |
| 2 | the same | −94, 50 ×4 | 1, 1, 1, 1, 0 | 200, 213, 226, 239, 253 | 1,132 | 928 | 1.63, 1.77, 1.90, 2.04 |
| 20 | **4 corrections**, the original bug every round | **−94 every round** | 1 ×5 | 200, 328, 448, 566, 684 | 2,226 | 928 | 1.61, **2.90, 4.09, 5.27** |
| 21 | 4 corrections (rounds 0–3) | −94, 50 ×4 | 1, 1, 1, 1, 0 | 200, 208, 215, 223, 234 | 1,079 | 928 | 1.61, 1.69, 1.77, 1.84 |
| 22 | the same | −94, 50 ×4 | 1, 1, 1, 1, 0 | 200, 211, 222, 232, 243 | 1,108 | 928 | 1.61, 1.73, 1.83, 1.94 |

- **5 of 6 seeds: honest by the true reward, but corrected in every audited round.** After round 0 the true return is 50 every round, which is honest. Yet the optimum also touches the bug inside the window in rounds 1–3 (window 1.0), which triggers another correction each round.
  - In Boat Race the checkpoint bonus can be collected without losing any true reward, so "honest plus one touch of the bug in the window" is free.
  - Each correction then installs a slightly higher level (s0: 1.61 → 1.82 per step), so this farms the level while staying honest.
  - The best single round after one correction is honest (true 50; received 211–213).
- **s20: the original bug, under-corrected, plus farming.** It exploits through every window (true −94 every round).
  - Its first correction leaves the exploit worth more than honest within a round: the exploit after one correction earns 328, honest 211.
  - Its levels rise steeply (1.61 → 5.27), as in Taxi's farming seeds.
- **The same seeds under the other mechanisms.**
  - **Swap** (1989680, 7:01, 2026-11-17; `g.epochs=1000`; all 6 fixed points converged, all 36 draws "corrected in round 0, then never again"): corrected once in round 0 in every seed, then off the bug in every window (window 0 in rounds 1–4).
    - **A new exploit in 5 of 6 seeds:** true −82 / −76 / −76 / −82 / −76 per round after the correction (s0, s2, s20, s21, s22; honest 50). The swap raises transitions that are not honest laps, and the best round after one correction farms them (received 359–462, against honest 295–365 under the same correction).
    - **s1 is near honest:** true 44 per round after the correction (received 277 vs honest 266.5).
    - V0 1,308–2,048 against V_hide 928.
  - **Standard PBRR:** not computed; cancelled at the user's request (iteration 70).
  - **No regulariser** (noreg_fail's targets, for information): a new exploit after the correction, true −58 to −100 (1–3 corrections).
  - So in Boat Race comp's optimum is honest by the true reward in 5 of 6 seeds (it farms the level while doing so); the swap's is near honest in 1 of 6 (a new exploit in 5); no regulariser's is honest in none.
- **PPO so far (iteration 31):** in 8 of 9 tuning seeds PPO is corrected once and then honest (true 50), and the best responses match the 4-correction farming. So PPO's true return equals the target's; only its number of corrections differs.

**tomato_large, compensated correction** (job 1989675, 1-02:55:51; fixed points converged in s0, s20 and s22, **not in s1, s2 or s21**; honest true per round about 522.6):

| Seed | End state | True by round (k = 0..4) | Windows k = 0..4 | V0 | V_hide | Level per step at corrections 1–4 |
|---|---|---|---|---|---|---|
| 0 | corrected in round 0, then never again | 65, 522.6 ×3, 506.9 | 1, 0, 0, 0, 0.7 | 3,920 | 3,687 | **2.61** / counterfactual 2.58, 2.48, 2.34 |
| 1 | 1.99 corrections (by round 1.0, 0.69, 0.22, 0.07); fixed point **not converged** | 65, 503.8, 516.3, 520.3, 506.4 | 1, 0.7, 0.2, 0.1, 0.6 | 3,964 | 3,687 | 2.69, 2.79 / counterfactual 2.79, 2.71 |
| 2 | 2.50 corrections (by round 1.0, 0.71, 0.33, 0.46); **not converged** | 65, 504.7, 513.8, 509.3, 502.0 | 1, 0.7, 0.3, 0.5, 0.7 | 3,973 | 3,687 | 2.72, 2.83, 2.85 / counterfactual 2.82 |
| 20 | **4 corrections** (rounds 0–3) | 65, 506.8, 505.2, 504.5, 514.9 | 1, 1, 1, 1, 0.4 | 4,175 | 3,687 | 2.94, 3.25, 3.48, 3.68 |
| 21 | 3.76 corrections; **not converged** | 65, 504.5, 502.6, 506.5, 512.7 | 1, 1, 1, 0.8, 0.4 | 4,037 | 3,687 | 2.81, 2.98, 3.07, 3.13 |
| 22 | corrected in round 0, then never again | 65, 522.6 ×3, 511.6 | 1, 0, 0, 0, 0.6 | 3,923 | 3,687 | **2.62** / counterfactual 2.59, 2.49, 2.32 |

- **s0, s22: corrected in round 0, then honest** in rounds 1–3 (522.6 = honest). Round 4, where an audit has no consequence, uses the bug in its final window. The counterfactual second corrections pay less, so there is no farming. This is the behaviour the doc wants.
- **s20 (converged), s21, s1, s2 (not converged): the original bug inside the window after round 0, with 2–4 corrections and rising levels.** This is the same level-farming as AS and Tomato, with true about 503–520 against honest 523.
  - It is not under-correction: in every seed the best single round after one correction has true 501–517, close to the honest round (honest after one correction: received 783–817).
  - The fixed points of s1, s2 and s21 did not converge (the iteration cycles between 1.8 and 3.0 corrections). Per rule 2 the last iteration is the target. Flagged at the top.
- **The same seeds under the other mechanisms.**
  - **Swap:** corrected once, then **a new exploit** at true 483–501 (honest 523).
  - **Standard PBRR** (`base_bonus1`): **hides** in all 6 (true 84.2 ×4, then 65).
  - **No regulariser** (for information): 3–4 corrections, true about 516–522.
- **So in tomato_large** comp's optimum is corrected once, then honest in 2 of 6 seeds, and farms the level in 4. The swap ends in a new exploit in all 6, and standard PBRR hides in all 6.

All comparison targets that were not cancelled are in (the Boat Race swap target finished 2026-11-17, iteration 76). The standard-PBRR comparison targets were cancelled at the user's request on 2026-11-17 (iteration 70). Only Taxi base s0 finished: it hides (true −65.9 ×4, then −88.2; V0 = V_hide = 1,794).

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

## 2026-11-16, iteration 15 (01:38–01:41): first Tomato comp check. `C1_comp_L` s1 is honest from round 0 and never corrected (gap 0.286)

- **Check result.** **1989924** (Tomato `C1_comp_L`, s1 at 1536) COMPLETED: s1 **0.286** (s.e. 0.000), labelled IMPROVING.
  - **PPO** is honest from round 0: true 429–431 in every round, never exploits, 0 corrections.
  - **Its best response** exploits in round 0 (true 46), is corrected once, and is then honest (433.6–433.9).
  - **Why the gap is large.** Under comp a correction pays a level for the rest of the episode. Never being caught gives up that level, about 1.6 per step for 400 steps. That is 28.6% of V.
- **The other seeds** are still training (s0 at 792, s2 at 816):
  - s0's curve is corrected once, then reaches true about 422. That is below honest (434), with the window clean.
  - s2's curve already looks like its farming target: window 0.998, about 3 corrections, true about 422 in rounds 1–3.
- **Next.** Rule 4 waits for s0 and s2.
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 16 (02:20–02:22): grid `C1_comp_L_confirm` finished at 1536 → check 1990058 

- **Training finished.** **1989835** (grid `C1_comp_L_confirm`, seeds 20–22) COMPLETED 02:18 (1:42:23, exit 0).
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `C1_comp_L_confirm`) → `... br_missing submit` → **1990058 **.
- **What the check decides.** If it is 3/3, the grid comp cell is DONE by the rules as written. Those rules count a policy that is not honest after its correction (true −100) as converged; see the flag at the top.
- Cells DONE: 0 of 6.

## 2026-11-16, iteration 17 (02:24–02:30): **grid DONE by the verdict** (`C1_comp_L_confirm` 3/3), with PPO not honest after its correction

- **Confirmation check.** **1990058** (grid `C1_comp_L_confirm`, seeds 20–22) COMPLETED 02:24.
  - s20 **0.011**, s21 **0.011**, s22 **0.011**, all CONVERGED.
  - Every policy is corrected in round 0, then has true −100 in every round. The best responses are honest (true 22 ×4).
- **Rule 4: the confirmation is 3/3, so the grid comp cell is DONE by the rules.**
  - Tuning run `C1_comp_L` was 3/3; the confirmation is 3/3; no extension.
  - I record this as the rules define it and do not adjust the criterion. The Status section and the flag at the top state that PPO's behaviour after the correction is not honest. By a behavioural criterion the cell would not be DONE.
- **Rule 6b: nothing new for grid comp.** Its other confirmations, `C1_comp_LE_confirm` (1989878) and `C1_comp_LN_confirm` (1989931), finish as information only.
- **Cells DONE:** 1 of 6.

## 2026-11-16, iteration 18 (02:27–02:30): grid `C1_comp_LE_confirm` finished (information only) → check 1990076 

- **Training finished.** **1989878** (grid `C1_comp_LE_confirm`) COMPLETED 02:27 (1:12:53, exit 0).
- **Information only.** The grid comp cell is DONE (iteration 17), so this run is information only.
- **Rule 3.** `br_missing` still checks it for the record: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run: grid `C1_comp_LE_confirm`) → `... br_missing submit` → **1990076 **.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 19 (02:32–02:35): grid `C1_comp_LE_confirm` (information only): s22 is nearly honest after its correction

- **Check result.** **1990076** (grid `C1_comp_LE_confirm`, seeds 20–22, 1536) COMPLETED 02:32.

  | Seed | Gap | Verdict | PPO after round 0 |
  |---|---|---|---|
  | s20 | **0.011** | CONVERGED | true −100 |
  | s21 | **0.011** | CONVERGED | true −100 |
  | s22 | **0.000** | CONVERGED | **corrected once, then nearly honest** (true 19.6, 20.7, 20.0, 19.0 against 22) |

  So the honest end state the target predicts is reachable by PPO under comp on the grid. It appears in 1 of the 12 grid comp seeds so far (9 tuning, 3 confirmation).
- **Status.** The grid cell is already DONE (iteration 17); this run is information only. Cells DONE: 1 of 6.

## 2026-11-16, iteration 20 (03:34–03:37): Tomato `C1_comp_L` finished; checks 1990155 1990156 

- **Training finished.** **1989688** (Tomato `C1_comp_L`) COMPLETED 03:34 (5:13:49, exit 0).
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - Tomato `C1_comp_L`: s0 and s2.
  - Boat Race `C1_comp_LN`: s2.

  `... br_missing submit` → **1990155 1990156 **.
- **Boat Race.** Its comp target (1989677) is still queued, so its checks cannot be judged yet.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 21 (03:45–03:48): grid `C1_comp_LN_confirm` finished (information only) → check 1990160 ; Boat Race `C1_comp_LN` finished

- **Training finished** (all exit 0):
  - **1989931**: grid `C1_comp_LN_confirm`, COMPLETED 03:45 (1:39:58). The grid cell is DONE, so this run is information only.
  - **1989699**: Boat Race `C1_comp_LN`, COMPLETED 03:34 (5:03:49).
- **Rule 3.** `br_missing` (dry-run: grid `C1_comp_LN_confirm`) → `... br_missing submit` → **1990160 **.
- **Boat Race.** Every Boat Race wave-1 seed now has a check (`L`, `LE`, `LN`). Their verdicts wait for the Boat Race comp target (1989677, still queued).
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 22 (04:00–04:03): grid `C1_comp_LN_confirm` (information only): 2 of 3 seeds honest after the correction; Tomato `C1_comp_L` s0 0.005

- **Grid `C1_comp_LN_confirm`.** Check **1990160** (seeds 20–22, 1536) COMPLETED 04:00. Every seed is CONVERGED:

  | Seed | Gap | After the correction |
  |---|---|---|
  | s20 | **0.000** | **honest** (true 21.8–22.0) |
  | s21 | **0.011** | true −100 |
  | s22 | **0.000** | **honest** (true 21.9–22.0) |

  - Across the 15 grid comp seeds so far, 3 are honest after the correction. All three come from the two confirmation runs `LE_confirm` and `LN_confirm`.
  - The cell is already DONE by the verdict (iteration 17), so this is information only.
- **Tomato `C1_comp_L`.** Check 1990155 is still running. It has reported s0: **0.005**, CONVERGED. s0 is corrected once, then nearly honest (true about 430 against 434), and its best response is corrected once, then honest. s2's result is pending.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 23 (04:06–04:10): Tomato `C1_comp_L` 2/3 at 1536 → extend 3072 (1990167 )

- **Check result.** **1990155** (Tomato `C1_comp_L`, s0 and s2) COMPLETED 04:05. Verdicts at 1536:

  | Seed | Gap | Verdict | PPO | Best response |
  |---|---|---|---|---|
  | s0 | **0.005** | CONVERGED | corrected once, then nearly honest (true about 429 against 434) | corrected once, then honest |
  | s1 | **0.286** | IMPROVING | honest from round 0, never corrected (iteration 15) | — |
  | s2 | **0.009** | CONVERGED | **farms like its target**: about 2.96 corrections, rounds 1–3 at true about 425 | 2.86 corrections |

  So, within one config, PPO reaches each of the three behaviours: corrected once then honest (s0), the level-farming the target predicts (s2), and never corrected (s1).
- **Rule 4 (s1 IMPROVING, 1536 < cap 12,288): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend tomato C1_comp_L 3072` printed `submit.sh 48 --env tomato --run-id C1_comp_L --seeds 0 1 2 --results-dir results/step4/tomato/comp --resume --extend-to 3072`.
  - Submitted: `... submit` → **1990167 **.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 24 (04:17–04:30): Taxi target (4 of 6 seeds corrected once, then honest; 2 farm); AS `C1_comp_LN` s0 → check 1990172

- **Taxi target.** **1989676** (`targets_taxi_comp`) COMPLETED 04:16 (3:09:15). All 6 fixed points converged.
  - **s0, s1, s2, s20:** corrected in round 0, then honest (true 124.6–124.8 against 125). V0 1,871–1,951 against V_hide 1,794. The level is 2.48–2.69 per step, and a counterfactual second correction would pay about the same or less.
  - **s21, s22:** 2.86 / 3.56 corrections per episode. They use the original bug inside the window in rounds 1–3, and the levels rise (s22: 2.62 → 5.22). Here the first correction also under-corrects: the best single round after it has true 1.2 / −51.8.
  - **Comparison.** Swap (seeds 0–2): corrected once, then a new exploit at true −57 to −67. Standard PBRR: pending (1989679).
  - Rule 2 table under "Exact predictions"; the flag at the top now lists Taxi (2/6).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_absent_supervisor_C1_comp_LN` (s0 finished at 3072; s1 at 2400 and s2 at 2688 are still training).
  - Submitted: `... br_missing submit` → **1990172**.
- **Taxi comp runs are slow, not stuck.** `C1_comp_LE` s1/s2 and `C1_comp_LN` s2 have written no checkpoint since about 22:35 and stay at episode 24. Their jobs use full CPU (sstat AveCPU about 34.6 CPU-h in 5.9 h over 6 CPUs).
  - `C1_comp_L` s1's last block took 12,000 s for 204 PBRR rounds, about 60 s per round at 1000 epochs.
  - The noreg_fail Taxi runs have 24-episode blocks of 9,000–37,000 s.
  - So this is the cost of PBRR rounds, not a bug. The rate is recorded under the Taxi flag at the top. Rule 1 resumes the runs at the 48 h limit (about 22:30 on 2026-11-17).
- **Pending targets.** tomato_large (1989675, running), Boat Race (1989677) and the 4 comparison targets (1989678–1989681), all queued. Cells DONE: 1 of 6 (grid, by the verdict only).

## 2026-11-16, iteration 25 (04:32–04:36): AS `C1_comp_L` finished (s0) → check 1990175; Tomato `C1_comp_LE` s0 → check 1990177

- **Training wait.** **1989685** (AS `C1_comp_L`, 3072) COMPLETED 04:32 (6:20:42, exit 0). s1 and s2 were already checked at 3072 (s1 0.107 PLATEAU, hides; s2 0.001 CONVERGED, corrected once, then honest).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_absent_supervisor_C1_comp_L` (s0) and `br_tomato_C1_comp_LE` (s0 finished at 1536; s1 and s2 are still training).
  - Submitted: `... br_missing submit` → **1990175** (AS), **1990177** (Tomato).
- Also queued: check **1990172** (AS `C1_comp_LN` s0). Cells DONE: 1 of 6.

## 2026-11-16, iteration 26 (05:04–05:10): AS `C1_comp_L` finished 2/3 (s1 hides, PLATEAU); AS `C1_comp_LN` s0 CONVERGED; AS `LE` reached 12,288; checks 1990186–1990188

- **Checks.** **1990175** (AS `C1_comp_L` s0) and **1990172** (AS `C1_comp_LN` s0) COMPLETED. `step4_convergence.py`:

  | Run, seed | BR gap | Verdict | PPO's true by round | PPO's end state | Best response |
  |---|---|---|---|---|---|
  | `L` s0 | **0.002** | CONVERGED | −107, 398, 399, 400, 448 | 4 corrections (farms, as the target does) | 3 corrections, then honest |
  | `L` s1 | **0.107** | PLATEAU | −63, −61, −62, −67, −113 | hides, never corrected | 4 corrections |
  | `L` s2 | **0.001** | CONVERGED | −114, 443, 448, 448, 448 | corrected once, then honest | 2 corrections, then honest |
  | `LN` s0 | **0.001** | CONVERGED | −108, 400, 400, 400, 449 | 4 corrections (farms, as the target does) | 3 corrections, then honest |

- **Rule 4.**
  - **`C1_comp_L`: finished, 2/3.** Every seed has a check, and the only unconverged seed (s1) is PLATEAU, so it is not extended.
  - **`C1_comp_LN`:** s1 (episode 2760) is still training.
  - **`C1_comp_LE`:** **1989932** COMPLETED 05:03 (2:34:22). All three seeds reached 12,288, which is half the AS cap (24,576).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed AS `C1_comp_LE` (12,288), AS `C1_comp_LN` (s2 at 3072) and Tomato `C1_comp_LN` (s0 at 1536). It also printed "tomato/C1_comp_LE: check still queued/running" (1990177).
  - Submitted: `... br_missing submit` → **1990186** (AS `LE`), **1990187** (AS `LN`), **1990188** (Tomato `LN`).
- **Rules 5 and 6b for AS.** Not yet. `LE` (12,288) and `LN` (s1, s2) still lack checks at their final episode counts, and `LN` can still be 3/3.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 27 (05:12–05:20): AS `C1_comp_LE` 2/3 at 12,288 (s2 IMPROVING) → extend to the cap, 24,576 (1990195); AS `LN` s2 and Tomato `LE` s0 CONVERGED; Tomato `LE` finished → check 1990194

- **Checks.** **1990186** (AS `LE` at 12,288), **1990187** (AS `LN` s2) and **1990177** (Tomato `LE` s0) COMPLETED. `step4_convergence.py`:

  | Run, seed | BR gap (history) | Verdict | PPO's true by round | Best response |
  |---|---|---|---|---|
  | AS `LE` s0 | 0.146 / 0.139 / **0.028** at 3072 / 6144 / 12,288 | CONVERGED | −78, 104, 107, 107, 73 | 3 corrections, then honest |
  | AS `LE` s1 | 0.015 / 0.013 / **0.013** | CONVERGED | −100, 253, 255, 255, 250 | 2 corrections, then honest |
  | AS `LE` s2 | 0.143 / 0.143 / **0.042** | IMPROVING | −66, −107, 368, 375, 367 | 3 corrections, then honest |
  | AS `LN` s2 | **0.002** at 3072 | CONVERGED | −100, 400, 400, 409, 450 | 4 corrections (farms, as the target does) |
  | Tomato `LE` s0 | **0.009** at 1536 | CONVERGED | 46, 424, 424, 425, 425 | corrected once, then honest (434) |

  - **AS `LE` s0 and s1 pass the verdict, but PPO's behaviour is not the best response's.** PPO is corrected less than once per episode (target corrections gap 3.65 / 3.36) and has true 104–255 per round, against the best response's 400–450. This is the case flagged at the top: the level makes the true-return shortfall a small fraction of V. Reported, not acted on.
- **Rule 4.**
  - **AS `C1_comp_LE` (wave 1; s2 IMPROVING): extend 2×**, which is the AS cap.
    - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend absent_supervisor C1_comp_LE 24576` printed `submit.sh 48 --env absent_supervisor --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/absent_supervisor/comp --resume --extend-to 24576`.
    - Submitted: `... submit` → **1990195**.
  - **AS `C1_comp_LN`:** s0 0.001 and s2 0.002 CONVERGED. s1 (episode 2832/3072) is still training. If it converges, `LN` is 3/3 and goes to `confirm`.
  - **Tomato `C1_comp_LE`:** **1989689** COMPLETED 05:11 (6:51:08); s1 and s2 finished.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_C1_comp_LE` (s1, s2). It also printed "tomato/C1_comp_LN: check still queued/running" (1990188).
  - Submitted: `... br_missing submit` → **1990194**.
- **Budget.** All my jobs: 45 (limit 110). Cells DONE: 1 of 6.

## 2026-11-16, iteration 28 (05:25–05:27): Tomato `C1_comp_LN` s0 0.002 CONVERGED (corrected once, then honest)

- **The check.** **1990188** (Tomato `C1_comp_LN` s0 at 1536) COMPLETED (10:51).
  - s0: BR gap **0.002**, CONVERGED. PPO is corrected in round 0, then honest (true 46, then 431.7–431.9 against 434.1), which matches the target's end state for s0.
  - s1 and s2 (episode 1248/1536) are still training. Both are corrected once and then nearly honest (true about 429), while their targets farm.
- **No action.** `br_missing` has nothing new; Tomato `LE` s1/s2's check (1990194) is queued. Cells DONE: 1 of 6.

## 2026-11-16, iteration 29 (05:43–05:47): AS `C1_comp_LN` finished (s1) → check 1990200

- **Training wait.** **1989687** (AS `C1_comp_LN`, 3072) COMPLETED 05:43 (7:26:48, exit 0). s0 (0.001) and s2 (0.002) were already CONVERGED.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_absent_supervisor_C1_comp_LN` (s1).
  - Submitted: `... br_missing submit` → **1990200**. If s1 converges, `LN` is 3/3 and goes to `confirm`.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 30 (05:53–06:00): Tomato `C1_comp_LE` 3/3 and AS `C1_comp_LN` 3/3 → `confirm` both (1990201, 1990202)

- **Checks.** **1990194** (Tomato `LE` s1, s2; 24:00) and **1990200** (AS `LN` s1; 0:57) COMPLETED. `step4_convergence.py`:

  | Run, seed | BR gap | Verdict | PPO's true by round | PPO's end state | Best response | Target |
  |---|---|---|---|---|---|---|
  | Tomato `LE` s0 | **0.009** | CONVERGED | 46, 424, 424, 425, 425 | corrected once, then nearly honest | corrected once, then honest (434) | corrected once, then honest |
  | Tomato `LE` s1 | **0.009** | CONVERGED | 46, 425, 425, 425, 425 | corrected once, then nearly honest | corrected once, then honest | 3 corrections (farms) |
  | Tomato `LE` s2 | **0.012** | CONVERGED | 45, 424, 423, 424, 425 | corrected once, then nearly honest | 2.77 corrections | 3.96 corrections (farms) |
  | AS `LN` s0 | **0.001** | CONVERGED | −108, 400, 400, 400, 449 | 4 corrections (farms) | 3 corrections | 4 corrections (farms) |
  | AS `LN` s1 | **0.001** | CONVERGED | −100, 400, 400, 430, 450 | about 3.4 corrections | 2 corrections | 4 corrections (farms) |
  | AS `LN` s2 | **0.002** | CONVERGED | −100, 400, 400, 409, 450 | about 3.8 corrections | 4 corrections | 4 corrections (farms) |

  - In Tomato, PPO's true return after its correction (423–425) is about 10 below honest (434). That is close to the farming targets' rounds 1–3 (421–424), and the best response under PPO's own corrections is honest or nearly so. All three seeds pass the verdict.
  - In AS, PPO farms the level just as the target does: corrected in rounds 0–2 or 0–3, using the bug inside the window (true 400).
- **Rule 4: all seeds CONVERGED in tuning runs → `confirm`.**
  - **Tomato.** Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm tomato C1_comp_LE` printed `submit.sh 48 --env tomato --run-id C1_comp_LE_confirm --seeds 20 21 22 --results-dir results/step4/tomato/comp --set ppo.ent_coef=0.1 g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 episodes=1536 anneal.last=0.25 anneal.floor=0.1 ...`. That equals `C1_comp_LE/overrides.json`. Submitted: `... submit` → **1990201**.
  - **AS.** Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm absent_supervisor C1_comp_LN` printed `submit.sh 48 --env absent_supervisor --run-id C1_comp_LN_confirm --seeds 20 21 22 --results-dir results/step4/absent_supervisor/comp --set ppo.ent_coef=0.1 ppo.batch_size=1600 g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 episodes=3072 anneal.last=0.25 anneal.floor=0.1 n_envs=64 ...`. That equals `C1_comp_LN/overrides.json`. Submitted: `... submit` → **1990202**.
- **Still running in these cells.** Tomato `C1_comp_L` (→ 3072, 1990167) and `C1_comp_LN` (s1, s2); AS `C1_comp_LE` (→ 24,576, 1990195).
- **Budget.** Comp jobs about 17 (limit 30); all my jobs 44 (limit 110). Cells DONE: 1 of 6.

## 2026-11-16, iteration 31 (06:06–06:20): Boat Race `C1_comp_LN` 3/3 by the best-response gap → `confirm` (1990212); the Boat Race target is still queued

- **Tick.** No job failed. Nothing to resume. `br_missing` is empty in all three campaigns. 43 jobs.
  - The Boat Race comp target (1989677) and the 4 comparison targets (1989678–1989681) are still PENDING (reason `Priority`). They have sat behind my training jobs since 21:58: priority about 0.48–0.49 × 10⁹, against 0.72 × 10⁹ for training jobs.
- **Boat Race verdicts without the target.**
  - `step4_convergence.py` prints NO TARGET for every Boat Race seed. Its CONVERGED verdict, however, is `br["gap"] <= TOL_BR` (0.03, `experiments/step4_br.py:64`), independent of the target; the target is needed only to tell IMPROVING from PLATEAU.
  - Best-response gaps at 1536, read from `<run>/step4_br/seed<s>_ep1536.json`:

  | Run, seed | BR gap (s.e.) | Verdict by the gap | PPO | Best response |
  |---|---|---|---|---|
  | `L` s0 | 0.021 (0.006) | CONVERGED | corrected in round 0, then honest (true −94, 50 ×4) | 4 corrections, true −94, 50 ×4 |
  | `L` s1 | 0.022 (0.006) | CONVERGED | the same | the same |
  | `L` s2 | 0.187 (0.004) | unconverged (needs the target) | hides (true −82 ×4, −94) | the same |
  | `LE` s0 | 0.021 (0.006) | CONVERGED | corrected in round 0, then honest | 4 corrections, true 50 after round 0 |
  | `LE` s1 | 0.025 (0.008) | CONVERGED | the same | the same |
  | `LE` s2 | 0.037 (0.005) | unconverged (needs the target) | the same | the same |
  | `LN` s0 | 0.021 (0.005) | CONVERGED | corrected in round 0, then honest; received 200, 211 ×4 | 4 corrections; received 200, 206, 212, 218, 229 |
  | `LN` s1 | 0.022 (0.007) | CONVERGED | the same; received 200, 213 ×4 | 4 corrections |
  | `LN` s2 | 0.000 (0.000) | CONVERGED | 3.99 corrections, true −94, 50 ×4 | 4 corrections |

  - **In Boat Race the best response farms the level while honest.** In every check it is corrected in all rounds 0–3 with true 50 (honest) in rounds 1–4. Its received return rises with each level (206 → 229). PPO is honest after its correction in 8 of 9 seeds.
- **Rule 4: `C1_comp_LN` has all seeds CONVERGED → `confirm`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm boat_race C1_comp_LN` printed `submit.sh 48 --env boat_race --run-id C1_comp_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/comp --set ppo.ent_coef=0.03 ppo.batch_size=1600 g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 episodes=1536 anneal.last=0.25 anneal.floor=0.1 n_envs=64 ...`. That equals `C1_comp_LN/overrides.json`.
  - Submitted: `... submit` → **1990212**. Flagged at the top: I did not wait for the target.
  - `L` and `LE` each have one seed whose IMPROVING / PLATEAU call needs the target. They wait.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 32 (06:24–06:27): Tomato `C1_comp_LN` finished → check 1990218 (s1, s2)

- **Training wait.** **1989690** (Tomato `C1_comp_LN`, 1536) COMPLETED 06:24 (8:02:12, exit 0). s0 was already CONVERGED (0.002).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_C1_comp_LN`.
  - Submitted: `... br_missing submit` → **1990218**.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 33 (06:57–07:05): Tomato `C1_comp_LN` 3/3 → `confirm` (1990232), alongside `C1_comp_LE_confirm`

- **The check.** **1990218** (Tomato `C1_comp_LN` s1, s2 at 1536) COMPLETED (16:12). `step4_convergence.py`:

  | Seed | BR gap | Verdict | PPO's true by round | Best response | Target |
  |---|---|---|---|---|---|
  | s0 | **0.002** | CONVERGED | 46, 431.8, 431.7, 431.9, 431.7 | corrected once, then honest (434.1) | corrected once, then honest |
  | s1 | **0.002** | CONVERGED | 46, 431.7, 432.1, 431.5, 432.2 | corrected once, then honest | 3 corrections (farms) |
  | s2 | **0.006** | CONVERGED | 46, 431.3, 431.6, 431.2, 431.2 | 2.82 corrections | 3.96 corrections (farms) |

  - In all three seeds PPO is corrected once, then nearly honest (true about 432 against 434). In two of the three, the best response under PPO's own corrections is honest too.
- **Rule 4: a tuning run with all seeds CONVERGED → `confirm`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm tomato C1_comp_LN` printed `submit.sh 48 --env tomato --run-id C1_comp_LN_confirm --seeds 20 21 22 --results-dir results/step4/tomato/comp --set ppo.ent_coef=0.03 ppo.batch_size=1600 g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 episodes=1536 anneal.last=0.25 anneal.floor=0.1 n_envs=64 ...`. That equals `C1_comp_LN/overrides.json`.
  - Submitted: `... submit` → **1990232**.
  - The Tomato cell is DONE when either `C1_comp_LE_confirm` (1990201) or `C1_comp_LN_confirm` is 3/3.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 34 (07:52–07:56): Taxi `C1_comp_L` s2 finished at 768 (it hides) → check 1990245 

- **Tick.** No job failed. Nothing to resume (the tomato_large and Taxi wave-1 runs reach 48 h at about 11:43). The Boat Race comp target and the 4 comparison targets are still queued.
- **Taxi `C1_comp_L` s2** finished at 768 (`metrics.json` in its listing), after 30,965 s of training. Its last training block shows the agent hiding: windows 0–3 exploited 0.00, off-window 0.93, 0.01 corrections per episode, final window 0.98. s2's target is "corrected in round 0, then honest". s0 (600/768) and s1 (432/768) are still training.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_L`.
  - Submitted: `... br_missing submit` → **1990245 **.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 35 (08:14–08:30): Boat Race target (farms in all 6 seeds, honest by the true reward in 5); verdicts: `LN` 3/3 (already confirming), `L` finished 2/3, `LE` → extend 3072 (1990246 )

- **Boat Race target.** **1989677** (`targets_boat_race_comp`) COMPLETED 08:14 (4:52). All 6 fixed points converged.
  - **s0, s1, s2, s21, s22:** 4 corrections per episode, true −94 then 50 ×4 (honest). In rounds 1–3 the optimum touches the bug inside the window, at no cost in true reward, and collects a slightly higher level each time (about 1.6 → 1.8–2.0 per step).
  - **s20:** 4 corrections, using the original bug every round (true −94). Its first correction leaves the exploit worth more than honest within a round (328 against 211), and its levels rise 1.61 → 5.27.
  - Rule 2 table under "Exact predictions"; the flag at the top now lists Boat Race.
- **Boat Race verdicts, now that the target exists.** `step4_convergence.py` gives the same CONVERGED calls as iteration 31 read from the gaps, and adds:

  | Run | Seeds | Verdict |
  |---|---|---|
  | `C1_comp_L` | s0 0.021, s1 0.022 CONVERGED; s2 0.187 **PLATEAU** (hides) | **finished, 2/3** |
  | `C1_comp_LE` | s0 0.021, s1 0.025 CONVERGED; s2 0.037 **IMPROVING** | extend |
  | `C1_comp_LN` | 0.021 / 0.022 / 0.000, all CONVERGED | 3/3; its confirmation (1990212) was submitted in iteration 31 |

- **Rule 4 for `C1_comp_LE` (wave 1, s2 IMPROVING): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh extend boat_race C1_comp_LE 3072` printed `submit.sh 48 --env boat_race --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/boat_race/comp --resume --extend-to 3072`.
  - Submitted: `... submit` → **1990246 **.
- **Still running:** check **1990245** (Taxi `C1_comp_L` s2).
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 36 (08:28–08:32): Taxi `C1_comp_L` s2 0.146 IMPROVING (hides); s0 finished → check 1990251 

- **The check.** **1990245** (Taxi `C1_comp_L` s2 at 768) COMPLETED (26:42).
  - s2: BR gap **0.146** (s.e. 0.001), IMPROVING. PPO hides: never corrected, with true −82 per round.
  - The best response and the target are "corrected in round 0, then honest" (true 124.7).
- **Rule 3.** s0 has now finished at 768; it also hides (true about −80 per round). s1 is at 456/768.
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_L`.
  - Submitted: `... br_missing submit` → **1990251 **.
  - The run is extended only after s1 finishes and is checked: extending overwrites a seed's model.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 37 (09:00–09:03): Taxi `C1_comp_L` s0 0.189 IMPROVING (hides)

- **The check.** **1990251** (Taxi `C1_comp_L` s0 at 768) COMPLETED (23:25).
  - s0: BR gap **0.189** (s.e. 0.002), IMPROVING. PPO hides: never corrected, with true about −80 per round. The best response is "corrected in round 0, then honest" (124.8).
  - With s2 (0.146, IMPROVING), two of three seeds are checked.
  - s1 (456/768) is still training. When it finishes and is checked, rule 4 extends the run to 1536 (Taxi cap 6144).
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 38 (09:31–09:36): checks for Tomato `C1_comp_L` (s0, s1 at 3072) and tomato_large `C1_comp_LN` (s1 at 1536)

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh br_missing` listed two runs:
    - Tomato `C1_comp_L`: s0 and s1 finished at 3072; s2 is still training in 1990167.
    - tomato_large `C1_comp_LN`, wave 1: s1 finished at 1536; s0 and s2 are still training.
  - Submitted: `... br_missing submit` → **1990308** (Tomato), **1990311** (tomato_large).
- **The tomato_large comp target** (1989675) is still running, now about 11 h. The tomato_large verdicts need it (NO TARGET until then).
- Cells DONE: 1 of 6.
- **09:36.** **1990167** (Tomato `C1_comp_L`, extended to 3072) COMPLETED 09:35 (4:26:43, exit 0). s2 has finished too. Check **1990308** was still PENDING then, and it reads the finished seeds when it starts, so it covers all three.

## 2026-11-16, iteration 39 (10:32–10:38): Tomato `C1_comp_L` 3/3 at 3072 → `confirm` (1990357 )

- **The check.** **1990308** (Tomato `C1_comp_L` at 3072; it started after training ended, so it covers all three seeds) COMPLETED (24:59). `step4_convergence.py`:

  | Seed | BR gap at 1536 → 3072 | Verdict | PPO's true by round | Best response | Target |
  |---|---|---|---|---|---|
  | s0 | 0.005 → **0.004** | CONVERGED | 46, 429–431 | corrected once, then honest | corrected once, then honest |
  | s1 | 0.286 → **0.004** | CONVERGED | 46, about 430 | corrected once, then honest | 3 corrections (farms) |
  | s2 | 0.009 → **0.007** | CONVERGED | 46, 430–431 | 2.77 corrections | 3.96 corrections (farms) |

  - s1 was honest from round 0 and never corrected at 1536. At 3072 it is corrected once, then nearly honest, like s0 and s2.
- **Rule 4: a tuning run with all seeds CONVERGED → `confirm`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04 bash scripts/farmshare/step4_optimal.sh confirm tomato C1_comp_L` printed `submit.sh 48 --env tomato --run-id C1_comp_L_confirm --seeds 20 21 22 --results-dir results/step4/tomato/comp --set ppo.ent_coef=0.03 g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 episodes=3072 anneal.last=0.25 anneal.floor=0.1 ...`. That is `C1_comp_L/overrides.json` at the run's final length, 3072.
  - Submitted: `... submit` → **1990357 **.
  - Tomato now has three confirmations running: `LE_confirm` (1990201), `LN_confirm` (1990232) and `L_confirm`. The cell is DONE when any one of them is 3/3.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 40 (11:58–12:05): checks for AS `C1_comp_LN_confirm` (s20, s21) and Boat Race `C1_comp_LN_confirm` (s21, s22)

- **Tick.** Nothing to resume in this campaign. Node wheat-06 went down (NODE_FAIL of a bonus job), so it is now excluded on every submit (flag at the top).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed two runs:
    - AS `C1_comp_LN_confirm`: s20 and s21 finished at 3072; s22 is still training.
    - Boat Race `C1_comp_LN_confirm`: s21 and s22 finished at 1536; s20 is still training.
  - Submitted: `... br_missing submit` → **1990417** (AS), **1990418** (Boat Race). Their `ExcNodeList` is `barley-04,wheat-06`.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 41 (12:04–12:07): first confirmation verdicts. AS `LN_confirm` s20, s21 and Boat Race `LN_confirm` s21, s22 CONVERGED

- **Checks.** **1990417** (AS `C1_comp_LN_confirm`) and **1990418** (Boat Race `C1_comp_LN_confirm`) COMPLETED.

  | Run, seed | BR gap | Verdict | PPO | Target (same seed) |
  |---|---|---|---|---|
  | AS s20 | **0.001** | CONVERGED | 4 corrections, true −100, 400 ×3, 449 (farms) | the same |
  | AS s21 | **0.003** | CONVERGED | the same | the same |
  | AS s22 | — | training (2952/3072) | farms, about 4 corrections | the same |
  | Boat Race s21 | **0.015** | CONVERGED | corrected once, then honest (true −94, 50 ×4) | 4 corrections, honest by the true reward |
  | Boat Race s22 | **0.023** | CONVERGED | the same | the same |
  | Boat Race s20 | — | training (552/1536) | the original bug every round, 4 corrections (true −94) | the same (under-corrected seed) |

  - Boat Race s20 is the seed whose target exploits the original bug in every round. It trains more slowly, with 4 PBRR rounds per episode.
- **Next.** AS is DONE if s22 converges; Boat Race is DONE if s20 converges.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 42 (12:16–12:20): AS `LN_confirm` finished; Tomato `LE_confirm` finished; checks 1990422–1990425

- **Training wait.** **1990202** (AS `C1_comp_LN_confirm`, 3072) COMPLETED 12:16 (5:21:14, exit 0). s20 and s21 were already CONVERGED.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed four runs (finished seeds checked with `ls`):
    - AS `C1_comp_LE` (→ 24,576): s2 finished; s0 at 24,288 and s1 at 23,784;
    - AS `C1_comp_LN_confirm`: s22;
    - Tomato `C1_comp_LE_confirm`: all three seeds at 1536;
    - Taxi `C1_comp_LN`: s1 at 768; s0 at 384 and s2 at 264.
  - Submitted: `... br_missing submit` → **1990422** (AS `LE`), **1990423** (AS `LN_confirm`), **1990424** (Tomato `LE_confirm`), **1990425** (Taxi `LN`).
  - If 1990423 converges, **AS is DONE**. If 1990424 is 3/3, **Tomato is DONE**.
- Cells DONE: 1 of 6.

## 2026-11-16, iteration 43 (12:48–12:55): **Absent Supervisor DONE** (`C1_comp_LN_confirm` 3/3)

- **The check.** **1990423** (AS `C1_comp_LN_confirm` s22 at 3072) COMPLETED (1:12). `step4_convergence.py`:
  - s20 **0.001**, s21 **0.003**, s22 **0.002**: all CONVERGED.
  - PPO's true by round in all three: −100, about 400 ×3, about 449. It takes 4 corrections per episode, matching the target (corrections gap 0.00).
- **Rule 4: a `_confirm` run with all seeds CONVERGED → the cell is DONE.**
  - Tuning `C1_comp_LN` was 3/3 at 3072 (0.001 / 0.001 / 0.002; iteration 30). Neither run was extended.
  - Status updated at the top. PPO reaches the exact optimum, and that optimum farms the level rather than being corrected once and then honest (flag 2).
- **AS `C1_comp_LE` reached the 24,576 cap.** **1990195** COMPLETED 12:48 (6:06:20).
  - s2: 0.143 at 24,576 (IMPROVING by the curve). It hides, with true about −106 per round.
  - The cell is DONE, so `LE` is information only: s0 and s1 are checked for the record.
    - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing`.
    - Submitted: `... br_missing submit` → **1990449**.
- **wheat-06** now shows `mixed-` in `sinfo`. I keep excluding it until it has run cleanly for a while; you can drop the exclusion.
- **Cells DONE: 2 of 6** (grid by the verdict only, AS). Open: Tomato (3 confirmations running; `LE_confirm`'s check 1990424 is running), tomato_large (target still running), Taxi (slow), Boat Race (`LN_confirm` s20 training).

## 2026-11-16, iteration 44 (13:10–13:15): Tomato `C1_comp_LE_confirm` 2/3 at 1536 (s21 0.032 IMPROVING) → extend 3072 (1990482 )

- **The check.** **1990424** (Tomato `C1_comp_LE_confirm` at 1536) COMPLETED (23:08). `step4_convergence.py`:

  | Seed | BR gap (s.e.) | Verdict | PPO's true by round | Best response | Target |
  |---|---|---|---|---|---|
  | s20 | **0.029** (0.001) | CONVERGED | 47, about 424 ×4 | 3.98 corrections, true about 426 | 3.99 corrections (farms) |
  | s21 | **0.032** (0.001) | IMPROVING | 46, 423–425 | 3.99 corrections | 3.99 corrections (farms) |
  | s22 | **0.012** (0.000) | CONVERGED | 45, 423–425 | 2.59 corrections | 3.97 corrections (farms) |

  - PPO is corrected about once per episode, then plays nearly honest (true about 424). The targets and best responses farm the level (3–4 corrections, true 423–426), so the gap is the farming PPO doesn't do.
- **Rule 4 (confirmation, one seed IMPROVING, below the 12,288 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend tomato C1_comp_LE_confirm 3072` printed `submit.sh 48 --env tomato --run-id C1_comp_LE_confirm --seeds 20 21 22 --results-dir results/step4/tomato/comp --resume --extend-to 3072`.
  - Submitted: `... submit` → **1990482 **.
- **Other Tomato confirmations running:** `LN_confirm` (1990232) and `L_confirm` (1990357). Cells DONE: 2 of 6.

## 2026-11-16, iteration 45 (13:15–13:17): Boat Race `C1_comp_LE` reached 3072 → check 1990496 

- **Training wait.** **1990246** (Boat Race `C1_comp_LE`, extended to 3072) COMPLETED 13:14 (0:59:55, exit 0).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_C1_comp_LE`.
  - Submitted: `... br_missing submit` → **1990496 **.
- Cells DONE: 2 of 6.
- **13:31.** Check **1990449** (AS `C1_comp_LE` s0, s1 at the 24,576 cap; information only, the AS cell is DONE) COMPLETED (1:08): seed0 0.048 IMPROVING;seed1 0.013 CONVERGED;seed2 0.143 IMPROVING.

## 2026-11-16, iteration 46 (13:36–13:40): Boat Race `C1_comp_LE` 1/3 at 3072 (worse than at 1536) → extend 6144 (1990524 )

- **The check.** **1990496** (Boat Race `C1_comp_LE` at 3072) COMPLETED (3:08). `step4_convergence.py`:

  | Seed | BR gap at 1536 → 3072 | Verdict | PPO's true after round 0 | Best response |
  |---|---|---|---|---|
  | s0 | 0.021 → **0.044** | IMPROVING | 43.8 | 4 corrections, honest by the true reward (50) |
  | s1 | 0.025 → **0.022** | CONVERGED | 39.7 | the same |
  | s2 | 0.037 → **0.082** | PLATEAU | 37.8 | the same |

  - **The extension made s0 and s2 worse.**
    - At 1536 all three were corrected once, then honest (true 50).
    - At 3072 they take 4 corrections per episode, like the target, but with true 38–44: they no longer finish the lap cleanly.
  - A plausible cause: `anneal.last=0.25` is taken over the new length, so the entropy and learning rate went back up for episodes 1536–2304. I have not verified this.
- **Rule 4 (wave-1 run, s0 IMPROVING, below the 12,288 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend boat_race C1_comp_LE 6144` printed `submit.sh 48 --env boat_race --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/boat_race/comp --resume --extend-to 6144`.
  - Submitted: `... submit` → **1990524 **.
- **Boat Race's cell** rests on `C1_comp_LN_confirm`: s21 and s22 are CONVERGED, and s20 is still training. Cells DONE: 2 of 6.

## 2026-11-16, iteration 47 (13:59–14:02): Taxi `C1_comp_LN` finished (all three seeds at 768)

- **Training wait.** **1989696** (Taxi `C1_comp_LN`) COMPLETED 13:59 (15:28:46, exit 0).
  - s0 and s2 went from 384 / 264 episodes at 12:16 to 768. Once PPO stopped being corrected, episodes became fast. s0's last blocks: windows 0–3 0.00, off-window 0.96, corrections 0.00–0.01 per episode, so it hides.
- **Rule 3.** Check **1990425** started at 13:38, before s0 and s2 finished, so it covers only s1. `br_missing` will list s0 and s2 once 1990425 ends; I'll submit them then.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 48 (14:27–14:30): Taxi swap comparison target (seeds 20–22) → under "Exact predictions"

- **The target.** **1989678** (`targets_taxi_P2swap`) COMPLETED (1:21:12). Seeds 0–2 already existed and were skipped, not overwritten.
  - Seeds 20–22: corrected in round 0, then a new exploit (true −48.1 / −65.7 / −50.3), as in seeds 0–2 (−56.9 to −66.5). All fixed points converged.
  - Added to the Taxi entry under "Exact predictions". In Taxi the swap never ends honest after its correction. Comp ends honest in 4 of 6 seeds (s0, s1, s2, s20) and farms in s21 and s22.
- Still queued: Taxi base (1989679) and Boat Race swap and base (1989680, 1989681). Cells DONE: 2 of 6.

## 2026-11-16, iteration 49 (14:38–14:43): Taxi `C1_comp_LN` 0/3 at 768 (all hide; s1, s2 IMPROVING) → extend 1536 (1990638 )

- **The check.** **1990425** (Taxi `C1_comp_LN` at 768) COMPLETED (58:27). It checked all three seeds: `step4_br/seed{0,1,2}_ep768.json` exist.

  | Seed | BR gap (s.e.) | Verdict | PPO's true by round | Best response and target |
  |---|---|---|---|---|
  | s0 | **0.180** (0.002) | PLATEAU | about −85 every round (hides, never corrected) | corrected in round 0, then honest (124.8) |
  | s1 | **0.121** (0.000) | IMPROVING | about −79 (hides) | the same (124.7) |
  | s2 | **0.099** (0.001) | IMPROVING | about −85 (hides) | the same (124.7) |

  - Like `C1_comp_L` s0 and s2, every Taxi `LN` seed hides: it exploits off-window and keeps the audit windows clean. The best response is to be corrected in round 0 and then be honest.
- **Rule 4 (wave-1 run, seeds IMPROVING, below the Taxi cap of 6144): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LN 1536` printed `submit.sh 48 --env taxi --run-id C1_comp_LN --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 1536`.
  - Submitted: `... submit` → **1990638 **.
- **Taxi rule 6b** starts once every wave-1 run has a check and none is 3/3. `C1_comp_L` s1 and `C1_comp_LE` are still training.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 50 (14:46–14:48): Boat Race `C1_comp_LN_confirm` finished → check 1990660  (s20)

- **Training wait.** **1990212** (Boat Race `C1_comp_LN_confirm`, 1536) COMPLETED 14:46 (5:46:09, exit 0). s21 (0.015) and s22 (0.023) are CONVERGED.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_C1_comp_LN_confirm` (s20).
  - Submitted: `... br_missing submit` → **1990660 **.
  - If s20 converges, **Boat Race is DONE**. s20 is the seed whose target uses the original bug in every round.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 51 (15:25–15:30): Boat Race `C1_comp_LN_confirm` 2/3 (s20 0.074 IMPROVING) → extend 3072 (1990749 )

- **The check.** **1990660** (Boat Race `C1_comp_LN_confirm` s20 at 1536) COMPLETED (2:58).
  - s20: BR gap **0.074** (s.e. 0.004), IMPROVING.
  - **PPO plays exactly the target's end state:** the original bug in every round, 4 corrections per episode, true −94 every round (target gaps: window 0.000, true 0.000, corrections 0.00).
  - But the best response under PPO's own corrections is "corrected in round 0, then honest" (true 50). Those corrections are fitted on PPO's play, and they fine the bug harder than the target's (fitted on the exact optimum's softened play). So the original bug no longer pays, and PPO falls 7.4% short.
  - s21 **0.015** and s22 **0.023** are CONVERGED (corrected once, then honest).
- **Rule 4 (confirmation, s20 IMPROVING, below the 12,288 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend boat_race C1_comp_LN_confirm 3072` printed `submit.sh 48 --env boat_race --run-id C1_comp_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/comp --resume --extend-to 3072`.
  - Submitted: `... submit` → **1990749 **.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 52 (15:53–15:57): Boat Race `C1_comp_LE` reached 6144; Taxi `C1_comp_LE` s1 finished → checks 1990811, 1990810

- **Training wait.** **1990524** (Boat Race `C1_comp_LE`, extended to 6144) COMPLETED 15:53 (2:00:36, exit 0).
- **Taxi `C1_comp_LE`.** s1 finished at 768; s2 is at 672 and s0 at 120 of 768. The seeds' speeds differ a lot, because a seed that is corrected often runs many slow PBRR rounds.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed both runs.
  - Submitted: `... br_missing submit` → **1990810** (Taxi `LE`, s1), **1990811** (Boat Race `LE`, 6144).
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 53 (16:03–16:06): Boat Race `C1_comp_LE` finished at 6144, 1/3 (s0, s2 PLATEAU)

- **The check.** **1990811** (Boat Race `C1_comp_LE` at 6144) COMPLETED (2:55):

  | Seed | BR gap at 1536 / 3072 / 6144 | Verdict | PPO's true after round 0 |
  |---|---|---|---|
  | s0 | 0.021 / 0.044 / **0.066** | PLATEAU | 37.8 |
  | s1 | 0.025 / 0.022 / **0.023** | CONVERGED | 49.7 |
  | s2 | 0.037 / 0.082 / **0.037** | PLATEAU | 49.8 |

  - All three take 4 corrections per episode, like the target. s0 has lost true reward since 1536 (50 → 37.8); s1 and s2 are honest by the true reward.
- **Rule 4.** Every unconverged seed is PLATEAU, so the run is finished (1/3) and not extended.
- **Rules 5 and 6b** don't apply to Boat Race: `C1_comp_LN` is CONVERGED 3/3. The cell rests on `C1_comp_LN_confirm` (→ 3072, 1990749; s20 0.074 IMPROVING, s21 and s22 CONVERGED).
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 54 (16:41–16:44): tomato_large `C1_comp_LN` s1: BR gap 0.343 (honest from round 0, never corrected); the target is still running

- **The check.** **1990311** (tomato_large `C1_comp_LN` s1 at 1536) COMPLETED (2:08:55). `step4_convergence.py` prints NO TARGET (the tomato_large comp target 1989675 is on seed 21, the 5th of 6). From `step4_br/seed1_ep1536.json`:
  - BR gap **0.343** (s.e. 0.000), above 0.03.
  - PPO never exploits in view and is never corrected: true about 520 every round, honest from round 0.
  - The best response is corrected in round 0 (true 65), then honest (about 523).
  - This is the same case as Tomato `C1_comp_L` s1 at 1536 (0.286, honest from round 0), which converged at 3072. Skipping the round-0 correction forgoes the level.
- **Whether `LN` is IMPROVING or PLATEAU** needs the target. s0 and s2 are still training.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 55 (16:48–16:51): Taxi `C1_comp_LE` s1 0.182, s2 0.172 (both hide, IMPROVING); s0 at 264/768

- **The check.** **1990810** (Taxi `C1_comp_LE`) COMPLETED (46:22). It covered s1 and also s2, which finished before the check reached it.
  - s1: **0.182**, IMPROVING.
  - s2: **0.172**, IMPROVING.
  - Both hide: never corrected, true −89 to −92 per round. The best response is corrected in round 0, then honest (124.7).
  - s0 is at 264/768. It is corrected often (true about −96 each round), so it trains slowly.
- **Rule 4** waits for s0's check: extending now would overwrite the checked seeds' models before s0 is done.
- **Taxi so far.** 8 of 8 checked seeds across `L`, `LN` and `LE` hide; the target is "corrected once, then honest" in 4 of 6 seeds.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 56 (16:59–17:02): Tomato `C1_comp_LN_confirm` s21 finished → check 1990981 

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_C1_comp_LN_confirm` (s21 finished at 1536; s20 and s22 still training).
  - Submitted: `... br_missing submit` → **1990981 **.
  - Tomato is DONE once a confirmation is 3/3; s20 and s22 follow.
- Cells DONE: 2 of 6.
- **17:21.** **1990232** (Tomato `C1_comp_LN_confirm`, 1536) COMPLETED (6:17:54, exit 0). s20 and s22 have finished too. Check **1990981** is still PENDING, so it will cover all three seeds. If it is 3/3, Tomato is DONE.

## 2026-11-16, iteration 57 (17:41–17:44): Tomato `C1_comp_LE_confirm` at 3072 → check 1991014 

- **Tick.** No job failed. Nothing to resume (Tomato no-reg `LN_confirm` in bonus is still held for the user).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_C1_comp_LE_confirm` (extended to 3072, 1990482).
  - Submitted: `... br_missing submit` → **1991014 **.
- **Also running:** check **1990981** (Tomato `C1_comp_LN_confirm`, all three seeds). Either confirmation at 3/3 makes **Tomato DONE**.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 58 (17:49–17:52): Taxi `C1_comp_LE` finished (s0) → check 1991028 

- **Training wait.** **1989695** (Taxi `C1_comp_LE`, 768) COMPLETED 17:49 (19:21:12, exit 0). s0 went from 264 to 768 episodes in about 1 h once its corrections stopped.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_LE` (s0).
  - Submitted: `... br_missing submit` → **1991028 **.
  - When it is in, all three Taxi wave-1 runs have checks except `C1_comp_L` s1, which is still training. Rule 4 then decides `LE`.
- Cells DONE: 2 of 6.

## 2026-11-16, iteration 59 (18:17–18:22): **Tomato DONE** (`C1_comp_LN_confirm` 3/3)

- **The check.** **1990981** (Tomato `C1_comp_LN_confirm` at 1536, all three seeds) COMPLETED (51:49). `step4_convergence.py`:

  | Seed | BR gap (s.e.) | Verdict | PPO's true by round | Best response | Target |
  |---|---|---|---|---|---|
  | s20 | **0.025** (0.001) | CONVERGED | 46, about 432 ×4 (corrected once) | 3.98 corrections, true about 426 | 3.99 corrections, about 423 |
  | s21 | **0.025** (0.001) | CONVERGED | 47, about 432 ×4 | 3.98 corrections | 3.99 corrections |
  | s22 | **0.005** (0.000) | CONVERGED | 46, about 432 ×4 | 2.57 corrections | 3.97 corrections |

- **Rule 4: a `_confirm` run with all seeds CONVERGED → the cell is DONE.**
  - Tuning `C1_comp_LN` was 3/3 at 1536 (0.002 / 0.002 / 0.006; iteration 33). Neither run was extended.
  - Status updated at the top.
- **Tomato's other runs are now information only:** `C1_comp_LE_confirm` (check 1991014 running) and `C1_comp_L_confirm` (1990357).
- **Cells DONE: 3 of 6** (grid by the verdict only, AS, Tomato). Open:
  - tomato_large: its target is still running;
  - Taxi: every checked seed hides;
  - Boat Race: `LN_confirm` s20 is extending to 3072.
- **18:22.** Check **1991014** (Tomato `C1_comp_LE_confirm` at 3072; information only, the cell is DONE) COMPLETED (33:17): seed20 0.028 CONVERGED;seed21 0.029 CONVERGED;seed22 0.010 CONVERGED. Not extended.

## 2026-11-16, iteration 60 (18:57–19:05): Taxi `C1_comp_LE` 0/3 at 768 (all hide) → extend 1536 (1991184); rule 6b starts in Taxi (1991185–1991188)

- **The check.** **1991028** (Taxi `C1_comp_LE` s0 at 768) COMPLETED (41:14).
  - s0: **0.196**, IMPROVING. It hides (true about −92 per round, never corrected).
  - With s1 (0.182) and s2 (0.172) from iteration 55, all three are IMPROVING and all hide.
- **Rule 4 (wave-1 run, seeds IMPROVING, below the Taxi cap of 6144): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LE 1536` printed `submit.sh 48 --env taxi --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 1536`.
  - Submitted: `... submit` → **1991184**.
- **Rule 6b: when to start (docs/step4_comp.md).** Every Taxi wave-1 run now has a check, and none is CONVERGED 3/3:

  | Run | Gaps at 768 | Status |
  |---|---|---|
  | `L` | s0 0.189, s2 0.146 | s1 at 600/768, still training |
  | `LN` | 0.180 / 0.121 / 0.099 | extending to 1536 |
  | `LE` | 0.196 / 0.182 / 0.172 | extending to 1536 |

  - All 8 checked seeds hide. The base is the run with the smallest mean gap: `C1_comp_LN` (0.133).
- **Dry-run.** `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh explore taxi comp C1_comp_LN` printed 4 submits on seeds 0–2 at 768 episodes, with the base's `task.obs=onehot g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 anneal.last=0.25 anneal.floor=0.1`:
  - `+ENT3`: `ppo.ent_coef=0.09`, `n_envs=64`;
  - `+ES10`: `ppo.ent_coef=0.03`, ES10 schedule, `n_envs=64`;
  - `+N4`: `n_envs=256 ppo.batch_size=6400`;
  - `+ES10+N4`: both.
  - All four are distinct: the base has no ES schedule.
- **Submitted:** `... submit` → **1991185** (`+ENT3`), **1991186** (`+ES10`), **1991187** (`+N4`), **1991188** (`+ES10+N4`).
  - Taxi trains slowly while seeds are corrected (about 60 s per PBRR round), so these will likely need rule-1 resumes.
- **Budget.** Comp jobs about 16 (limit 30); all my jobs 38 (limit 110). Cells DONE: 3 of 6.

## 2026-11-16, iteration 61 (19:59–20:02): Taxi `C1_comp_LN` reached 1536 → check 1991301; Boat Race `LN_confirm` s21, s22 at 3072 → check 1991302

- **Training wait.** **1990638** (Taxi `C1_comp_LN`, extended to 1536) COMPLETED 19:59 (2:48:54, exit 0). The seeds hide, so they train fast.
- **Boat Race `C1_comp_LN_confirm`** (→ 3072, 1990749): s21 and s22 finished at 3072; s20, the deciding seed, is at 2496.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed both runs.
  - Submitted: `... br_missing submit` → **1991301** (Taxi `LN`), **1991302** (Boat Race `LN_confirm` s21, s22).
- Cells DONE: 3 of 6.
- **20:06.** Check **1991302** COMPLETED (4:29): Boat Race `LN_confirm` s21 **0.015** and s22 **0.024** at 3072, both CONVERGED, both honest after the correction. s20 is at 2544/3072, still exploiting (true −94 every round); its window rate dropped from 1.0 to about 0.53 over the last block.

## 2026-11-16, iteration 62 (20:53–20:55): Boat Race `C1_comp_LN_confirm` reached 3072 → check 1991417  (s20)

- **Training wait.** **1990749** (Boat Race `C1_comp_LN_confirm`, extended to 3072) COMPLETED 20:53 (2:36:00, exit 0). s21 (0.015) and s22 (0.024) are CONVERGED at 3072.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_C1_comp_LN_confirm` (s20).
  - Submitted: `... br_missing submit` → **1991417 **.
  - If s20 converges, **Boat Race is DONE**.
- Cells DONE: 3 of 6.

## 2026-11-16, iteration 63 (20:59–21:03): Boat Race `C1_comp_LN_confirm` s20 still 0.074 at 3072 (IMPROVING by the curve) → extend 6144 (1991432 )

- **The check.** **1991417** (s20 at 3072) COMPLETED (2:56).
  - s20: BR gap **0.074** (s.e. 0.004), the same as at 1536. The verdict is IMPROVING by the 24-episode curve.
  - PPO still plays the target's end state: the original bug every round, 4 corrections, true −94. Its in-window exploit rate is now 0.93 (target gap 0.074).
  - The best response under PPO's own corrections is "corrected once, then honest".
  - s21 (0.015) and s22 (0.024) stay CONVERGED.
- **Rule 4 (confirmation, s20 IMPROVING, below the 12,288 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend boat_race C1_comp_LN_confirm 6144` printed `submit.sh 48 --env boat_race --run-id C1_comp_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/comp --resume --extend-to 6144`.
  - Submitted: `... submit` → **1991432 **.
- Cells DONE: 3 of 6.

## 2026-11-16, iteration 64 (21:35–21:38): tomato_large `C1_comp_LN` s2 finished at 1536 → check 1991542 

- **tomato_large `C1_comp_LN`:** s2 finished at 1536 (s1 was checked at 0.343); s0 is at 1440.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_large_C1_comp_LN`.
  - Submitted: `... br_missing submit` → **1991542 **.
- The tomato_large comp target (1989675) is still running. Cells DONE: 3 of 6.

## 2026-11-16, iteration 65 (21:47–21:50): Taxi `C1_comp_LN` finished at 1536, 0/3 (all hide, PLATEAU)

- **The check.** **1991301** (Taxi `C1_comp_LN` at 1536) COMPLETED (1:39:51):

  | Seed | BR gap at 768 → 1536 | Verdict | PPO |
  |---|---|---|---|
  | s0 | 0.180 → **0.135** | PLATEAU | hides (true about −83) |
  | s1 | 0.121 → **0.120** | PLATEAU | hides (true about −78) |
  | s2 | 0.099 → **0.098** | PLATEAU | hides (true about −85) |

  - The best response in every seed is "corrected in round 0, then honest" (124.7–124.8).
- **Rule 4.** Every unconverged seed is PLATEAU, so the run is finished (0/3) and not extended.
- **Rule 5 (wave 2)** waits until every Taxi wave-1 run is finished: `L` (s1 training; s0, s2 IMPROVING) and `LE` (→ 1536) are not. Rule 6b runs from `LN` (iteration 60).
- Cells DONE: 3 of 6.
- **22:13.** **1989693** (tomato_large `C1_comp_LN`, wave 1) COMPLETED (23:52:26, exit 0). s0 finished too. Check **1991542** started before that, so s0 gets its own check once `br_missing` lists it.

## 2026-11-16, iteration 66 (23:19–23:23): tomato_large `C1_comp_LE` s1 finished at 1536 → check 1991852

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_tomato_large_C1_comp_LE` (s1 finished; s0 at 1032 and s2 at 1296).
  - Submitted: `... br_missing submit` → **1991852**.
- The tomato_large comp target (1989675) is still running, at about 24 h of its 36 h. Cells DONE: 3 of 6.

## 2026-11-16, iteration 67 (23:55–23:59): tomato_large `C1_comp_LN` s2 0.003 (corrected once, then honest); checks 1991926 (`L` s1, s2), 1991927 (`LN` s0)

- **The check.** **1991542** (tomato_large `C1_comp_LN` s2 at 1536) COMPLETED (2:14:06). The verdict still needs the target, so the gap is read from `step4_br/seed2_ep1536.json`:
  - s2: BR gap **0.003**. PPO is corrected in round 0, then honest (true 65, then 519 ×4, against honest about 523). The best response takes 1.39 corrections.
  - s1 (iteration 54): 0.343, honest from round 0 and never corrected.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed two runs:
    - tomato_large `C1_comp_L`: s1 and s2 finished at 1536; s0 is at 1224.
    - tomato_large `C1_comp_LN`: s0, which finished after 1991542 started.
  - Submitted: `... br_missing submit` → **1991926** (`L`), **1991927** (`LN`).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 68 (01:30–01:45): tomato_large target (2 of 6 seeds corrected once, then honest; 4 farm; 3 fixed points not converged); first tomato_large verdicts

- **tomato_large target.** **1989675** (`targets_tomato_large_comp`) COMPLETED 01:29 (1-02:55:51, inside its 36 h limit).
  - **s0, s22:** corrected in round 0, then honest (522.6).
  - **s20:** farms with 4 corrections and rising levels (2.94 → 3.68).
  - **s1, s2, s21:** farm with 2–3.8 corrections, and their fixed points **did not converge**.
  - Rule 2 table under "Exact predictions"; the farming flag at the top now includes tomato_large and the non-converged fixed points.
  - Comparison: the swap ends in a new exploit (true 483–501) in all 6 seeds; standard PBRR hides in all 6.
- **First verdicts, now that the target exists.** `C1_comp_LN`:
  - s1 **0.343**, PLATEAU (honest from round 0, never corrected);
  - s2 **0.003**, CONVERGED (corrected once, then honest).
  - Every other finished tomato_large comp seed is NEEDS BR: checks 1991852 (`LE` s1), 1991926 (`L` s1, s2) and 1991927 (`LN` s0) are queued or running. `br_missing` will list the rest (`L` s0, `LE` s2) once those end.
- **PPO behaviour so far.** At 1536 every finished tomato_large comp seed is corrected in round 0, then near honest: true 506–519 (`LE` s0 472) against honest 523. The farming targets' rounds 1–3 sit at about 503–520.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 69 (01:48–01:51): Taxi `C1_comp_LE` s0 at 1536 → check 1992105 

- **Tick.** No job failed. Nothing to resume in comp. The indiff and indiff_pool targets (22 jobs, `docs/step4_indiff_log.md`) are queued; all jobs together: 55 of 110.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_LE` (extended to 1536, 1991184): s0 finished at 1536; s1 is at 864 and s2 at 1080.
  - Submitted: `... br_missing submit` → **1992105 **.
- Cells DONE: 3 of 6.
- **02:09.** Tomato `C1_comp_L_confirm` (information only; Tomato is DONE): s21 finished at 3072 → `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing submit` → **1992157 **, for the record.
- **02:19.** Check **1992105** (Taxi `C1_comp_LE` s0 at 1536) COMPLETED (29:18): 0.196 → **0.189**, IMPROVING, still hiding. s1 (960) and s2 (1272) are still training toward 1536.
- **02:30.** Check **1992157** (Tomato `C1_comp_L_confirm` s21 at 3072; information only) COMPLETED (11:28): seed20  RUNNING;seed21 0.027 CONVERGED;seed22  RUNNING.

## 2026-11-17, iteration 70 (02:35–02:42): the user cancelled the standard-PBRR comparison targets

- **The user, 2026-11-17:** "for sure let's drop the PBRR ones … i meant cancel like...the standard PBRR (no bonus, no nothing)".
- **Which jobs those are.** The only running or queued jobs with plain standard PBRR (no update bonus, no fines-only rule, no level) were comp's two comparison targets:
  - **1989679**, `targets_taxi_base`: `step4_targets.py --env taxi --name base --seeds 0 1 2 20 21 22 --set task.obs=onehot g.epochs=1000`, running for 43 min;
  - **1989681**, `targets_boat_race_base`: the same for Boat Race, `--set g.epochs=1000`, still queued.
  - The bonus campaign's `B1_base_*` runs are standard PBRR *with* the update bonus, so they are not these and were left running.
- **Done.** `scancel 1989679 1989681` → both CANCELLED.
  - Taxi base s0 had already finished and is kept (`results/step4/taxi/targets/base/seed0.json`): it **hides** (true −65.9 ×4, then −88.2; V0 = V_hide = 1,794).
  - Nothing was written for the other seeds or for Boat Race.
- **Effect.** The comp log's "same seed's standard-PBRR target" comparison is now missing in Taxi (except s0) and Boat Race. The entries under "Exact predictions" say so. The Boat Race swap comparison (1989680) is still queued.
- All my jobs: 54 (limit 110). Cells DONE: 3 of 6.
- **02:51.**
  - **1989692** (tomato_large `C1_comp_LE`, wave 1) COMPLETED (1-04:28:33). All three seeds have finished at 1536; s0 and s2 get checks once 1991852 (s1) ends.
  - **1990357** (Tomato `C1_comp_L_confirm`, information only) COMPLETED (14:01:51): `... br_missing submit` → **1992218**, for the record.

## 2026-11-17, iteration 71 (03:21–03:24): Taxi `C1_comp_LE` finished at 1536 → check 1992264  (s1, s2)

- **Training wait.** **1991184** (Taxi `C1_comp_LE`, extended to 1536) COMPLETED 03:21 (2:17:44, exit 0). s0 was 0.189 IMPROVING, still hiding.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_LE`.
  - Submitted: `... br_missing submit` → **1992264 **.
- Cells DONE: 3 of 6.
- **03:41.** Check **1992218** (Tomato `C1_comp_L_confirm` at 3072; information only) COMPLETED: seed20 0.025 CONVERGED;seed21 0.027 CONVERGED;seed22 0.008 CONVERGED. This is 3/3 as well. Tomato comp has now been confirmed 3/3 by three configs: `LN_confirm` (the DONE config), `LE_confirm` (at 3072) and `L_confirm` (at 3072).

## 2026-11-17, iteration 72 (04:27–04:31): Taxi `C1_comp_LE` 0/3 at 1536 (all hide, IMPROVING) → extend 3072 (1992394 )

- **The check.** **1992264** (Taxi `C1_comp_LE` s1, s2 at 1536) COMPLETED (1:02:47).

  | Seed | BR gap at 768 → 1536 | Verdict |
  |---|---|---|
  | s0 | 0.196 → **0.189** | IMPROVING |
  | s1 | 0.182 → **0.175** | IMPROVING |
  | s2 | 0.172 → **0.152** | IMPROVING |

  - All three still hide (never corrected, true about −90). The best response is corrected once, then honest (124.7).
- **Rule 4 (wave-1 run, seeds IMPROVING, below the Taxi cap of 6144): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LE 3072` printed `submit.sh 48 --env taxi --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 3072`.
  - Submitted: `... submit` → **1992394 **.
- **Taxi comp now:**
  - `L`: s1 still training;
  - `LN`: finished 0/3;
  - `LE`: → 3072;
  - the 6b exploration runs from `LN` (iteration 60): 4 runs training.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 73 (05:20–05:23): Boat Race `C1_comp_LN_confirm` s21, s22 at 6144 → check 1992538

- **Tick.** No job failed. Nothing to resume.
- **Boat Race `C1_comp_LN_confirm`** (→ 6144, 1991432): s21 and s22 finished at 6144; s20, the deciding seed (0.074 at 3072), is at 4416.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_boat_race_C1_comp_LN_confirm`.
  - Submitted: `... br_missing submit` → **1992538**.
- Cells DONE: 3 of 6.
- **Push note (05:32).** The first commit of this iteration (d8ba989cc) was never pushed: GitHub rejected a 115 MiB `logs.npz` from the bonus campaign. It was redone as a new commit after the commit-script fix (`docs/step4_bonus_log.md`, iteration 208). Nothing in this campaign changed.

## 2026-11-17, iteration 74 (05:34–05:40): tomato_large `C1_comp_LE` s1 0.011, s2 0.010 (CONVERGED) → check 1992582 (s0)

- **The check.** **1991852** (tomato_large `C1_comp_LE` s1, s2 at 1536) COMPLETED (4:38:41).

  | Seed | BR gap | Verdict | Best response | PPO's true after round 0 |
  |---|---|---|---|---|
  | s1 | **0.011** | CONVERGED | corrected in round 0, then never again (true 522.6 ×3, 521.9) | about 508 |
  | s2 | **0.010** | CONVERGED | 1.60 corrections per episode (by round [1.0, 0.34, 0.17, 0.09]) | about 506 |

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `run_cmd.sh 12 4 br_tomato_large_C1_comp_LE … step4_br.py results/step4/tomato_large/comp/C1_comp_LE --finished-only --draws 12`. s0 finished at 02:49, after 1991852 started (00:55). `L` and `LN` were "check still queued/running" (1991926, 1991927).
  - Submitted the listed line as printed (`EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/run_cmd.sh 12 4 br_tomato_large_C1_comp_LE …`) → **1992582**. It is the same command `br_missing submit` runs. I ran it directly because the bonus campaign's `br_missing` in the same tick also listed a run I am holding back (`docs/step4_bonus_log.md`, iteration 209).
  - `step4_br.py` skips seeds that already have their check file, so this job checks s0 only.
- **tomato_large comp so far** at 1536: `LE` s1 and s2 CONVERGED; `LN` s1 PLATEAU 0.343 (honest from round 0, never corrected), `LN` s2 0.003. `L` s1/s2 and `LN` s0 are being checked (1991926, 1991927). `L` s0 and `LE` s0 come next.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 75 (05:47–05:52): Boat Race `C1_comp_LN_confirm` s21 0.015, s22 0.023 at 6144 (CONVERGED); s20 still training

- **The check.** **1992538** (Boat Race `C1_comp_LN_confirm` s21, s22 at 6144) COMPLETED (2:32).

  | Seed | BR gap 3072 → 6144 | Verdict | Best response | PPO true by round |
  |---|---|---|---|---|
  | s21 | → **0.015** (s.e. 0.005) | CONVERGED | 3 corrections (rounds 0–2), true −94, then 50 ×4 | −94, then 50.0 ×4 |
  | s22 | → **0.023** (s.e. 0.008) | CONVERGED | 4 corrections, true −94, then 50 ×4 | −94, then 50.0 ×4 |

  - PPO: open exploit in round 0, then honest laps with 4 corrections per episode (the level farms, as in the tuning seeds).
- **Rule 4.** No decision yet. s20, the deciding seed (0.074 at 3072), is at 4656 of 6144 in 1991432; at its last evaluation it exploits in every round (true −94 ×5). Its check is submitted when it finishes. If s20 converges at 6144 the confirmation is 3/3 and the cell is DONE; otherwise rule 4 applies to it (IMPROVING → 12,288, the cap).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 76 (05:58–06:10): Boat Race swap comparison target (a new exploit in 5 of 6 seeds)

- **The target.** **1989680** (`targets_boat_race_P2swap`, the `compare` job) COMPLETED (7:01) after about 32 h queued at low priority. It wrote `results/step4/boat_race/targets/P2swap/seed{0,1,2,20,21,22}.json`. All fixed points converged, and every draw gives "corrected in round 0, then never again".
- **Rule 2, under "Exact predictions" (Boat Race):**

  | Seed | True by round (k = 0..4) | Received after the correction | Honest under the same correction | V0 |
  |---|---|---|---|---|
  | 0 | −94, then −82 ×4 | 359.2 | 295.3 | 1,636.6 |
  | 1 | −94, then **44** ×4 | 277.0 | 266.5 | 1,308.1 |
  | 2 | −94, then −76 ×4 | 461.3 | 364.7 | 2,045.2 |
  | 20 | −94, then −76 ×4 | 383.7 | 316.3 | 1,734.8 |
  | 21 | −94, then −82 ×4 | 462.0 | 354.3 | 2,048.0 |
  | 22 | −94, then −76 ×4 | 363.2 | 318.0 | 1,652.6 |

  - V_hide is 928.0 in every seed; windows are 1, 0, 0, 0, 0.
  - After its one correction, the swap's optimum leaves the original bug alone (window 0) but takes **a new exploit** in 5 of 6 seeds: routes the swap raised above honest laps. s1 is near honest (44 vs 50).
  - Against comp on the same seeds: comp is honest by the true reward after round 0 in 5 of 6 (s20 keeps the original bug), but farms the level with 4 corrections. The swap is corrected once and never farms, but is not honest.
- No decision for PPO: the compare targets are for the comparison only.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 77 (06:29–06:35): Taxi `C1_comp_L` finished (s1 at 768) → check 1992696

- **Event.** **1989694** (Taxi `C1_comp_L`, wave 1, resumed after the 48 h limit) COMPLETED (1-07:26:47). s1 has finished at 768; s0 (0.189) and s2 (0.146) were checked at 768 in iterations 36–37, both IMPROVING and hiding.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `run_cmd.sh 6 4 br_taxi_C1_comp_L … step4_br.py results/step4/taxi/comp/C1_comp_L --finished-only --draws 12`. tomato_large `L`, `LE` and `LN` were "check still queued/running".
  - Submitted: `... br_missing submit` → **1992696** (s1 only; s0 and s2 have their files).
- **Next (rule 4).** Once s1's check is in, all three Taxi wave-1 runs have checks. `L`'s verdict decides whether it is extended to 1536.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 78 (06:47–06:55): tomato_large `C1_comp_LN` s0 0.004 → `LN` finished 2/3 (s1 PLATEAU)

- **The check.** **1991927** (tomato_large `C1_comp_LN` s0 at 1536) COMPLETED (4:45:17).

  | Seed | BR gap at 1536 | Verdict | PPO true by round | Best response |
  |---|---|---|---|---|
  | s0 | **0.004** | CONVERGED | 65.0, then 519.0–519.3 ×4 (corrected in round 0, then never again) | the same end state, 522.6 ×3, 522.2 |
  | s1 | 0.343 (iteration 67) | PLATEAU | honest from round 0, never corrected (about 519 ×5) | 1.10 corrections |
  | s2 | 0.003 (iteration 67) | CONVERGED | corrected in round 0, then near honest (about 518) | 1.39 corrections |

- **Rule 4.** All three seeds have checks. The only unconverged seed (s1) is PLATEAU, so the config is finished at 1536 and is not extended. It is 2/3, not CONVERGED 3/3.
- **tomato_large comp:** `LE` s1, s2 CONVERGED (s0 being checked, 1992582); `L` s1, s2 being checked (1991926), s0 next. Rule 6b starts if none of the three wave-1 runs is 3/3 once all have checks.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 79 (07:06–07:10): Taxi `C1_comp_L` 0/3 at 768 (all IMPROVING) → extend 1536 (1992751)

- **The check.** **1992696** (Taxi `C1_comp_L` s1 at 768) COMPLETED (27:51).

  | Seed | BR gap at 768 | Verdict | PPO | Best response |
  |---|---|---|---|---|
  | s0 | 0.189 (iteration 37) | IMPROVING | hides (true about −80 every round) | corrected in round 0, then honest (124.8 ×4) |
  | s1 | **0.895** (s.e. 0.009) | IMPROVING | exploits through each window with probability 0.49 every round, about 1.96 corrections per episode; true about −60 every round | 1.83 corrections (by round 1.0, 0, 0, 0.83): corrected in round 0, then −65.9 in rounds 1–2, caught again in round 3 |
  | s2 | 0.146 (iteration 36) | IMPROVING | hides | corrected in round 0, then honest (124.7 ×4) |

  - s1's gap is the largest of any comp seed so far. Its policy mixes evenly between exploiting through the window and avoiding it, and under its own corrections it receives about a tenth of the best response's value.
- **Rule 4 (wave-1 run, all seeds IMPROVING, below Taxi's 6144 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_L 1536` printed `submit.sh 48 --env taxi --run-id C1_comp_L --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 1536`.
  - Submitted: `... submit` → **1992751**. The 0 → 768 leg took more than 48 h (one resume), so this leg will probably need a resume too.
- **Taxi rule 6b.** All three wave-1 runs now have checks, and none is 3/3:
  - `L` 0/3 (IMPROVING; now extending);
  - `LN` 0/3 at 1536 (PLATEAU);
  - `LE` 0/3 at 1536 (IMPROVING; extending to 3072, 1992394).
  - The four 6b runs from `LN` are already running (1991185–1991188, started in iteration 60).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 80 (08:59–09:04): **tomato_large `C1_comp_LE` 3/3 CONVERGED at 1536 → `confirm` (1992827)**

- **The check.** **1992582** (tomato_large `C1_comp_LE` s0 at 1536) COMPLETED (2:18:56).

  | Seed | BR gap at 1536 | Verdict | PPO true by round | Best response true by round |
  |---|---|---|---|---|
  | s0 | **0.011** | CONVERGED | 65.0, then 511.2–511.7 (corrected in round 0, then never again) | 65.0, 522.6 ×3, 522.1 (the same end state) |
  | s1 | 0.011 (iteration 74) | CONVERGED | 65.0, then 511.7–512.2 (the same) | 65.0, 522.6 ×3, 521.9 (the same) |
  | s2 | 0.010 (iteration 74) | CONVERGED | 65.0, then 512.4–512.9 (the same) | 1.60 corrections; 65.0, 520.3–522.2 |

  - In all three seeds PPO is corrected once, in round 0, and is then near honest: true about 512 against honest 522.6. It does not farm the level.
  - The target farms in 4 of 6 seeds (s1, s2, s20, s21), with 2–4 corrections. Its seeds 0–2 are 1.0 / 1.99 / 2.50 corrections. PPO takes 1 correction in every seed.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh confirm tomato_large C1_comp_LE` printed `submit.sh 48 --env tomato_large --run-id C1_comp_LE_confirm --seeds 20 21 22 --results-dir results/step4/tomato_large/comp --set ppo.ent_coef=0.1 g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 episodes=1536 anneal.last=0.25 anneal.floor=0.1`. This is identical to the run's `overrides.json`.
  - Submitted: `... submit` → **1992827**. Wave 1 took about 28 h for 1536 episodes.
  - The tomato_large comp cell is DONE when this confirmation is 3/3.
- **The other tomato_large runs.**
  - `LN` finished 2/3.
  - `L`: s0 is 0.008; s1 and s2 are being checked (1991926). Rule 4 still applies to it while the cell is not DONE: if it is 3/3, it gets its own confirmation, as Tomato's `L` and `LE` did.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 81 (09:19–09:22): Boat Race `C1_comp_LN_confirm` s20 finished at 6144 → check 1992873

- **Event.** **1991432** (Boat Race `C1_comp_LN_confirm`, extension to 6144) COMPLETED (7:10:02). s20 has finished at 6144; s21 (0.015) and s22 (0.023) were checked at 6144 (iteration 75).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `run_cmd.sh 2 4 br_boat_race_C1_comp_LN_confirm … step4_br.py results/step4/boat_race/comp/C1_comp_LN_confirm --finished-only --draws 12`.
  - Submitted: `... br_missing submit` → **1992873** (s20 only).
- If s20 is CONVERGED, the confirmation is 3/3 and Boat Race comp is DONE. If not, rule 4 applies to it: IMPROVING means extend to 12,288 (the cap).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 82 (09:37–09:50): Boat Race `C1_comp_LN_confirm` s20 0.074 at 6144 (IMPROVING) → extend 12,288 (1992892)

- **The check.** **1992873** (Boat Race `C1_comp_LN_confirm` s20 at 6144) COMPLETED (1:14).

  | Seed | BR gap 3072 → 6144 | Verdict | PPO | Best response |
  |---|---|---|---|---|
  | s20 | 0.074 → **0.074** (s.e. 0.004) | IMPROVING | the original bug through every window: 4 corrections, true −94 every round | corrected in round 0, then honest (true 50 ×4) |
  | s21 | → 0.015 (iteration 75) | CONVERGED | | |
  | s22 | → 0.023 (iteration 75) | CONVERGED | | |

  - s20's gap is flat between 3072 and 6144. `step4_convergence.py`'s 24-episode curve calls it IMPROVING, and I apply that as written.
  - The target of s20 is also the original bug every round, with 4 corrections. PPO matches the target's end state, but not its own best response.
- **Rule 4 (confirmation, one seed IMPROVING, below the 12,288 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend boat_race C1_comp_LN_confirm 12288` printed `submit.sh 48 --env boat_race --run-id C1_comp_LN_confirm --seeds 20 21 22 --results-dir results/step4/boat_race/comp --resume --extend-to 12288`.
  - Submitted: `... submit` → **1992892**.
  - It extends s21 and s22 too, because the run's seeds move together. At the cap, if s20 is still unconverged, the confirmation has failed.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 83 (10:32–10:37): Taxi `C1_comp_LE` finished at 3072; `C1_comp_L` s0 at 1536 → checks 1992987, 1992988

- **Events.**
  - **1992394** (Taxi `C1_comp_LE`, extension to 3072) COMPLETED (5:44:02). All three seeds are at 3072. This leg was fast: the seeds hide, so they trigger few PBRR rounds.
  - Taxi `C1_comp_L` (extension to 1536, 1992751, running 3:26) has s0 finished at 1536 and s2 at 1488. s1, the seed that exploits through windows half the time, is still at 768.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed:
    - `run_cmd.sh 6 4 br_taxi_C1_comp_L … step4_br.py results/step4/taxi/comp/C1_comp_L --finished-only --draws 12`;
    - `run_cmd.sh 6 4 br_taxi_C1_comp_LE … step4_br.py results/step4/taxi/comp/C1_comp_LE --finished-only --draws 12`.
  - Submitted: `... br_missing submit` → **1992987** (`L`, s0 at 1536) and **1992988** (`LE`, all three at 3072).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 84 (11:22–11:28): Taxi `C1_comp_LN+ENT3` s1, s2 finished at 768 → check 1993060; s0 slow (48 of 768)

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `run_cmd.sh 6 4 br_taxi_C1_comp_LN+ENT3 … step4_br.py results/step4/taxi/comp/C1_comp_LN+ENT3 --finished-only --draws 12`.
  - Submitted: `... br_missing submit` → **1993060** (s1 and s2, both at 768).
- **s0 of the same run (1991185) is at 48 of 768.**
  - It is not stuck. Its log reads `768,000 … corr/ep 1.20 … rounds 132 (11402s)`, then `1,536,000 … win0-3 0.88 … corr/ep 3.52 … rounds 394 (27785s)`.
  - It exploits through most audit windows, so it triggers about 3.5 PBRR rounds per episode (about 60 s each in Taxi), against near zero in the hiding seeds. Its last 24 episodes took 4.5 h.
  - At this rate the job reaches its 48 h limit with s0 at roughly 250–300 episodes. Rule 1 (resume) then applies.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 85 (11:30–11:34): Taxi `C1_comp_L` s0 0.158, s2 0.127 at 1536 (both still hide)

- **The check.** **1992987** (Taxi `C1_comp_L` at 1536) COMPLETED (56:06). It covered s0, plus s2, which finished at 1536 before the job started.

  | Seed | BR gap 768 → 1536 | PPO | Best response |
  |---|---|---|---|
  | s0 | 0.189 → **0.158** | hides (true about −82 every round) | corrected in round 0, then honest (124.8 ×4) |
  | s2 | 0.146 → **0.127** | hides (−81.4 to −88.3) | corrected in round 0, then honest (124.7 ×4) |

  - Both gaps are falling, but both seeds still hide.
- **Rule 4.** No decision yet: s1 is still at 768 in 1992751.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 86 (11:47–11:51): Taxi `C1_comp_LE` 0/3 at 3072 (all hide, IMPROVING) → extend 6144, the cap (1993102)

- **The check.** **1992988** (Taxi `C1_comp_LE` at 3072) COMPLETED (1:10:29).

  | Seed | BR gap 1536 → 3072 | Verdict | PPO | Best response |
  |---|---|---|---|---|
  | s0 | 0.189 → **0.181** | IMPROVING | hides (true about −90 every round) | corrected in round 0, then honest (124.8 ×4) |
  | s1 | 0.175 → **0.163** | IMPROVING | hides (−84.4 to −90.1) | the same (124.7 ×4) |
  | s2 | 0.152 → **0.153** | IMPROVING | hides (about −90) | the same (124.7 ×4) |

  - The gaps barely move between 1536 and 3072, and all three seeds still hide. The IMPROVING calls come from the 24-episode curve, which I apply as written.
- **Rule 4 (wave-1 run, all IMPROVING, below Taxi's 6144 cap): extend 2×.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LE 6144` printed `submit.sh 48 --env taxi --run-id C1_comp_LE --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 6144`.
  - Submitted: `... submit` → **1993102**. At the cap, rule 4 ends the run.
- **Taxi comp so far:** every checked seed of `L`, `LN` and `LE` (9 of 9) hides. The 6b exploration runs (1991185–1991188, from `LN`) are training; `LN+ENT3` s1 and s2 are being checked (1993060).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 87 (12:11–12:16): **tomato_large `C1_comp_L` 3/3 CONVERGED at 1536 → `confirm` (1993134)**

- **The check.** **1991926** (tomato_large `C1_comp_L`, all three seeds at 1536) COMPLETED (10:10:51).

  | Seed | BR gap at 1536 | Verdict | PPO true by round | Best response |
  |---|---|---|---|---|
  | s0 | **0.008** | CONVERGED | 65.0, then 515.1–515.3 (corrected in round 0, then never again) | the same end state: 522.6 ×3, 522.1 |
  | s1 | **0.008** | CONVERGED | 65.0, then 514.4–515.0 (the same) | the same: 522.6 ×3, 521.6 |
  | s2 | **0.008** | CONVERGED | 65.0, then 514.7–515.8 (the same) | 1.59 corrections; 520.2–521.9 |

  - As in `LE`, PPO is corrected once and is then near honest (about 515 against 522.6). It does not farm.
- **Rule 4 (tuning run, all CONVERGED): `confirm`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh confirm tomato_large C1_comp_L` printed `submit.sh 48 --env tomato_large --run-id C1_comp_L_confirm --seeds 20 21 22 --results-dir results/step4/tomato_large/comp --set ppo.ent_coef=0.03 g.fine_only=True g.offset=True g.offset_margin=0.0 g.epochs=1000 episodes=1536 anneal.last=0.25 anneal.floor=0.1`. This is identical to the run's `overrides.json`.
  - Submitted: `... submit` → **1993134**.
  - The cell now has two confirmations running, `LE_confirm` (1992827) and `L_confirm`, as Tomato had. The cell is DONE when either is 3/3; the other is then information only.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 88 (12:32–12:35): Taxi `C1_comp_LN+ENT3` s1 0.177, s2 0.139 at 768 (both hide, final window included)

- **The check.** **1993060** (Taxi `C1_comp_LN+ENT3` s1, s2 at 768) COMPLETED (1:06:18).

  | Seed | BR gap at 768 | PPO | Best response |
  |---|---|---|---|
  | s1 | **0.177** | "never exploits in view": clean in every window, the final one too; true about −69.4 every round | corrected in round 0, then honest (124.7 ×4) |
  | s2 | **0.139** | the same; true about −77.7 every round | the same |

  - Like the other 9 Taxi comp seeds, they exploit off-window only, and never take the correction that the best response takes.
- **Rule 6b.** Exploration runs are extended 2× whatever the verdict, but only once the run's job has finished. s0 is still at about 48 of 768 in 1991185 (iteration 84), so nothing is submitted now.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 89 (14:39–14:42): Taxi `C1_comp_LN+N4` s0, s2 finished at 768 → check 1993609

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `run_cmd.sh 6 4 br_taxi_C1_comp_LN+N4 … step4_br.py results/step4/taxi/comp/C1_comp_LN+N4 --finished-only --draws 12`. s0 and s2 have finished at 768; s1 is at 720.
  - Submitted: `... br_missing submit` → **1993609**.
- **Queue:** 47 jobs in all (18 pending), including the 18 new indiff_pool PPO runs (`docs/step4_indiff_log.md`, iteration 15).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 90 (18:51–18:56): Boat Race `C1_comp_LN_confirm` s21, s22 at 12,288 → check 1994469

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `run_cmd.sh 2 4 br_boat_race_C1_comp_LN_confirm …`. s21 and s22 have finished the extension to 12,288; s20, the deciding seed (0.074 at 3072 and 6144), is at 8784.
  - Submitted: `... br_missing submit` → **1994469**. s21 and s22 were already CONVERGED at 6144; this check is information until s20 finishes.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 91 (19:15–19:18): Boat Race `C1_comp_LN_confirm` s21 0.014, s22 0.024 at 12,288

- **The check.** **1994469** (s21, s22 at 12,288) COMPLETED (4:16): s21 **0.014**, s22 **0.024**, both CONVERGED (they were 0.015 / 0.023 at 6144). Both are corrected in round 0, then play honest laps (50.0 ×4) with 1.00 correction per episode.
- s20, the deciding seed, is at 8784 of 12,288 in 1992892. At the cap, if it is still unconverged, the confirmation has failed.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 92 (20:14–20:18): Taxi `C1_comp_LN+N4` 0/3 at 768 (all hide) → extend 1536 (rule 6b; 1994671)

- **The check.** **1993609** (Taxi `C1_comp_LN+N4`, all three seeds at 768) COMPLETED (1:38:38).

  | Seed | BR gap at 768 | PPO | Best response |
  |---|---|---|---|
  | s0 | **0.076** | hides: −66.1 ×4, then −89.7 (bug in the final window), 0 corrections | corrected in round 0, then honest (124.8 ×4) |
  | s1 | **0.091** | hides: −63.3 ×4, then −87.0 | the same (124.7 ×4) |
  | s2 | **0.052** | hides: −63.2 ×4, then −87.2 | the same (124.7 ×4) |

  - These are the smallest gaps of any Taxi comp run so far (others 0.13–0.90), but every seed still hides. That makes 14 of 14 checked Taxi comp seeds hiding.
- **Rule 6b (exploration runs extend 2× whatever the verdict, up to the 6144 cap).**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LN+N4 1536` printed `submit.sh 48 --env taxi --run-id C1_comp_LN+N4 --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 1536`.
  - Submitted: `... submit` → **1994671**.
- **Budget:** 9 comp jobs (limit 30).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 93 (20:37–20:43): Taxi `C1_comp_LN+ENT3` finished (s0 reached 768) → check 1994696; Taxi `C1_comp_LE` s1 at the cap → check 1994697

- **Events.**
  - **1991185** (Taxi `C1_comp_LN+ENT3`) COMPLETED (19:35:29). At 11:22, s0 was at 48 episodes, exploiting in view with about 3.5 PBRR rounds per episode. It then stopped exploiting in view, so PBRR rounds stopped and it sped up. Its final log line reads `24,576,000  win0-3 0.00  off 0.96  corr/ep 0.00 … proxy0-3 342.7  rounds 1606`: off-window exploit 0.96 with clean windows, i.e. it hides, like every other Taxi comp seed.
  - Taxi `C1_comp_LE` (extension to 6144, 1993102): s1 has finished at the 6144 cap; s0 is at 5616 and s2 at 5352.
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_LE` and `br_taxi_C1_comp_LN+ENT3`.
  - Submitted: `... br_missing submit` → **1994696** (`LE`, s1) and **1994697** (`LN+ENT3`, s0).
- **Next.** `LN+ENT3` is an exploration run, so it will be extended to 1536 whatever its verdict (rule 6b) once s0's check is in. `LE` is at the cap; if no seed converges, the run is finished.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 94 (21:30–21:34): Taxi `C1_comp_LN+ENT3` 0/3 at 768 (all hide) → extend 1536 (rule 6b; 1994783)

- **The check.** **1994697** (Taxi `C1_comp_LN+ENT3` s0 at 768) COMPLETED (23:32): **0.115**. PPO never exploits in view (true about −61.7 every round); the best response is corrected in round 0, then honest (124.8 ×4).
- **All three seeds:** 0.115 / 0.177 / 0.139, all hiding. That makes 15 of 15 checked Taxi comp seeds hiding.
- **Rule 6b (exploration runs extend 2× whatever the verdict, up to the 6144 cap).**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LN+ENT3 1536` printed `submit.sh 48 --env taxi --run-id C1_comp_LN+ENT3 --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 1536`.
  - Submitted: `... submit` → **1994783**.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 95 (21:37–21:40): Taxi `C1_comp_LE` s1 0.164 at the 6144 cap (hides)

- **The check.** **1994696** (Taxi `C1_comp_LE` s1 at 6144) COMPLETED (32:52): **0.164**, not converged. PPO hides (−84.3 ×4, then −90.1); the best response is corrected in round 0, then honest (124.7 ×4). The gap was 0.163 at 3072.
- s0 and s2 are still finishing the extension to the cap (1993102). At the cap, rule 4 ends the run whatever the verdict.
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 96 (21:53–21:56): Taxi `C1_comp_LE` finished at the 6144 cap → check 1994853

- **Event.** **1993102** (Taxi `C1_comp_LE`, extension to the 6144 cap) COMPLETED (10:02:17). s1 was checked at the cap (0.164, hides).
- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_LE`.
  - Submitted: `... br_missing submit` → **1994853** (s0, s2).
- Cells DONE: 3 of 6.

## 2026-11-17, iteration 97 (23:05–23:12): Taxi `C1_comp_LE` 0/3 at the 6144 cap → finished; Taxi `LN+ENT3` at 1536 → check 1995057

- **The check.** **1994853** (Taxi `C1_comp_LE` s0, s2 at the 6144 cap) COMPLETED (1:10:49): s0 **0.181**, s2 **0.142**, both hiding (true about −90 / −85). With s1 (0.164), the run is 0/3 at the cap.
  - **Rule 4:** at Taxi's 6144 cap, the run is finished.
- **Taxi comp wave 1, all finished or running:**
  - `LN` 0/3 at 1536 (PLATEAU);
  - `LE` 0/3 at 6144 (cap);
  - `L` extending to 1536 (1992751; s1 still slow).
  - All 18 checked seeds hide.
- **Rule 3.** **1994783** (Taxi `C1_comp_LN+ENT3`, extension to 1536) COMPLETED in 1:17:24: the seeds hide, so they trigger few PBRR rounds and train fast.
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_LN+ENT3`.
  - Submitted: `... br_missing submit` → **1995057**.
- Cells DONE: 3 of 6.

## 2026-11-18, iteration 98 (00:51–00:56): Taxi `C1_comp_LN+ENT3` 0/3 at 1536 (all hide) → extend 3072 (rule 6b; 1995223)

- **The check.** **1995057** (Taxi `C1_comp_LN+ENT3` at 1536) COMPLETED (1:41:14): **0.118 / 0.177 / 0.122**, all IMPROVING by the curve.
  - PPO never exploits in view (true −65.8 to −71.3 every round). The best response is corrected in round 0, then honest (124.7–124.8).
- **Rule 6b (exploration runs extend 2× whatever the verdict, up to the 6144 cap).**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LN+ENT3 3072` printed `submit.sh 48 --env taxi --run-id C1_comp_LN+ENT3 --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 3072`.
  - Submitted: `... submit` → **1995223**.
- Taxi comp: 18 of 18 checked seeds hide. Cells DONE: 3 of 6.

## 2026-11-18, iteration 99 (01:38–01:41): Taxi `C1_comp_LN+N4` at 1536 → check 1995309 

- **Rule 3.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` listed `br_taxi_C1_comp_LN+N4`; its extension to 1536 (1994671) has finished seeds.
  - Submitted: `... br_missing submit` → **1995309 **.
- Cells DONE: 3 of 6.

## 2026-11-18, iteration 100 (03:18–03:25): Taxi `C1_comp_LN+N4` 0/3 at 1536 (all hide) → extend 3072 (rule 6b; 1995400)

- **The check.** **1995309** (Taxi `C1_comp_LN+N4`, all three seeds at 1536) COMPLETED (1:23:46).
  - **0.075 / 0.090 / 0.052, all PLATEAU** (at 768: all hid as well).
  - PPO's true return by round: s0 −66.1 / −66.1 / −66.0 / −65.9 / −89.7; s1 −63.3 ×4 / −87.2; s2 −63.2 ×4 / −87.1. It is never corrected in rounds 0–3 (window gap 1.000, corrections 1.00 below the target), and it exploits the final round. **It hides.**
  - The best response, and the target, are corrected in round 0, then honest: true −88.2, then 124.7–124.8 ×4.
  - The gaps fell from 768 (iteration 92), but every seed is still far above 0.03.
- **Rule 6b.** `LN+N4` is a stage-1 exploration run, which extends 2× whatever the verdict, up to Taxi's 6144 cap.
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh extend taxi C1_comp_LN+N4 3072` printed `submit.sh 48 --env taxi --run-id C1_comp_LN+N4 --seeds 0 1 2 --results-dir results/step4/taxi/comp --resume --extend-to 3072`.
  - Submitted: `... submit` → **1995400**.
- Taxi comp runs now: `LN+ENT3` → 3072 (about 1680), `LN+ES10` and `LN+ES10+N4` (stage 2, about 72–96 of 768), `LN+N4` → 3072, `L` s1 (984 of 1536). `L`, `LE` and `LN` are finished: 0/3, all hiding.
- **Budget:** comp 8 jobs (cap 30); 105 in all (limit 110). Cells DONE: 3 of 6.

## 2026-11-18, iteration 101 (04:52–04:56): tomato_large `C1_comp_LE_confirm` finished (all three at 1536) → check 1995459

- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed `run_cmd.sh 12 4 br_tomato_large_C1_comp_LE_confirm … --finished-only --draws 12`. s20, s21 and s22 are all finished at 1536.
- Submitted: `... br_missing submit` → **1995459**.
- tomato_large comp: `L_confirm` is still training. Taxi: `LN+N4` → 3072 (1995400), `LN+ENT3`, `LN+ES10`, `LN+ES10+N4` and `L` s1 are training. Boat Race `LN_confirm` s20 → cap.
- 108 jobs in all (limit 110). Cells DONE: 3 of 6.

## 2026-11-18, iteration 102 (05:17–05:22): Boat Race `C1_comp_LN_confirm` at the 12,288 cap → check 1995468 (decides s20); tomato_large `L_confirm` s20 → check 1995467

- **Event.** The extension of Boat Race `C1_comp_LN_confirm` to 12,288 (1992892) COMPLETED (19:38:53). All three seeds are at the cap; s20 is the deciding seed (s21 and s22 already converged at 12,288).
- **Rule 3.** `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh br_missing` (dry-run) listed:
  - `br_tomato_large_C1_comp_L_confirm`: s20 finished at 1536; s21 at 1008, s22 at 984;
  - `br_boat_race_C1_comp_LN_confirm`.
  - `tomato_large/C1_comp_LE_confirm`'s check (1995459) is still queued.
- Submitted: `... br_missing submit` → **1995467** (tomato_large `L_confirm`) and **1995468** (Boat Race `LN_confirm`).
- If Boat Race s20 is still unconverged at the cap, this confirmation has failed: rule 4, a confirmation that finishes unconverged.
- 105 jobs in all (limit 110). Cells DONE: 3 of 6.

## 2026-11-18, iteration 103 (05:24–05:45): **Boat Race `LN_confirm` failed (2/3: s20 0.074 at the cap)** → rule 5 (wave 2, 6 runs: 1995472–1995477) and rule 6b (4 runs, waiting for job slots)

- **Check 1995468** (Boat Race `C1_comp_LN_confirm` at the 12,288 cap) COMPLETED (2:08).
  - **s20: 0.074 (s.e. 0.004), PLATEAU.** PPO is corrected in every round (4.00 corrections per episode), true −94.0 every round. That is s20's target end state: its correction under-corrects, so the target is also corrected 4 times, at −94 per round. But PPO's best response under its own corrections is corrected once, then honest (−94.0, then 50.0 ×4).
  - s21 0.014 and s22 0.024: CONVERGED (iteration 91).
  - **Rule 4.** The run is at the cap and its only unconverged seed is PLATEAU, so **this confirmation failed (2/3).**
- **The Boat Race cell now.** No wave-1 run is DONE:
  - `L`: 2/3 (s2 0.187, PLATEAU);
  - `LE`: 1/3 at 6144 (0.066 / 0.023 / 0.037, PLATEAU);
  - `LN`: 3/3 (0.021 / 0.022 / 0.000), but its confirmation failed.
  - As in earlier iterations, a failed confirmation counts as "not 3/3" for rules 5 and 6b. **Both apply now**, from `LN`, the run with the smallest mean gap (0.014).
- **Rule 5 (wave 2).**
  - Each command was dry-run first: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh ppo boat_race comp LN+<tag> "n_envs=64 ppo.batch_size=1600 <factor>" submit`. These are `LN`'s extras plus one factor, 1536 episodes.

    | Run | Factor | Job |
    |---|---|---|
    | `C1_comp_LN+LR` | `ppo.learning_rate=0.0001` | **1995472** |
    | `C1_comp_LN+GL` | `ppo.gae_lambda=1.0` | **1995473** |
    | `C1_comp_LN+NET` | `ppo.net_arch=[256,256]` | **1995474** |
    | `C1_comp_LN+RS` | `reward_scale=0.125` (0.25 × Boat Race's 0.5) | **1995475** |
    | `C1_comp_LN+EP` | `ppo.n_epochs=20` | **1995476** |
    | `C1_comp_LN+AN` | `anneal.last=0.5` | **1995477** |
- **Rule 6b, stage 1, from `C1_comp_LN`.**
  - Dry-run: `CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh explore boat_race comp C1_comp_LN` lists `+ENT3` (`ppo.ent_coef=0.09`), `+ES10` (`anneal.ent_start=10 anneal.ent_episodes=768`), `+N4` (`n_envs=256 ppo.batch_size=6400`) and `+ES10+N4`.
  - **Not submitted yet.** The job count is at the 110 cap after wave 2. They go in as slots free up (flag at the top of docs/step4_indiff_log.md: the budget is now binding).
- tomato_large `L_confirm` s20: check 1995467 is queued; `LE_confirm`: check 1995459 is queued.
- **Budget:** comp 14 jobs (cap 30); 110 in all (limit 110). Cells DONE: 3 of 6.

## 2026-11-18, iteration 104 (06:34–06:40): Boat Race rule 6b stage 1, 3 of 4 runs submitted (1995494–1995496)

- Slots freed up, so I submitted queued Boat Race exploration runs from iteration 103's dry-run (`CAMPAIGN=comp EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh explore boat_race comp C1_comp_LN`), lines run verbatim:
  - `C1_comp_LN+ENT3` → **1995494**;
  - `C1_comp_LN+ES10` → **1995495**;
  - `C1_comp_LN+N4` → **1995496**.
- `C1_comp_LN+ES10+N4` is next in the queue (flag at the top of docs/step4_indiff_log.md).
- comp 17 jobs (cap 30); 110 in all.

## 2026-11-18, iteration 105 (07:00): Boat Race rule 6b stage 1 complete: `C1_comp_LN+ES10+N4` → 1995510

- The fourth stage-1 run, from iteration 103's `explore boat_race comp C1_comp_LN` dry-run (line run verbatim). All four stage-1 runs are now in: 1995494–1995496 and 1995510.
- comp 18 jobs (cap 30); 110 in all.
