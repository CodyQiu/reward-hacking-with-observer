# Step 4: the update-bonus campaign (FarmShare, from 2026-11-13)

## Where it comes from (as stated)

**The mentor, 2026-11-12, relayed by the user:**
> "it should always be optimal for the agent to seek the state where its reward function is updated cuz doing so would increase return. however, such a state may be hard to find. Maybe one way we can get around this is by adding an additional state feature which is +1 if the reward function was updated and 0 otherwise, so the policy can learn to seek out the grid cells where the reward function is updated."

- **The user's reading:** "+1 when reward function updates and +0 otherwise", i.e. a reward bonus.
- **The user's concern:** "isn't that just gonna make the agent want to exploit in the next sub-episode? ... what we want is it gets caught in first sub-episode and then behaves in the next 4 ones".
- **The mentor's reply, 2026-11-13:**
  > "yes if exploiting leads to a reward update then thats correct; if we assume that the reward function is corrected though, then IMO this would be a good thing."
- **The user then agreed** and asked for this:
  - "implement this on the same three experiments first (like the grid world, absent supervisor, tomato, tomato large) like before. let's also throw in PBRR in there just because. don't rerun the other ones. this run should be similar to what we literally just did but for these two methods."
  - The two methods are the swap and no-regulariser.

These are the user's and the mentor's assumptions, recorded as stated. They are hypotheses to test, not rules.

## What the bonus is (`protocol.update_bonus`, from 2026-11-13)

**Where it is paid.**
- The received reward pays **+b on the last step (τ = T_sub − 1) of every sub-episode whose audit triggers a correction.** That means rounds 0–3 only. The last audit corrects nothing (the reward resets), so it pays nothing.
- It is paid for every correction, not just the first. That follows the mentor's reply.
- It is part of the received reward only, not of the proxy or the true reward.
- **b = 1.0, in the environment's own reward units** (before `reward_scale`). The setting is `--set protocol.update_bonus=1.0`, and the default 0 is off.

**Why it is paid at the end of the round.**
- Because p_detect = 1 and γ = 1, paying it at the end of the round has the same value as paying it on the step that sets the audit flag (the "cell where the reward function is updated").
- At the end of the round it is exact for any p.
- It also lands in the same PPO rollout as the action that triggered it. The audit flag is in the observation, so the critic can carry the credit back within at most W = 10 steps.

**The observation is unchanged.** It already shows the correction count (one-hot) and the audit flag (`src/step3/protocol.py`, `encode_obs`).

**Scale.** b = 1 is about one step's reward in every env:

| Env | One step's reward | The learner sees b as |
|---|---|---|
| grid | −1 per step; the exploit pays +100 per step | 0.01 |
| Absent Supervisor | −1 per move, +50 per lap | 0.065 (0.01625 in `LN+RS`) |
| Tomato | about 4.3 per step honest | 0.17 |
| tomato_large | | 0.13 |

So b = 1 can change an exact optimum only where two options are within about b × (corrections per episode). Whether it changes any of them is the first thing the targets show.

**Code:**
- `src/step3/protocol.py`: the env.
- `src/step3/dp.py`: `solve_levels`, `evaluate_levels`, `evaluate_levels_probs`.
- `experiments/step4_br.py`: adds the bonus to V_PPO and to every draw.
- `experiments/step4_targets.py`: includes it through the DP. `game_key` leaves the field out when it is 0, so runs and targets from before 2026-11-13 keep matching.

**Tests** (`tests/test_step4.py`):
- On the Step 1 grid with the oracle patch, b = 0 hides (39,500).
- With b = 10,000 it is caught in rounds 0–3: 8,700 + 3 × (−100) + 22 + 4b = 48,422.
- The env pays exactly where the DP does.
- The best-response check moves by exactly b per correction.

## Cells

There are 12 cells: 4 envs (grid, absent_supervisor, tomato, tomato_large) × 3 variants:

| Variant | `--set` |
|---|---|
| `P2swap` | `g.l_minus_on=dispreferred` |
| `P1eq1` | `g.use_regularization=False` |
| `base` | standard PBRR (max1), as in Steps 2–3 |

Every cell also has `protocol.update_bonus=1.0`. Outside the grid the g fit runs for 1000 epochs, as in the optimal campaign.

Runs are `B1_<variant>_<tag>` in `results/step4/<env>/bonus/`. Targets are `results/step4/<env>/targets/<variant>_bonus1/seed<s>.json`.

**Every driver command runs with `CAMPAIGN=bonus` in front:** `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh …`. Without it, the command acts on the optimal campaign, which this campaign must not touch: "don't rerun the other ones".

## Pipeline

