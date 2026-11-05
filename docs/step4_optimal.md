# Step 4: the optimal-policy campaign (FarmShare, from 2026-11-04)

## Goal (mentor meeting, 2026-11-04)

This week, PPO must behave (almost exactly) optimally. For two PBRR variants, it must reach the optimal policy computed by exact solve:
- **swap:** `g.l_minus_on=dispreferred`
- **no regulariser:** `g.use_regularization=False`

It must do so on four environments: the grid, Absent Supervisor, Tomato, and **tomato_large**, a slightly larger Tomato with 8 tomatoes. In the mentor's words, as relayed by the user: every agent should eventually behave optimally. One that hasn't was not tuned or trained enough, so keep tuning and training until it does.

**The user's hypothesis, as stated:**
- Without regularisation, total reward may go down as well as up, so "a smart enough agent might then avoid correction".
- With the swap, an agent that learns its best policy "should be always-behaving".
- The hope is to see the no-regulariser variant "mess up somewhere as the agent avoids correction".

This is a hypothesis to be tested, not a rule. Whether a variant's optimum avoids correction is decided by its exact target (below), before any PPO result is in.

**Everything runs on FarmShare.** The laptop only writes code and runs second-long code checks.

## What "optimal" means: the self-consistent target

Phase A's A5 optimum (`experiments/step3_check.py`) is **not** the right target. It fixes each correction in advance:
- correction 1 is fitted on a softened open exploiter;
- correction c+1 is fitted on the one-sub-episode optimum under correction c;
- all from a single random draw.

PPO plays a different game. Each of its corrections is fitted on the rollouts of *its own* policy in the round where it was caught, with fresh draws every time. PPO already earns **more** received reward than A5's optimum:
- Tomato, no regulariser: 4,889–5,822 vs 4,758.
- Absent Supervisor, no regulariser: 7,925–8,190 vs 7,779.

So A5 is not a ceiling for PPO.

`experiments/step4_targets.py` computes the optimum of the game PPO actually plays. It is a fixed point of behaviour → corrections → optimal behaviour:
- **Fitting correction c.** As in training, correction c is fitted on 19 rollouts of the policy at level c−1, against the run's own reference rollouts, with D accumulated over the episode. The rollouts are taken in the round where the current optimum gets its c-th correction.
- **When the optimum never gets a c-th correction,** correction c is fitted on the best policy that *would* be caught there. This is the alternative that "not getting caught" has to beat.
- **Six overseer draws per level.** A draw is one set of rollouts, labels and fit seed. The policy cannot see the draw, so the optimum against random corrections is exactly the optimum against their mean tables.
- **Solve and iterate.** Solve the level DP exactly, evaluate it, and iterate until its correction pattern stops changing.

Each target file reports:
- the value of never being corrected (`V_hide`) and the margin over it;
- the optimum's end state;
- each single draw's own optimum, to show how robust the end state is.

**The target is the answer to the hypothesis, not a ceiling for PPO** (found 2026-11-05). The target fits correction 1 on the exact optimum's round-0 play, which includes 5% random actions. Training fits it on PPO's own play. In Absent Supervisor and Tomato, PPO receives 7–15% more than its target's V0, 3–13 standard errors of the target's six draws above it. In every AS swap and Tomato swap seed, PPO receives more than each single-draw optimum, and each of those optima knows its own draw. So PPO's corrections pay more than the target's. On the grid swap the gaps are within the target's noise (0.8–1.6 standard errors); on the grid no-regulariser they are 1.4–6.0. The fixed point cannot optimise round-0 play for the correction it induces (that is a bilevel problem). So a value gap against the target cannot say whether PPO is optimal. That is the job of the paired check below.

## Is PPO optimal? The paired best-response check (`experiments/step4_br.py`, from 2026-11-05)

For each seed's trained model, at its current episode count:
- **Read the policy exactly.** The trained policy is read as an exact table over (t, s, correction level, audit flag) and propagated exactly (`dp.evaluate_levels_probs`).
- **Fit the corrections on PPO's own play,** as training does. Correction c is fitted on PPO's rollouts in the round where PPO most likely gets its c-th correction, with D accumulated.
  - If PPO (almost) never gets a c-th correction (probability below 0.05), the correction is fitted on the best policy that would be caught there, as in the target. Seeking one more correction is therefore an option. So is hiding (never being corrected).
