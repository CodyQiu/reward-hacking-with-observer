# Experiment 4 — Learned Reward Repair with Multiple Exploits

## Question

Experiment 3 showed that PBRR (Preference-Based Reward Repair) can repair a proxy reward
containing **one** bug, using a correction `g(s,a,s')` learned from trajectory
preferences. But with one bug there is nothing left to find once it is closed, so the
proxy/true training curves fork exactly once.

This experiment asks the scaled-up version: **when several exploits are live at once, does
each newly discovered one produce its own fork — a sawtooth — and does the correction
eventually close them all?**

## Setup

**Environment** (`src/bigworld.py`). 15×15 grid, walls at every (odd, odd) cell → 49
walls, 176 free cells, fully connected. START (0,0), GOAL (14,14), shortest path 28 steps,
horizon 56, γ = 1.

- **True reward:** −1 per step, +40 for entering GOAL. Honest optimum = **+12** in 28 steps.
- **The bug:** a *repeatable* +2 bonus paid every step the agent stands on a bonus tile
  (a missing "already collected" flag), so dwelling nets +1/step.
- **Six exploits**, identical bonuses, at increasing distance from START (4, 8, 12, 16,
  20, 24), minimum pairwise distance 8. Because every free cell satisfies
  `d_start + d_goal = 28`, all six lie on a shortest path and offer 28 dwell steps each —
  they are equally valuable to an optimal planner by construction, so the only thing
  distinguishing them is whether `g` has covered them.
- **Potential-based shaping** in the proxy (`F = d_goal(s) − d_goal(s')`). Policy-invariant
  (Ng/Harada/Russell 1999), so the honest optimum is unchanged. Required: without it PPO
  never finds a goal 28 steps away (oracle goal rate 0.00 at 13×13 and 15×15, versus 1.00
  with shaping), and a repaired exploit would leave the agent with no alternative behaviour.
- Observation is a one-hot over the 176 cells; no clock, no patch flag. `g` is tabular over
  transitions: 880 parameters.

Because γ = 1 and the goal stays reachable, dwelling one extra step is purely **additive**.
So a tile is a live exploit iff `−1 + bonus + g(tile, stay) > 0`, i.e. it dies only once
`g < −1.0`. This also means the optimal policy is a **step function** of `g`.

**Method.** PBRR as specified (Hatgis-Kessell, Bhamidipaty & Brunskill, arXiv:2510.13036v2):
`r̂ = r_proxy + g`, with `g` fit from preferences over trajectory pairs drawn from a
reference policy and from the policy optimal under the current `r̂`. Preferences are labelled
by a Boltzmann model on the true return — the only place the true reward is used. `g` is
re-initialised and refit from scratch on all accumulated preferences each round.

Two loops are run:

- **DP loop** — the inner policy is the *exact* optimum, solved by dynamic programming. A
  diagnostic: can PBRR repair this reward at all, absent any learning failure?
- **PPO loop** — a **fresh** PPO is trained for 100k steps each round, per Algorithm 1
  line 4. This is the real experiment and the only one that can show a sawtooth, since
  teeth require a learner that takes time to find each exploit.

## What we find

**1. The sawtooth is real.** With a fresh policy per round, the received return forks away
from the true return in every one of 30 rounds (per-round peak gap 74–108), and the learner
visits all six exploits across the run. (`figures/exp4_sawtooth_15x15.png`)

**2. The paper's weight decay is essential.** Appendix E.1 Table 2 sets
`Weight Decay = True` for the correction term — a plain L2 on `g`, separate from the two
ridge terms of Eq 3. Omitting it caused two artefacts I initially mistook for findings:

| | without weight decay | with (0.01) |
|---|---|---|
| round-to-round change in `g` | 23.86 | **0.16** |
| ‖g‖₂ | 92.9 | **5.4** |
| max positive `g` | +0.49 | **+0.26** |
| peak received return (PPO loop) | **+823** | +51.9 |

The +823 was the agent abandoning the bonus tiles entirely to exploit the *learned
correction itself* — reward-model Goodharting. Weight decay bounds `g` and removes it.

**3. Repair does not complete.** A repairing `g` provably exists (the analytic ideal gives
exactly +12), and the DP loop reaches the honest optimum. But through the learning loop,
after 30 rounds and 4,320 preferences, the end-of-round true return is **−56 in every
round** (honest optimum +12). Solving the PPO loop's own learned `g` exactly still gives
−16 with all six exploits live, so the reward function itself was never repaired — this is
not a weak learner failing to exploit a good reward. Every exploit is corrected in the
right direction but 1.6×–70× too weakly:

    (2,2) −0.62   (0,8) −0.56   (10,2) −0.45
    (2,14) −0.27  (14,6) −0.31  (10,14) −0.01        (each needs < −1.0)

**4. The equilibrium is marginal, which is why it oscillates.** In the DP loop a dwell
value ends up parked **0.02** from the threshold while `g` jitters by **0.16** per refit, so
the induced policy flips between farming and honest (3 flips over 30 refits, with or
without weight decay). The likely cause is structural: `L⁺` and weight decay both pull `g`
toward zero, and the preference loss is satisfied as soon as the trajectory *ranking* is
correct, so nothing pushes a dwell value past the threshold once it is marginally negative.
The fit converges to the **minimal correction that satisfies the preferences**, which lands
the policy exactly on the decision boundary.

## Main takeaways

- Multiple simultaneous exploits do produce a sawtooth, but only if the learner
  **re-explores after each repair**. Retraining per round gives one tooth per round;
  continuing a single policy across refits instead produces total lock-in (the converged
  agent farms its weakened exploit *less* rather than finding another). That is a property
  of the optimiser, not of PBRR.
- **A learned correction can itself become a reward-hacking target.** Nothing in Eq 3
  bounds `g` from above on transitions the preferences do not pin down; the paper's weight
  decay is what prevents this, and it is easy to omit.
- Scaling from one exploit to six broke convergence at this preference budget, and the
  most likely reason is that PBRR's regularisation targets the *minimum* correction, which
  leaves the repaired policy on a knife edge. A margin term ("make the bad trajectory worse
  by at least δ, not merely worse") is the natural fix, but it is a deviation from Eq 3
  rather than part of the published method.

## Caveats

Single seed throughout. `d_goal`, not `d_start`, appears to govern which exploit the
learner finds once shaping is present — 23 of 30 rounds attacked the two tiles nearest the
goal, so four tiles are starved of preference data; the exploit ladder is ordered on the
wrong axis. Preference budget is ~720 per exploit versus 2,888 for the single exploit in
Exp 3, and the paper uses 361 preferences/iteration where these runs use 144. None of
these has been tested, so the non-convergence should not yet be read as a limitation of
PBRR itself.
