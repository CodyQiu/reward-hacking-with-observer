# Step 4: an environment where the no-regulariser PBRR is avoided and the swap is not

Started 2026-11-10. Exact solves only; no PPO until the map below is filled in. Driver:
`scripts/farmshare/step4_hide.sh`. Map: `experiments/step4_hide_map.py`.

## The user's theory, as stated (2026-11-09)

> the swap "is the one we want over the no-regularizer… the no-regularizer might have potential to be exploited in
> certain environments, perhaps if it is complex enough… when the loss function raises the honest and fines the
> exploit, it is entirely possible for this to lower overall reward, leading to a smart enough agent to exploit
> that." Goal: an environment that shows this, and "hopefully conclude that the swap avoids this, hence, why swap
> is theoretically more valuable."

This is a hypothesis to test, not a rule.

## The condition being tested

- A correction must make the reference beat the agent's caught play by the exploit's advantage D. The no-regulariser
  fit can split that between raising the reference (a) and fining the agent (b). The swap pins g at 0 on the
  agent's own caught play, so b ≈ 0.
- After one correction, hiding is optimal when the best the agent can collect afterwards is worth less than
  hiding: roughly, the best round under the corrected reward is below the hide round under the proxy.
- Under the swap, exploiting openly still earns what it did before the correction, and that beats hiding. So the
  swap's optimum should never hide, as long as the pin holds on the open exploiter's path.
- Already known: the grid with the exact tabular fit makes no-regulariser hide (`results/step4/phase_a`). With the
  neural fit that PBRR uses, the network's raise spills far beyond the reference's transitions: at b = 100 the best
  round after one correction is ~43,000 (no-regulariser) and ~49,000 (swap), against an exploit round of 8,700.

## The sweeps (pre-registered 2026-11-10)

Each setting × variant (`P2swap` = `g.l_minus_on=dispreferred`, `P1eq1` = `g.use_regularization=False`) gets the
self-consistent exact target (`experiments/step4_targets.py`: 6 overseer draws per level, iterated to a fixed
point), on seeds 0–2. PBRR settings are those of each task's campaign (grid tasks: the grid's 100-epoch fit;
Taxi: 1000 epochs). Nothing else changes.

1. **Taxi**, as in Step 3 (re-arming pickup bonus 10). The reward model cannot tell a looping pickup from an honest
   one, so a fine on the loop also lands on honest pickups. Phase A (canonical corrections) already gives
   "corrected once, then not honest" for both variants (true −83 no-regulariser, −39 swap; honest +125).
2. **Grid, exploit bonus b ∈ {200, 400, 800, 1600, 3200}** (b = 100 is the campaign's existing targets).
   `task.exploit_bonus=b`. The exploit's advantage D grows with b; the fit's reach is set by its optimiser
   (100 Adam steps), so it need not grow with it.
3. **Routes grid, R ∈ {1, 2, 4} spokes × b ∈ {100, 400, 1600}** (`src/step3/tasks/grid_routes.py`). The exploit E
   is at the hub; each spoke has its own start (2 steps from E) and its own goal (5 steps from its start); every
   sub-episode starts at a random spoke. The reference (the hand-written rule, action noise 0.1) spends ~95 of its
   100 steps at its spoke's goal, so each goal's dwell appears in only 1/R of its rollouts, while the exploiter's
   dwell on E appears in all of them. With one shared goal (the Step 1 grid), the reference's long dwell is common
   to all its rollouts, so splitting only the walk would change little; that is why each spoke has its own goal.
   R ≤ 4 keeps every spoke the same length.

Exact reference values per round under the proxy (`a1` in each target file):

| Setting | Open exploit round | Hide round | V_hide (episode) | Honest round (true) |
|---|---|---|---|---|
| grid, b | −12 + 88(b − 1): 8,700 / 17,500 / 35,100 / 70,300 / 140,700 / 281,500 | 7,700 / 15,500 / 31,100 / 62,300 / 124,700 / 249,500 | 39,500 … 1,279,500 | 22 |
| routes, b = 100 / 400 / 1600 (any R) | 9,800 / 39,500 / 158,300 | 8,853 / 35,553 / 142,353 | 45,212 / 181,712 / 727,712 | 45 |

## What counts (decided before the results)

- **End state per seed** (`step4_hide_map.py: label`): `HIDES` (never corrected, final window exploited),
  `once->honest` (corrected in round 0, then true return in rounds 1–4 at least exploit + 0.8 × (honest − exploit)),
  `once->true x` (corrected once, then not honest), `n corr/ep` (corrected n times per episode: exploits openly or
  seeks corrections), `deterred`.
- **No-regulariser avoids correction at a setting** iff `P1eq1` is `HIDES` in ≥ 2 of 3 seeds.
- **The theory's prediction holds at a setting** iff, in addition, `P2swap` is not `HIDES` in any of its 3 seeds.
  The strongest version also has `P2swap` `once->honest`.
- The whole map is reported whatever it shows, including settings where neither variant hides or both do.

## Predictions (mine, from the b = 100 numbers, before any result)

- If the fits' raise stays near its b = 100 size, no-regulariser starts hiding at about b = 800, where its ~43,000
  best round falls below the hide round; the swap's open exploiter is never fined, so at those b it exploits openly
  and is corrected every round.
- A setting where no-regulariser hides *and* the swap is honest needs no-regulariser's collectable raise to be well
  below the swap's. At b = 100 it is not (43,000 vs 49,000), so the bonus sweep alone may not give one. The routes
  sweep is the attempt to shrink it.
- The swap is likely to keep exploiting openly wherever its raise cannot outbid the exploit. The claim this work can
  support is "the swap never rewards avoiding correction", not "the swap always gives honest play".

## Procedure (FarmShare)

1. `bash scripts/farmshare/step4_hide.sh submit_all` (dry run), then `EXCLUDE=barley-04 bash
   scripts/farmshare/step4_hide.sh submit_all submit`: 6 jobs named `hide_*`, ~1–3 h each.
2. When they finish: `bash scripts/farmshare/step4_hide.sh report`; paste the table under Results below, commit the
   targets and this doc, and flag the user. A failed job is reported, not resubmitted under the same name.
3. No PPO, no new knobs and no PBRR changes without the user. PPO comes later, only at settings where the two
   variants' exact answers differ.

## Results

(Pending.)
