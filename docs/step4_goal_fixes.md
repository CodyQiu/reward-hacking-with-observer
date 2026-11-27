# Step 4 goal fixes: a single method that gives "corrected, then good behaviour"

Overnight investigation (from 2026-11-27 02:40), for the outcome-audit campaign (`docs/step4_goal.md`). The running campaigns are not touched. Exact targets only, no PPO.

**The goal (the user, as stated):** "our biggest gap is we want correction and then good behavior, which is what we were expecting for boat race and taxi (expecting good behavior under swap specifically) ... what we want to see is a single method (ideally smth like swap, or smth else) that leads to improved behavior (reaching the goal) after seeking a correction." And: "make sure it's not making changes so that it would be unfair, and it should adhere to our goals as much as possible."

**Fairness rules** (from the request, applied throughout):
- **Nothing in the setup changes:** environments, goals, hidden states, thresholds, protocol, criteria and defaults stay as they are.
- **One method, fixed settings,** applied unchanged to all five goal envs.
- **Only what PBRR already has:** the caught rollouts, the reference rollouts, the idealised labels and the reward model. No true reward, no bug or hidden-state location, no exact DP inside the method.
- **Predictions are written before each run.**
- **New code is opt-in,** with defaults identical to today's.
- **Feature changes are controls,** not fixes.

The summary sections below are kept current. The log below them is append-only.

## Status

- **Diagnosis:** code in, 10 jobs running (2029894–2029903). Boat Race seed 0 screening done (below).
- **Candidates:** C1 and C2 pre-registered below; their exact targets are submitted with this commit. C3 is pre-registered and waits for job slots.
- **Opt-in code:** `GConfig.reg_rows` / `unseen` / `unseen_post` (`src/pbrr_core.py`, `src/step3/pbrr.py`) and the Taxi `g_bit` control. Test: `test_goal_fix_options_are_opt_in_and_change_only_what_they_name`.

## Diagnosis (with numbers)

