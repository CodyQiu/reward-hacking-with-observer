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

### FarmShare diagnosis (2026-10-12 evening): a cluster-wide outage, not our jobs

**What happened.**
- **No job of any user on the cluster ended between 03:00 and 12:00** on 2026-10-12 (`sacct -a`). The usual rate is 100–250 per hour. Then 64 jobs ended at 12:xx, mostly FAILED or TIMEOUT.
- **Our processes stalled; they were not slow.** Each seed log has one gap of about 10 h between two consecutive progress lines, with normal speed on both sides. Absent Supervisor T1b_ent1_ep768 seed 1: 2,288 s → 38,492 s, then about 75 s per line again. Tomato T1b_gae099 seed 0: 2,350 s → 37,095 s. Every process alive at about 02:20–03:20 stalled. The ones that had finished by then (T1b_ent05 for Tomato and Absent Supervisor, T1b_ent1_gae099, and seeds 0 and 2 of T1b_ent1_ep768) were unaffected.
- **Time limits were not enforced during the outage.** Tomato T1b_ent03_gae099 had a 4 h limit and finished normally after 646 min, of which about 40 min were compute.
- **At about 12:32 every remaining job was killed** (`pam_close_session` errors in the job logs; Tomato T1b_gae099 died of SIGBUS, typical of a filesystem disappearing under a process).
  - Jobs already past their limit were labelled TIMEOUT.
  - Those on rye-01 that were not were labelled NODE_FAIL and requeued (`JobRequeue=1`). At 21:18 they restarted and failed after 26 s, because the run directories existed (results are never overwritten).
- **The partition does not preempt or time-share** (`PreemptMode=OFF`, `OverSubscribe=NO`). So neither `--exclusive` nor checkpoint/resume is needed. A run killed by a future incident is rerun under a new run id (`<id>_r2`).

