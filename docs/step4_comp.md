# Step 4: the compensated correction (FarmShare, from 2026-11-16)

## Where it comes from (as stated)

**The user, 2026-11-15:**
> "the old PBRR gives agents an incentive to avoid correction and continue exploiting (but it does not introduce new exploits) but the new swap allows the agent to be corrected quickly but has potential to introduce new exploits ... and i guess no-regularizer is somewhere in the middle. a method either along those lines or whatnot would do, it should generalize to mostly all environments, and it should be useful in our setup, where there's some sort of monitor that goes on (that is, do not change our setup)."

Then, about this recommendation: "yes, implement 1 ... remember, the behavior we're looking for is it gets corrected quickly and then behaves".

## The mechanism

The fit is standard PBRR, unchanged: max1, L⁻ on the preferred trajectory, as in Steps 2–3. What changes is how the overseer applies it. There are two changes:

1. **Fines only, never relaxed** (`g.fine_only=True`). Each g_i is still fitted from scratch on all of D. But after k corrections in an episode, the correction in force is min(0, g_1, …, g_k):
   - no transition ever pays more than the proxy;
   - a later correction never relaxes an earlier fine.
2. **A level** (`g.offset=True g.offset_margin=0.0`). With correction k, the overseer also installs a constant c_k. It is received on every step until the episode ends:

   c_k = [V_before − V_ref,after]⁺ / T_sub

   - V_before is the mean return of the round's caught rollouts. These are the agent's own policy in the round where it was caught, measured under the reward in force at the time, c_{k−1} included.
   - V_ref,after is the mean return of the reference rollouts under proxy + the new correction, with no level.

   So after the correction, honest reference play earns exactly what the caught play earned before it.

**What is unchanged:**
- the monitor and detection (proxy ≠ true in the last W steps);
- the pairs, labels and the D⁺/D⁻ split;
- the reset every episode;
- γ = 1.

The correction and the level are in the received reward only, not in the proxy or the true reward.

## Why it should work

- **The level cannot create an exploit.** Every round is exactly T_sub steps, with no early termination, and γ = 1. So a constant per step adds the same amount to every behaviour in that round. It changes only whether being corrected pays, not which behaviour is best within a round.
- **Fines only means a correction cannot create a new exploit by raising anything.** After a correction, a behaviour can beat honest play in only two ways:
  - **(a) The original bug, if the correction under-corrects.** That is still visible to the monitor, so it gets corrected again, and the agent has no reason to avoid that (next point).
  - **(b) Another honest-ish route.** Its true return can fall short of honest by at most the fine that spilled onto the honest route, and L⁻ protects the reference's own transitions.

  The swap is different. It raises honest transitions, and routes that reuse the raised transitions beat honest play: AS −50, Boat Race −76, Taxi −39. These are new exploits, and the monitor cannot see them.
- **The level removes the cost of being corrected,** which is what makes standard PBRR hide. Hiding still gives up the exploit inside the audit window. So the optimum exploits in view in round 0 and is corrected at once.
  - On the Step 1 grid with the oracle patch: 5 × 8,700 = 43,500, against 39,500 for hiding (`test_compensated_correction_closed_forms_on_the_step1_grid`).
  - Being caught later is worse, because every hidden round gives up its window.
- **No farming.** There is no margin, so a second correction pays back only what the play that triggered it earned. That play includes the cost of using the bug inside the window. And with fines never relaxed, a second correction cannot unlock anything. So it is worth less than staying honest: on the oracle grid, 8,578 < 8,700.
- **Why the fines must never relax: a laptop code check, 2026-11-16** (1 draw, grid, seeds 0–1; not a result).
  - **The level alone farms.** Refits start from scratch, so the second correction was fitted on a play that only touches the bug, and that weakened the fine on the exploit. The optimum therefore re-triggered on purpose to reach the weaker reward. It was corrected in every round, with true −100 throughout, and the level climbed 86.8 → 81.1 → 95.3 → 98.1.
  - **With fines never relaxed,** the same check gives "corrected in round 0, then never again": true −100 then 22 ×4, V0 43,518 against 39,500 for hiding. The fixed point converged, and the counterfactual later corrections pay less (81 → 76 → 70 per step).

## What could still fail (stated before any target)

- **Under-correction.** Where one standard-PBRR correction leaves the original bug paying, the agent keeps exploiting openly and keeps being corrected; it never hides.
  - Phase A, which used fewer epochs, saw this in Taxi (true +16 after one correction, 200 epochs) and Boat Race (−94, 50 epochs).
  - At the campaign's 1000 epochs this is unknown. The `compare` targets (standard PBRR, 1000 epochs) say which.
