# Step 4: no-regulariser where its optimum is not the desired behaviour (FarmShare, from 2026-11-14)

## Where it comes from

**The question (the user, 2026-11-10).** Does the swap's new exploit in Absent Supervisor also happen with no-regulariser PBRR, and with standard PBRR?

**The answer from the exact Phase A checks** (`results/step4/<env>/phase_a/P1eq1_ep1000/summary.json`, the best round after one correction). No-regulariser's best play is a **new exploit**: it uses no original bug and never gets caught, yet true return falls well below honest. There are three such environments:

| Env | No-reg best play after one correction | Honest true |
|---|---|---|
| Boat Race | true −100. It pushes into the wall at the (4,4) corner for about 92 steps. | +50 |
| Taxi | true −83. It makes 0.6 deliveries instead of 7.1, bumping or shuttling with a passenger on board. | +125 |
| MountainCar | true −107 (mild). It reaches the flag about 7 steps late. | −100 |

Standard PBRR never creates a new exploit; it only under-corrects. See the memory note "paying corrections create new exploits".

**The user, 2026-11-14:** "run environments where no-regularizer does not reach desired behavior". The desired behaviour is to be corrected, then behave honestly.

## Cells

There are two cells: **Taxi** and **Boat Race**, with the **no-regulariser** variant (`g.use_regularization=False`, g fit for 1000 epochs as in all Step 4 runs). Each is run like the optimal campaign (docs/step4_optimal.md): PPO must reach its exact optimum. The exact target says what that optimum does after its correction; PPO shows that a trained agent actually ends there.

Two environments are left out:
- **MountainCar.** It is continuous. Its exact solves use a grid approximation (`mountain_car.dp_task`), which `experiments/step4_targets.py` and `step4_br.py` do not support: they need `task.tables`. Its failure (about 7 steps late) is also about the size of that approximation's error.
- **LunarLander.** It has no exact solve at all.

The swap is not run here, because the user asked for no-regulariser. Its Phase A optimum also fails in both cells (Taxi −39, Boat Race −76). The setting to add it is `VARIANTS` in the driver.

**Driver.** Every command runs with `CAMPAIGN=noreg_fail` in front: `CAMPAIGN=noreg_fail bash scripts/farmshare/step4_optimal.sh …`. Runs are `N1_P1eq1_<tag>` in `results/step4/<env>/noreg_fail/`. Targets are `results/step4/<env>/targets/P1eq1/seed<s>.json`.

## What is already known

**Taxi targets for seeds 0–2** exist from the hide-environment sweep (2026-11-10). They are the same game as these runs: `task.obs=onehot`, no regulariser, 1000 epochs. The `targets` command skips them and computes seeds 20–22. All three are **corrected in round 0, then true −78 to −81 in every later round** (honest 125). Seed 0's V0 is 11,668 against 1,794 for hiding. Boat Race has no target yet.

**Earlier PPO runs** used the frozen Step 3 configs on seeds 10–12 (`results/step4/<env>/ppo/S4_P1eq1_ep1000*`), with no convergence check:
- **Boat Race:** all 3 seeds are corrected once, then get true about −100.
- **Taxi:** seed 10 is corrected once, then gets true −99 to −150. Seed 11 never found the exploit, so it was never corrected (true −90).

So no run was checked against its exact optimum. That check is what this campaign adds.

## Pipeline

1. **Targets:** `CAMPAIGN=noreg_fail bash scripts/farmshare/step4_optimal.sh targets submit`. That is 2 jobs, for seeds 0–2 and 20–22.
2. **Wave 1:** `CAMPAIGN=noreg_fail bash scripts/farmshare/step4_optimal.sh wave1 submit`. That is 6 jobs on seeds 0–2: `L`, `LE` and `LN`, as in the optimal campaign's wave 1, each annealed over the last 25%. They start from the frozen Step 3 configs:
   - Taxi: `task.obs=onehot ppo.ent_coef=0.03`.
   - Boat Race: `ppo.ent_coef=0.03`.

   | Env | Wave-1 length | Why |
   |---|---|---|
   | Boat Race | 1536 episodes (4× Step 3's) | |
   | Taxi | 768 episodes (its frozen length) | A seed that exploits took 47 h for 768 episodes, because the PBRR fits dominate. Its runs will hit the 48 h limit, and rule 1 resumes them. |

3. **Everything after that** uses the commands of docs/step4_optimal.md, each with `CAMPAIGN=noreg_fail` in front.

## Verdict, criteria and decision rules

**They are identical to docs/step4_optimal.md:**
- The paired best-response gap ≤ 0.03 is CONVERGED.
- A cell is DONE at 3/3 tuning seeds plus 3/3 confirmation seeds. Extended confirmations count.
- Log in `docs/step4_noreg_fail_log.md`.

**Changes:**
- **Rule 2 (targets).** Log each cell's target as there, against the honest true return per round (Taxi 125, Boat Race 50), at the top of the log under "Exact predictions". Rule 2 already asks for its end state, true return by round, V0, V_hide and the per-draw end states. Say whether the optimum after its correction is honest, still uses the original bug, or is a new exploit (true clearly below honest with the window clean).
- **Rule 4 (caps).** Taxi 6144 episodes, Boat Race 12,288: 8× the wave-1 length.
- **Rule 6b (exploration).** Start it in a cell once every wave-1 run of that cell has a check and none is CONVERGED 3/3. Use the cell's run with the smallest mean gap as the base. The extension rule and stage 2 are as there.
- **Rule 8 (budget).** At most 20 queued or running jobs for this campaign.
- **Rule 9 (stop).** Stop when both cells are DONE or the user says stop. The final summary gives, for each cell:
  - the target's end state and true return by round, against honest;
  - the converged config and every seed's gap;
  - PPO's and the best response's true and received return by round;
  - whether PPO's behaviour after its correction is the new exploit (window clean, true below honest).

**Never** change environments, criteria or targets to get a hoped-for result.

## Prompt

The FarmShare loop prompt that runs this campaign together with the update-bonus campaign is in `docs/step4_loop_prompt.md`.