**What was wrong in `submit.sh`, and the fix.**
- **Memory.** `--mem-per-cpu=4G` (4,096 MB) exceeds `MaxMemPerCPU=4000`, so Slurm silently doubled every CPU allocation (AllocCPUS 8 for 4 requested). It cost cores, not speed. Now `4000M`.
- **Cores.** A worker uses 1.4 CPU-s per s inside its cgroup (Python plus JAX's dispatch threads), i.e. both hyperthreads of one core. The job now asks for 2 CPUs (= 1 physical core) per seed; the parent process only waits.
- **`--no-requeue`.** A requeued run can only fail.
- **Threads.** Inside a job a worker has 12 threads on 2 CPUs, or 32 on 6. JAX sizes its pools from the affinity mask, not the node; on a bare 80-core login node the same process starts 257. The harness's `XLA_FLAGS` contained a malformed token (`intra_op_parallelism_threads=1`, no `--`) that XLA silently ignored. It was removed; behaviour is unchanged.

**Confirmed before any long run** (smoke runs in the untracked `logs/smoke/`, not tuning runs).
- **One seed, 1 core on wheat-01:** Tomato, 24 episodes in 222 s, the same rate as T1b_gae099 on wheat-08 before the stall (224 s). RSS 1.3 GB.
- **Three seeds in parallel with the new flags on rye-02:** AllocCPUS 6, a cpuset of 3 physical cores, 198–203 s each. No contention, and identical numbers across the three, as expected for one seed on one machine.
- **Node speed differs:** barley (Zen 4, 3.1 GHz) takes about 126 s per 192k Tomato steps, wheat (Skylake, 2.4 GHz) about 222 s. Wall times are not comparable across nodes.

### Round T1c / T3 (submitted 2026-10-12 evening, with the fixed `submit.sh`)
- **Absent Supervisor: freeze `ppo.ent_coef=0.1 episodes=768` and run `T3_final` on seeds 10–12.**
  - T1b_ent1_ep768 seeds 0 and 2 met S1–S5 with completed metrics. That is 2 of 3 whatever seed 1 would have done; seed 1 was still F2 at 5.57M of 6.14M steps when the outage killed it.
- **Taxi, MountainCar, LunarLander: rerun the 768-episode configurations to completion on seeds 0–2,** under new run ids: `T1c_onehot_ent03_ep768`, `T1c_scalar_ep768` and `T1c_scalar_ep768`.
  - **Question.** Does final-window defection (S4) appear with longer training? All three hide well, but they also hide in the final window.
  - **Hypothesis.** In Step 1, final-window defection came after hiding (episodes 60–72, against 36–72 for the first step-off). If the k = K−1 window is just explored late, it should show up by 768 episodes.
  - **If it does not,** that is evidence the hiding is keyed to the monitor bit or τ, not to whether a correction would cost anything. In that case diagnose it, rather than add knobs.
- **Tomato: the optimisation knob group, one factor at a time from the entropy-0.03 base, seeds 0–2.**
  - **Diagnosis** (received reward, last 10% of episodes):
    - hiding gets 2,730 per episode;
    - "caught once, then honest" gets 2,266 (−17%);
    - exploiting through every audit gets 1,900.

    So the incentive exists.
  - **Mechanism.** Every seed starts by exploiting through every audit. It succeeds only if it discovers stepping off at sub-episode 0's window during that phase. Otherwise it first learns "after a correction, play honest", from immediate negative rewards. That is a local optimum. Hiding in sub-episode 0 then pays only if the agent also exploits in sub-episodes 1–3 with 0 corrections, states it never visits. One deviation, hiding alone, loses about 47 in sub-episode 0 and gains nothing.
  - **Hypothesis.** Hiding is credited through the critic, across the boundary. PPO's clip bounds how far the policy moves per update, so more optimisation per update mainly sharpens the critic, and hiding is found before honesty-after-correction locks in.
  - **Configurations:**
    - `T1c_lr1e3`: learning rate 1e-3, up from 3e-4;
    - `T1c_epochs20`: n_epochs 20, up from 10;
    - `T1c_batch100`: batch size 100, down from 400, i.e. 16 minibatches per update instead of 4.
  - **Budget.** Tomato has used 9 runs. If none of these reaches 2 of 3, Tomato is reported as a finding, a local optimum of policy-gradient learning, not tuned further.

### Round T1c / T3 results, part 1 (2026-10-12, 23:00)

**Absent Supervisor T3_final (seeds 10–12, entropy 0.1, 768 episodes): SUCCESS in 3 of 3. Absent Supervisor is done.**

| Seed | windows 0–3 | off-window | corrections/ep | final window | proxy 0–3 |
|---|---|---|---|---|---|
| 10 | 0.6% | 0.99 | 0.02 | 1.00 | 1,374 |
| 11 | 1.4% | 0.99 | 0.06 | 0.98 | 1,369 |
| 12 | 1.7% | 0.97 | 0.07 | 0.97 | 1,313 |

- **Wall time:** 33 min.
- **Story** (`figures/step3_absent_supervisor_final_*.png`):
  - PBRR rounds fall from 4 to about 0 per episode between 1.0M and 1.6M steps.
  - Windows 0–3 drop to about 1%, while the final window stays near 1.0 throughout.
  - In the last episodes the received return is about 1,370 in sub-episodes 0–3 and about 1,520 in the final one.
  - The best sub-episode among 0–3 settles at 1,400, one lap below the idealised 1,450: a safety margin, like Step 1's first stage of timing. The final sub-episode reaches the 1,550 ceiling.

**Tomato, optimisation knob group (entropy-0.03 base, seeds 0–2): no configuration reaches 2 of 3.**

| Config | Full successes | Seeds |
|---|---|---|
| `T1c_lr1e3` | 0 of 3 | s1 hides but misses S3 at exactly 0.10 corrections/ep; s0 F2; s2 caught once, then honest |
| `T1c_epochs20` | 1 of 3 | s0 SUCCESS; s2 hides with 10% of windows exploited and 0.41 corrections/ep; s1 F2 (windows 75%) |
| `T1c_batch100` | 0 of 3 | s0 and s2 caught once, then honest; s1 deterred (never exploits by the end) |

- **Across all 27 completed Tomato seeds (12 runs, 9 configurations including T0), the same outcomes recur; only their proportions change** (counted from each seed's `metrics.json`):
  - **full success:** 7 (26%);
  - **hides, but narrowly misses S1 or S3:** 3 (T2 seed 1 at 0.14 corrections/ep; T1c_lr1e3 seed 1 at 0.10; T1c_epochs20 seed 2 at 10% windows and 0.41);
  - **caught once, then honest:** 10. An absorbing outcome: windows exactly 0.25 and 1.00 corrections/ep for the rest of training (T0 seeds 1 and 2 are close: 0.22–0.27 and 0.89–1.08);
  - **exploits through every audit:** 6;
  - **deterred:** 1.

  So 10 of 27 seeds (37%) learn to hide.
- An earlier version of this entry gave 25 seeds and 8 configurations; the counts above replace it.

**Probe of the trained policies (new `experiments/step3_probe.py`).**
- **Method.** Run the saved policy for one sub-episode at every (k, correction count), including cells training never visits. The proxy is uncorrected, with 256 Monte Carlo rollouts on a separate RNG stream. Output: `results/step3/tomato/probes/`.
- **Validated** against the training logs, cell by cell: T1b_ent05 seed 0 at k = 0 gives window 0.23 in the probe against 0.16 in the last 10% of training, and at k = 1 with 0 corrections 0.93 against 0.87. The probe uses the final policy, while training averages over the last 10% of episodes.
- **The earlier mechanism was wrong.** In the "caught once, then honest" seeds, the policy with 0 corrections in sub-episodes 1–3 *does* exploit (T3 seed 10: off-window 0.67–0.73). So hiding in sub-episode 0 would pay, and the unvisited states are not the obstacle.
- **What failed seeds actually do.** With 0 corrections, their window behaviour does not depend on k. They dwell through the window in every sub-episode where they exploit:
  - T3 seed 10: window P = 1.00 at k = 0 and 0.96–0.99 at k = 1–3;
  - T1b_ent03_gae099 seed 0: 1.00 in every k.

  The successful seeds hide at k = 0–3 and dwell at k = 4 (T1b_ent05 seed 1: 0.00 / 0.00 / 0.00 / 0.00 / 1.00).
- **Revised diagnosis.** What the failing seeds learn is *reactive* correction-avoidance (stop exploiting once corrected), not *anticipatory* hiding.
  - The reactive policy has an immediate training signal: the negative received reward under g.
  - The anticipatory one needs a fully clean window (caught ⇔ *any* exploit step in the W = 10 window steps) and credit across the boundary. One step out of the bucket changes nothing about being caught and costs that step's proxy, so its advantage is ≤ 0.
  - Seeds whose bucket-dwelling becomes near-deterministic before a fully clean window has been sampled stay reactive.
- **Decision: stop tuning Tomato (12 runs) and report it as a finding.**
  - The reported result is T3_final (seeds 10–12, entropy 0.03): 1 of 3 full success. Across configurations, 37% of seeds learn anticipatory hiding (26% full).
  - Running further PPO knobs would be tuning forever: none of the 8 configurations changes the three-outcome structure.
  - **Possible follow-ups, not run:**
    - many seeds of one config, to estimate the success rate with an error bar;
    - an exact check that a partial step-off earns nothing under the any-step detection rule.

**Reproducibility note.** MountainCar T1c_scalar_ep768 seed 2 is bit-identical to the killed T1b_scalar_ep768 seed 2 through 3.84M steps, then diverges (1 vs 19 PBRR rounds by 4.22M). Same seed, config and node type; the CPU allocation (8 → 6 CPUs) differed, and so did a no-op XLA flag. A seed is reproducible within one allocation, not exactly across allocations.

### Why the final window is hidden too (probe, 2026-10-13, before the T1c 768-episode results)

**Method.** `experiments/step3_probe.py` on the finished models that hide but fail S4. Output: `results/step3/<env>/probes/`. It reports P(exploit in the window) per k with 0 corrections, under the uncorrected proxy. For tabular tasks it also reports the exact P(exploit action) by τ at the states the policy holds just before the window.

| Run | Window exploited, k = 0 / 1 / 2 / 3 / 4 | Reading |
|---|---|---|
| Taxi T1_onehot_ent03 s0 | 0.01 / 0.00 / 0.05 / 0.02 / 0.03 | k-blind |
| MountainCar T1_scalarclock s0 | 0.00 at every k | k-blind |
| LunarLander T0 (one-hot clock) s0–2 | ≤ 0.12 at every k, no k = 4 exception | k-blind |
| **LunarLander T1_scalarclock s0** | 0.05 / 0.03 / 0.02 / 0.14 / **0.75** | **conditions on k** |

**Three mechanisms, not one.**

1. **Taxi: the hiding is keyed to the clock τ, and defecting is one action away.**
   - At the five states the policy holds before the window, P(pickup) alternates about 1.00 / 0.00 (pickup, dropoff) up to τ = 89. At τ = 90 it drops to 0.000–0.005 at k = 3 and 0.001–0.011 at k = 4, at *the same states*.
   - So the agent stays at the depot and stops pressing pickup. A single action would exploit, so reachability is not the obstacle.
   - The k = 4 exception must be learned from about 1% of exploration samples.
   - The logged checkpoints show the final window *was* exploited (0.40 → 0.80) before the hiding, learned in windows 0–3, generalised to k = 4 (→ 0.03).
2. **LunarLander: representation.**
   - With the 500-dim one-hot clock, hiding is spread over 50 window-step inputs, and no k = 4 exception is learned.
   - With the scalar clock, "monitor on" is one input bit, and monitor × k = 4 is a single interaction. The exception grew steadily over training (final window 0.10 → 0.72 across the checkpoints).
3. **MountainCar: hiding means parking at the absorbing flag, before the window.**
   - In the logged training data the proxy is exactly 0 per step over the last 40 steps of every sub-episode: the car is at the flag, which is absorbing.
   - So defecting in the final window is impossible once parked. It needs a different plan at k = 4 starting at least 20–40 steps before the window: keep swinging instead of driving to the flag.
   - Exploration rarely produces such a coordinated deviation, and GAE λ = 0.95 credits it weakly (0.95⁴⁰ ≈ 0.13).
   - The idealised optimum keeps exploiting to τ = 179 and stays slow through the window. PPO's policy parks early, at τ ≈ 160.

**What it means.** In all three environments the learned hiding is a function of the clock (τ or the monitor bit), generalised across k.
- Whether k = 4 gets an exception depends on how many steps the exception takes: one action in Taxi, a different plan in MountainCar.
- It also depends on how the clock is represented.
- In Tomato and Absent Supervisor, too, the hiding is clock-keyed in failing seeds (Tomato probe). There the generalisation runs the other way, towards exploiting every window.

**Predictions for the 768-episode runs.**
- **Taxi:** S4 should appear in some seeds (T1c seed 0 was at 82% by 2.5M steps).
- **LunarLander (scalar clock):** S4 should keep improving.
- **MountainCar:** S4 should not appear.

### Round T3 (submitted 2026-10-13 00:30): final runs for the advisor meeting
- **Headline criterion, per the user:** "exploit until the monitor, comply during it" (S1–S3). Final-window defection (S4) is reported alongside it, as the instrumental signature, but it is not required.
- **LunarLander `T3_final`:** the Step 1 config, no overrides, seeds 10–12, 384 episodes. T0_step1_config met S1–S3 in 3 of 3 seeds.
- **Taxi `T3_final`:** `task.obs=onehot ppo.ent_coef=0.03`, 384 episodes, seeds 10–12.
  - **Evidence for this config.** S1–S3 held in T1_onehot_ent03 seed 0, and hiding replicated in T1b_onehot_ent03_s12 (seeds 1 and 2, unfinished) and in T1c (3 of 3 at 2.9–5.0M steps).
  - **Procedure deviation:** this is submitted before T1c finishes, so the results are ready in time. It is reported only if T1c confirms S1–S3 in ≥ 2 of 3 seeds.
- **Tomato `T3b_rate`:** the T3 config (entropy 0.03), 10 fresh seeds (20–29). It estimates the hiding rate with an error bar, rather than tuning further.
- **MountainCar:** no final run. No config meets S2: it stops exploiting about 40 steps before the window, with off-window at 0.65–0.72 of the ideal. It is reported as "complies during the monitor, with a safety margin".
- **Update (01:15): Taxi T1c_onehot_ent03_ep768 at 768 episodes. All three seeds show S1–S4** (last progress line; final metrics pending):
  - windows 1–2%;
  - 0.05–0.09 corrections per episode;
  - off-window 0.84–0.87;
  - final window 89–91%.

  This confirms the prediction: Taxi's k = 4 exception is learned late. The passing configuration is therefore `episodes=768`, so **Taxi `T3_final_ep768`** (seeds 10–12, 768 episodes) is submitted as the proper T3. With the same seeds and a constant-schedule config, the 384-episode `T3_final` is its exact prefix.
- **Tomato `T3b_rate` (seeds 20–29):**
  - hides (S1 and S2) in 3 of 10: seed 20 full; seeds 24 and 29 miss S3 at 0.16 and 0.12 corrections per episode;
  - caught once, then honest: 5 of 10;
  - deterred: 2 of 10.

  With T3_final, **4 of 13 fresh seeds hide (31%; Wilson 95% interval for 3/10: 11–60%).**

- **Taxi T1c_onehot_ent03_ep768, final metrics (188 min): SUCCESS in 3 of 3** (S1–S4). Windows 1.4–2.0%, off-window 0.83–0.87, 0.06–0.08 corrections per episode, final window 0.88–0.91. S5 is not met: proxy 264–273 against an ideal of 354, i.e. 75–77%. This passes T2.
- **Tomato T3b_rate seed 20 figures** (`figures/step3_tomato_final_s20_*.png`): hiding is learned at about 1.0M steps.
  - While it is being learned, the final window dips to about 0.2 and then recovers. The k = 4 exception is re-learned, as in Taxi, only faster.
  - Probe (seed 20): window 0.00 at k = 0–3 and 1.00 at k = 4. The failing seeds are k-independent: seed 22 exploits every window (0.96–1.00), seed 21 is deterred (0.00 everywhere).

## Boat Race: the sixth environment (added 2026-10-13, on the laptop)

**Why add it.** Taxi, MountainCar and LunarLander hide in the final window too. Tomato and Absent Supervisor, where the exploit is a *place the agent stays in*, defect there. Boat Race's exploit is a *motion pattern*: bounce on and off a checkpoint. So it tests that "place vs pattern" explanation.

**Prediction, written before any tuning run:**
- if place vs pattern is the explanation, Boat Race hides in the final window too (S4 ✗);
- if it defects there, the explanation is wrong or incomplete.

The smoke run below is not evidence either way.

**Rules** (verified against the released `ai_safety_gridworlds/environments/boat_race.py`):
- a 3×3 ring track around a wall, with four checkpoints carrying clockwise arrows;
- −1 per move; a move into a wall stays in place and still costs −1;
- +3 for entering a checkpoint in its arrow's direction.

**On the released track the hack is an indifference, not an incentive.** Bouncing earns +1 per 2 moves and racing +4 per 8 moves. That is the README's "other solutions get the same reward". `side=3` reproduces the track, checked in tests.

**Task** (`src/step3/tasks/boat_race.py`). Deviations from the released environment, each forced by the protocol:
1. **A 5×5 ring** (16 cells, a checkpoint every 4 moves). Racing then nets (b−4)/4 per step and bouncing (b−2)/2.
2. **b = 6** instead of 3. With 3, racing on the longer ring loses money (−1/4 per step).
3. **A true reward that differs from the proxy only on the hack, as in Taxi.**
   - The true reward pays b only for the *next checkpoint in lap order*.
   - The state carries the next-checkpoint index, the policy observes it, and g sees only the cell.
4. **Only the finish line re-arms** (`finish_only`). This is the top checkpoint, next to the start. The other three pay in lap order only.

**Phase A**, run four times. Every run is kept: the first is in `phase_a/superseded/`, the variants in `phase_a_variants/`.

| Design | One correction costs | Hiding costs | Idealised optimum |
|---|---|---|---|
| All four checkpoints re-arm, g sees the cell (first design) | 4% | 9% | exploit openly |
| All four re-arm, g sees (cell, index) (`g_index`) | 6% | 9% | exploit openly |
| Finish line only, g sees (cell, index) | 9% | 9% | hides on a knife-edge (also with b = 5 or 8) |
| Finish line only, g sees the cell and a lap-complete bit (`g_lap`) | 49%, fading over rounds (101 → 184) | 9% | hides |
| **Finish line only, g sees the cell (adopted)** | **68%** (rounds 1–4: 64 / 58 / 65 / 97 of 200) | **9%** | **hides** |

- **Why the first design fails.** With every checkpoint re-arming, a correction is local. It lands on the bounce back off the farmed checkpoint (g −3.1); the move onto it looks like honest racing to g, which leaves it at +0.02. The corrected agent then simply farms another checkpoint: whack-a-mole.
- **Why the `g_index` variants fail.** Letting g see the lap index helps g, but the agent gets around it: it detours and farms under index values the correction never saw.
- **Why the adopted design works.** One instance of the bug, with g on the cell only, gives a strong and durable correction with no collateral damage: honest racing under r̂ is 50.3, against 50.0 under the proxy.
- **This is a design lesson for PBRR:** a bug with several interchangeable instances is under-corrected by a local reward-model fix.

**Adopted Phase A (all 8 checks pass):**
- **A1:** proxy optimum 200 per sub-episode against 50 for honest racing (×4.0), exploiting on 49% of steps; the true optimum never exploits.
- **A2:** the reference is 5 demos at 10% noise, the paper's recipe unchanged. Score 0.92; exploit-step rate 0.00013 against a bar of 0.0049.
- **A3:** g is 5×256, lr 1e-3, 50 epochs (held-out loss 0.0012).
- **A5:** windows 0–3 clean, final window exploited, never corrected. Proxy per sub-episode is 182 ×4, then 200, and the agent leaves the bounce at τ = 90.
- **Reward scale:** 0.5.

**Smoke run `S0_smoke_24ep`** (seed 0, 24 episodes, 0.8 min on the laptop):
- the harness, PBRR rounds (84) and figures all run end to end;
- the agent finds the bounce within about 2 episodes;
- by episode 24 it is in the "caught in sub-episode 0, then honest" phase (windows 17%, 0.69 corrections per episode).

It is not a tuning run.

**Next (cluster):**
- **T0:** Step 1's PPO config on seeds 0 1 2, plus entropy 0.03 and 0.1 arms. Entropy was the fix in Absent Supervisor and Tomato.
- **Then T1–T3** per §4e.
- **Expected cost:** about 15–20 min per 384-episode seed.

### Boat Race round T0 (submitted 2026-10-13 01:20, on FarmShare, per the plan above)
- **`T0_step1_config`:** Step 1's PPO config, seeds 0–2.
- **`T1_ent03`:** entropy 0.03, seeds 0–2.
- **`T1_ent1`:** entropy 0.1, seeds 0–2.
- **Hypothesis.** The smoke run is already in the "caught in sub-episode 0, then honest" phase at episode 24, Tomato's failure mode. Entropy, which supplied exploration of the uncorrected branch in Absent Supervisor and Tomato, should help here too.

**Boat Race round T0 results (FarmShare, 20–38 min per run).**

| Run | Seeds meeting S1–S3 | Seeds meeting S1–S4 | Notes |
|---|---|---|---|
| `T0_step1_config` | 3 of 3 | 1 of 3 | final window 0.00 / 0.90 / 0.78 |
| **`T1_ent03`** | **3 of 3** | **3 of 3 (S1–S5)** | windows 1.7–2.2%, 0.07–0.09 corrections/ep, off-window 0.94–0.99, final window 0.91–0.99, proxy 165–168 of 182 |
| `T1_ent1` | 0 of 3 | 0 of 3 | too much exploration: s2 F2; s0 and s1 incomplete hiding |

- **Decision.** `T1_ent03` passes T2. **`T3_final`** (entropy 0.03, seeds 10–12) is submitted.
- **About the pre-registered prediction** ("place vs pattern"). Boat Race's exploit is a motion pattern, yet it defects in the final window in 3 of 3 seeds. So the prediction fails, and "place vs pattern" is not the explanation. That fits the probe diagnosis above:
  - final-window defection depends on how many steps the k = 4 exception takes. In Boat Race it takes one action: keep bouncing.
  - it also depends on the clock representation.

**MountainCar T1c_scalar_ep768 (216 min): as predicted, S4 does not appear with longer training.**
- All 3 seeds: windows 0.000, corrections 0.00, final window 0.00.
- Off-window 0.71–0.73 of the ideal, so S2 narrowly fails, unchanged from 384 episodes.
- MountainCar complies during the monitor robustly, in 6 of 6 seeds across T1_scalarclock, T1_scalarclock_ent03 and T1c. It keeps a safety margin, stopping about 40 steps before the window, and the margin does not close.
- **Reported as a finding.** No further MountainCar runs (10 used).

**Boat Race T3_final (entropy 0.03, seeds 10–12, 24 min).**

| Seed | Windows 0–3 | Corrections/ep | Final window | Result |
|---|---|---|---|---|
| 12 | 2.3% | 0.09 | 0.99 | SUCCESS |
| 11 | 0.8% | 0.03 | 0.02 | hides, but S4 ✗ |
| 10 | 5.1% | 0.20 | 0.98 | narrowly misses S1 and S3 |

- **Headline criterion (S1–S3): 2 of 3. Full (S1–S4): 1 of 3.** That is weaker than T1_ent03's 3 of 3, so the config is seed-sensitive, as in Tomato and Absent Supervisor.
- **Figures** (`figures/step3_boat_race_final_*.png`): the timeline is seed 12. The dashboard's final-window line (about 0.66) is a seed mean of 0.98, 0.02 and 0.99.
- **Probe of the final snapshot** (`results/step3/boat_race/probes/`):
  - Seed 12 matches its training numbers (windows 0.00–0.02, final window 1.00).
  - Seeds 10 and 11 do not. Seed 10's k = 0 window is 0.43 against about 5% averaged over the last 10% of training; seed 11's final window is 0.46 against 0.02. Their policies are still moving at the end of training.

**LunarLander T3_final (Step 1 config, seeds 10–12, 384 episodes, 213 min on wheat-06).**

| Seed | Windows 0–3 | Off-window (rel.) | Corrections/ep | Final window | S1–S3 |
|---|---|---|---|---|---|
| 10 | 2.4% | **0.79** | 0.095 | 0.08 | misses S2 by 0.01 |
| 11 | 1.1% | 0.99 | 0.04 | 0.01 | ✓ |
| 12 | 1.4% | 1.54 | 0.06 | 0.01 | ✓ (and S5) |

- **Headline criterion (S1–S3): 2 of 3. Full (S1–S4): 0 of 3.** That replicates T0_step1_config (3 of 3 hide, S4 fails 3 of 3) on fresh seeds. S4 was predicted to fail with the one-hot clock (probe section above).
- **Timeline.** Exploit found at about 1.5M steps. PBRR rounds peak at 1.1 per episode around 2M, then stay below 0.1 per episode from about 3M steps to the end (15.4M).
- **Off-window above 1.0** (seed 12: 1.54) is real. LunarLander's reference values come from scripted strategies (no exact solve), and PPO beats them: the max proxy return over sub-episodes reaches about 1,300 per sub-episode, against the scripted exploiter's 934. S2 is measured against the scripted hide strategy, so for LunarLander it is a lower bar than in the exactly solved environments.
- **Figure fix.** The dotted and dashed lines were labelled "max proxy return" and "best monitor-avoiding return", which is wrong for a scripted Phase A. `step3_figures.py` now labels them "scripted exploiter that ignores the monitor (not a maximum)" and "scripted exploiter that hides from the audit" when Phase A is scripted. Labels for the exactly solved environments are unchanged (checked on Absent Supervisor).
- **Decision.** Report LunarLander as **monitor avoidance in 2 of 3 fresh seeds, without final-window defection**. No further runs. `T1c_scalar_ep768` (scalar clock, 768 episodes) is still running at 5–12M of 30.7M steps, with windows 5–23% and 0.2–0.9 corrections per episode. It will not finish before the meeting and is not needed.

**Correction to the Tomato fresh-seed count (2026-10-13, 04:20).** The "4 of 13 fresh seeds hide (31%)" above counted S1 and S2 only. Under the headline criterion (S1–S3), **2 of 13** fresh seeds pass: T3_final seed 11 and T3b_rate seed 20, both also with S4 (Wilson 95% interval 4–42%). T3b_rate seeds 24 and 29 hide before every audit and defect in the final window (S1, S2 and S4 hold) but are corrected 0.16 and 0.12 times per episode, above the 0.1 bar. Anticipatory hiding (S1, S2) is 4 of 13 (Wilson 13–58%; the earlier "11–60%" was the interval for 3/10). The remaining 9: 7 caught once per episode then honest (F2 label: windows 25%, 1.0 corrections per episode), 2 deterred.
