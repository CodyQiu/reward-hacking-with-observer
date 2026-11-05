# Step 4 optimal-policy campaign: log

This log is append-only. The procedure, criteria and decision rules are in `docs/step4_optimal.md`. The newest entries are at the bottom; the two sections at the top are kept current.

## Flags for the user

- **Node barley-04 kills every job within 3–7 s** (2026-11-04, from 21:27). The batch step is cancelled with signal 53 and no `.out` file is written. Slurm still shows the node as idle, so it keeps scheduling jobs there. Our jobs avoid it via `ExcNodeList=barley-04` (see the iteration-1 review). Consider reporting it to FarmShare support; I have not contacted anyone.
  - **Every iteration:** check `sacct` for jobs that ended within a minute. When submitting new jobs, exclude barley-04 until it is fixed (submit behind a held gate job, then `scontrol update JobId=<id> ExcNodeList=barley-04`, then release the gate). This works around the node without changing code, since `submit.sh` has no way to pass `--exclude`.

## Exact predictions (targets; the answer to the hypothesis)

| Cell | Target end state | True return by round (k = 0..4) | V0 / V_hide (margin) | Draws |
|---|---|---|---|---|
| grid, swap (P2swap) | **corrected in round 0, then never again** (1.00 correction per episode), in all 6 seeds (0–2, 20–22) | −100, then +22 ×4 (= honest) | V0 177,886–218,956 vs V_hide 39,500 (margin 138,386–179,456) | 36 of 36 single draws give the same end state; the fixed point converges in every seed (after 1 iteration) |

- **Grid, swap.** The exact optimum does not hide. It exploits in view in round 0, takes the one correction, and then behaves for the rest of the episode. This is what the hypothesis predicts for the swap.
- The swap's raise is very large: received return in rounds 1–4 is 42,297–52,564 per round, against 8,700 for exploiting and 22 true. Never being corrected is worth 18–22% of the optimum's episode value (V_hide / V0).
- The other 7 cells are still being computed.

---

## 2026-11-04, iteration 1 (first iteration)

**Seen.**
- HEAD was b095a3a (the campaign commit), and `docs/step4_optimal_log.md` did not exist yet, so this is the first iteration.
- Still running: the Taxi and MountainCar `*_r2_*` jobs from 2026-11-03 (1928834–6, 1928838). The other four r2 jobs had completed. Per rule 7, I touched none of them.

**Tests.** `.venv/bin/python tests/test_step4.py` ran as Slurm job 1934126: 10 tests, 0 failed.

**Phase A (tomato_large).**
- `bash scripts/farmshare/step4_optimal.sh phase_a submit` submitted Phase A as **PHASEA_JOB = 1934127**, plus the three variant checks (1934128–30).
- The variant checks went in without a dependency, because PHASEA_JOB was not set yet. They read Phase A's `summary.json`, so they would have crashed. Rerunning `phase_a submit` would also have submitted a second Phase A.
- So I cancelled 1934128–30, about 1 min after they started (they had written nothing but empty output directories). I resubmitted them with `DEPENDENCY=afterok:1934127 bash scripts/farmshare/run_cmd.sh 12 4 phase_a_tomato_large_<variant> .venv/bin/python -u experiments/step3_check.py --env tomato_large --variant <variant> --g-set <...>`, for each of `P2swap_ep1000`, `P2swapNoLplus_ep1000` and `P1eq1_ep1000`. The new job ids are 1934135–7.
- **Process note.** The first `phase_a submit` should itself wait for Phase A. Since it can't know the id beforehand, the fix belongs in the driver (submit Phase A, capture its id, then submit the variants). That is not a bug fix, so I'm only noting it here.

**Targets.**
- Command: `PHASEA_JOB=1934127 bash scripts/farmshare/step4_optimal.sh targets submit`, after a dry run.
- It covers 4 envs × {P2swap, P1eq1}, seeds 0 1 2 20 21 22, as jobs 1934141–8. The tomato_large ones (1934147–8) wait on 1934127.

**Wave 1.**
- The first `PHASEA_JOB=1934127 bash scripts/farmshare/step4_optimal.sh wave1 submit` submitted **nothing** and exited 1 with no message.
- **Bug** in `scripts/farmshare/submit.sh` (from b095a3a): `job=...$( (( resume )) && echo "_resume..." ).sh`. With resume = 0 the command substitution's status 1 becomes the assignment's status, and `set -e` ends the script before `sbatch`. Every fresh (non-resume) submit was affected; the r2 jobs of 2026-11-03 were submitted before this change.
- Fixed in bf52fba, with the regression test `test_submit_sh_submits_fresh_and_resumed_runs` (a stub `sbatch`; fresh submit, `--resume`, and both directory guards). The test fails on the old script and passes on the new one, and `tests/test_step4.py` gives 11 tests, 0 failed (Slurm).
- While debugging, one probe call ran `submit.sh` for real (`O1_test_dryprobe`). It exited at the same bug, so it submitted no job and wrote no run directory.
- Resubmitted: `PHASEA_JOB=1934127 bash scripts/farmshare/step4_optimal.sh wave1 submit`, after a dry run. The 24 runs O1_{P2swap,P1eq1}_{L,LE,LN} × 4 envs, seeds 0–2, are jobs 1934154–1934178. The tomato_large ones wait on 1934127.
- In the LE configs, `ppo.ent_coef` is listed twice (frozen, then 3×). `parse_sets` keeps the last value, so the 3× value applies.