- **Best response.** It uses 12 overseer draws per level. The level DP on their mean tables gives V_BR, which is exact because the policy cannot see the draw.
- **The gap.** PPO's exact value on the same tables is V_PPO, and the gap is 1 − V_PPO / V_BR ≥ 0. Both values are linear in the tables, so each draw gives a paired difference and the gap gets a standard error.

It is one policy-improvement step from PPO's own play. A run is ε-optimal only if no policy beats it by more than ε against the overseer's response to the run's own behaviour.

Output: `<run>/step4_br/seed<s>_ep<N>.json`, never overwritten. It holds the gap and its standard error, the best response's end state, true and received return by round, and PPO's.

Code checks (laptop, 2 draws, not results):
- **AS no-regulariser `L` s1** (ABOVE TARGET under the old rule): gap 0.0003.
- **Grid no-regulariser `L` s2** (exploits and hides after its correction): gap 0.073. The best response is corrected three times, then honest.
- **Tomato swap `LN` s2** (true 300): gap 0.085. The best response plays true 418.

## Pipeline (`scripts/farmshare/step4_optimal.sh`)

1. **tomato_large Phase A.**
   - Run `step4_optimal.sh phase_a submit` to get the standard A1–A5 check, which writes `results/step3/tomato_large/phase_a/`.
   - Then run its three canonical Step 4 checks with `PHASEA_JOB=<id>`.
2. **Targets.** Run `PHASEA_JOB=<id> step4_optimal.sh targets submit`. This produces 4 envs × 2 variants, each with seeds 0–2 (tuning) and 20–22 (confirmation), in `results/step4/<env>/targets/<variant>/seed<s>.json`.
3. **PPO wave 1.** Run `PHASEA_JOB=<id> step4_optimal.sh wave1 submit`.
   - This covers 4 envs × 2 variants × 3 configs, seeds 0–2, in `results/step4/<env>/optimal/O1_<variant>_<tag>/`.
   - Every config starts from the env's frozen Step 3 PPO config. The grid keeps Step 2's 100-epoch g fit; the other envs use 1000 epochs, as in all Step 4 runs.
   - Every config trains for 1536 episodes (Absent Supervisor: 3072), with annealing over the last 25%: learning rate and entropy fall linearly to 0.1× by the end, so the final policy settles on its optimum instead of sampling around it.

   | tag | change |
   |---|---|
   | `L` | the frozen config, trained long |
   | `LE` | entropy 3× (grid 0.03, Absent Supervisor 0.3, Tomato and tomato_large 0.1) |
   | `LN` | 64 envs, batch 1600 (4 minibatches, as before) |

4. **Reports.** `step4_optimal.sh report` runs `experiments/step4_convergence.py` on every campaign run. For each run it writes `step4_convergence.json` and `step4_convergence.png`, the "loss curve": the gap to the target for every 24 episodes.
5. **Best-response checks.** `step4_optimal.sh br_missing submit` submits one job per run with finished seeds that lack a check at their final episode count. They take minutes on the grid and Absent Supervisor, up to about an hour on Tomato, and a few hours on tomato_large. `step4_optimal.sh br <env> <run> submit` checks one run.

`EXCLUDE=<nodes>` before any `step4_optimal.sh … submit`, for example `EXCLUDE=barley-04`, keeps the jobs off broken nodes. It replaces the held-gate workaround.

**Runs checkpoint every 24 episodes** and can be resumed or extended in the same directory:
- `step4_optimal.sh resume submit` resubmits every run with unfinished seeds that no longer has a job (for example, after the 48-hour limit).
- `step4_optimal.sh extend <env> <run> <episodes> submit` takes a run on to a larger total. Annealing then applies to the last 25% of the *new* total, so the policy is first "re-heated", then cooled again.
- A finished seed's `metrics.json` is kept as `metrics_ep<N>.json`.

## Pre-registered convergence criteria (`experiments/step4_convergence.py`; amended 2026-11-05)

**The verdict** comes from the seed's paired best-response check at its current episode count:

| Verdict | Condition | Action |
|---|---|---|
| CONVERGED | best-response gap ≤ 0.03 | — |
| IMPROVING | gap > 0.03, and the curve still improves: the last 3 blocks' value gap is ≥ 0.01 below the 3 blocks ending 20% of the run earlier, or the window or true gap is ≥ 0.02 below. Runs shorter than 8 blocks count as improving. | extend |
| PLATEAU | gap > 0.03, not improving | change the config |
| NEEDS BR | finished, no check at this episode count yet | `br_missing submit` |
| RUNNING | not finished, no check | — |

