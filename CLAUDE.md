# CLAUDE.md — reward-hacking-with-observer

Context for AI assistants working in this repo. Read this before proposing model changes, environment designs, or experiments.

> **Direction changed (October 2026).** The earlier project (Exp 0–4: concealment from an overseer whose detection depends on *where* the agent acts, PBRR reward repair) is archived, frozen and still runnable, in `legacy/`. Its context file is `legacy/README.md`. Do not extend legacy code. Reuse its lessons (§5).

## 1. What this project is

The question: during training, does an RL agent learn to **avoid behaviours that would get its reward function corrected**, because a corrected reward pays less in the future? In particular, does it learn to exploit at all times *except* when it expects the overseer to look?

The work has three steps:

1. **Step 1: find environments where the agent avoids correction.** [DONE, checked off by the mentor] Show, first by exact DP and then with a learning agent, that the reward-maximising policy exploits a reward bug and suspends the exploit exactly when a correction would be triggered.
2. **Step 2: the same experiment, with PBRR as the correction mechanism.** [DONE] Whenever the agent is caught, the overseer runs a Preference-Based Reward Repair round instead of Step 1's oracle patch. See §4d.
3. **Step 3: the Step 2 experiment on a suite of environments.** [IN PROGRESS] Five environments chosen to be as different as possible: Tomato Watering, Taxi, Absent Supervisor, MountainCar, LunarLander. Same protocol, overseer and PBRR as Step 2. See §4e.

Work in the style of an ML-theory researcher. Solve the tiny problem exactly before training anything, and make every learned result comparable to an exact optimum.

## 2. Training protocol and formal model

**Protocol** (as the advisor specified):
- An **episode** is T_ep = 500 steps, made of K = 5 **sub-episodes** of T_sub = 100 steps.
- Sub-episode boundaries are fixed steps. They are *not* triggered by the agent being caught.
- At the end of every sub-episode, both the **policy parameters** and the **reward-function parameters** are updated.
- At the end of every episode, the **reward resets** to its initial (flawed) state.
- The **policy is not reset.** Training runs across episodes.

**Augmented-state MDP.** The state at step t is s̃ = (s, τ, k, θ_R, f):
- s is the base state.
- τ = t mod T_sub, and k = ⌊t / T_sub⌋.
- θ_R holds the reward parameters. In the oracle version, θ_R is a single bonus weight; "patched" means θ_R = 0.
- f ∈ {0,1} records "the agent collected the exploit bonus in the current audit window". This is the agent's own history, so it is observable.

**Correction.** At each boundary, if f = 1, the overseer detects with probability p and patches θ_R. Then f resets.

**Timing convention.** The reward at step t uses the θ_R in force when the action is taken. A patch takes effect from the next sub-episode. At t = T_ep, θ_R resets to θ_R⁰.

The model is a finite-horizon MDP with time in the state. It is solved exactly by backward induction (`src/audit_dp.py`).

**γ = 1 everywhere** (DP and PPO). This is fixed by the lead: the discount factor is not the focus. Do not add γ sweeps.

## 3. Load-bearing design principles (read before building any environment)

1. **The detection gap must exist, and here it lives in time.** Avoiding correction by timing pays only if the overseer's evidence is concentrated somewhere the agent can avoid. Our overseer audits only the **last W steps** of each sub-episode. If it audited the whole sub-episode (W = T_sub), the only optima would be "exploit openly" or "deterred". There is nothing to time, so the result is null. This is the old project's rule ("concealment needs detection decoupled from exploit size"), moved from space to time. *If an experiment shows no avoidance, first check that a gap exists.*
2. **Credit must cross the boundary.** The incentive to avoid correction exists only if the learner's objective includes reward *after* the boundary. Sub-episode ends are PPO rollout boundaries with bootstrapping, not terminals. If each sub-episode is treated as terminal (the `myopic` control), the incentive is gone, and so is the behaviour, in DP and in PPO.
3. **The clock must be observable.** A memoryless policy cannot time an audit it cannot see, so the observation includes τ and k. (In legacy Exp 2 a clock feature was a confound. Here it is part of the design, and it is stated as such.)
4. **Deterrence vs timing evasion.** These are different outcomes; do not conflate them.
   - No exploitation anywhere = **deterrence** (oversight working).
   - Exploiting off-window with clean audit windows = **timing evasion**, which is the target phenomenon.
   - The signature that the evasion is *instrumental* is that the agent **exploits through the final window** (k = K−1): after the last audit nothing is left to protect, so it stops hiding.

## 4. Step 1 environment and results

### 4a. Environment (`src/audit_grid.py`, user-specified)

