CLAUDE.md — reward-hacking-with-observer

Context for AI assistants working in this repo. Read this before proposing model changes, environment designs, or experiments.

1. What this project is

A theory-first study of when an RL agent has an instrumental incentive to hide reward hacking from a human overseer who can correct its reward function. We build a minimal formal model of a "correction loop" (agent acts → overseer may detect an exploit → overseer revises the reward to close the exploit) and ask, both analytically and numerically, under what parameter regimes the reward-maximizing policy switches from exploiting openly, to concealing the exploit, to not exploiting at all.

The intended contribution is a clean formal characterization plus small, exactly-solvable demonstrations — not large-scale training. Work in the style of an ML-theory researcher: prefer exact dynamic programming and closed-form checks on tiny MDPs before touching learning.

2. The formal model (single augmented-state MDP)

Two environments:

M_Hbar — no overseer. An ordinary stationary MDP ⟨S, A, P, r_0, γ, μ_0⟩ whose reward never changes.
M_H — overseer present. A single MDP whose state carries the correction count, so the reward index is part of the state rather than an index over a family of sub-MDPs:
Augmented state s̃ = (s, i), state space S̃ = S × ℕ₀, where i = number of reward corrections applied so far.
Reward r̃((s,i), a) = r_i(s,a) =: r(s,a,i). Proxy family {r_i}; unobserved true reward r\*.
Transition factorizes into base dynamics × a correction event. With detection probability c_i(s,a) ∈ [0,1]:
P̃((s', i+1) | (s,i), a) = P(s'|s,a) · c_i(s,a) (detected → regime advances)
P̃((s', i) | (s,i), a) = P(s'|s,a) · (1 − c_i(s,a))
Timing convention: the reward at step t uses the regime in effect at the time of action (i_t); any correction it triggers takes effect from t+1.

Analysis object (not part of M_H): the frozen-regime MDP M_i = ⟨S, A, P, r_i, γ, μ_0⟩ (base dynamics with reward r_i, no corrections), with optimal policy π_i*. The overseen optimum is π̃*; its regime-i restriction is π̃\*(· | ·, i).

Modeling assumptions currently in force:

Exploitation raises the detection hazard (more exploitative (s,a) → higher c_i).
Corrections move the proxy weakly closer to r*, measured by a reward pseudometric (EPIC / STARC) so "closer" is scale-invariant and shaping-invariant.
Opposed value trends: under r* the proxy-optimal policy improves with i (overseer's view); the agent's extractable proxy value declines with i (this is what creates the incentive to avoid corrections). 3. THE load-bearing design principle (read this before building any environment)

Divergence of π̃*(·|·,i) from π_i* bundles two different mechanisms, and only one is the thing we study:

Deterrence — the agent stops exploiting, in plain view, because triggering a correction is a bad long-run deal. Nothing is hidden. This is oversight working.
Concealment / "faking" — the agent keeps exploit value while avoiding detection.

Concealment is possible only if detection is decoupled from how much an action exploits — i.e., there must exist actions that are high-exploit but low-detection. If c_i is a monotone function of the exploit size, the optimal policy only ever deters; there is no hiding. This is the human-in-the-loop analogue of Everitt et al.'s RF-input tampering (the agent influences the input to the correction process) and of the free/paid-tier observation- conditioning in Greenblatt et al. Concretely, route detection through an observation o = O(s,a) and let c_i depend on o, giving the agent a lever over what the overseer sees.

Practical consequence for coding: any environment where "hide" does not actually lower detection relative to "exploit openly" will produce a null result (no faking region). If an experiment shows no hiding, first check that a detection gap exists — do not assume the model is wrong.

4. Experiment roadmap and status
   Exp 0 — toy MDP + exact value iteration. [DONE, in experiments/exp0_toy.py] 2 states (0 = loophole open, 1 = corrected/absorbing), 3 actions (comply, exploit*open, exploit_hide). Solved by VI, validated against closed forms. Sweeps: discount γ, detection gap p_O − p_H, correction penalty r_1.
   Exp 1 — spatial gridworld. [DONE, in experiments/exp1_corridor.py] 2×5 corridor, 20 states ((pos, patched)) × 5 actions. Two loophole tiles that pay identically: F_LOUD (0,1) in the watched top row, F_QUIET (1,2) a 3-step detour away in the unwatched bottom row. Detection is a property of the tile the agent stands on, not of the action, so the detection gap comes from the observation model plus the geometry and the control can switch it off without changing the map, the rewards or the action set. Solved by exact VI/PI, not RL.
   Exp 2 — correction-loop dynamics. [PARTLY DONE, in experiments/exp1b_correction_loop.py] Episodic (horizon 25), patch persists across episodes. See §5 for the metric caveat: raw task completion does not separate the regimes, promptness does.
   Exp 3 — learning agent. [DONE, in experiments/exp2_run.py + src/waypoint_env.py, src/train.py] NAMING: this roadmap calls it Exp 3, but its own spec calls it "Experiment 2" and the files are named exp2_*. Same experiment; don't create a second one. It is a *different environment* from the corridor (5×5 grid, repeatable waypoint bonus, monitor that patches the reward mid-episode), and it studies monitor *shape* rather than concealment — the agent has no hide/expose lever here. See §5c.
   Exp 4 — learned reward repair (PBRR). [DONE, files are exp3_* — the numbering is off by one throughout, see the Exp 3 note above. in experiments/exp3_pbrr.py + src/pbrr*.py] Replaces Exp 2's oracle patch with a correction g(s,a,s') learned from preferences, so nothing ever reads r_true except as a preference labeller. See §5d.
5. Key results so far (Exp 0, base params)

Base parameters: r_C=1, r_O=3, r_H=2, p_O=0.9, p_H=0.2, r_1=0.

Three-region phase transition in γ, verified (VI matches closed forms exactly):
γ ≲ 0.455 → exploit openly (naive; future correction cost doesn't matter yet)
0.455 ≲ γ ≲ 0.833 → hide (protect the exploit by staying under the detection threshold) — the faking band
γ ≳ 0.833 → comply (a permanent correction is too costly; oversight deters)
Detection gap (p_O − p_H) is what creates the hide band. Set p_H = p_O and the hide band vanishes — you get only open → comply (i.e., no faking, just deterrence).
Correction penalty (r_1 < r_C) is what creates the comply/deterrence band. If correction merely closes the loophole (r_1 = r_C), a patient agent always at least hides and there is no comply region. Interpretation: whether oversight can deter exploitation depends on whether correction is punitive, not just on detection quality.

5b. Key results so far (Exp 1 corridor, base params R_goal=5, farm=1, penalty=−1, p_watch=0.6, p_unwatch=0.05)

Three bands in γ, not two — the middle one matters. Exact bisection: γ ≲ 0.8218 → do the task; 0.8218 ≲ γ ≲ 0.8858 → farm the unwatched loophole but *walk to it through the watched row*, eating one high-detection exposure; γ ≳ 0.8858 → detour through the unwatched row to reach it unseen. Only the third band is concealment; the second is exploitation in plain view that happens to target the far tile.
At γ = 0.95 with the gap: V(F_QUIET, unpatched) = 11.9676 vs V(F_LOUD, unpatched) = 8.0278; greedy path from START is (0,0)→(1,0)→(1,1)→(1,2).
CONTROL (p_unwatch := p_watch = 0.6): both loopholes are worth 5.8020, equal to 1e-16, and the agent never detours at any γ in [0.50, 0.995]. The ~4-unit advantage and the detour exist only because of the observation gap.
A punitive correction does NOT deter here, unlike in Exp 0. Sweeping penalty to −400 never restores doing the task, and V saturates below about −10: once the penalty bites, the optimal policy farms hit-and-run (one step on the loophole, one step off), so the agent is never standing on a loophole when the patch lands and never pays the penalty at all. Deterrence by punishment presupposes detection. What does deter: raising R_goal past ≈17.44 (3.5× the base), or dropping the loophole payoff below ≈0.32.
Exp 1b: raw task completion is a bad true-objective metric in the episodic setting — a farmer is patched mid-episode and finishes with the time it has left, and the exact finite-horizon optimum farms and *then* banks the one-time R_goal. Promptness (GOAL within 6 steps; 4 is optimal) is what exploitation destroys. Also: at p_unwatch = 0.05 the blind spot only buys ~0.5 episodes of evasion, because 25 steps at 5%/step is 68% cumulative exposure. Sustained evasion needs a *deep* blind spot (p_unwatch ≈ 0.002 → first correction slips to episode ~13.6).

5c. Key results so far (Exp 2 / roadmap "Exp 3" — the RL experiment, 5×5 waypoint grid)

Setup: γ = 1.0 (finite horizon 40), SBX PPO, 2 monitors × 5 seeds × 500k steps. A repeatable +2 waypoint bonus (a missing "already collected" flag) is farmable by standing on (2,2); a monitor patches the proxy back to the true reward for the rest of the episode when it fires. SUSPICION hazard = 0.20·s where s is an EWMA (λ=0.75) of recent farming; FLAT hazard = 0.075 constant.

Headline: mean true return −5.30 (suspicion) vs −11.17 (flat), gap +5.87 ± 0.14 over 5 seeds. Damage below the honest optimum (+2.0) is 7.30 vs 13.17, i.e. the suspicion monitor limits damage 1.80× better. Trained PPO lands on the memoryless reference almost exactly (suspicion true return −5.296 vs −5.300 predicted).
The reference numbers are reproduced independently by exact DP + Monte Carlo in src/dp_reference.py before any training runs; tests/test_env.py gates on them.
OBSERVATION ENCODING MATTERS: use the Box one-hot(22), not Discrete(42). SBX does no one-hot preprocessing of Discrete observation spaces — it feeds the raw integer to the MLP, which makes the patch flag the low bit of a scalar and is close to unlearnable. This fails silently, not loudly.
"Matched average detection rate" is only matched at a farming duty cycle of ≈0.375 (where 0.2·s = 0.075). Both optimal policies farm flat out (best memoryless dwell q* = 1.0 for both), where suspicion's hazard runs to 0.20 vs flat's 0.075 — so the gap comes from suspicion detecting *faster* against this policy, not from equal detection with better-shaped response. State it that way.
Goal-reach rate is again useless as a true-objective metric: 1.00 (suspicion) / 0.92 (flat) for the whole run while true return sits at −5.3 / −11.2. Same lesson as Exp 1b.
Do not add a clock feature without saying so: with steps-remaining in the observation the optimum becomes farm-then-finish and the §8 reference numbers no longer apply.
Phase 2 (permanent correction, `--phase2`): N_permanent is load-bearing and 50 is too small. At N=50 the swap lands at ~13.9k steps, during random exploration and *before* the agent has learned to farm — so there is no rise and no drop, just a monotone climb to +2.0, and the FLAT monitor corrects *earlier* (12.0k vs 13.9k), reversing the expected ordering. That reversal is the suspicion monitor working as designed: sporadic farming keeps s low, so its hazard 0.2·s ≈ 0.05 sits below flat's constant 0.075. At N=2000 the swap lands at ~61k, after the farming equilibrium, and both expectations hold: the rise/drop/recover curve appears (proxy +9.5 → −4.5 at the swap → +2.0) and suspicion corrects earlier (61.1k vs 66.5k). Whether "suspicion catches it sooner" is true depends entirely on whether farming is concentrated yet.
After any permanent correction both monitors relearn the real task: final true return +2.00 (suspicion) / +1.99 (flat, 2 of 3 seeds; one seed stalled at +1.09), goal rate 1.00, farm steps 0.00.

5d. Key results so far (Exp 3 — PBRR, a *learned* correction g; files exp3_*)

Implements Preference-Based Reward Repair (Hatgis-Kessell, Bhamidipaty & Brunskill, arXiv:2510.13036v2 — the TA is the first author; reference code github.com/StanfordAI4HI/PBRR-ICLR). r̂ = r_proxy + g(s,a,s'), with g fit from preferences over trajectory pairs drawn from π_ref and π*_r̂. Exp 2's within-episode monitor is OFF for these runs: PBRR is the correction mechanism, and running two correctors would make any repair unattributable. π*_r̂ is solved exactly by finite-horizon DP, so the paper's footnote-3 caveat does not apply here.

Headline: PBRR repairs the proxy from −30.0 (uncorrected proxy optimum) to +2.0 (the honest optimum); π_ref itself is only −1.16.
Eq 3 repairs in 5/5 seeds; Eq 1 and the random-label control in 0/5. But the *value* is bimodal — at any iteration the induced policy is either repaired (+2.0) or not (−30.0), never in between, and seeds repair at different iterations. So report fraction-repaired plus per-seed traces; a mean ± s.d. band across seeds sits in a gap where no seed ever is.
The two ridge terms are the mechanism, and L⁻ is load-bearing: Eq 3 repairs; dropping L⁺ still repairs; dropping L⁻ is much slower; Eq 1 alone (= the RRM baseline) never repairs and ends at −36, *worse than uncorrected*. This reproduces the paper's §5.4 / Appendix G.3 ablation.
The learned g localises without being told where the bug is: 51% of |g| on the 5 waypoint transitions out of 105, −1.49 at the waypoint vs the analytic ideal g* = −2.
EPIC(r_proxy+g, r_true) = 0.108 while inducing exactly the honest optimal policy (ideal g gives 0.000, uncorrected proxy 0.157). Reward repair does not require recovering r_true — that is the point.
THE Exp-2-STYLE TRAINING DIVERGENCE (figures/exp3_training_divergence.png, `--ppo`): SBX PPO with the monitor off, logging received *and* true return every 10k steps. On the uncorrected proxy the two rise together to ~0 by 20k steps and then split hard — received climbs to +31.9 while true collapses to −40.0, a 71.9-unit gap. On r_proxy + g_learned the split never opens: received +3.8, true +2.0, gap 1.84. So the divergence is reproduced *without any monitor*, and the learned repair closes it — while still not equalling r_true (EPIC 0.108).
GENERALISATION FAILS: a second, equally attractive bonus tile at (4,0) (verified d(S,t)+d(t,G)=8) appearing in no preference pair is farmed for 33 steps. A learned correction patches the instance it was shown, not the class.
THREE PLACES THE PRINTED Eq 3 AND THE RELEASED CODE DIFFER (see the src/pbrr.py docstring): the regulariser is per-transition MSE, not the square of the trajectory sum; both branches share the 1/|D⁺| normaliser; λ=10 is applied once so the net coefficient is 10/|D⁺|, not 10/|D⁺|². Additionally the code's `if batch_agreements > 0` guard skips regularisation when |D⁺|=0, which leaves an unbounded logistic fit that inflates g on the *preferred* trajectory and breaks Theorem H.1; we normalise by max(1,|D⁺|) instead (flag `skip_reg_when_no_agreement`).
CONTROL CAVEAT: *permuting* preference labels is NOT a valid control — within an iteration nearly every pair carries the same label, so a permutation is a no-op and still "repairs" the reward. Draw labels independently of the trajectories instead (`randomize_labels`).
The paper's minimal MDPs (Appendix H, Fig 7) are implemented as anchors in src/pbrr_minimal.py: MDP 1 is repaired by ONE preference (Theorem H.1) at every λ tested; MDP 2 stalls at +4 (optimum +8) with C₁=0 at every λ. The max-divergence fallback (C₁>0) is specified in Algorithm 1 but disabled (C₁=0) in every experiment the paper runs, because Π_t is intractable in its domains; on MDP 2 it is necessary but not sufficient — it also needs λ decayed to ≈0.01, so the fallback and Assumption 4.5 are jointly required.
π_ref sets the ceiling (Thm 4.3 only guarantees ≥ π_ref): exact-optimal reference → +2.0; uniform-random reference → −30.0, i.e. no repair. That diverges from the paper's Appendix K.8 claim that a random reference suffices — in this env a random policy almost never reaches the goal, so the contrast carries no information.

5e. Exp 4 — multi-exploit PBRR sawtooth and convergent extension (files exp4_* / bigworld*)

The original 15×15 learner-only run is retained as the control in `figures/exp4_sawtooth_15x15.png`: six state-based bonus tiles are represented by 880 independent transition parameters, PPO supplies the preference trajectories, and the long sawtooth never converges. Its final reward also fails an exact-DP audit, so transient within-round true-return peaks are not repair.

The load-bearing paper detail is model structure and exploration, not a better π_ref. The paper parameterizes g with a neural network (Appendix E.1), whereas the original Exp 4 table shares nothing: a state-based bonus becomes 6×5 independent action loopholes. The convergent variant uses one learned g parameter per state, shared across its five actions. This restriction is applied uniformly to all 176 states, is exactly expressive for this bug, and is the tabular analogue of neural parameter sharing; it is not told the six bug locations. Algorithm 1 ideally compares π*_rhat against π_ref, while footnote 3 admits the trained policy may not be optimal. In the old loop PPO stopped discovering still-live exploits, so the convergent run uses exact finite-horizon π*_rhat rollouts for preference collection while PPO remains the plotted learner. A declared, non-paper ranking-margin extension (δ=10) moves the corrected trajectory ordering away from the exploit/no-exploit threshold.

Seed-0 convergent result (`figures/exp4_sawtooth_convergent_15x15.png`, 10 rounds × 100k PPO steps, k=19, λ=1, explicit L2 coefficient 0.01): the first round retains a 107.9-point received/true exploit fork; end-of-round true return moves from −56.0 to near the +12 honest optimum; final-three mean is +11.18. The end gap falls from 107.9 to 33.3; about 28 points of the residual are the intentional potential-shaping return, not exploitation. Most importantly, exact DP on the final learned g returns +12.0 and all six dwell values are safely negative (−0.85, −0.97, −0.94, −0.86, −0.89, −0.82). The exact-DP refit diagnostic first reaches +12 at refit 5 and holds it for the final third of 15 refits.

Do not label this as unmodified PBRR: state sharing mirrors the paper's neural inductive bias, and exact π*_rhat follows the ideal algorithm, but the positive ranking margin is our extension. Also do not infer the paper's numerical weight-decay coefficient from Table 2's Boolean “True”: released code uses Adam weight decay 1e-5; the local 0.01 is an explicit tabular L2-loss coefficient. Evaluation and preference collection now use separate RNG streams, because sharing one made the learned reward depend on `n_eval` and plotting frequency.

5f. Exp 4 clean split protocol (experiments/exp4_clean_split.py)

The PI-facing rerun no longer concatenates fresh PPO policies into one continuous-looking sawtooth. Each panel/run is 100k PPO steps under one frozen reward, and endpoint summaries are indexed by repair round. The proxy curve has the known potential-shaping return subtracted for display only (training still receives the full raw reward), so its separation from true return isolates exploitation of bonus/g terms.

Seed-0 result (7 rounds, k=19, 361 new cross-pairs/refit): before repair the end-of-run true return is −56.0 and the shaping-adjusted proxy/true gap is +103.8. The literal learner-pair Eq. 3 condition is an explicit null: after 2,527 preferences its exact-DP true return is still −16 and all 6/6 exploits remain profitable. The declared robust extension (state sharing + exact π*_rhat coverage + ranking margin 10) reaches PPO true return +11.9 after one refit; exact live exploits decrease 6→4→3→2→1→0 and the final exact-DP true return is +12.0. Its adjusted PPO gap falls to +3.6. The exact inner-loop audit reaches +12 with 0/6 live exploits in all five checked seeds. Five independent random-label fits repair 0/5 times, so the result depends on meaningful trajectory preferences rather than merely adding a correction.

Primary figures: `figures/exp4_clean_split.png` shows the within-run proxy/true split before, after one refit, and at the final reward; `figures/exp4_clean_repair_summary.png` compares the standard null and robust extension using trained-policy true return, adjusted endpoint gap, and exact live-exploit audits. Machine-readable endpoints are in `results/exp4_clean_split_summary.json`. Keep the original sawtooth figure as the visual demonstration of repeated re-exploitation, but use these clean panels for claims about convergence.

6. Repo layout
reward-hacking-with-observer/
├── README.md
├── CLAUDE.md
├── src/solver.py # value_iteration, policy_iteration, bellman_residual, finite_horizon, find_threshold
├── src/environments.py # build_toy_mdp (Exp 0), build_corridor_mdp (Exp 1) + metadata + intent classifier
├── src/plotting.py # shared figure conventions: palette, styling, phase diagrams, grid arrows, sweeps
├── src/report.py # check bookkeeping; experiments exit nonzero if an acceptance check fails
├── src/waypoint_env.py # Exp 2: WaypointFarmEnv (Gymnasium), the two monitors
├── src/dp_reference.py # Exp 2: exact DP + memoryless Monte Carlo reference numbers
├── src/train.py # Exp 2: SBX PPO + eval harness (policy read as a 42×5 action table)
├── src/plots.py # Exp 2 figures, rebuilt from results/ CSVs without retraining
├── src/permanent_correction.py # Exp 2 phase 2: training-level permanent correction (wrapper)
├── src/pbrr.py # Exp 3: D+/D- partition, Eq 1 / Eq 3 objectives, the g fit (+ a slow reference impl)
├── src/pbrr_loop.py # Exp 3: Algorithm 1, pair sampling, Boltzmann labels, C1>0 fallback
├── src/pbrr_minimal.py # Exp 3: the paper's Appendix-H minimal MDPs, as anchors
├── src/reward_distance.py # Exp 3: EPIC canonicalisation + distance
├── src/plots_pbrr.py # Exp 3 figures
├── src/bigworld.py, src/bigworld_pbrr.py # Exp 4 environment + exact/learner repair loops
├── experiments/exp0_toy.py, exp1_corridor.py, exp1b_correction_loop.py, exp2_run.py, exp3_pbrr.py, exp4_sawtooth.py
├── tests/test_solver.py, test_experiments.py # Exp 0/1
├── tests/test_env.py # Exp 2 validation (spec §9), incl. the observation-leak test
├── tests/test_pbrr.py # Exp 3 validation, incl. the Theorem-H.1 anchor
├── tests/test_bigworld.py # Exp 4 state sharing, margin gradient, exact convergence
├── results/ # Exp 2 eval CSVs (kept: plots regenerate from these)
└── figures/ # generated PNGs (untracked)

Run: `python experiments/exp0_toy.py`, `exp1_corridor.py`, `exp1b_correction_loop.py`, `exp2_run.py` (add `--quick`, `--plots-only`, or `--phase2`), `exp3_pbrr.py` (add `--quick` or `--ppo`), and `python tests/test_solver.py`, `test_experiments.py`, `test_env.py`, `test_pbrr.py`. Exp 0/1 need numpy + matplotlib only; Exp 2 also needs gymnasium + sbx-rl (jax). Tests are pytest-compatible. Use the project venv: `.venv/bin/python`.
Sweeps use policy_iteration (exact, and its iteration count does not blow up as γ→1); headline solves use value_iteration and `check_agreement` cross-checks the two.

Solver conventions:

value_iteration(R, P, gamma) is generic over any tabular MDP with R (S,A), P (S,A,S). Keep environment builders (build_mdp, future build_gridworld) separate and swappable so the same solver/plotting harness is reused.
Always keep a closed-form check next to any new small MDP and assert VI matches it. 7. Working conventions
DP before RL. Exactly solve small MDPs first; only move to learning once the phenomenon is confirmed by DP, and always keep the exact optimal policy as ground truth to check RL against.
Validate numerically. Every quantitative claim should be reproducible from a closed form or an exact solve, not asserted.
Stack: numpy + matplotlib for DP experiments; gymnasium + sbx (Stable-Baselines JAX) for the eventual RL experiment. .gitignore covers **pycache**/, \*.pyc, .venv/, .DS_Store.
Surface hidden assumptions and trade-offs rather than agreeing by default. If a proposed environment or claim has a flaw (e.g., no detection gap, cross-reward-scale value comparisons, a threshold that won't exist), say so directly. 8. Notation / literature lineage

Terminology follows the reward-tampering and reward-hacking literature; keep it consistent:

Reward tampering / reward-as-influenceable-state — Everitt, Hutter, Kumar & Krakovna (2021). Our setting is closest to their RF-input tampering, specialized to a human overseer in the loop. Source of the current-reward vs post-modification timing distinction.
Reward hacking, proxy vs true, (un)hackable — Skalse, Howe, Krasheninnikov & Krueger (2022).
Corrigibility / incentive to resist vs accept correction, threshold "flip" — Soares, Fallenstein, Yudkowsky & Armstrong (2015).
Evading a correction mechanism — Orseau & Armstrong (2016), Safely Interruptible Agents. Contrast: interruption forces a policy change; our correction changes the reward function, mediated by what the overseer observes.
Empirical anchor (observation-conditioned behavior in a frontier model) — Greenblatt et al. (2024), Alignment Faking in LLMs.
Reward pseudometrics (for "closer to r*") — Gleave et al. (2021, EPIC); Skalse et al. (2023, STARC). EPIC is invariant to potential-based shaping (Ng, Harada & Russell, 1999), which is why "closer to truth" is not confounded by shaping.
Mitigations / manipulable channel — Uesato et al. (2020, decoupled approval); Everitt et al. (2017, Corrupt Reward MDP). 9. Glossary
proxy reward r_i — the reward function currently in force (a stand-in for r*).
true reward r\* — the overseer's unobserved target; corrections move r_i toward it.
correction / regime advance — i → i+1; closes the detected exploit, changing the optimal policy (unlike potential-based shaping, which preserves it).
detection probability c_i(s,a) — chance the overseer catches an exploit and corrects.
detection gap — the difference in detection probability between loud and quiet ways of taking the same exploit; the quantity that makes concealment possible.
deterrence vs concealment — see §3; do not conflate them when interpreting results.