1. **Targets:** `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh targets submit`. That is 12 jobs, seeds 0–2 and 20–22. Same method as the optimal campaign (docs/step4_optimal.md, "the self-consistent target").
2. **Wave 1:** `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh wave1 submit`. That is 20 jobs, seeds 0–2.
   - **Swap and no-regulariser (8 runs).** Each cell's reference run from the optimal campaign, with the bonus, at the listed length:
     - for a DONE cell, its converged config;
     - for an open cell, its tuning run with the smallest mean best-response gap.

     The seeds are the same, so each run pairs with its no-bonus run, which has the same config and seeds.

     | Cell | Reference run (optimal campaign) | Episodes | Its status without the bonus |
     |---|---|---|---|
     | grid swap | `O1_P2swap_LE+NET+ENT3` | 1536 | DONE |
     | grid no-reg | `O1_P1eq1_LN+LR` | 6144 | open: 3/3 at 6144, confirmation 0/3 |
     | AS swap | `O1_P2swap_LN` | 3072 | DONE |
     | AS no-reg | `O1_P1eq1_LN+RS` | 6144 | DONE |
     | Tomato swap | `O1_P2swap_LN+ES10+N4` | 1536 | DONE |
     | Tomato no-reg | `O1_P1eq1_LN` | 6144 | DONE |
     | tomato_large swap | `O1_P2swap_LE` | 1536 | open: 3/3 at 1536, confirmation running |
     | tomato_large no-reg | `O1_P1eq1_LN+ES10` | 1536 | open: 0/3. Its best response seeks about 4 corrections per episode where PPO takes 1, which is the case the mentor's idea is aimed at. |

   - **Standard PBRR (12 runs).** `L`, `LE` and `LN`, exactly as the optimal campaign's wave 1:
     - the frozen Step 3 config, trained long;
     - entropy 3×;
     - 64 envs with batch 1600.

     Each runs 1536 episodes (Absent Supervisor 3072), annealed over the last 25%.
3. **Reports, best-response checks, resume, extend, confirm, explore, ppo:** the same commands as in docs/step4_optimal.md, each with `CAMPAIGN=bonus` in front.

## Verdict and criteria

They are identical to docs/step4_optimal.md, "Pre-registered convergence criteria":
- The verdict is the paired best-response check: CONVERGED iff the gap ≤ 0.03. Otherwise the seed is IMPROVING, PLATEAU, NEEDS BR or RUNNING, as defined there.
- The target gaps are information only.
- **A cell is DONE** when one config is CONVERGED in 3/3 tuning seeds and in 3/3 confirmation seeds (20–22). A confirmation may be extended (rule 4), and its seeds count once CONVERGED.

## Decision rules

Apply the rules of docs/step4_optimal.md in order (1, 2, 3, 4, 5, 6, 6b, 7, 8, 9), with these changes. Log every decision in `docs/step4_bonus_log.md`.

**Rule 2 (targets).** Log each cell's target as there. Then compare:
- **For swap and no-regulariser,** compare with the no-bonus target of the same seed (`results/step4/<env>/targets/<variant>/seed<s>.json`):
  - Is the end state the same?
  - Did V0 move by about 1 × the corrections?
  - Do the corrections per episode differ?
- **For `base`,** say whether the target hides. The bonus only adds value to being corrected. So a target that hides with the bonus would also hide without it.

Put the comparison at the top of the log under "Exact predictions".

**Rule 4 (caps).** The cap is as in the optimal campaign: grid, Tomato and tomato_large at 12,288 episodes; Absent Supervisor at 24,576.

**Rule 5 (wave 2).** For a swap or no-regulariser cell, the one wave-1 run is "the config with the smallest mean gap". Its extras are that run's own overrides (`.venv/bin/python scripts/farmshare/run_sets.py results/step4/<env>/bonus/<run>`, minus `episodes=`).

**Rule 6b (exploration).**
- **When to start.** Start it in a cell once every wave-1 run of that cell has a check and none is CONVERGED 3/3 (whether awaiting or failing its confirmation). Don't wait for waves 2–3.
- **Base.** The cell's run with the smallest mean best-response gap: `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh explore <env> <variant> <B1 run> submit`.
- **Stage 2 and the extension rule** are as there.
- **Order:** grid, then Absent Supervisor, then Tomato, then tomato_large.

**Rule 8 (budget).** At most 60 queued or running jobs for this campaign. The optimal campaign's jobs that are still running finish on their own. Don't cancel or resubmit them, and don't run their checks. `step4_commit.sh` commits their results as they finish.

**Rule 9 (stop).** Stop when all 12 cells are DONE, or when the user says stop. Then write the final summary at the top of the log. For each cell it gives:
- the target end state, and whether the bonus changed it;
- the converged config;
- every seed's best-response gap;
- PPO's true and received return by round, against its best response and the target;
- the convergence curve.

For each swap and no-regulariser cell it also compares with its no-bonus reference run (same config and seeds):
- the best-response gaps at the same episode count;
- the corrections per episode;
- the true return in rounds 1–4.

**Never** tune environments, criteria or b towards a hoped-for result. b stays 1.0 unless the user changes it.

## Prompt

The FarmShare loop prompt that runs this campaign, together with the no-regulariser failure campaign (`docs/step4_noreg_fail.md`), is in `docs/step4_loop_prompt.md`. It replaced the bonus-only prompt that was here on 2026-11-13.