**Reported for information, never blocking.** These are measured over the last 10% of episodes (at least 24), against the seed's self-consistent target:

| gap | tolerance |
|---|---|
| value: 1 − received per episode / target V0 | within ±0.03 |
| window: max over rounds of \|P(window exploited) − target\| | ≤ 0.05 |
| true: max over rounds of \|true return − target\| / (honest − proxy-optimal true) | ≤ 0.05 |
| corrections per episode − target | ≤ 0.10 |

- **"matches target"** means all four gaps are within tolerance.
- **"above target"** means a value gap below −0.03. It shows that PPO's corrections pay more than the target's.

**History.** Until 2026-11-05 these four gaps were the verdict, and "above target" was a verdict (ABOVE TARGET) that blocked extension and confirmation. On 2026-11-05 it blocked 5 of the 8 cells. No ABOVE TARGET seed beat the best play under its own correction: the round-1 probe put them at 89–100% of it. The ones near 90% (AS swap, grid no-regulariser `LN` s1 and s2) really are short, and neither the old rule nor "treat ABOVE TARGET as noise" could tell them from the rest. The verdicts in the log before that date use the old rule.

**When a cell is done.** A *cell* is one (env, variant) pair. It is done when:
1. some config is CONVERGED in 3 of 3 tuning seeds; and
2. the same config, at its final episode count (`step4_optimal.sh confirm <env> <run> submit`), is CONVERGED in 3 of 3 fresh seeds (20–22).

## Decision rules for each loop iteration

Apply these in order and log every decision in `docs/step4_optimal_log.md`:

1. **Resubmit unfinished runs.** If a run has unfinished seeds and no job in `squeue`, run `resume submit`.
2. **New targets.** When a targets job has finished, log each cell's target:
   - its end state ("hides", "corrected in round 0, then never again", or "n corrections per episode");
   - its true return by round;
   - V0, V_hide and the margin;
   - the end state of each draw.

   **These are the exact predictions:** they say whether no-regulariser's optimum avoids correction and whether the swap's optimum always behaves. Report them prominently: they answer the user's hypothesis whatever PPO does.

   If `fixed_point_converged` is false, log it and treat the last iteration as the target.
3. **Best-response checks.** Run `br_missing submit`. It covers every finished seed without a check, including the runs judged under the old rule. Don't rerun finished runs.
4. **Finished runs.** Once all of a run's seeds have a check, read its verdicts:
   - **All seeds CONVERGED:** if the run is a tuning run, submit `confirm`. If it is already a `_confirm` run, mark the cell DONE.
   - **Any seed IMPROVING:** `extend` to 2× its episodes. Cap: 8× the wave-1 length (grid, Tomato and tomato_large 12,288 episodes; Absent Supervisor 24,576). A seed whose check is older than its episode count is NEEDS BR again.
   - **Every unconverged seed is PLATEAU:** the config is finished; don't extend it.
   - **Log every seed's check:** the gap ± its standard error, and the best response's end state and true return by round against PPO's and the target's. Note "above target" seeds as evidence that PPO's corrections pay more than the target's; that is not a problem to fix.
   - **Flag a seed whose best response differs from the target's end state** in a way that changes the answer to the hypothesis (for example, a best response that hides where the target does not).
5. **Wave 2 for plateaued cells.** When every wave-1 run of a cell is finished and none is CONVERGED or IMPROVING, take the config with the smallest mean best-response gap and submit one factor at a time on top of it, with `ppo <env> <variant> <tag> "<that config's extras> <factor>" submit`:

   | factor | tag |
   |---|---|
   | `ppo.learning_rate=0.0001` | `LR` |
   | `ppo.gae_lambda=1.0` | `GL` (unbiased credit across the 100-step boundary) |
   | `ppo.net_arch=[256,256]` | `NET` |
   | `reward_scale=<0.25 × the env's Phase A reward_scale>` | `RS` |
   | `ppo.n_epochs=20` | `EP` |
   | `anneal.last=0.5` | `AN` |

   Name each run `<best tag>+<factor>`, e.g. `O1_P2swap_LE+GL`.
