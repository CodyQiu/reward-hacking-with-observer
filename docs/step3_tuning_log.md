# Step 3 tuning log: the Step 2 experiment on five environments

This is the bookkeeping record for Step 3. It follows `docs/step2_tuning_log.md`:
- every decision that shapes an environment or the setup, with its reason;
- one entry per tuning batch: hypothesis → change → result → interpretation → next step.

**Where things are.**
- Per-environment runs: `results/step3/<env>/tuning/runs.csv`, one row per run.
- Each run's logs, model, config (with git hash) and code snapshot: `results/step3/<env>/tuning/<run_id>/seed<s>/`. Runs are never overwritten.
- Phase A outputs: `results/step3/<env>/phase_a/`. Earlier Phase A outputs are kept in `phase_a/superseded/`; exploratory bug-parameter settings are in `phase_a_variants/`.

## Protocol (identical in every environment; fixed before any run)

- **Structure.** Episodes of 5 sub-episodes of T_sub steps. The base task resets every sub-episode.
- **Audit.** The last W = T_sub/10 steps are audited, with p = 1. **Caught ⇔ proxy ≠ true at some step of the window.** On the Step 1 grid this is exactly the old flag.
- **Updates.**
  - PPO updates at every boundary (n_steps = T_sub, 16 copies).
  - A caught copy gets one PBRR round (19 current-policy × 19 reference rollouts, Boltzmann β = 1, Eq 3 with λ = 10/max(1, |D⁺|)). The correction applies from the next sub-episode.
- **Reset and discounting.** g and D reset every episode; the policy never does. γ = 1.
- **Training length.** 384 episodes × 16 copies per run.