- **Estimation.** V_before comes from 19 rollouts, and its noise has mean zero. If V_before comes out low by more than hiding costs per round (the window's value), hiding returns. That value is 1,000 on the grid, 100 in AS, about 46 in Tomato and about 61 in tomato_large.
- **PPO shaping its correction.** PPO could pick an odd caught play to shape the correction it gets. That is outside the targets' model, as it is for every variant.
- **Larger rewards.** Received rewards after a correction are about the exploit's level instead of the honest level.

## Expected end states (written 2026-11-16, before any target)

**Grid, AS, Tomato and tomato_large: "corrected in round 0, then never again", then honest.** At 1000 epochs, the standard-PBRR correction makes honest play the best round in all four (bonus campaign targets, seed 0):

| Env | Best round after one correction | Honest |
|---|---|---|
| grid | 22.2 | 22 |
| AS | 451.2 | 449.6 |
| Tomato | 434.0 | 434.0 |
| tomato_large | 524.3 | 522.5 |

**Taxi and Boat Race: unknown** (see under-correction above).

**The swap, for comparison** (true return per round after its correction):
- grid: honest (22);
- AS: −50 in 5 of 6 seeds, −100 in s2 (honest 450);
- Tomato: 416–425 (honest about 434);
- tomato_large: 483–501 (honest about 523);
- Taxi: −39 (Phase A; honest 125);
- Boat Race: −76 (Phase A; honest 50).

## Cells

There are six cells: grid, absent_supervisor, tomato, tomato_large, taxi and boat_race, each with the variant `comp`.

**Settings:** `--set g.fine_only=True g.offset=True g.offset_margin=0.0`, plus `g.epochs=1000` outside the grid, plus `task.obs=onehot` for Taxi.

**Where things go:**
- runs: `C1_comp_<tag>` in `results/step4/<env>/comp/`;
- targets: `results/step4/<env>/targets/comp/seed<s>.json`.

**Every driver command starts with `CAMPAIGN=comp`:** `CAMPAIGN=comp bash scripts/farmshare/step4_optimal.sh …`.

## Pipeline

1. **Targets.** `CAMPAIGN=comp bash scripts/farmshare/step4_optimal.sh targets submit`: 6 jobs, seeds 0–2 and 20–22.
2. **Comparison targets.** `CAMPAIGN=comp bash scripts/farmshare/step4_optimal.sh compare submit`: 4 jobs, the swap (`P2swap`) and standard PBRR (`base`) in Taxi and Boat Race at 1000 epochs. Taxi's swap seeds 0–2 already exist, match the game, and are skipped.

   The other four envs already have both:
   - **The swap:** the optimal campaign's `P2swap` targets.
   - **Standard PBRR:** the bonus campaign's `base_bonus1`, which hides in all 24 seeds. The bonus only adds value to being corrected, so standard PBRR without it hides too.
3. **Wave 1.** `CAMPAIGN=comp bash scripts/farmshare/step4_optimal.sh wave1 submit`: 18 runs, `L`, `LE` and `LN` per env on seeds 0–2, annealed over the last 25%. They start from each env's frozen Step 3 config, and Taxi takes `task.obs=onehot`.

   | Env | Episodes |
   |---|---|
   | grid, Tomato, tomato_large, Boat Race | 1536 |
   | AS | 3072 |
   | Taxi | 768 (its runs reach the 48 h limit; rule 1 resumes them) |
4. **Everything after that** uses the commands of docs/step4_optimal.md, each with `CAMPAIGN=comp` in front.

## Verdict, criteria and decision rules

**These are identical to docs/step4_optimal.md:**
- A seed is CONVERGED when its paired best-response gap is ≤ 0.03.
- A cell is DONE at 3/3 tuning seeds plus 3/3 confirmation seeds. Extended confirmations count.
- Rules 1–9 apply.
- Log in `docs/step4_comp_log.md`.

**Changes:**
- **Rule 2 (targets).** Put each target at the top of the log under "Exact predictions". For each cell give:
  - the end state;
  - the true return by round, against honest: grid 22, AS 450, Tomato about 434, tomato_large about 523, Taxi 125, Boat Race 50;
  - the corrections per episode;
  - V0 against V_hide;
  - each correction's level (`behaviour[].level`);
  - the same seed's swap and standard-PBRR targets;
  - whether the behaviour after the correction is honest, the original bug (under-correction) or a new exploit.
- **Rule 4 (caps).** Grid, Tomato, tomato_large and Boat Race: 12,288 episodes. AS: 24,576. Taxi: 6,144.
- **Rule 6b (exploration).** Start it in a cell once every wave-1 run of that cell has a check and none is CONVERGED 3/3. The base is the cell's run with the smallest mean gap.
- **Rule 8 (budget).** At most 30 queued or running jobs for this campaign, and at most 110 for all campaigns together.
- **Rule 9 (stop).** Stop when all six cells are DONE or the user says stop. The final summary gives, for each cell:
  - the target's end state and true return by round, against honest, the swap and standard PBRR;
  - the converged config and every seed's gap;
  - PPO's and the best response's true and received return by round;
  - whether PPO's behaviour after its correction is honest.

**Never** change environments, criteria, the mechanism or the targets to get a hoped-for result.

## Code

- **`src/pbrr_core.py`:** the `GConfig` fields `fine_only`, `offset` and `offset_margin`. The defaults are off, and older runs are unchanged.
- **`src/step3/protocol.py`:** the per-copy level (`AuditedVecEnv.level`, which resets with the reward) and `MinCorrection`.
- **`src/step3/pbrr.py`:**
  - The overseer composes the correction in force and installs the level.
  - `rollout_returns` and `level_offset`.
- **`src/step3/dp.py`:** `round_value` (the exact V_before of a policy's caught round) and `round_probs`.
- **`experiments/step4_targets.py` and `experiments/step4_br.py`:** the same rule per draw.
  - V_before is the caught play's exact round value. For PPO that means its own probabilities. For the deterministic optimum, it is taken without the rollouts' action noise, because the agent's own rollouts would carry none.
  - V_ref,after comes from the run's reference rollouts, as in training.
- **Tests** in `tests/test_step4.py`:
  - the oracle-grid closed forms;
  - `round_value` against the level evaluations;
  - the env paying the level;
  - the formula;
  - the running minimum;
  - the best-response identities;
  - a one-draw grid target.

## Prompt

The FarmShare loop prompt is in `docs/step4_loop_prompt.md`, campaign (C).