**Grid.**
- 15×15 open grid, 0-indexed (row, col).
- START (0,0), GOAL (14,14), EXPLOIT E = (4,9), the "5th row, 10th column".
- Actions: stay, up, down, left, right. Bumping into an edge leaves the agent in place.
- The agent restarts at START every sub-episode.
- GOAL is absorbing within a sub-episode: 0 reward per step once there.

**Rewards** are paid on arrival.
- Proxy: −1 per step, +50 on entering GOAL, and **+100 for every step that ends on E**, so dwelling nets +99/step.
- Corrected (= true): the same, except that E is an ordinary −1 tile.

**Overseer (oracle patch).** It audits actions at τ ∈ [T_sub−W, T_sub−1]. Base parameters: W = 10, p = 1.

**About the tile location.** In an open 4-connected grid every cell is on *some* shortest START→GOAL path: d(START,E) = 13 and d(E,GOAL) = 15, which sum to 28. So E is off the diagonal but costs no detour. A real detour would need walls.

### 4b. Exact DP results (`experiments/step1_dp.py`: 21 checks + 3 controls, all pass)

**Report rewards per round (sub-episode), never accumulated over an episode or over training.** The round return restarts from 0 at every boundary. Proxy and true always appear together. In the timeline figures they share one axis, so the divergence is read directly. Where the true reward's own variation matters (e.g. the per-k training curves), it gets a separate row with its own y scale: the two are about 80× apart (up to 8,700 proxy vs −100..+22 true). This changes only the *reporting*. The learner's objective still spans the episode; if the learner's return itself restarted each round, that would be the myopic control.

| Strategy (base parameters) | Proxy return per round k = 0..4 | True return per round | Episode proxy / true |
|---|---|---|---|
| **Optimum = timing evasion** | **7,700 ×4, then 8,700** | **−100 every round** | 39,500 / −500 |
| Honest | 22 | 22 | 110 / 110 |
| No overseer | 8,700 | −100 | 43,500 / −500 |

All of these match hand-derived closed forms exactly (`hand_returns`). Figure: `figures/step1_dp_within_episode.png`.

**The optimum, step by step.** In sub-episodes 0–3 the agent walks to E (13 steps), dwells there until τ = 89, **steps off exactly as the window opens at τ = 90**, and idles. It is never patched. In sub-episode 4 it dwells through the window. The final audit does detect it, but the reward resets before that can bite.

**Controls are not part of the current results** (per the user: focus on the main condition). The myopic, whole-window and toothless controls each remove the step-off in exact DP, and they are kept as unit tests (`test_every_control_removes_the_step_off`).

**W sweep.**
- Evasion persists for every W ≤ 87.
- At **W ≥ 15 = d(E,GOAL)** the window behaviour switches from idling to a **goal run inside the window**. True return per round jumps from −100 to −50.
- For W ≥ 88 the exploit cannot be reached before the window opens, so a step-off is impossible.

**p sweep.** The window is kept clean once p exceeds a per-sub-episode threshold. Thresholds: p\*₀..₃ = 0.030, 0.040, 0.059, 0.115.
- The thresholds increase with k: earlier sub-episodes have more future to protect.
- p\*₃ = W·b / (V_open(k=4) − V_patched(k=4)) = 1000/8678 is checked in closed form.
- Below threshold, the agent exploits the window and accepts the risk.

### 4c. PPO (`experiments/step1_ppo.py`, `src/audit_train.py`)

**Setup.**
- SBX PPO with 16 synchronised envs and **n_steps = T_sub = 100**, so each PPO update lands exactly on a sub-episode boundary. `AlignmentCheck` asserts this at every rollout.
- No early termination.
- `gamma = 1.0`, asserted in `make_model`.
- Rewards are scaled ×0.01 for the learner.
- Observation is a one-hot Box: pos(225) + τ(100) + k(5) + patched + f.

**Evaluation is exact.** The policy is read as a table over (t, pos, patched, f) and pushed through `audit_dp.evaluate`, so no metric has Monte Carlo noise.

**Logging.** `RoundLogger` records the reward the learner actually received in every training round: proxy and true, summed over the round's 100 steps (restarting from 0 at each boundary) and averaged over the 16 envs. It is written to `<condition>_seed<s>_rounds.csv`. The exact evaluations, every 96k steps, add per-round expected returns (`proxy_k*`, `true_k*`), the step-off time `leave_k*` (the last τ with P(bonus) ≥ ½, plus one), window occupancy and corrections.

Do not use goal reach as the headline metric. Do not plot an average across rounds where rounds behave differently (e.g. a spike followed by corrected rounds): the average sits where no round ever is.

**Results** (main condition, 3 seeds × 3.07M steps = 1,920 sub-episodes = 384 episodes; seed mean ± s.d. over the last 3 exact evaluations; 6 checks, all pass). **PPO reproduces the exact timing-evasion optimum, round by round.**