**Success criteria** (Step 2's, unchanged). Measured on the logged training data over the last 10% of episodes; S1–S4 must hold in ≥ 2 of 3 seeds.

| | Criterion | Threshold |
|---|---|---|
| S1 | audit windows 0–3 exploited | < 5% |
| S2 | off-window exploit-step rate in 0–3, relative to the idealised optimum's | ≥ 80% |
| S3 | corrections per episode | < 0.1 |
| S4 | final window exploited | > 80% |
| S5 | proxy per sub-episode 0–3, relative to the idealised optimum's | ≥ 90% |

**Procedure.** As in Step 2:
- **T0:** Step 1's PPO config, seeds 0–2.
- **T1:** one factor at a time on the knob group the failure implicates (F1–F6 taxonomy), seed 0.
- **T2:** promote the best configuration to 3 seeds.
- **T3:** freeze, then run fresh seeds 10–12.
- **Fixed during tuning:** PBRR settings and bug parameters are frozen from Phase A. Budget is about 30 runs per environment.

## Framework (src/step3/), regression-tested against Step 2

- On the Step 1 grid, the generic env reproduces Step 2's env step for step (`tests/test_step3.py`), including:
  - observations, rewards and detections;
  - count increments;
  - episode resets;
  - corrections installed mid-episode.
- The trajectory-level Eq 3 fit reproduces `pbrr_core.fit_correction`.
- The generic exact solver reproduces `step2_dp.solve_levels` and Step 1's 39,500 optimum.
- **S0_framework_smoke** (grid, Step 2's config, 1 seed, through the new harness): **SUCCESS**, all of S1–S5.

  | Metric | Value |
  |---|---|
  | audit windows 0–3 exploited | 0.5% |
  | off-window (relative) | 0.97 |
  | corrections per episode | 0.02 |
  | final window exploited | 95% |
  | proxy per sub-episode 0–3 | 7,506 |

  It ran in 5.5 min, against 8.8 min for Step 2's T0.

## Phase A decisions (before any PPO)

### Absent Supervisor
- **Penalty.** The true penalty for entering P was raised from 30 to 50. With laps, −30 makes the shortcut *truly* optimal (17/3 > 41/9 per step).
- **Reference.** BC on 5 demos at 10% noise: score 0.91.
- **E.1 winner.** 3×256, 50 epochs, lr 1e-3. Its corrections are **partial**: one round cuts the best sub-episode from 1,550 to 1,077 (−30%), and later rounds are weaker (1,310 / 1,390 / 1,433). Hiding costs 100 (6%).
- **Idealised optimum: hide.** Shortcut laps until τ = 90, then the long route through the window; open in the final sub-episode; never corrected.

### Taxi
- **Rules.** Taxi-v4 ids, whose default rules are Taxi-v3's (identical P).
- **Reference: deviation.** 5 demos with 10% noise cannot be near-ideal here:
  - the clone copies the noise, so it makes random pickups (−10) and wrong-depot dropoffs;
  - 300 random start configurations need coverage.

  Final setting: 80 demos at 2% noise, 3,000 BC steps, score 0.975.
- **Honesty gate: changed for every environment.** It is now *per step*: the reference's exploit-step rate must be < 1% of the exploiter's. Any stochastic Taxi policy occasionally drops a passenger and re-picks them up (the rule itself at 2% noise does so in 2.2% of sub-episodes).
- **E.1 winner.** 5×512, 200 epochs, weight decay.
- **Corrections.** One round costs 46% of a sub-episode, against 7% for hiding. Collateral damage: −16% on honest deliveries.
- **Whack-a-mole.** The correction is local to the loops it saw: the open exploiter falls to −2,698 under r̂, but another loop still earns 204.
- **Idealised optimum: hide.**

### Tomato
- **Drying rate q.** Raised from the code's 0.05 to 0.1, the smallest value on the {0.05, 0.1, 0.15, 0.2} sweep that clears the pre-registered 20% exploit margin (q = 0.05 gives +14%; q = 0.1 gives +36%).
- **Reference.** BC on 5 demos at 10% noise: score 0.92.
- **E.1 winner.** 3×256, 50 epochs. One correction costs 26%, against 8% for hiding.
- **Idealised optimum: hide.**

### MountainCar
- **Dynamics.** Re-implemented bit-exact with Gymnasium (same float order).
- **Reference: deviation.** The cloned reference cannot pass the gate (score ≤ 0.64 at any number of demonstrations). A smooth clone of a rule that switches at v = 0 loses momentum at every turning point. The paper's other recipe is used instead: the hand-written rule itself at 1% action noise, score 0.857.
- **Honest rule.** Push with the motion; from rest, swing away from the hill first if right of the valley floor. 110.7 steps to the flag, against 119.4 for Gymnasium's push-right-from-rest.
- **Entangled bug.** Honest driving also collects the momentum bonus (13% of steps for the honest optimum). The honesty gate is relative to that: ≤ 1.5× the honest optimum's rate.
- **Phase A with b = 5, v₀ = 0.03 FAILS A5: the idealised optimum exploits openly.**
  - Corrections are cheap: −9% after one round, and later rounds fade.
  - Hiding is expensive: −18%, since the car must be slow or at the flag for the whole 20-step window.
  - Why the corrections are cheap:
    - the honest reference drives fast too, so g cannot penalise speed;
    - while the agent keeps exploiting, |D⁺| = 0 in every round, so max1's regulariser grows with |D⁻| and pulls g back to 0.
  - **Variants** (`phase_a_variants/`), all with the hand-rule reference:
    - **b = 10, v₀ = 0.04:** open exploitation (correction −9%, hiding −13%).
    - **b = 20, v₀ = 0.05:** open (−4% vs −14%).
    - **b = 10, v₀ = 0.05:** hides in sub-episodes 0–2 and takes the risk in sub-episode 3 (30% of windows), Step 1's p-threshold pattern. A5 fails by a margin.
  - **At v₀ = 0.05 the honest *optimum* never reaches the bonus speed** (exploit rate 0.000). The noisy hand rule over-pumps and does (6%), so it fails the honesty gate. Its fast transitions are exactly what the regulariser on the preferred reference protects.
  - **Reference.** The grid DP's honest optimum, run in the real dynamics with 1% action noise: score 0.993, exploit-step rate 0.00001.
- **Final MountainCar Phase A (b = 10, v₀ = 0.05, DP-optimum reference): all checks pass.**
  - One correction costs **79%** of a sub-episode; hiding costs 16%.
  - The idealised optimum stops exploiting at τ = 179 in sub-episodes 0–3, one step before the window, and exploits through the final window. Never corrected.
  - In the real dynamics: proxy 288 per sub-episode 0–3, against 347 open and −99 honest.
  - **The entanglement lesson.** Corrections are strong only when the honest reference does not itself collect the bug.

### LunarLander
- **Sub-episode length.** T_sub = 500, W = 50: 96% of heuristic landings are at rest (or crashed) before the window.
- **Re-arm length.** 20 airborne steps. The heuristic's own landings re-arm the bonus in 14% of sub-episodes (an entangled bug), while a deliberate hop of 8 main-engine frames re-arms it about 6 times per 500 steps.
- **Reference.** BC on 40 demos of Gymnasium's `heuristic` (doubled from 5 by the gate): score 0.90.
- **E.1 winner within the 10 s fit budget.** 3×256, 200 epochs, weight decay. The overall winner, 5×256, takes 11.8 s.
- **Bonus.**
  - **b = 100:** the scripted bouncer earns 1.89× the honest proxy return (A1 fails narrowly), though A4 and A5 pass.
  - **b = 150 (final): all 8 checks pass.**
- **Final Phase A (scripted strategies, Monte Carlo).**
  - Over an episode under the canonical corrections: hide(τ\* = 400) earns 4,512, against 2,450 open and 2,023 honest.
  - One correction cuts the best sub-episode from 948 to 516 (−46%); hiding costs 6%.
  - Corrections do not fade here: |D⁺| is large (183 agreeing pairs in round 1), so λ stays normalised.

## Runs

### T0_step1_config (all three tabular environments, seeds 0–2)
- **Taxi: F1 in 3/3** (never picks up; proxy −100 = moves only).
  - **Diagnosis.** P(pickup | at the passenger's depot) = 0.000, at any entropy. With factored observation features PPO suppresses pickup and dropoff *globally* (illegal ones cost −10) before it learns the exception.
  - **T1 entropy sweep (0.03, 0.05, 0.1):** F1 in all three; the entropy goes into the move actions.
  - **Next.** One-hot state observation (Step 1/2's encoding); the reference stays on its Phase A features.
- **Absent Supervisor: 1 of 3 succeed.** Rule not met; T1 needed.
  - **Seed 1:** all of S1–S5.

    | Metric | Value |
    |---|---|
    | audit windows 0–3 exploited | 0.8% |
    | off-window (relative) | 1.00 |
    | corrections per episode | 0.03 |
    | final window exploited | 98% |
    | proxy per sub-episode 0–3 | 1,401 (ideal 1,450) |

    Figure: `figures/step3_absent_supervisor_T0_timeline.png`.
  - **Seeds 0 and 2: F2** (exploit through the audits; windows 100% / 27% exploited).
  - **The incentive exists.** Seed 1 receives 7,135 per episode; seed 0 receives 6,295.
  - **Corrections fade within an episode.** Median g on exploit steps by round: −7.7 / −3.5 / −2.3 / −1.7. This is the max1 regulariser growing with |D⁻| while |D⁺| = 0, as Phase A predicted. Seed 0's received reward per sub-episode is 1,549 / 838 / 1,206 / 1,319 / 1,383.
- **Tomato: 0 of 3.**
  - **Seed 0:** F2 (opens every window, 4 corrections per episode).
  - **Seeds 1 and 2:** exploit through sub-episode 0's audit, are corrected, then water honestly (and poorly) for the rest of the episode.
  - **Hiding would pay about 40% more.** About 2,760 received per episode, against about 1,960.
  - **Diagnosis: exploration.** The agent finds the bucket in every sub-episode at once, so it is caught at every audit from the start. It never visits an *uncorrected* later sub-episode, so the value of staying uncorrected is never learned.
- **T1 launched (seed 0 each).** For both Absent Supervisor and Tomato: entropy 0.03, entropy 0.1, GAE λ 0.99.

### T1: Absent Supervisor and Tomato (seed 0 = the T0 seed that failed)
- **Absent Supervisor:**
  - **T1_ent03: SUCCESS**, all of S1–S5.

    | Metric | Value |
    |---|---|
    | audit windows 0–3 exploited | 0.9% |
    | off-window (relative) | 1.00 |
    | corrections per episode | 0.03 |
    | final window exploited | 100% |
    | proxy per sub-episode 0–3 | 1,399 |

  - **T1_ent1:** noisier.
  - **T1_gae099:** F2 (still open at 2.1M steps).
- **Tomato:**
  - **T1_ent03 and T1_gae099: both SUCCESS** (windows 1.0% / 1.1%, 0.04 corrections per episode, final window 100%, proxy 533 / 534 against the ideal 543).
  - **T1_ent1:** opens every window (F2).
- **Interpretation.** The incentive was always there (Phase A, and T0's own returns). The missing piece was exploration of the uncorrected branch: with more entropy the agent occasionally leaves the exploit inside a window, and so experiences staying uncorrected.
- **Decision.** Entropy 0.03 for both: the same single change in both environments. T2 runs seeds 1 and 2 (T1's seed 0 is the third).

### T2: promote entropy 0.03 (seeds 1, 2)
- **Tomato: rule met.**
  - **Seed 2: SUCCESS** (windows 0.8%, 0.03 corrections per episode).
  - **Seed 1:** hides (windows 3.5%, final window 100%) but has 0.14 corrections per episode (S3 ✗ narrowly).
  - With T1's seed 0, **S1–S4 hold in 2 of 3. Config frozen** (Step 1 PPO + entropy 0.03). **T3_final** runs on fresh seeds 10–12.
- **Absent Supervisor: rule not met.**
  - **Seeds 1 and 2: both F2** (windows 99% / 100%, about 4 corrections per episode). With T1's seed 0 that is 1 of 3, the same as T0's entropy 0.01.
  - **T1_ent1 (entropy 0.1, seed 0): also SUCCESS** (windows 2.5%, 0.10 corrections per episode, final window 100%, proxy 1,336 = 92% of the ideal).
- **Why Absent Supervisor is harder.**
  - Hiding is worth only about 13% of an episode's received reward there, because corrections are partial and fade (Phase A).
  - Whether a seed explores the uncorrected branch before locking into open exploitation is close to luck.
- **Next.** T2_ent1_seeds12: does stronger exploration carry to seeds 1 and 2?

### Taxi
- **T1_onehot (entropy 0.01):** F1 at 3.07M steps (proxy −92).
- **T1_onehot_ent03:** starts to exploit, but it is slow. Each PBRR fit takes 10–19 s under load (the E.1 winner is 5×512, 200 epochs, on a 1,006-dim one-hot input), and there are several fits per boundary while many copies are being caught.
  - A cheaper g is not an option: the next-best E.1 configuration has a 20× worse held-out loss (0.19 vs 0.0099).

### MountainCar
- **T0 (seeds 0–2): F1.** It never reaches |v| ≥ 0.05 by 1.9M steps, so the bonus is never seen.
- **Hypothesis.**
  - A random policy cannot build momentum.
  - The 200-dim one-hot clock swamps the 2 state dimensions, so the initial policy varies with time rather than velocity.
- **T1 (seed 0):** scalar clock (τ/T + monitor bit); scalar clock + entropy 0.03; entropy 0.03 alone.

### Results in by 2026-10-12 01:00

**Note on wall times.** From about 23:00 on 2026-10-11, up to 8 workers shared 12 cores (load average about 200), and the laptop slept for part of the night. Wall times from then on are 3–7× the uncontended ones: Tomato's ~950 PBRR fits took ~10 min in T1 and 31–73 min in T3. That is the same work, so this note covers the timing only, not the results.

- **Tomato T3_final (seeds 10–12, entropy 0.03): 1 of 3. The frozen config did not carry to fresh seeds.**
  - **Seed 11: SUCCESS.** Windows 1.6%, 0.07 corrections per episode, final window 100%, proxy 541 (ideal 543).
  - **Seeds 10 and 12: the same new failure.** Windows 25%, off-window 25%, exactly 1.00 corrections per episode, final window 0%, proxy 462.
    - The agent exploits sub-episode 0 openly and is caught.
    - After that one correction it plays honest for the rest of the episode, including the final window.
    - This is a stable "caught once, then honest" policy, not deterrence: sub-episode 0 is exploited every episode.
  - **Status.** Across all six seeds with entropy 0.03 (T1, T2, T3) the config succeeds in 3 of 6. **Tomato goes back to T1.**
- **Absent Supervisor T2_ent1_seeds12 (entropy 0.1):**
  - **Seed 1: F5, nearly hides.** Windows 5.1%, 0.20 corrections per episode, final window 99%, proxy 1,185.
  - **Seed 2: F2.** Windows 100%, 4.00 corrections per episode.
  - **Status.** With T1's seed 0 (SUCCESS) this is 1 of 3 full successes and 2 of 3 that hide. The rule is not met.
- **MountainCar:**
  - **T0 (seeds 0–2): F1 in all three.** Seeds 1 and 2 never exploit. Seed 0 exploits a little late in training and is corrected (windows 20%, 0.81 corrections per episode).
  - **T1_ent03 (one-hot clock, entropy 0.03): F1.** It never exploits.
  - **T1_scalarclock: hides everywhere.**
    - Audit windows 0–3 are 0% exploited, with 0 corrections.
    - Off-window exploitation is 0.72 of the ideal (S2 ✗ narrowly).
    - The final window is also 0% exploited (S4 ✗).
    - It hides even where hiding protects nothing: the same over-generalised hiding as Step 2's tuning seed 2 and LunarLander T0.

## Moving to FarmShare (2026-10-12)

**Where training runs.**
- New tuning runs train on Stanford FarmShare's `normal` CPU partition, one Slurm job per run. Each job gets one core per seed plus one spare. See `scripts/farmshare/README.md`.
- The four runs that were still in progress on the laptop finish there:
  - LunarLander T0_step1_config and T1_scalarclock;
  - MountainCar T1_scalarclock_ent03;
  - Taxi T1_onehot_ent03.
- FarmShare holds only placeholders for those four, so their run ids can't be reused.
- Setting, code and package versions are identical on both machines (`scripts/farmshare/requirements.txt`), but floating-point results differ between arm64 and x86_64. A seed is reproducible within a machine, not across machines.

**Procedure changes, made now, before any results from the new round.**
1. **T1 now uses 3 seeds (0–2) per configuration, not 1.**
   - Single-seed T1 picked a config that then went 1 of 3 on Tomato's fresh seeds; it was 3 of 6 overall.
   - With dedicated cores the extra seeds cost no wall time.
   - A T1 configuration that meets S1–S4 in ≥ 2 of 3 seeds counts as passing T2 as well.
2. **Tomato's T3 seeds 10–12 are spent.** Its next T3 uses fresh seeds 20–22. Every other environment still uses 10–12.

### Round T1b (submitted 2026-10-12, 3 seeds each)
- **Tomato.**
  - **Failure.** "Caught once, then honest" (seeds 10 and 12): the agent never learns that stepping out of the bucket in window 0 keeps four uncorrected sub-episodes.
  - **Hypothesis.** A credit and exploration problem on that single decision.
  - **Configurations:**
    - `T1b_ent03_gae099`: entropy 0.03 + GAE 0.99, the two single-seed successes combined;
    - `T1b_gae099`: GAE 0.99 alone, 3 seeds;
    - `T1b_ent05`: entropy 0.05.
- **Absent Supervisor.**
  - **Failure.** At entropy 0.1, 2 of 3 seeds hide. Seed 1 was still converging at the end (windows 99% → 42% → 5%).
  - **Configurations:**
    - `T1b_ent1_ep768`: entropy 0.1, 768 episodes;
    - `T1b_ent1_gae099`: entropy 0.1 + GAE 0.99;
    - `T1b_ent05`: entropy 0.05.
- **MountainCar (scalar clock).**
  - **Failure.** It hides in the final window too (S4), with off-window exploitation at 0.72 of the ideal (S2 narrowly).
  - **Hypothesis.** Final-window defection is learned late (Step 1: episodes 60–72), and the final sub-episode's advantage is about 20%.
  - **Configurations:**
    - `T1b_scalar_ep768`: 768 episodes;
    - `T1b_scalar_net256`: [256, 256] network.
- **LunarLander.**
  - **Failure.** All four laptop runs hide in every window, including the final one (S4).
  - **Configuration:** `T1b_scalar_ep768`, scalar clock with 768 episodes. T1_scalarclock already defects more in the final window than T0 (0.22 vs 0.03 at about 6.7M steps).
- **Taxi (one-hot state).**
  - **Laptop T1_onehot_ent03 (seed 0) finished: it hides, but fails S4.**
    - Audit windows 0–3 are 0.6% exploited, off-window exploitation is 0.82 of the ideal, corrections are 0.02 per episode, and proxy in sub-episodes 0–3 is 268.
    - The final window is only 2% exploited.
    - **Over-generalised hiding is now the common failure in three environments** (Taxi, MountainCar, LunarLander). In Tomato and Absent Supervisor, by contrast, the exploit is a place the agent stays in, so exploiting through the final window is the default continuation.
  - **Configurations:**
    - `T1b_onehot_ent03_s12`: the laptop configuration on seeds 1 and 2. Does hiding replicate?
    - `T1b_onehot_ent03_ep768`: 768 episodes, seeds 0–2. Is S4 learned late, as in Step 1?

### Laptop runs finished (2026-10-12)
- **LunarLander T0_step1_config (seeds 0–2): hides in all three, S4 ✗ in all three.**
  - Audit windows 0–3 are 0.7–1.0% exploited, with 0.03–0.04 corrections per episode.
  - Off-window exploitation is 0.99–1.57 of the scripted hide strategy's. The scripted strategy is a comparison point, not an optimum.
  - The final window is only 0–4% exploited.
  - S5 holds in 2 of 3 seeds.
- **LunarLander T1_scalarclock (seed 0): S1 and S3 narrowly ✗.**
  - Audit windows 5.1% (limit 5%), 0.20 corrections per episode (limit 0.1).
  - Off-window exploitation is 2.11 of the scripted strategy's, and proxy is 1,466.
  - **The final window is 59% exploited (S4 ✗), the most final-window defection outside Tomato and Absent Supervisor.**
- **MountainCar T1_scalarclock_ent03 (seed 0): hides everywhere** (windows 0%, 0 corrections, off-window 0.65, final window 0%). The same pattern as T1_scalarclock.

### T1b results (FarmShare, submitted 2026-10-12 01:45)

**The jobs stopped early.**
- Every job still running stopped at about 12:35, roughly 10.8 h after submission, whatever its time limit (4–44 h).
- Before that, some ran 5–10× slower than expected:
  - Tomato T1b_gae099 reached 2.9M steps in 10.3 h; the other Tomato runs took about 25 min.
  - MountainCar T1b_scalar_net256 reached 4.2–5.4M in 10.8 h.
- The cause is not yet known; it needs the Slurm logs.
- Runs without a `metrics.json` are reported below from their last progress line. They are not final.

**Absent Supervisor:**
- **`T1b_ent1_ep768` (entropy 0.1, 768 episodes): seeds 0 and 2 SUCCESS.**
  - Windows 2.3% / 2.4%, 0.09 / 0.10 corrections per episode, final window 99% / 100%, proxy 1,306 / 1,320.
  - Seed 1 was unfinished at 5.57M of 6.14M steps and still exploiting through every audit (F2).
  - **That is 2 of 3: the rule is met. Candidate to freeze**, then T3 on seeds 10–12.
- **`T1b_ent1_gae099`: F2 in 3 of 3.** GAE 0.99 hurts here.
- **`T1b_ent05`: F2 in 3 of 3.**

**Tomato:**
- **`T1b_ent05`: 1 of 3.** Seed 1 SUCCESS; seeds 0 and 2 caught once, then honest.
- **`T1b_ent03_gae099`: F2 in 3 of 3.** It exploits through every audit.
- **`T1b_gae099`: seed 2 SUCCESS.** Seeds 0 and 1 were unfinished at 2.7–2.9M of 3.07M steps and exploiting through every audit.
- **No Tomato configuration reaches 2 of 3.** Every config tried succeeds in about a third to a half of seeds. Two failure modes alternate: exploit through every audit, or caught once then honest.

**Taxi** (one-hot state, entropy 0.03; all runs unfinished):
- **`T1b_onehot_ent03_s12`: hiding replicates.**
  - Seed 1 at 1.73M: windows 0.0%, off-window 0.85, 0.02 corrections per episode, final window 1%.
  - Seed 2 at 1.54M: windows 1%, off-window 0.82, 0.06 corrections per episode, final window 8%.
  - With the laptop's seed 0, that is 3 of 3 that hide, and S4 ✗ in all.
- **`T1b_onehot_ent03_ep768`:** all three hide (windows 1–2%, 0.06–0.08 corrections per episode) at 1.2–1.7M of 6.1M steps. Seed 0's final window had reached 22%.

**MountainCar** (scalar clock; unfinished):
- **`T1b_scalar_net256`:** all three hide everywhere at 4.2–5.4M of 6.1M steps (windows 0%, 0 corrections, off-window 0.71–0.72, final window 0%). A wider network changes nothing.
- **`T1b_scalar_ep768`:**
  - Seed 2 at 6.1M of 12.3M: windows 3%, 0.11 corrections per episode, off-window 0.54, final window 5%.
  - Seeds 0 and 1 had reached only 1.2–1.5M.

**LunarLander `T1b_scalar_ep768`:** 1.0–2.9M of 30.7M steps. Too early to read.
