AGENTS.md — reward-hacking-with-observer

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
   Exp 3 — learning agent (only after DP confirms the phenomenon). Wrap the gridworld as a Gymnasium env, train PPO with SBX (Stable-Baselines JAX), and check whether a learned agent discovers hiding. Two-curve training plot: proxy return vs. ground-truth success (divergence = learned hiding).
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

6. Repo layout
reward-hacking-with-observer/
├── README.md
├── AGENTS.md
├── src/solver.py # value_iteration, policy_iteration, bellman_residual, finite_horizon, find_threshold
├── src/environments.py # build_toy_mdp (Exp 0), build_corridor_mdp (Exp 1) + metadata + intent classifier
├── src/plotting.py # value-vs-γ envelope, phase diagrams, grid-policy arrows, sweeps
├── src/report.py # check bookkeeping; experiments exit nonzero if an acceptance check fails
├── experiments/exp0_toy.py, exp1_corridor.py, exp1b_correction_loop.py
├── tests/test_solver.py # VI vs closed form, VI vs policy iteration, environment structure guards
├── tests/test_experiments.py # the published acceptance numbers and controls
├── figures/ # generated PNGs (untracked)
└── (later) rl_sbx/ # Exp 3 only

Run: `python experiments/exp0_toy.py`, `python experiments/exp1_corridor.py`, `python experiments/exp1b_correction_loop.py`, `python tests/test_solver.py`, `python tests/test_experiments.py`. Needs numpy + matplotlib only; the tests are also pytest-compatible.
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