**1. An unanchored level cannot change which route is best (cause iii is ruled out for the route).** Every round is exactly T steps and γ = 1, so adding a constant c per step adds T·c to every round. The best route within a level is unchanged. The level only changes how much being corrected is worth across levels, i.e. whether a correction is sought. So "the best round is an exploit at every level" is not a level effect. A level-normalised fit (shift each correction so the reference's return is unchanged) would only remove the reason to seek a correction.

**2. Boat Race, one draw, seed 0, correction 1 under no-reg** (`experiments/step4_goal_diag.py`, the targets' iteration-0 chain; mean g per distinct reward-model row):
- **The caught play bounces on the top checkpoint.**
  - Its own step-back gets g = −5.0.
  - The top checkpoint's entry gets −5.7. That entry is aliased: an honest in-order entry is the same row, so honest laps are fined there too.
- **Every other row is raised.**
  - Rows only the reference uses: +7.4 to +8.3 (ordinary moves +8.3, entries +7.7).
  - The other checkpoints' step-backs, never seen: +7.8 and +9.0.
  - The hidden bottom checkpoint's step-back: +7.4. It is in the reference rollouts, so it is "seen" (point 4).
- **Effect:**
  - Level 1: the best round bounces on the left checkpoint (received 1,012, true −100), against honest play's 735.
  - Level 2: it bounces on the hidden one (1,103, true −82; honest 692).

**3. The data constrain only "reference ≻ caught play".** Bradley-Terry on hard labels has no finite optimum, so how far honest play is pushed above the exploit copies the data never show is set by optimisation length, not by the data.
- Boat Race arithmetic: a bounce pays +2 per step, honest racing +0.5.
- A correction that raises honest moves by r_m and entries by r_e, and leaves an unseen copy's step-back at 0, makes honest beat that copy only if 0.75 r_m − 0.25 r_e > 1.5, i.e. r_m > ~3.5 at the observed r_e ≈ 1.3 r_m.
- Screened fits raise honest moves by about 2 (table below).

**4. The reference itself takes the hidden exploit's transition** (counted on each seed's 19 reference rollouts):

| env | exploit-only transitions in the reference rollouts (seeds 0, 1, 2, 20, 21, 22) |
|---|---|
| Boat Race | 4, 6, 3, 5, 6, 4. Every seed includes the **hidden bottom checkpoint's step-back** (3–6 times); s20 and s22 also step back off the right or top one once. |
| Taxi | 0, 0, 0, 0, 1, 2. s21: one Y→R in-place dropoff; s22: Y→R and G→Y. |

So in Boat Race, any rule that treats reference transitions as preferred raises the hidden exploit's own transition.

**5. Screening on Boat Race seed 0** (2 draws, levels 1–3; the best round under the mean table of the iteration-0 chain). None makes honest play best at any level:

| fit | level 1 best round | level 2 best round | decode (correction 1, draw 0) |
|---|---|---|---|
| no-reg (today) | bounce left, 1,012 vs honest 735 | bounce bottom (hidden), 1,103 vs 692 | see 2 |
| swap (today) | bounce left, 468 vs 233 | bounce bottom (hidden), 754 vs 385 | ref rows +2.3–2.4; caught rows 0; unseen step-backs +1.1 / +3.5 |
| no-reg, unseen pulled to the caught mean inside the fit, held fixed (`unseen=pess`, first version) | received −12,326 | | **runaway:** g ≈ −145 everywhere. The pull has no anchor, and BCE is shift-invariant. Replaced. |
| no-reg, same, differentiable (`unseen=pess`) | bounce bottom, 534 vs 432 | bounce left, 891 vs 606 | the pull washes out the caught fine (+1.8 against +3.9 on moves) |
| swap + `unseen=pess` | bounce right, 402 vs 228 | bounce bottom, 582 vs 263 | unseen step-backs 0, ref rows +2.1 / +3.0: the raise is too small (point 3) |
| contrastive (`reg_rows=shared`) | bounce left, 422 vs 209 | bounce bottom, 371 vs 159 | caught step-back −1.0, ref rows +2.0 |
| contrastive + `unseen=pess` | bounce left, 336 vs 204 | bounce bottom, 338 vs 168 | |
| no-reg + `unseen=zero` | bounce left, 276 vs 76 | bounce bottom, 292 vs 39 | |
| swap + `unseen=zero` | bounce bottom, 385 vs 243 | raise farming, 3,445 (true −100, no exploit-only step) vs 562 | |
| **no-reg + `unseen_post=pess`** (C1) | bounce bottom, 904 vs 681 | raise farming, 1,062 (true −88) vs 761 | |
| **swap + `unseen_post=pess`** (C2) | bounce bottom, 589 vs 305 | raise farming, 3,580 vs 613 | |

**6. Boat Race, all seeds 0–2, 6 draws** (diagnosis jobs 2029894 and 2029898; the iteration-0 chain, so correction c is fitted on the best caught policy at level c−1). The best round under the mean table at levels 1–4, against honest play under the same table:

| method | seed 0 | seed 1 | seed 2 | single draws with honest play best |
|---|---|---|---|---|
| standard PBRR | bounce left, then hidden ×3 (gap to honest 137–144) | left, right, hidden ×2 | left, hidden ×3 | 0 / 72 |
| no-reg | left, hidden, right, raise farming (gap 328–445) | left, right, farming, farming (251–376) | left, hidden, right, farming (381–435) | 0 / 72 |
| swap | hidden, right, left, raise farming at 15,811 received (gap 218–15,549) | left, hidden, farming at 4,224, right | left, hidden, farming at 9,878, right | 0 / 72 |
| **control: no-reg, g also sees the lap index** (`task.g_index=True`) | left, hidden, **honest (true 44, goal met; gap 1)**, **honest (true 50; gap 3)** | left, hidden, right (gap 44), hidden round **2** below honest | left, hidden, **honest (true 50; gap 0)**, hidden round 5 below honest | 0 / 72 |
| control: swap, lap index | hidden, raise farming (4,351), left, right | same pattern | same pattern | 0 / 72 |
| control: standard, lap index | left, then hidden ×3 | same | same | 0 / 72 |

Decode of correction 1, mean over 6 draws (seed 0):
- **Standard PBRR** fines only the caught step-back (−9.4; the top copy −10.6). Every other row stays at 0.
- **No-reg:**
  - the caught step-back −3.7 and the aliased caught entry −3.2;
  - rows only the reference used +8.4 to +9.0;
  - never-seen step-backs +9.0, and the hidden one (seen in the reference) +8.4.
- **Swap:** caught rows 0; reference rows +2.3 to +4.4; the never-seen and hidden step-backs +2.5 / +2.8.

**What this says.**
- **No method's corrections, as they are, ever make honest play the best round**, at any level, in any seed or draw.
- **With the cell-only reward model, aliasing blocks the no-regulariser.** Once g can tell an in-order entry from a re-entry, the same no-regulariser corrections make the expected corrected reward's best round honest (or within 0–5 of it) after two or three corrections in all three seeds. The swap still farms its raise and standard PBRR still only fines.
- So in Boat Race, (i) aliasing is necessary for the no-regulariser's failure, and (ii) local repair sets how many corrections the fix takes (one per copy). That feature change is a control, not a fix: it changes what the overseer observes.

**Working diagnosis (Taxi still to be confirmed by the running jobs):** in Boat Race the failure is (ii) local repair with several exploit copies, compounded by (i) aliasing: the paying entry is an honest row, so it is raised with honest play or fined with it. On top of that, the reference rollouts take the hidden copy's step-back, so it counts as preferred. Once the copies are handled, the raise on reference rows creates new exploits: a round that shuttles over raised transitions the reference took by noise.

## Candidates

Each candidate is one `GConfig` setting, the same in all five envs. Sets: the goal targets' own variant words (`g.use_regularization=False` for no-reg, `g.l_minus_on=dispreferred` for the swap; `g.epochs=1000` in every env but the grid), plus the candidate's words. Seeds 0–2 first; 20–22 for any that look good.

### C1: no-reg + pessimistic extrapolation (`P1eq1_pess`: `g.use_regularization=False g.unseen_post=pess`)

- **What it changes.** After the usual no-regulariser fit, every reward-model row that no trajectory in the data contains gets one value t. t is the count-weighted mean g on the rows that only dispreferred trajectories contain (the caught play's own transitions). Rows in the data keep their fitted g. There is no free parameter.
- **Why.** A Bradley-Terry fit is silent about transitions it never saw; today the network's spill decides them, and it raises them with everything else (point 2). C1 extrapolates the evidence it has: "behaviour the data never shows is treated like the misbehaviour the data does show". So every copy of the exploit that needs a transition the data never show is fined like the caught one. No-reg keeps its raise on reference rows, so a correction still pays (the reason to seek one).
- **Fairness.**
  - It uses the caught rollouts, the reference rollouts, the labels and the reward model's own input domain (which rows exist), all things PBRR has.
  - It does not use the true reward, the bug's location or the hidden state's location, and has no DP inside it.
  - It is a strong prior: it also fines honest transitions the reference never took. This is stated, not hidden.
- **Predicted (2026-11-27 03:40, before any C1 target; the Boat Race seed 0 screening above was seen):**
  - grid: corrected in round 0, then honest, 3/3 (as no-reg).
  - Tomato: corrected in round 0, then honest, 3/3 (as no-reg).
  - AS: as no-reg on these seeds. s2 honest; s0, s1 still farm corrections (the farming route uses rows the reference takes, which C1 does not touch).
  - **Boat Race: fails, 0/3.** After the correction it exploits at the hidden checkpoint (whose step-back is in every seed's reference, so C1 leaves its raise) or farms raised reference rows.
  - **Taxi: corrected in round 0, then meets the goal near honest (true ≥ about 110), 3/3.** Seeds 0–2's references contain no loop dropoff, so every loop copy, depot B's included, is fined like the caught one, while honest pickups and deliveries keep the raise.

### C2: swap + pessimistic extrapolation (`P2swap_pess`: `g.l_minus_on=dispreferred g.unseen_post=pess`)

- **What it changes.** The same override after the swap's fit. Under the swap the caught play's rows are held near 0, so t ≈ 0. Unseen rows then get 0, not the network's spill.
- **Why.** It is the closest to the user's "ideally smth like swap". The swap pays a correction by raising the preferred trajectory; C2 stops that raise from spilling onto exploit copies the data never show.
- **Fairness:** as C1.
- **Predicted (before any C2 target):**
  - grid and Tomato: corrected, then honest, 3/3 (as the swap).
  - AS: s0 honest. For s1 and s2 (the swap exploits in hiding on a −50 route) there is no confident prediction: if that route's transitions are unseen, C2 removes their raise.
  - **Boat Race: fails, 0/3** (screening: the hidden copy at level 1, raise farming at level 2).
  - **Taxi: fails, 0/3.** A loop pays +4 per step, honest play about +1.25. With loop copies at 0 and pickups raised along with honest play, honest wins only if the swap's raise on honest rows exceeds about 5.5 per step. The data ask for less (point 3).

### C3: contrastive + pessimistic extrapolation (`contrast_pess`: `g.reg_rows=shared g.unseen_post=pess`, standard PBRR otherwise)

- **What it changes.** The user's contrastive idea. Standard PBRR's coefficient, but the regulariser covers only rows that occur in both trajectories of a pair (shared rows, pinned at 0, which also anchors the level). Rows exclusive to the caught play are free to be fined, rows exclusive to the reference free to be raised, and unseen rows get the C1 override.
- **Fairness:** as C1.
- **Predicted (before any C3 target):** in all five envs, a correction costs about what standard PBRR's does (the raise on reference-only rows is about 2 per step in the screening), so the optimum avoids correction where it can. It hides in grid, AS, Taxi and Boat Race, as standard PBRR does, and ends in the bucket in Tomato. That fails the user's goal ("after seeking a correction"); it is run because it is the user's suggestion.

### Reference point (set aside by the user): the indifference family

Fines only, plus a level payment for being corrected (the twin, `docs/step4_indiff.md`). Its exact targets on the base envs (not the goal envs): 27 of 30 honest by the end; no seed hides. Quoted only as a reference point. Nothing new was run.

## Ranked proposals for the user

(Pending the C1–C3 targets.)

## Open questions for the user

- **Should the reward model see progress features** (Boat Race's lap index, Taxi's picked-up bit)? In Boat Race that alone lets the no-regulariser's own corrections make honest play best after two or three corrections (Diagnosis 6). It changes what the overseer observes, so it is not done here; it is your call.
- **Boat Race's reference takes the hidden exploit's transition in every seed** (Diagnosis 4). Any method that trusts the reference raises that transition. Is a cleaner reference acceptable as part of the setup? That would change the setup, so it is not done here.

---

## Log

### 2026-11-27, iteration 1 (02:40–03:50)

- Read `docs/step4_goal.md` in full (including the control and the Taxi 6-delivery decision) and the top of `docs/step4_goal_log.md`. The running campaigns are not touched from here on.
- Code (opt-in; defaults unchanged, test `test_goal_fix_options_are_opt_in_and_change_only_what_they_name`):
  - `GConfig.reg_rows` ("traj" default | "shared"), `unseen` ("none" default | "zero" | "pess"), `unseen_rows`, `unseen_coef` (inside the fit, `src/step3/pbrr._fit_ext`, a separate compiled function so the default path is untouched).
  - `unseen_post` ("none" default | "pess"; `src/step3/pbrr.unseen_override`, applied to the correction table by `experiments/step4_targets.py`).
  - `game_key` drops the new fields at their defaults.
  - Taxi `g_bit` (default False; the aliasing control).
- `experiments/step4_goal_diag.py`: replays the targets' iteration-0 corrections with the same random streams and decodes them by transition type and by where each reward-model row was seen; best round per level and per draw.
- **Diagnosis jobs** (`bash scripts/farmshare/run_cmd.sh <h> 4 <name> .venv/bin/python -u experiments/step4_goal_diag.py ...`):
  - 2029894: Boat Race, seeds 0–2, base / no-reg / swap.
  - 2029895–97: Taxi, seeds 0 / 1 / 2.
  - 2029898: Boat Race `task.g_index=True` (aliasing control), seeds 0–2.
  - 2029899: Taxi `task.g_bit=True`, seed 0.
  - 2029900 / 2029901: Boat Race / Taxi seed 0 under seed 1's references (variance).
  - 2029902 / 2029903: Boat Race / Taxi seed 0 with `pbrr.k=50` (50 rollouts per side instead of 19; variance).
- Screening on Boat Race seed 0 done on the login node (table above). It changed the plan:
  - The in-fit pessimistic prior first ran away, then washed out the fine.
  - The post-fit override (C1, C2) is the version with no free parameter and no drift.
- **Taxi smoke test of C1 (seed 0, correction 1, one draw; launched before the C1 predictions were written, read after them). It contradicts the C1 Taxi prediction.**
  - **The caught play loops at many depot/destination pairs.** Its in-place dropoffs get g = −19.4. The aliased legal pickups it used get −22.1, and honest pickups are the same rows. Ordinary moves are raised by +23 to +33, deliveries by +10 to +18.
  - **Under no-reg as it is**, the best round after the correction is not a loop: it farms the raised moves (no exploit-only step, true −95.7, received 3,279 against honest play's 2,722).
  - **Under C1** the same holds (true −87.2, received 3,209 against honest 2,539). The override also sets the 1,079 move rows no trajectory showed to the caught fine, and honest routes use some of them.
  - So in Taxi the dominant failure at level 1 is the raise creating a new exploit, together with aliasing (honest pickups fined with the loop's). The C1 Taxi prediction stands as written; the full targets decide.
  - **Tooling caveat:** the diagnostic's decode shows g before the override; the best-round numbers use the overridden table.

### 2026-11-27, iteration 2 (03:48–04:10)

- All investigation jobs were pending on Priority (the cluster is full; our running campaigns hold much of the fair share). From 03:30 they start one by one.
- **Landed:**
  - 2029894 (Boat Race diagnosis, seeds 0–2; 11.6 min) and 2029898 (the `g_index` control; 11.5 min).
  - Table in Diagnosis 6. No method makes honest play best at any level, in any seed or draw. With the lap index, no-reg's mean-table best round becomes honest after 2–3 corrections in all three seeds.
- **Submitted C3** (`contrast_pess`, pre-registered in iteration 1) once slots allowed:
  - 2030009: grid, AS, Boat Race and Tomato, seeds 0–2, one job;
  - 2030010–12: Taxi seeds 0 / 1 / 2.
  - Same commands as C1 / C2 with `--set g.reg_rows=shared g.unseen_post=pess` (+ `g.epochs=1000` outside the grid).
- 20 investigation jobs queued or running (the cap).
