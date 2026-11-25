# Step 4 outcome audit (CAMPAIGN=goal): decision log

Procedure: `docs/step4_goal.md`. Every round is judged on its outcome: a copy is corrected iff it misses the round's goal, does not end the round in the hidden state, and its return under the reward in force reaches the reference's ("still learning" exemption below it).
- **Envs:** `grid_goal`, `absent_supervisor_goal`, `tomato_goal`, `taxi_goal`, `boat_race_goal`. **Variants:** standard PBRR (`base`), no regulariser (`P1eq1`), the swap (`P2swap`). 15 cells.
- **Exact targets:** `CAMPAIGN=goal bash scripts/farmshare/step4_optimal.sh targets submit`: 15 jobs (seeds 0–2 and 20–22, 6 draws) → `results/step4/<env>/targets/<variant>/`. Each target records `exemption_by_level` (a level with `binds: true` is flagged, not trusted).
- **PPO:** `CAMPAIGN=goal`, runs `G1_<variant>_<tag>` in `results/step4/<env>/goal/`. Wave 1: L, LE, LN × 3 variants × 5 envs, seeds 0–2, each env's base frozen config (45 runs).
- **Verdict and rules:** `docs/step4_optimal.md` (paired best-response check, CONVERGED iff gap ≤ 0.03; extend, confirm, waves, 6b). Caps as the base envs.
- **Budget:** at most 60 jobs. Every submit carries `EXCLUDE=barley-04,wheat-06`. From 2026-11-25 this campaign is first in priority; the indifference campaigns (indiff_twin3, the hideout twin cells) are set aside by the user and their new submissions come after this campaign's.
- **Never** tune the environments, thresholds or criteria toward the predictions after seeing a target.

This log is append-only below the three summary sections.

## Status

- **Targets:** 15 jobs submitted 2026-11-25 (iteration 0), 2023183–2023197. None in yet.
- **PPO wave 1:** 45 runs submitted 2026-11-25 (iteration 0), 2023198–2023242.
- Cells DONE: **0 of 15.**

## Flags for the user

- None yet. The comparison of the targets with the pre-registered predictions will be flagged here as soon as all 15 target jobs are in.

## Exact predictions

**Pre-registered** (`docs/step4_goal.md`, 2026-11-25, before any target):
- **Standard PBRR** avoids correction in every env: it exploits and ends the rounds hidden. Its corrections fine, so being corrected costs it the exploit.
- **No regulariser and the swap** seek correction: they miss the goal in view in round 0, are corrected, then meet the goal. Risk: their corrections also raise transitions they never saw; if that lifts the hidden exploit, the optimum becomes "corrected, then exploit in hiding". Boat Race and Taxi are most at risk; Absent Supervisor's no-reg also hid in a 1-draw code check.
- New exploits outside the hidden state are caught (they miss the goal).

**Targets** (filled in as each lands; per env × variant × seed: end state, true by round against honest, corrections by round, whether the agent ends its rounds hidden after its last correction, `exemption_by_level` with any `binds: true` level flagged):

_None in yet._

## 2026-11-25, iteration 0 (13:40–14:00): campaign started; 15 target jobs and 45 PPO runs submitted

- **New campaign from the user (2026-11-25), first in priority from now on.** Read `docs/step4_goal.md` in full. `git pull --no-rebase --no-edit --ff` brought 570b081c (the outcome audit: `src/step3/goal.py`, the five `*_goal` tasks, `Protocol.learn_exempt`, `exemption_by_level`).
- **Tests:** `.venv/bin/python tests/test_step4.py`: 54 tests, 0 failed. `.venv/bin/python tests/test_step3.py`: 13 tests, 0 failed.
- **Targets.** Dry-run `CAMPAIGN=goal EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh targets` printed 15 `run_cmd.sh` lines, `experiments/step4_targets.py --env <env> --name <variant> --seeds 0 1 2 20 21 22 --draws 6 --set <variant words>` (`g.use_regularization=False` for P1eq1, `g.l_minus_on=dispreferred` for P2swap; `g.epochs=1000` for every env but the grid, as in their base Phase A). Time limits 4 h (grid, AS, Boat Race), 8 h (Tomato), 12 h (Taxi). Submitted →
  - grid_goal: **2023183** (base), **2023184** (P1eq1), **2023185** (P2swap);
  - absent_supervisor_goal: **2023186**, **2023187**, **2023188**;
  - tomato_goal: **2023189**, **2023190**, **2023191**;
  - taxi_goal: **2023192**, **2023193**, **2023194**;
  - boat_race_goal: **2023195**, **2023196**, **2023197**.
- **PPO wave 1.** Dry-run `CAMPAIGN=goal EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh wave1` printed 45 `submit.sh 48 --env <env> --run-id G1_<variant>_<tag> --seeds 0 1 2 --results-dir results/step4/<env>/goal --set ...` lines, each env's base frozen config:
  - grid_goal: `episodes=1536 anneal.last=0.25 anneal.floor=0.1` (LE: `ppo.ent_coef=0.03`; LN: `n_envs=64 ppo.batch_size=1600`);
  - absent_supervisor_goal: `ppo.ent_coef=0.1 g.epochs=1000 episodes=3072` (LE: entropy 0.3);
  - tomato_goal: `ppo.ent_coef=0.03 g.epochs=1000 episodes=1536` (LE: 0.1);
  - taxi_goal: `ppo.ent_coef=0.03 g.epochs=1000 episodes=768` (LE: 0.09); its one-hot observation is the task's own default (`src/step3/tasks/taxi_goal.py`: `obs="onehot"`), so `task.obs` is not on the line;
  - boat_race_goal: `ppo.ent_coef=0.03 g.epochs=1000 episodes=1536` (LE: 0.09);
  - plus `g.use_regularization=False` (P1eq1) or `g.l_minus_on=dispreferred` (P2swap).
  - Submitted → grid_goal **2023198–2023206** (base L/LE/LN, P1eq1 L/LE/LN, P2swap L/LE/LN), absent_supervisor_goal **2023207–2023215**, tomato_goal **2023216–2023224**, taxi_goal **2023225–2023233**, boat_race_goal **2023234–2023242** (same order in each env).
- **Budget:** 60 jobs (cap 60). All jobs: 91 of 110.
- **Other campaigns:** indiff_twin3 and the hideout twin cells are set aside by the user: their running jobs finish and their finished seeds get checks, but new submissions there come after this campaign's. bonus and noreg_fail continue as before.
