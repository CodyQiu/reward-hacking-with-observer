# Handoff prompt: Exp 4 (PBRR with multiple exploits) — why won't it converge?

Paste everything below to another agent. It is self-contained.

---

## What I want from you

Read the situation below and tell me what you think is actually going on, and what you
would test next. I am specifically **not** looking for another hyperparameter sweep
unless you can say why it should work. I have four untested structural hypotheses at the
bottom; tell me which you think is right, whether I have missed one, and whether any of
my reasoning is wrong.

## Project context

A study of reward hacking under a correcting overseer. Prior experiments (all working,
all validated against closed forms or exact DP) established: an agent will conceal an
exploit when detection is decoupled from exploit size; and a monitor that patches the
reward mid-episode limits damage.

Experiment 4 implements **PBRR (Preference-Based Reward Repair)** from
*"Repairing Reward Functions with Feedback to Mitigate Reward Hacking"*,
Hatgis-Kessell, Bhamidipaty & Brunskill, arXiv:2510.13036v2
(code: github.com/StanfordAI4HI/PBRR-ICLR).

PBRR repairs a misspecified proxy reward with an additive, transition-dependent
correction learned from trajectory preferences:

    r_hat_{t+1}(s,a,s') = r_proxy(s,a,s') + g_t(s,a,s')        (their Eq 2)

Loss (their Eq 3), with D+ = pairs where the proxy's ranking already matches the human
preference, D- = the rest:

    L(g) = L_pref(r_proxy + g; D)
         + lambda * ( L+  : push g -> 0 on BOTH trajectories of an agreeing pair
                    + L-  : push g -> 0 on the PREFERRED trajectory ONLY of a
                            disagreeing pair, which forces "lower the bad" rather
                            than "raise the good" )

Implementation notes (I followed the released code, which differs from the printed Eq 3
in three places): the regulariser is a per-transition MSE, not the square of the summed
correction; both branches share the 1/|D+| normaliser; lambda = 10 is applied once, so
the net coefficient is 10/|D+|, which is the decay Appendix E.6 describes. Also
Appendix E.1 Table 2 sets `Weight Decay = True` for the correction term — a plain L2 on
g, separate from L+/L-. g is re-initialised and refit from scratch on ALL accumulated
preferences every round (Appendix E.2).

Exp 3 ran PBRR successfully on a 5x5 grid with ONE exploit: repaired in 5/5 seeds,
reaching the honest optimum. Exp 4 scales to many exploits, and does not converge.

## The Exp 4 environment (`src/bigworld.py`)

- 15x15 grid, walls at every (odd,odd) cell => 49 walls, 176 free cells, fully connected
  (even rows/cols are open corridors).
- START (0,0), GOAL (14,14), d(START,GOAL) = 28. Horizon H = 56. gamma = 1 (finite
  horizon, undiscounted).
- True reward: -1 per step, +40 for entering GOAL. Honest optimum = -28 + 40 = **+12** in
  28 steps.
- The bug: a **repeatable** +2 bonus paid for every step the agent *stands on* a bonus
  tile (a missing "already collected" flag). Net dwell value +1/step uncorrected.
- **Six bonus tiles**, identical bonuses, at (2,2), (0,8), (10,2), (2,14), (14,6),
  (10,14). Distances from START: 4, 8, 12, 16, 20, 24 (a deliberate "staircase").
  Minimum pairwise distance 8.
- Every free cell has d_start + d_goal = 28 = d(START,GOAL), so all six tiles lie on a
  shortest path, cost nothing to detour to, and offer 28 dwell steps each — i.e. they
  are equally valuable to an optimal planner by construction.
- **Potential-based shaping in the proxy**: F = d_goal(s) - d_goal(s'). Policy-invariant
  (Ng/Harada/Russell 1999, Phi(GOAL)=0), added because without it PPO never reaches the
  goal at this size (see measurements). It does NOT change the honest optimum.
- Observation: one-hot over the 176 free cells. No clock feature, no patch flag.
- g is tabular over (s,a,s'): dynamics are deterministic so s' = move(s,a), giving
  176 x 5 = **880 parameters**.
- Proxy DP optimum: received +74, unshaped true return -16.
- Preference labels: Boltzmann on the **unshaped true** return; exact ties -> mu = 0.5.
  This is the only place the true reward is used.
- pi_ref = eps-greedy shortest path to GOAL, eps = 0.3.

**Key analytic fact.** With gamma = 1 and the goal always reachable, dwelling one extra
step is purely *additive* — you still collect the +40, just later. So a tile is a live
exploit iff

    dwell value = -1 + bonus + g(tile, stay) > 0,   i.e. it dies only when g < -1.0

This makes "is this exploit still open?" a one-line check, and makes the optimal policy a
**step function** of g.

## Two loops (this distinction matters)

- **DP loop** (`bigworld_pbrr_dp`): at each refit, pi*_{r_hat} is the *exact* finite-horizon
  optimal policy, solved by dynamic programming. No learning. A diagnostic: it answers
  "can PBRR repair this reward at all?" Runs in seconds.
- **PPO loop** (`sawtooth_run`): at each round, train a **fresh** SBX PPO for 100k steps on
  the current r_proxy + g, then refit g from its rollouts vs pi_ref's. This follows
  Algorithm 1 line 4 ("Compute pi*_{r_hat_t}") and footnote 3 ("we train a policy using
  r_hat_t") — a new policy per iteration, not a continuation. ~10 min for 30 rounds.

## Everything measured so far

**1. Solvability / oracle (r-PPO = PPO trained directly on the true reward).**
Goal rate and true return: 9x9 -> +12.0, 1.00. 11x11 -> +12.0, 1.00. 13x13 -> -48, 0.00.
15x15 (no shaping) -> -80, 0.00. **15x15 with shaping -> +11.97, 1.00.** So shaping is
what makes 15x15 a valid benchmark at all.

**2. A repairing g provably exists.** The analytic ideal g* = -bonus on every transition
out of every tile gives exactly +12 under DP. So non-convergence is a search/stability
question, not an impossibility.

**3. DP loop, lambda sweep** (30 refits, k=12, no weight decay) — refit at which the
honest optimum is first reached: lambda=10 -> 23/24; lambda=3 -> 15; lambda=1 -> 16-20;
lambda=0.3 -> 12.

**4. DP loop, weight decay x lambda** (30 refits, k=12). "#opt" = refits at the honest
optimum; "last10" = how many of the final 10 refits held it:

| lambda | wd | first@ | #opt | last10 | max +g |
|---|---|---|---|---|---|
| 10 | 0 | 24 | 6/30 | 6/10 | +0.49 |
| 10 | 0.001 | 14 | 16/30 | 10/10 | +0.54 |
| 10 | 0.01 | 12 | 18/30 | 10/10 | +0.26 |
| 10 | 0.05 | 15 | 16/30 | 10/10 | +0.20 |
| 10 | 0.1 | 26 | 5/30 | 5/10 | +0.20 |
| 1 | 0 | 16 | 13/30 | 10/10 | +0.96 |
| 1 | 0.001 | 9 | 21/30 | 10/10 | +0.54 |
| 1 | 0.01 | 8 | 21/30 | 10/10 | +0.26 |
| 1 | 0.05 | 10 | 20/30 | 9/10 | +0.31 |
| 1 | 0.1 | 10 | 19/30 | 8/10 | +0.32 |

**5. The oscillation mechanism** (DP loop, 30 refits, lambda=10):

| | wd = 0 | wd = 0.01 |
|---|---|---|
| policy flips (farm <-> honest) over 30 refits | **3** | **3** |
| round-to-round change in g, median max abs | **23.86** | **0.16** |
| ‖g‖_2 final | 92.90 | 5.37 |
| final dwell values (need < 0) | -0.52 -0.28 -0.22 +0.33 +0.39 +0.49 | -0.57 -0.40 -0.36 -0.35 **+0.02** +0.06 |
| closest dwell value to the 0 threshold | 0.223 | **0.020** |

Weight decay shrinks round-to-round jitter 150x and ‖g‖ 17x, and removes large positive
g — but does **not** reduce the flip count. The flips are threshold-hovering: a dwell
value parked 0.02 from the cliff while g jitters by 0.16 per refit.

My reading, which I would like you to check: L+ and weight decay both pull g toward zero,
and L_pref is satisfied as soon as the trajectory *ranking* is right, so nothing pushes a
dwell value past the threshold once it is marginally negative. The fit therefore converges
to the **minimal correction that satisfies the preferences**, which lands the induced
policy exactly on the decision boundary. That is L+ behaving as designed (the paper says
it "prevents unnecessary adjustments"), but it makes the equilibrium marginal, and a
marginal equilibrium plus a refit-from-scratch estimator oscillates.

**6. PPO loop results** (30 rounds x 100k steps, k=12 => 4,320 preferences total). End-of-
round true return, which is the correct metric:

| config | end-of-round true | live exploits | notes |
|---|---|---|---|
| lambda=10, wd=0 | **-56 in all 30 rounds** | 6/6 | peak received **+823** with ~1 farm step |
| lambda=10, wd=0.01 | **-56** | 6/6 | peak received 51.9, max +g +0.20 (Goodharting gone) |
| lambda=1, wd=0.01 | **-56** | 5/6 | received ~19-22 |

Honest optimum is +12. Solving the PPO loop's own learned g **exactly** by DP gives
**-16** with 6/6 exploits live — so the reward function itself was never repaired; this is
not merely a weak learner failing to exploit a good reward.

Final g on each exploit (lambda=10, wd=0.01), against the -1.0 needed to kill it:

    (2,2) -0.621   (0,8) -0.556   (10,2) -0.451
    (2,14) -0.268  (14,6) -0.307  (10,14) -0.014

All six corrected in the right direction, all **1.6x to 70x too weak**.

**7. Which tiles the learner actually attacks** (30 rounds, wd=0.01), with d_goal:

    (14,6) d_goal=8  : 18 rounds     (2,14) d_goal=12 : 2
    (10,14) d_goal=4 :  5            (0,8)  d_goal=20 : 1
    (2,2)  d_goal=24 :  3            (10,2) d_goal=16 : 1

23 of 30 rounds went to the two tiles nearest the GOAL. My staircase was ordered by
distance from START, but with shaping present the agent follows the shaping gradient
toward the goal, so **d_goal** appears to govern discoverability, not d_start. Four tiles
are therefore starved of preference data.

**8. pi_ref is not the problem.** At eps=0.3 it reaches the goal 100% of the time with
true return +0.28, versus the farming policy's -26.49, and the Boltzmann labeller prefers
the farmer in only 0.5% of pairs. Clean signal.

**9. A deleted variant.** An earlier version kept training ONE PPO policy across refits
instead of retraining. That produced total lock-in: the agent farmed (2,2) for 600k steps
through nine refits and never migrated, even at ent_coef=0.05 and lambda=1. A converged
policy-gradient learner responds to its exploit being weakened by farming it *less*, not
by finding another. Deleted because it deviates from Algorithm 1 line 4.

**10. The sawtooth itself works.** With a fresh policy per round the received return forks
away from the true return in every one of the 30 rounds (per-round peak gap 74-108), and
the learner visits all six tiles across the run. That part reproduces fine.

## Mistakes I made (please do not repeat, and check I have not made more)

1. Ran a single continuous PPO across refits instead of retraining per round -> lock-in,
   which I nearly reported as a finding.
2. Concluded "PBRR cannot repair this" from a 20-refit budget when 23 were needed. Did
   the same earlier at 11x11 (ran 8, needed 11). **Check trends before declaring failure.**
3. Claimed the true return "recovers" using max-within-round; that was a transient (a
   fresh agent passing through good behaviour before finding a tile). End-of-round is the
   correct metric and shows no recovery.
4. Ran the PPO loop at lambda=10 after my own sweep had shown lambda=1 was better.
5. Omitted the paper's `Weight Decay = True` entirely. That single omission caused both
   the g-exploitation (+823) and much of the apparent instability.
6. Ordered the exploit staircase by d_start when shaping makes d_goal the operative
   quantity.
7. Called "last-10-refits-at-optimum" *stability*; it actually measures convergence
   speed. Flip count is the same (3) with and without weight decay.

The pattern in my errors is reading extrema or single favourable points as convergence.

## Untested hypotheses for the remaining failure

**A. Marginal equilibrium (my favourite).** L+ plus weight decay drive g to the minimal
correction satisfying the preference ranking, so the induced policy sits on the decision
boundary and fit noise flips it. Fix: add a **margin/hinge** term — require the corrected
return of the dispreferred trajectory to be worse by at least delta, not merely worse — so
dwell values land near -0.5 instead of -0.02. This is a deviation from Eq 3, so it would
be our modification, not the paper's.

**B. Diffuse credit assignment.** PPO's trajectories are noisy and cover many transitions,
so L-'s negative correction smears across all of them instead of concentrating on the
dwell transition; the DP loop's clean 28-step-plus-dwell path does not have this problem.
This would explain why DP repairs with the same preference count and PPO does not.
Testable by comparing how concentrated g is between the two loops.

**C. Shaping steers discovery.** See measurement 7 — 23/30 rounds on the two goal-adjacent
tiles starves the other four. Fix: order the staircase by d_goal, or weaken the shaping so
it guides without dominating.

**D. Preference budget.** 4,320 preferences spread over six exploits is ~720 each, versus
Exp 3's 2,888 for a single exploit. The paper uses k=19 (361 preferences/iteration); I
used k=12 (144). So I may simply be running at ~2.5x too few per round.

## Caveats on everything above

Single seed throughout. The `live_exploits` check only inspects g(tile, stay) and ignores
penalties on the transitions *entering* a tile, so a tile can show a positive dwell value
while the exact optimum still avoids it — the behavioural DP result is the trustworthy
one. No tests exist for `bigworld`. Nothing about Exp 4 is in the project's CLAUDE.md, and
none of these files are committed to git.

## Files

    src/bigworld.py            env, geometry, shaping, exact finite-horizon DP
    src/bigworld_pbrr.py       both loops: bigworld_pbrr_dp and sawtooth_run
    src/pbrr.py                the PBRR objective, shared with Exp 3 (env-agnostic)
    experiments/exp4_sawtooth.py   end-to-end, CheckLog-gated
    src/plots_pbrr.py          fig_sawtooth