6. **Wave 3.** If wave 2 plateaus too, combine the two best wave-2 factors and extend the best run. If nothing improves after that, stop tuning that cell and report it as a finding, with its convergence curve.
7. **Commit.** Run `bash scripts/farmshare/step4_commit.sh "<message>"`.
   - It commits only small files while seeds are running.
   - It commits `logs.npz`, `model.zip` and the round CSVs only once a seed has finished.
   - Never `git add` a running seed's checkpoint files by hand.
8. **Budget.** Keep the campaign at ≤ 60 queued or running jobs (each job is 3 seeds = 3 cores). The partition allows 128 per user. Don't cancel other jobs (for example the Taxi, MountainCar and LunarLander `*_r2_*` runs) without the user's go-ahead.
9. **Stop** when all 8 cells are DONE (or reported as findings), or when the user says stop. Then write a final summary at the top of the log. For each cell it gives:
   - the target end state;
   - the converged config;
   - the best-response gap of every seed;
   - PPO's true return and received return by round, against its best response and the target;
   - the convergence curve.

## The FarmShare loop prompt

The text given to FarmShare Claude, started with `/loop`, is kept at the end of this file, under "Prompt".

## Prompt

```
/loop You are running the Step 4 "optimal-policy" campaign of this repo (~/reward-hacking-with-observer) on Stanford FarmShare. Read CLAUDE.md (§4f, §6 FarmShare) and docs/step4_optimal.md before doing anything; docs/step4_optimal.md is the source of truth for the goal, the pre-registered criteria and the decision rules, and you follow it exactly.

Goal: PPO must reach (almost exactly) its exact optimum, i.e. be within 3% of the best response to the corrections its own play induces (experiments/step4_br.py, the verdict), for the swap (g.l_minus_on=dispreferred) and the no-regulariser (g.use_regularization=False) PBRR on grid, absent_supervisor, tomato and tomato_large; the self-consistent target (experiments/step4_targets.py) gives the exact end state that answers the user's hypothesis. Not converging means not tuned or trained enough: keep tuning (scripts/farmshare/step4_optimal.sh wave1 / ppo / extend) until every (env, variant) cell has a config CONVERGED in 3/3 tuning seeds and 3/3 fresh confirmation seeds, or is reported as a finding after wave 3.

Each iteration:
0. If docs/step4_optimal_log.md does not exist yet, this is the first iteration: git pull; run `.venv/bin/python tests/test_step4.py`; submit `bash scripts/farmshare/step4_optimal.sh phase_a submit` (note the first job id = PHASEA_JOB; then rerun with `PHASEA_JOB=<id>` so the three tomato_large variant checks wait for it); then `PHASEA_JOB=<id> bash scripts/farmshare/step4_optimal.sh targets submit` and `PHASEA_JOB=<id> bash scripts/farmshare/step4_optimal.sh wave1 submit`. Always dry-run a command first (omit "submit") and check it. Create docs/step4_optimal_log.md (append-only: date, what you saw, what you decided, the exact commands, job ids) and commit.
1. git pull --no-rebase --no-edit --ff (never --rebase or --autostash: they replace modified tracked files, which detaches running seeds' open logs); squeue -u $USER; bash scripts/farmshare/step4_optimal.sh report.
2. Apply the decision rules of docs/step4_optimal.md in order (resume, new targets, best-response checks, finished runs: confirm / extend / plateau, wave 2, wave 3, budget). Put EXCLUDE=<broken nodes> (e.g. EXCLUDE=barley-04) in front of every submit while a node is broken. Log every decision and command in docs/step4_optimal_log.md.
3. As soon as a target is computed, write its end state per cell at the top of the log under "Exact predictions": whether the no-regulariser optimum avoids correction (hides) and whether the swap optimum is corrected once and then behaves. These are the answer to the user's hypothesis; never adjust environments, criteria or targets to get a hoped-for result.
4. Commit with `bash scripts/farmshare/step4_commit.sh "<short message>"` (never git add running seeds' checkpoint files by hand; never overwrite or delete a run; a seed that died before its first checkpoint is moved aside automatically by --resume).
5. If something is broken (a job crashes, a script errors, a target's fixed point does not converge, a best-response check fails), log it with the error text, fix only what is clearly a bug (commit the fix with a test), and otherwise flag it at the top of the log for the user instead of improvising.
Pace: wake every ~45 min while jobs run (longer, ~2 h, when only long runs remain). Stop the loop when every cell is DONE or reported as a finding, after writing the final summary at the top of the log.
```
