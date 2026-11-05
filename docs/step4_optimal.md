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

It does not model one thing: an agent behaving oddly in a caught round to shape its correction. If a PPO run earns clearly more than its target, it is outside the target's model (verdict ABOVE TARGET).

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

**Runs checkpoint every 24 episodes** and can be resumed or extended in the same directory:
- `step4_optimal.sh resume submit` resubmits every run with unfinished seeds that no longer has a job (for example, after the 48-hour limit).
- `step4_optimal.sh extend <env> <run> <episodes> submit` takes a run on to a larger total. Annealing then applies to the last 25% of the *new* total, so the policy is first "re-heated", then cooled again.
- A finished seed's `metrics.json` is kept as `metrics_ep<N>.json`.

## Pre-registered convergence criteria (`experiments/step4_convergence.py`)

These are measured per seed over the last 10% of episodes (at least 24), against that seed's target:

| gap | tolerance |
|---|---|
| value: 1 − received per episode / target V0 | within ±0.03 |
| window: max over rounds of \|P(window exploited) − target\| | ≤ 0.05 |
| true: max over rounds of \|true return − target\| / (honest − proxy-optimal true) | ≤ 0.05 |
| corrections per episode − target | ≤ 0.10 |

**Verdicts:**

| Verdict | Condition | Action |
|---|---|---|
| CONVERGED | all four gaps within tolerance | — |
| ABOVE TARGET | value gap < −0.03 | investigate |
| IMPROVING | the last 3 blocks' value gap is ≥ 0.01 below the 3 blocks ending 20% of the run earlier, or the window or true gap is ≥ 0.02 below | extend |
| PLATEAU | none of the above | change the config |

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
3. **Finished runs.** For each finished run, read its verdicts:
   - **All seeds CONVERGED:** if the run is a tuning run, submit `confirm`. If it is already a `_confirm` run, mark the cell DONE.
   - **Any seed IMPROVING, none ABOVE TARGET:** `extend` to 2× its episodes. Cap: 8× the wave-1 length (grid, Tomato and tomato_large 12,288 episodes; Absent Supervisor 24,576).
   - **Every unconverged seed is PLATEAU:** the config is finished; don't extend it.
   - **Any seed ABOVE TARGET:**
     - run `experiments/step4_probe.py <run>`;
     - log what PPO does differently from the target (received and true by round, corrections);
     - flag it for the user at the top of the log;
     - keep it out of the "done" count.
4. **Wave 2 for plateaued cells.** When every wave-1 run of a cell is finished and none is CONVERGED or IMPROVING, take the config with the smallest value gap and submit one factor at a time on top of it, with `ppo <env> <variant> <tag> "<that config's extras> <factor>" submit`:

   | factor | tag |
   |---|---|
   | `ppo.learning_rate=0.0001` | `LR` |
   | `ppo.gae_lambda=1.0` | `GL` (unbiased credit across the 100-step boundary) |
   | `ppo.net_arch=[256,256]` | `NET` |
   | `reward_scale=<0.25 × the env's Phase A reward_scale>` | `RS` |
   | `ppo.n_epochs=20` | `EP` |
   | `anneal.last=0.5` | `AN` |

   Name each run `<best tag>+<factor>`, e.g. `O1_P2swap_LE+GL`.
5. **Wave 3.** If wave 2 plateaus too, combine the two best wave-2 factors and extend the best run. If nothing improves after that, stop tuning that cell and report it as a finding, with its convergence curve.
6. **Commit.** Run `bash scripts/farmshare/step4_commit.sh "<message>"`.
   - It commits only small files while seeds are running.
   - It commits `logs.npz`, `model.zip` and the round CSVs only once a seed has finished.
   - Never `git add` a running seed's checkpoint files by hand.
7. **Budget.** Keep the campaign at ≤ 60 queued or running jobs (each job is 3 seeds = 3 cores). The partition allows 128 per user. Don't cancel other jobs (for example the Taxi, MountainCar and LunarLander `*_r2_*` runs) without the user's go-ahead.
8. **Stop** when all 8 cells are DONE (or reported as findings), or when the user says stop. Then write a final summary at the top of the log. For each cell it gives:
   - the target end state;
   - the converged config;
   - PPO's true return and received return by round, against the target;
   - the convergence curve.

## The FarmShare loop prompt

The text given to FarmShare Claude, started with `/loop`, is kept at the end of this file, under "Prompt".

## Prompt

```
/loop You are running the Step 4 "optimal-policy" campaign of this repo (~/reward-hacking-with-observer) on Stanford FarmShare. Read CLAUDE.md (§4f, §6 FarmShare) and docs/step4_optimal.md before doing anything; docs/step4_optimal.md is the source of truth for the goal, the pre-registered criteria and the decision rules, and you follow it exactly.

Goal: PPO must reach (almost exactly) the self-consistent exact optimum (experiments/step4_targets.py) for the swap (g.l_minus_on=dispreferred) and the no-regulariser (g.use_regularization=False) PBRR on grid, absent_supervisor, tomato and tomato_large. Not converging means not tuned or trained enough: keep tuning (scripts/farmshare/step4_optimal.sh wave1 / ppo / extend) until every (env, variant) cell has a config CONVERGED in 3/3 tuning seeds and 3/3 fresh confirmation seeds, or is reported as a finding after wave 3.

Each iteration:
0. If docs/step4_optimal_log.md does not exist yet, this is the first iteration: git pull; run `.venv/bin/python tests/test_step4.py`; submit `bash scripts/farmshare/step4_optimal.sh phase_a submit` (note the first job id = PHASEA_JOB; then rerun with `PHASEA_JOB=<id>` so the three tomato_large variant checks wait for it); then `PHASEA_JOB=<id> bash scripts/farmshare/step4_optimal.sh targets submit` and `PHASEA_JOB=<id> bash scripts/farmshare/step4_optimal.sh wave1 submit`. Always dry-run a command first (omit "submit") and check it. Create docs/step4_optimal_log.md (append-only: date, what you saw, what you decided, the exact commands, job ids) and commit.
1. git pull --rebase --autostash; squeue -u $USER; bash scripts/farmshare/step4_optimal.sh report.
2. Apply the decision rules of docs/step4_optimal.md in order (resume, new targets, finished runs: confirm / extend / plateau / above-target, wave 2, wave 3, budget). Log every decision and command in docs/step4_optimal_log.md.
3. As soon as a target is computed, write its end state per cell at the top of the log under "Exact predictions": whether the no-regulariser optimum avoids correction (hides) and whether the swap optimum is corrected once and then behaves. These are the answer to the user's hypothesis; never adjust environments, criteria or targets to get a hoped-for result.
4. Commit with `bash scripts/farmshare/step4_commit.sh "<short message>"` (never git add running seeds' checkpoint files by hand; never overwrite or delete a run; a seed that died before its first checkpoint is moved aside automatically by --resume).
5. If something is broken (a job crashes, a script errors, a target's fixed point does not converge, a run is ABOVE TARGET), log it with the error text, fix only what is clearly a bug (commit the fix with a test), and otherwise flag it at the top of the log for the user instead of improvising.
Pace: wake every ~45 min while jobs run (longer, ~2 h, when only long runs remain). Stop the loop when every cell is DONE or reported as a finding, after writing the final summary at the top of the log.
```