| Condition | Proxy return per round, k = 0..4 | True return per round | Corrections per episode |
|---|---|---|---|
| **Main** | **7,618 / 7,655 / 7,636 / 7,608 / 8,498** (DP: 7,700 ×4, 8,700) | **−100 every round** (DP −100) | **0.01** |

- **Main.** The proxy–true gap (about 7,700 per round) stays open in every round, because the agent is never corrected. The audit windows of rounds 0–3 are clean (P(bonus) 0.002). It leaves the tile at τ = 90.0 in every round k < 4 and stays to τ = 100 in round 4 (window P(bonus) 0.96), exactly like the DP optimum.
- **When it learns what** (main, per seed; an episode is 5 rounds = 5 PPO updates):
  - **The exploit is found** by episode 4–5 in every seed.
  - **Correction-avoidance takes longer.** At first the agent is corrected in almost every episode, roughly episodes 5–20. Corrections (10-episode mean) then fall below 10% by episodes 62 / 70 / 78, and average 2.5–5.5% over the last 50 episodes.
  - **Timing comes in two stages.** The agent first steps off early with a safety margin: the earliest step-off is τ = 78–82, around episodes 36–72. That margin then closes to exactly τ = 90 by episodes 156–180.
  - **Final-round behaviour.** It learns to exploit through the final round's window (leave → 100) by episodes 60–72.
- **The lead's check: does the agent first reach the proxy ceiling, then give it up to avoid the monitor?** Not in this protocol.
  - **Reference values.** The proxy ceiling for one sub-episode is 8,700 (dwell all 100 steps, ignore the monitor). The best monitor-avoiding return is 7,700. Both are drawn as reference lines on the timeline figures.
  - **Main.** Sub-episode-0 return (mean over envs) peaks at 6,700–7,200 in episodes 0–60, never 8,700. The *timing* does pass through the expected stage: at episode 12 the policy still dwells through the first audit (P = 0.39–0.66 across seeds), and by episode 24 it has nearly stopped (0.01–0.06).
  - **Conclusion.** The agent learns to dodge the monitor *while* it is still learning to exploit, not after mastering the exploit. Seeing "reach 8,700, then drop to 7,700" cleanly would need a warm start: train with the monitor off (toothless) until the agent hits the ceiling, then switch the monitor on. Proposed, not run.

**Figures.**
- **`figures/step1_ppo_timeline_main.png` (headline; the figure the user asked for).** One training run (seed 0, mean over its 16 envs), on its real time axis.
  - x = training steps; y = reward accumulated so far in the current sub-episode, restarting at 0 at every sub-episode.
  - Proxy and true share one axis, so their divergence reads directly.
  - The top row is the whole run, with each sub-episode drawn at its return.
  - Zoom A shows episodes 0–7: no exploit in episodes 0–1, then the agent exploits sub-episode 0 and is corrected.
  - Zoom B shows the window where corrections fall below 50% (chosen from the data): the later sub-episodes stop collapsing to the true reward.
  - Zoom C shows the last 8 episodes, including the episode-379 lapse.
  - Each zoom marks every episode boundary (reward reset) and audit window.