**Budget.** 24 wave-1 jobs, 8 targets and 4 Phase A jobs: 36 campaign jobs, within the cap of 60.

**Next.** Wait for Phase A and the targets. As soon as each target lands, write "Exact predictions".

**Later in iteration 1: a second fix, and the r2 results.**
- **Bug** in `scripts/farmshare/step4_commit.sh`. `git add -A docs/step4_optimal_log.md results/step3/tomato_large 2>/dev/null || true` fails as a whole while `results/step3/tomato_large` does not exist, so 7e3a68c committed the wave-1 run files but **not this log**. Also, its `git pull --rebase` refused while a running job had modified a tracked `runs.csv`.
- The fix adds each path only if it exists and pulls with `--autostash`. Test: `test_step4_commit_sh_commits_the_log_before_tomato_large_exists` (a scratch clone with a bare remote). It fails on the old script and passes on the new one, and `tests/test_step4.py` gives 12 tests, 0 failed (Slurm).
- **Not part of the campaign:** the taxi, mountain_car and lunar_lander `*_r2_*` readouts are committed (1955b4d), per the user's 2026-11-03 instruction (every ~12 h).
  - All the MountainCar runs that finished have 0 corrections.
  - In Taxi, P2swapNoLplus seeds 10 and 12 at checkpoints 432 and 696 meet R1–R3 but not R4: true return after the first correction is −93 / −68.
- The first grid target (P2swap seed 0, then seed 1) has already landed. "Exact predictions" will be filled in once each cell has all six seeds.

## 2026-11-04 ~21:50, review of iteration 1 (the user asked me to recheck my work)

**Error: 11 of the 24 wave-1 jobs had failed and I had not noticed.**
- Jobs 1934161–4 and 1934166 (absent_supervisor O1_P2swap_LE, O1_P2swap_LN, O1_P1eq1_{L,LE,LN}) and 1934167–72 (all six tomato O1 runs) all ended FAILED, ExitCode 0:53, 7 s after starting at 21:27:22.
- All 11 were on **barley-04**. None wrote a Slurm `.out` file or a run directory.
- I had counted the queue right after submitting (24 jobs) and reported "24 runs", but never checked again.
- A diagnostic job pinned to barley-04 (1934251, `-w barley-04`, it only runs `hostname` and an import test) failed the same way in 3 s with no output. So the node is broken; this is not our code.

**Resubmitted** the same 11 runs under the same run ids. No directory existed for any of them, so nothing is overwritten, and the driver's `report`, `resume`, `extend` and `confirm` expect these names.
- I took their exact commands from the wave-1 dry run (`PHASEA_JOB=1934127 bash scripts/farmshare/step4_optimal.sh wave1`, filtered to the 11 runs) and submitted each as `DEPENDENCY=<gate> bash scripts/farmshare/submit.sh 48 ...`.
- The gate, `sbatch --hold --exclude=barley-04 --wrap true` (1934255), kept the new jobs pending. Meanwhile `scontrol update JobId=<id> ExcNodeList=barley-04` went on the 11 new jobs (1934256–66) and on the 11 pending tomato_large jobs (1934135–7, 1934147–8, 1934173–8). Then `scontrol release 1934255`.
- All 11 started on wheat-04/07, barley-03 and rye-01/02. One minute later they were still running and had written their run directories.
- I checked the effective configs (`seed0/config.json`):
  - LE runs have 3× entropy (absent_supervisor 0.3, tomato 0.1, grid 0.03);
  - LN runs have n_envs 64 and batch 1600;
  - the grid keeps 100 g-fit epochs, the others 1000;
  - episodes are 3072 (absent_supervisor) and 1536 (others), with annealing over the last 25% to 0.1×.

**Other checks.** No other problems found.
- The 13 wave-1 jobs that had survived are progressing (grid ×6 and absent_supervisor O1_P2swap_L).
- The target jobs are running. `targets_grid_P2swap` completed in 7 min with `fixed_point_converged` true in all 6 seeds (see "Exact predictions").
- The three tomato_large variant checks were resubmitted into existing empty folders. `step3_check.py` uses `makedirs(exist_ok=True)` and `_keep_previous`, so they will not fail on them.
- Dry runs of `resume`, `extend grid O1_P1eq1_L 3072` and `confirm grid O1_P1eq1_L` produce correct commands. `run_sets.py` takes the run's final episode count and annealing.
- `report` hides `step4_convergence.py`'s errors (`2>/dev/null || true`). Run by hand on `grid/optimal/O1_P2swap_L`, it works: all 3 seeds are IMPROVING at episodes 72–144.
- No other `$( (( … )) && … )` construct is left in `scripts/farmshare/*.sh`.
- The regression test for `step4_commit.sh` now sets the scratch clone's upstream explicitly (`push -u`) and disables commit signing, so it does not depend on the machine's git defaults. `tests/test_step4.py`: 12 tests, 0 failed (Slurm).

**Also corrected in `docs/step3_tuning_log.md`.** My Tomato T3c entry said seed 21's 384-episode prefix "was not bit-identical". That was a guess, and it is wrong: all 10 seeds, and Taxi's 3, have bit-identical prefixes. Seed 21 changed from deterred to reactive during episodes 384–768. I also fixed two small wording and time errors there.

**Loop note.** The user ran `/exit` after the 22:16 wakeup had been scheduled. I re-arm the wakeup at the end of this review.