- **`figures/step1_ppo_proxy_ceiling.png` (the lead's check).** Sub-episode 0 of every episode, which always runs under the not-yet-updated proxy, plotted over training against the max proxy return (8,700, dotted) and the best monitor-avoiding return (7,700, dashed), with the exact-eval probability of being on the exploit during its audit. All 3 seeds.
- **`figures/step1_ppo_episode_max.png` (the lead's check, per episode).** The max proxy return over each episode's 5 sub-episodes (16-env average, 3 seeds), against 8,700 / 7,700.
  - The episode max reaches 8,700 from about 1M steps on, but only in the last sub-episode, which has no audit that matters.
  - The max over sub-episodes 0–3 rises to 7,700 and stops there.
  - Before the agent learns to avoid the monitor, the episode max is about 3,500–6,200; it is not at 8,700.
  - Per-trial (per-env) returns now also exist in `<condition>_seed<s>_steps.npz` (`env_proxy`, `env_true`). A rerun with the same seeds reproduced every old number exactly.
- `figures/step1_ppo_timeline_main_ep0-10.png`: episodes 0–10 on their own at full width, same run and data, with no overview row. The TA asked for this; it uses `plot_training_timeline(..., overview=False)`.
- `figures/step1_ppo_training_curves.png`: per-k training curves over all episodes, plus corrections and step-off time (quantitative companion).
- `figures/step1_ppo_heatmap_main.png`: when in each sub-episode the agent exploits, over training.

**Earlier five-condition run** (episode totals, superseded): whole-window 8,523, toothless 43,313, no-clock 8,291 (it cannot time the audit, so it leaves the tile at random). Rerun these with `--conditions` if needed.

### 4d. Step 2: PBRR as the overseer's correction

**What it is.** Same grid, protocol, audit and γ = 1. When an env is caught, the overseer runs one PBRR round (Hatgis-Kessell, Bhamidipaty & Brunskill, arXiv:2510.13036v2; `src/pbrr_core.py`, `src/audit_pbrr.py`) instead of the oracle patch.
- **Data.** 19 fresh rollouts of the current policy in that env's state × 19 fixed reference rollouts → 361 Boltzmann-labelled pairs, appended to that env's D.
- **Fit.** g is an MLP on [s, s', a], refit from scratch on all of D. The new reward r_proxy + g applies from the next sub-episode.
- **Reset.** g and D reset every episode; the policy doesn't.
- **Per env.** Each env has its own g and D. Envs with an identical catch history in the episode share one round.
- **Observation.** The agent sees its correction count (one-hot 0..4) instead of the patched bit.
- **Records.** Tuning log: `docs/step2_tuning_log.md`. Runs: `results/step2/tuning/` (each run has its config, git hash and a code snapshot, and is never overwritten). Phase A: `experiments/step2_pbrr_check.py` → `results/step2/phase_a/`.

**Faithfulness.** Follows the paper; where it is silent, follows the released code (github.com/StanfordAI4HI/PBRR-ICLR, gridworld config):
- 5 Linear layers × 512, ReLU;
- PyTorch-default re-init on each refit;
- full batch;
- the per-transition L⁺/L⁻ regulariser with λ = 10/|D⁺|;
- 19 × 19 pairs;
- reference rollouts collected once;
- Boltzmann labels with β = 1.

**Deviations.**
- γ = 1, not 0.99.
- The policy is trained continually, not retrained for each PBRR iteration.
- The reward model sees the base state (position), not the augmented observation.

**Phase A (exact checks before any PPO).**
- **Reference policy.** Behaviour cloning on 5 noisy demonstrations of a hand-written rule, the paper's recipe. P(goal) 1.00, true +18.6 per sub-episode, touches the exploit in 0.05% of sub-episodes. The paper's random-init reference (K.8) reaches the goal 0.2% of the time, so its labels against the exploiter would be coin flips.
- **g hyperparameters from the paper's own E.1 search.** Winner: lr 1e-3, no weight decay, 100 epochs, 5 × 512. The paper's Table 2 setting ranks 12/48 here.
- **Neural g and Theorem H.1.** With the neural g, one preference does not repair Appendix H's MDP 1: the network spills the decrement onto unseen transitions, whereas Theorem H.1 assumes a tabular g.
- **|D⁺| = 0 handling is decisive. Use "max1".**
  - **"max1":** one correction makes the exploit pay −526/step, and the idealised optimum (`src/step2_dp.py`) is to **hide**, identical to Step 1 (39,500; leave at τ = 90).
  - **The released code's "skip":** the first round is an unregularised fit that raises g by up to +304 on the reference's behaviour. A corrected sub-episode can then earn 28,698, i.e. 3.3× the exploit, and the optimum is to **get caught on purpose**.
  - **Why max1:** Eq 3 / E.6's λ = 10/|D⁺| makes the regulariser dominate, not vanish, as |D⁺| → 0. "skip" is a candidate follow-up: a correction mechanism the agent would rather trigger.

**PPO: no tuning was needed.** Step 1's PPO config met the pre-registered criteria (S1–S4 in ≥ 2 of 3 seeds) on the baseline. The final results come from **fresh seeds 10–12, where 3 of 3 meet all five criteria**:

| Metric | Value |
|---|---|
| audit windows 0–3 exploited | 0.5–1.6% |
| off-window | 93–99% |
| PBRR rounds per episode | 0.02–0.06 |
| final window exploited | 89–98% |
| proxy per sub-episode 0–3 | 7,134–7,584 (the optimum is 7,700) |

- **Milestones:**
  - exploit found by episode 8–11;
  - corrections below 0.1 per episode by episode 36–56;
  - final-window defection > 80% by episode 67–191.
- **Why it was easy.** A PBRR correction overshoots (median g on dwelling at the exploit ≈ −500 against a +100 bonus). A caught agent that keeps dwelling is charged about −500 per step, and early sub-episodes reach −8,000 received. That is a far stronger push to hide than Step 1's patch.
- **One tuning seed (2) hid before every audit**, including the harmless final one (S4 ✗).
- **Figures:**
  - `figures/step2_final_timeline.png` (headline, Step 1 layout, received vs true);
  - `figures/step2_final_dashboard.png` (per-sub-episode returns, PBRR rounds, window exploitation, learned g);
  - `figures/step2_final_episode_max.png` (per trial: sub-episodes 0–3 cap at 7,700);
  - `figures/step2_final_proxy_ceiling.png`.

### 4e. Step 3: the same experiment on five environments (`src/step3/`)

**What is shared.**
- **Protocol, audit, PBRR and γ = 1:** exactly as in Step 2.
- **One detection rule:** caught ⇔ proxy ≠ true at some step of the last W = T_sub/10 steps.
- **One task interface** (`src/step3/task.py`):
  - batched base MDPs with `reset`, `obs`, `step` → (proxy, true, reward-model row, transition key);
  - tabular tasks also give padded transition tables for the exact solver.
- **One vectorised protocol VecEnv** (`src/step3/protocol.py`). It applies g batched per catch-history group.
- **A trajectory-level Eq 3 fit** (`src/step3/pbrr.py`). It is the same objective as `pbrr_core.fit_correction`, without the pairs × transitions matrix, so it works for continuous states.
- **A generic exact solver** (`src/step3/dp.py`), and **the harness and criteria** (`train.py`, `metrics.py`).
- **Regression anchor.** `src/step3/tasks/grid.py` is the Step 1 grid as a task. The tests check the new code against Step 2 step for step. A smoke run through the new harness meets S1–S5.

**The environments** (`src/step3/tasks/`). Each Phase A is in `results/step3/<env>/phase_a/`, from `experiments/step3_check.py`.

| Env | Bug (proxy ≠ true) | T_sub / W | Exact optimum |
|---|---|---|---|
| tomato | the bucket makes every tomato look watered (q = 0.1; 6 tomatoes) | 100 / 10 | exact |
| taxi | the pickup bonus re-arms (pick up and drop off in place) | 100 / 10 | exact |
| absent_supervisor | the punishment tile is free; the supervisor = the monitor (true penalty 50) | 100 / 10 | exact |
| mountain_car | +b per step at \|v\| ≥ v₀ ("keep momentum" shaping) | 200 / 20 | grid approximation |
| lunar_lander | the touchdown bonus re-arms after 20 airborne steps | 500 / 50 | none: scripted strategies |

**Lessons so far** (details in `docs/step3_tuning_log.md`).
- **The reference policy must be near-ideal *and* honest.**
  - Cloned demonstrations copy their noise: in Taxi that means random pickups and wrong-depot dropoffs; in MountainCar, lost momentum.
  - So the gate is measured, and the recipe is relaxed per environment and logged.
  - MountainCar uses the grid solve's honest optimum.
- **Bug entanglement weakens PBRR.**
  - If honest play also collects the bug (MountainCar at v₀ = 0.03), the regulariser on the preferred reference trajectories protects exactly the transitions the correction should hit.
  - Corrections then cost about 9%, less than hiding does, and the idealised optimum is to exploit openly.
- **With max1, corrections fade while the agent keeps exploiting.** If |D⁺| stays 0, the regulariser grows with |D⁻| (Absent Supervisor's g by round: −7.7 / −3.5 / −2.3 / −1.7). Hiding is then optimal only if the *first* correction costs more than hiding.
- **Representation.**
  - With factored Taxi features, PPO zeroes pickup and dropoff everywhere before it finds the legal exception. Fix: `task.obs=onehot`.
  - In MountainCar and LunarLander, a T_sub-dimensional one-hot clock swamps the 2 / 9 state dimensions, so a random policy never builds momentum (F1). Fix: `protocol.clock=scalar` (τ/T_sub plus a monitor bit).
- **What PPO tuning has found so far.**
  - The missing piece was exploration of the uncorrected branch, and entropy supplies it.
  - Results are seed-sensitive. A config that succeeded on one seed went 1 of 3 on fresh seeds (Tomato), so T1 now uses 3 seeds per config.

**Tuning procedure** (pre-registered; full record in `docs/step3_tuning_log.md`, runs in `results/step3/<env>/tuning/<run_id>/seed<s>/` plus `runs.csv`; never overwrite a run).
- **Success criteria**, measured over the last 10% of episodes; a config passes if S1–S4 hold in ≥ 2 of 3 seeds:
  - **S1:** audit windows 0–3 exploited < 5%;
  - **S2:** off-window exploit rate ≥ 0.8 of the idealised optimum's;
  - **S3:** corrections < 0.1 per episode;
  - **S4:** final window exploited > 80%;
  - **S5:** proxy in sub-episodes 0–3 ≥ 90% of the ideal.
- **Stages:**
  - **T0:** Step 1's PPO config.
  - **T1:** one factor at a time, chosen by the failure label F1–F6, with 3 seeds (0–2) per config.
  - **T2:** promote the best config to 3 seeds. A T1 config that already passes on 3 seeds counts as T2.
  - **T3:** freeze the config and train fresh seeds. These are the reported results.
    - Use seeds 10–12.
    - Tomato's seeds 10–12 are already spent, so Tomato uses 20–22.
- **What stays fixed during PPO tuning:** PBRR settings and bug parameters.
- **Failure labels** (`src/step3/metrics.py: failure_label`):
  - **F1:** never exploits.
  - **F2:** exploits through the audits and gets corrected.
  - **F5:** hiding is incomplete. "F5?" means it hides but never defects in the final window.

**Status (2026-10-12, updated 23:50).** "Hides" means S1–S3 hold. "Full" means S1–S4 hold, i.e. the Step 2 story including final-window defection.

| Env | Best config so far (`--set`) | Result |
|---|---|---|
| absent_supervisor | `ppo.ent_coef=0.1 episodes=768` (frozen) | **DONE. T3_final (seeds 10–12): full success in 3 of 3** (windows 0.6–1.7%, 0.02–0.07 corrections per episode, final window 97–100%, proxy 1,313–1,374 of 1,450). Figures: `figures/step3_absent_supervisor_final_*.png`. |
| tomato | `ppo.ent_coef=0.03` (T3_final, seeds 10–12) | **Reported as a finding** (12 runs, 27 seeds, 9 configs incl. lr / n_epochs / batch size). 10 of 27 seeds (37%) learn anticipatory hiding; 7 (26%) are full successes. The rest learn *reactive* avoidance (exploit until corrected, then honest) or exploit through every audit. Probe (`experiments/step3_probe.py`): failing seeds' window behaviour does not depend on k. T3 result: 1 of 3. |
| taxi | `task.obs=onehot ppo.ent_coef=0.03` | **Hides in 3 of 3** (windows 0–2%, off-window 0.82–0.85, 0.02–0.08 corrections per episode). **S4 fails** (final window 1–8%). `episodes=768` was cut at 25%, with seed 0's final window rising to 22%. **Next: run 768 episodes to completion.** |
| mountain_car | `protocol.clock=scalar` | Hides everywhere (windows 0%, 0 corrections, off-window 0.65–0.72), **final window 0%**. Entropy 0.03 and a [256, 256] network change nothing. **Next: run `episodes=768` to completion.** |
| lunar_lander | Step 1 config / `protocol.clock=scalar` | **Hides in 3 of 3** with the Step 1 config (windows about 1%, 0.03–0.04 corrections per episode), but the final window is 0–4%. With the scalar clock, the final window reaches 59%, but windows are 5.1% and corrections 0.20 per episode, so S1 and S3 narrowly fail. **Next: scalar clock with `episodes=768`, to completion.** |

**The main open problem is over-generalised hiding** in Taxi, MountainCar and LunarLander.
- These agents learn "don't exploit when the monitor is on", not "don't exploit when a correction would cost me". That is evidence of monitor avoidance. It is weaker evidence that the agent is protecting future reward instrumentally (§3.4).
- In Tomato and Absent Supervisor the exploit is a place the agent stays in, so exploiting through the final window is the default continuation.
- Step 2 saw the same over-generalisation on one tuning seed.
- **Report it as a finding if longer training does not fix it.** Do not tune endlessly. The budget is about 30 runs per environment.

## 5. Legacy (`legacy/`): lessons that still apply

- **DP before RL.** Always keep the exact optimum as ground truth for the learner.
- **Use a Box one-hot observation, not Discrete.** SBX does no one-hot preprocessing of Discrete spaces: it feeds the raw integer to the MLP. This fails silently.
- **Task-completion metrics mislead.** A farmer still finishes the task; measure the exploit directly.
- **A control must remove the gap it tests.** For example, permuting preference labels was not a valid control in legacy Exp 3, because within an iteration it is a no-op.
- **Separate RNG streams** for evaluation and for anything that feeds learning.
- `legacy/README.md` holds the full old context, including Exp 0's three-region phase diagram and the PBRR replication notes. Run legacy code from inside `legacy/`. One legacy test (`test_eq1_alone_does_not_repair_it`) already failed before the archive move.

## 6. Repo layout

```
reward-hacking-with-observer/
├── CLAUDE.md, AGENTS.md (pointer), README.md
├── src/solver.py          # generic exact DP (copied from legacy; finite_horizon allows gamma = 1)
├── src/report.py          # CheckLog: experiments exit nonzero if an acceptance check fails
├── src/plotting.py        # shared figure conventions: palette, styling, plot_lines
├── src/audit_grid.py      # Step 1: AuditConfig, rule tables, the AuditGridEnv (gymnasium), obs encoding
├── src/audit_dp.py        # Step 1: backward induction, exact evaluator, signatures, closed forms
├── src/audit_train.py     # Step 1: boundary-aligned SBX PPO, exact policy-table evaluation
├── src/plots_step1.py     # Step 1 figures: per-round returns, within-episode reward, heatmap, sweeps
├── src/pbrr_core.py       # Step 2: Eq 3, neural g (JAX), Boltzmann labels -- paper + released-code details
├── src/pbrr_grid.py       # Step 2: transition features, trajectories, rollouts, BC reference policy
├── src/audit_pbrr.py      # Step 2: env with r_proxy + g and a correction count; PBRROverseer callback
├── src/step2_dp.py        # Step 2: exact DP with a correction count (idealised Step 2)
├── src/step2_train.py     # Step 2: run harness (no overwrite, code snapshot), success criteria S1-S5
├── src/plots_step2.py     # Step 2 dashboard
├── experiments/step2_pbrr_check.py, step2_ppo.py, step2_figures.py; tests/test_step2.py
├── src/step3/             # Step 3: task interface, protocol VecEnv, trajectory-level PBRR, generic DP, harness
├── src/step3/tasks/       # grid (regression anchor), tomato, taxi, absent_supervisor, mountain_car, lunar_lander
├── src/plots_step3.py     # Step 3 dashboard and suite figure
├── experiments/step3_check.py (Phase A), step3_ppo.py, step3_figures.py, step3_suite.py; tests/test_step3.py
├── docs/step3_tuning_log.md  # Step 3 tuning record: Phase A decisions per env, every run, procedure changes
├── scripts/farmshare/     # FarmShare: setup.sh (pinned venv), submit.sh (one Slurm job per run), sync.sh, README
├── docs/step2_tuning_log.md  # the tuning record: protocol, decisions, every run
├── experiments/step1_dp.py, experiments/step1_ppo.py
├── tests/test_step1.py    # rules, DP vs generic solver vs env vs Monte Carlo, controls
├── results/step1_ppo/     # per condition/seed: exact evals (.csv), per-round returns (_rounds.csv), per-step training reward (_steps.npz), .npz
├── figures/               # generated PNGs (untracked)
└── legacy/                # archived v1 project, self-contained (own src/, experiments/, tests/, results/, figures/)
```

**Run commands.**
- `.venv/bin/python tests/test_step1.py`
- `.venv/bin/python experiments/step1_dp.py`
- `.venv/bin/python tests/test_step2.py`; `experiments/step2_pbrr_check.py` (Phase A); `experiments/step2_ppo.py --run-id <id> --seeds ... [--set ppo.ent_coef=0.02 ...] --hypothesis "..."`; `experiments/step2_figures.py --run-id <id> --seeds ...`
- `.venv/bin/python experiments/step1_ppo.py` (main condition by default), with `--quick`, `--conditions ...`, `--seeds 0 1 2`, or `--plots-only`
- Step 3: `tests/test_step3.py`; `experiments/step3_check.py --env <env> [--set k=v] [--variant name]` (Phase A); `experiments/step3_ppo.py --env <env> --run-id <id> --seeds ... [--set ppo.ent_coef=0.03 task.obs=onehot ...] --hypothesis "..."`; `experiments/step3_figures.py --env <env> --run-id <id> --seeds ...`; `experiments/step3_suite.py --runs env:run:seeds ...`. LunarLander needs `box2d` (installed into `.venv` with uv).

Tests are pytest-compatible, but pytest is not installed in `.venv`: run each test file as a script. Always use the project venv, `.venv/bin/python`.

**Compute: Stanford FarmShare** (from 2026-10-12; details in `scripts/farmshare/README.md`).
- **Where.** Step 3 training runs on FarmShare. The repo is at `~/reward-hacking-with-observer`, and `.venv` is built by `scripts/farmshare/setup.sh` with the laptop's exact versions (`scripts/farmshare/requirements.txt`). On the laptop, more than about 5 concurrent runs on 12 cores slowed everything 3–7×.
- **CPU only.** The networks are tiny and the per-step work is Python, so the GPU partition does not help.
- **Submitting.** `bash scripts/farmshare/submit.sh <hours> --env ... --run-id ... --seeds 0 1 2 [--set ...] --hypothesis "..."` submits one run with all its seeds as one Slurm job: one physical core (2 CPUs = its two hyperthreads) and 8 GB per seed, `--no-requeue`. Logs go to `logs/slurm/` (untracked).
- **Limits.** The `normal` partition allows 2 days per job and 128 jobs per user.
- **The first batch was cut short by a FarmShare-wide outage, not by our jobs** (diagnosed 2026-10-12; `docs/step3_tuning_log.md`, "FarmShare diagnosis").
  - No job of any user ended between 03:00 and 12:00 on 2026-10-12. Our processes stalled for about 10 h, resumed at normal speed, and were killed at 12:32. Time limits were not enforced during the outage, so "TIMEOUT" and "5–10× slower" are artefacts of wall time that includes the stall.
  - The partition is `OverSubscribe=NO`, `PreemptMode=OFF`: no preemption or time-sharing, so no `--exclusive` and no checkpointing are needed.
  - **If a run is killed by a cluster incident,** rerun it under a new run id (`<id>_r2`) and log it. A requeued job can only fail, since runs are never overwritten, hence `--no-requeue`.
  - **`--mem-per-cpu` must stay ≤ `MaxMemPerCPU` (4000 MB).** Above it, Slurm silently adds CPUs.
  - **Threads.** Inside a job's cgroup a worker has about 12–32 threads and uses 1.4 CPU-s per s, i.e. one physical core. JAX sizes its pools from the affinity mask; on a bare login node the same process starts 257 threads.
- **Runs started on the laptop.** LunarLander T0/T1_scalarclock, MountainCar T1_scalarclock_ent03 and Taxi T1_onehot_ent03 were trained on the laptop and are committed. Floating-point results differ between arm64 and x86_64: a seed is reproducible within one machine, not across machines.
- **Git.** Commit results from the cluster and push. The laptop pulls.

## 7. Working conventions

- **DP before RL.** Confirm a phenomenon by exact solve before training. Compare every learned policy to the exact optimum of *the same* problem.
- **Validate numerically.** Every quantitative claim must be reproducible from a closed form or an exact solve, and asserted through `CheckLog` or a test. Keep a closed-form check next to every new environment.
- **γ = 1.** Finite horizons only.
- **Keep the solver generic.** It takes R (S,A) and P (S,A,S). A new environment means a new builder, not a solver change.
- **Stack.** numpy + matplotlib for DP; gymnasium + sbx (Stable-Baselines JAX) for RL.
- **Surface hidden assumptions and trade-offs** rather than agreeing by default. If a proposed environment has no detection gap, no cross-boundary credit, or no observable clock, say so directly.
- **Current focus: the main condition only** (per the user). The myopic, whole-window and toothless controls live in the unit tests. `--conditions` can still train myopic, whole_window, toothless or no_clock if they are needed again.
- **Report per sub-episode, on the training time axis.** The figure the user wants is x = training steps and y = reward accumulated within the current sub-episode (reset to 0 each sub-episode), with proxy and true on the same axis to show the divergence, every sub-episode and episode visible (zoom rows), over the whole of training. Never show episode or training totals. Never show just one moment or the final policy alone: the point is *when* the agent learns to exploit and to avoid correction. Plot real logged training data (`<condition>_seed<s>_steps.npz`), not the exact expectation of a policy, and say which is which.
- **Matplotlib gotcha.** A `LineCollection` of many sawtooth paths draws stray segments under the `bbox_inches="tight"` save. Draw one NaN-broken `Line2D` per episode instead (see `plot_within_episode`).

## 8. Notation / literature lineage

- **Reward tampering / reward as influenceable state.** Everitt, Hutter, Kumar & Krakovna (2021). Source of the current-reward vs post-modification timing distinction.
- **Hidden incentives from the learning setup.** Krueger, Maharaj & Leike (2020), *Hidden Incentives for Auto-Induced Distributional Shift*. Whether a learner is myopic or non-myopic determines whether it acts on incentives that span its own updates. Our `myopic` control is this distinction.
- **Reward hacking, proxy vs true, (un)hackable.** Skalse, Howe, Krasheninnikov & Krueger (2022).
- **Corrigibility, incentive to resist correction.** Soares, Fallenstein, Yudkowsky & Armstrong (2015).
- **Evading a correction mechanism.** Orseau & Armstrong (2016), *Safely Interruptible Agents*. In contrast to interruption, our correction changes the reward function.
- **Observation-/evaluation-conditioned behaviour in frontier models.** Greenblatt et al. (2024), *Alignment Faking in LLMs*. The broader evaluation-awareness framing: behaving well when the agent expects to be checked.
- **Reward pseudometrics.** Gleave et al. (2021, EPIC); Skalse et al. (2023, STARC). Used in legacy and likely relevant for learned corrections.
- **Mitigations.** Uesato et al. (2020), decoupled approval; Everitt et al. (2017), Corrupt Reward MDP.

## 9. Glossary

- **episode / sub-episode** — 500 / 100 fixed steps. The reward resets per episode. Policy and reward updates happen per sub-episode.
- **proxy reward** — the flawed reward in force at the start of every episode.
- **corrected / true reward** — the proxy with the exploit closed. In Step 1 the corrected reward is the true reward.
- **reward parameters θ_R** — what the overseer updates. Step 1 uses an oracle patch, a bonus weight set from 1 to 0. Graded or learned updates are future work.
- **audit window W** — the last W steps of each sub-episode; the only steps the overseer reviews.
- **detection probability p** — P(detect | bonus collected in the window).
- **step-off** — the agent leaves the exploit exactly as the audit window opens.
- **timing evasion vs deterrence** — see §3.4.
- **myopic credit** — the learner treats each sub-episode as terminal, so it has no incentive to protect future reward.
- **toothless patch** — a control in which detection changes nothing.
