# Step 4 optimal-policy campaign: log

This log is append-only. The procedure, criteria and decision rules are in `docs/step4_optimal.md`. The newest entries are at the bottom; the two sections at the top are kept current.

## Flags for the user

- **Node barley-04 kills every job within 3–7 s** (2026-11-04, from 21:27). The batch step is cancelled with signal 53 and no `.out` file is written. Slurm still shows the node as idle, so it keeps scheduling jobs there. Our jobs avoid it via `ExcNodeList=barley-04` (see the iteration-1 review). Consider reporting it to FarmShare support; I have not contacted anyone.
  - **Every iteration:** check `sacct` for jobs that ended within a minute. When submitting new jobs, exclude barley-04 until it is fixed (submit behind a held gate job, then `scontrol update JobId=<id> ExcNodeList=barley-04`, then release the gate). This works around the node without changing code, since `submit.sh` has no way to pass `--exclude`.
- **I deviate from loop step 1: I pull with `git pull --no-rebase --no-edit --ff`, not `git pull --rebase --autostash`** (from 2026-11-04 22:40).
  - An autostash replaces every modified tracked file with a new file. A running worker writes its seed log through an open handle, so after the swap its log lines go to a deleted file and are lost (on NFS: "stale file handle").
  - This happened to 4 running seeds: taxi r2 P1eq1 s10, P2swapNoLplus s10 and s12; grid O1_P2swap_LN s2. Their results files are not affected, since those are written by path at every checkpoint.
  - A merge pull leaves such files alone. `step4_commit.sh` is fixed the same way (c5beacb, with a test).
  - **Suggest changing step 1 of the prompt in `docs/step4_optimal.md` accordingly.** I have not edited your prompt.
- **The Absent Supervisor swap optimum is not honest after its correction** (targets, 2026-11-04). After the one correction, the best route under the corrected reward is a true −50 route (true −100 in seed 2), not the honest route (true +450).
  - It is better by only a few percent of received return (seed 0: 1,998 vs 1,942 per round).
  - So a PPO run that plays honest after the correction would count as unconverged on the true-return gap (500 / 550 = 0.91 > 0.05), while a run that plays the −50 route would count as converged.
  - This follows from the pre-registered target and criteria, and I do not change them (loop rule 3). It does mean that, in this cell, "PPO reaches the optimum" and "the agent behaves after the correction" are different goals. Your call whether that changes what the cell should show.
- **Absent Supervisor no-regulariser, seed 21: the target's fixed point does not converge.** Over iterations 0–4 it alternates between 3 corrections per episode (V0 8,037) and 1 correction (V0 7,926). Per rule 2 the last iteration (3 corrections) is the target. Seed 21 is a confirmation seed, so this matters only once a confirmation run is made.

## Exact predictions (targets; the answer to the hypothesis)

| Cell | Target end state (6 seeds: 0–2, 20–22) | True return by round (k = 0..4) | V0 vs V_hide (margin) | 36 single draws |
|---|---|---|---|---|
| grid, swap (P2swap) | **corrected in round 0, then never again**, in all 6 seeds | −100, then +22 ×4 (= honest) | 177,886–218,956 vs 39,500 (138,386–179,456) | 36 the same; the fixed point converges in every seed |
| grid, no regulariser (P1eq1) | **never hides.** Corrected once (seeds 0, 2, 20, 21) or twice (seeds 1, 22), then honest | −100 (×1 or ×2), then +22 (= honest) | 171,310–185,847 vs 39,500 (131,810–146,347) | 0 hide; 13 corrected once, 15 twice, 8 three times; converges in every seed |
| absent_supervisor, swap (P2swap) | **corrected in round 0, then never again**, in all 6 seeds | −100, then **−50 ×4** (seed 2: −100 ×4); honest is +450 | 9,543–10,015 (seed 2: 47,139) vs 7,350 (2,193–2,665; seed 2: 39,789) | 36 the same; converges in every seed |
| absent_supervisor, no regulariser (P1eq1) | **never hides.** Corrected once (seed 1), twice (seeds 0, 20, 22) or three times (seeds 2, 21), then honest | −100, then 400 in each further corrected round, then +450 (= honest) | 7,706–8,733 vs 7,350 (356–1,383, i.e. 5–19%) | 1 of 36 hides (seed 1); the rest are corrected 1–4 times; seed 21 does not converge (flag) |

**What the targets say about the hypothesis so far** (exact optima; PPO is not involved):
- **Swap → "always-behaving".**
  - Grid: yes. The optimum takes one correction in round 0, then is honest.
  - Absent Supervisor: it takes one correction and never hides, but it is not honest afterwards (see the flag).
- **No regulariser → "a smart agent might avoid correction".**
  - Not on the grid or in Absent Supervisor. The optimum never hides; it *seeks* corrections, 1–3 per episode.
  - Each correction raises the received reward (grid seed 1: 8,700 → 38,583 → 46,188 per round), so a further correction can pay. Hiding is never optimal for the mean overseer, and for only 1 of 72 single draws across both environments.
  - In Absent Supervisor the margin over hiding is thin: 5–19% of V_hide.
- The swap's raise is very large on the grid: received return in rounds 1–4 is 42,297–52,564 per round, against 8,700 for exploiting. In Absent Supervisor seed 2 it is 11,397 per round, against 1,550.
- Tomato and tomato_large: their targets are still being computed.

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

## 2026-11-04 22:07, iteration 2 (the session was restarted inside tmux; the loop was restarted with the same prompt)

**Seen.**
- `phase_a_tomato_large` (1934127) COMPLETED in 43 min (exit 0, so all its acceptance checks passed).
- Its dependents are running: the three variant checks, the two tomato_large targets and the six tomato_large wave-1 runs. None are on barley-04.
- Targets COMPLETED: grid P2swap (7 min), grid P1eq1 (30 min), absent_supervisor P2swap (27 min) and P1eq1 (27 min). Still running: tomato ×2 and tomato_large ×2.
- No new failures: nothing ended within a minute, except the barley-04 jobs already logged.

**Rule 1 (resume).** Every campaign run has a job, so there is nothing to resume.

**Rule 2 (new targets).** grid P1eq1, absent_supervisor P2swap and absent_supervisor P1eq1 are logged under "Exact predictions" at the top.
- absent_supervisor P1eq1 seed 21: `fixed_point_converged` is false (iterations 0–4 alternate between end states "3 corrections" and "1 correction"). Per rule 2 the last iteration is the target; flagged.
- New flag: the absent_supervisor swap optimum is not honest after its correction.

**Rule 3 (finished runs).** None has finished.
- `bash scripts/farmshare/step4_optimal.sh report` (2 min) wrote verdicts for every run whose env has targets (grid and absent_supervisor). All seeds are still running, so these verdicts are early readings: IMPROVING or PLATEAU at episodes 24–1368.
- **To watch:** seed 1 of absent_supervisor is ABOVE TARGET in four runs: P1eq1_L (value gap −0.04), P1eq1_LN (−0.08), P2swap_L (−0.95) and P2swap_LN (−1.26).
  - PPO's received reward is up to 2.3× the target V0 (9,554 for P2swap seed 1).
  - One possible reason: the swap's raise depends on the rollouts the correction is fitted on. Target seed 2 shows how large it can get (11,397 per round, against about 2,000 in the other seeds), and PPO's round-0 play is not the optimum's.
  - Not acted on yet: per rule 3 the probe is for finished runs.
- **Speed:** absent_supervisor P2swap_LE is at episode 24 of 3072 after 17 min (about 36 h at that rate, but corrections should become rarer). The others are faster. A run that reaches the 48 h limit is resumed under rule 1.

**Rules 4–7.** Nothing is due. The budget is 38 campaign jobs queued or running (cap 60).

**Commit:** `bash scripts/farmshare/step4_commit.sh "..."`.

## 2026-11-04 ~22:20–22:45, iteration 2 continued: the commit helper's pull failed, and it had detached live logs

**Seen.**
- `step4_commit.sh` committed 4514df2, then its `git pull --rebase --autostash` stopped halfway ("cannot rebase: You have unstaged changes"). The autostash had reset the modified tracked files, and running jobs wrote to tracked files again before the rebase could continue.
- The repo was left mid-rebase, with the stash not reapplied.

**Diagnosis.**
- A scratch test showed that `git stash` replaces a modified file with a new inode. A process holding the old file open (a worker's stdout, i.e. its `seed<s>.log`) then writes to a deleted file (nlink 0), and its lines no longer reach the visible log.
- I checked every running worker on every node, with an overlapping step inside one of my own jobs on each node (`srun --jobid=<job> --overlap -n1 -c1 --mem=0 ...`; read-only). The check compared `stat -L /proc/<pid>/fd/1` with the log's inode.
  - **70 workers OK, 4 detached:** taxi `S4_P1eq1_ep1000_r2_s10_s12` s10, `S4_P2swapNoLplus_ep1000_r2_s10_s12` s10 and s12 (exactly the stashed files), and grid `O1_P2swap_LN` s2 (its log changed in the moment between the helper's `git add` and its pull).
  - Reading a detached log through the worker's handle fails with "Stale file handle". The NFS server has deleted the old file, so those 4 logs' lines after the swap cannot be recovered.
  - The workers are alive. NFS reports the error only when a write is flushed to the server, so a worker may exit with an error status at the end. It writes `metrics.json` before exiting, and the launcher, the readouts and the convergence report go by `metrics.json`. **The trained results are not affected:** `logs.npz`, the CSVs, the model and `progress.json` are written by path (atomic rename) at every checkpoint.

**Repairs.**
- `git rebase --quit`, which leaves the working tree as it is and moves the autostash to `stash@{0}` (kept, not applied, not dropped). Then `git push`.
- The rebase had left these files at their committed (older) versions. From `stash@{0}` I restored, to the working tree only, the 8 files the jobs had not rewritten since: taxi r2 P1eq1 s10's checkpoint (progress back to episode 384, from 360) and the three taxi logs up to 22:15. The other 10 had already been rewritten by their jobs at a newer checkpoint.
- **Fix:** `step4_commit.sh` now pulls with `git pull --no-rebase --no-edit --ff`, which never rewrites modified files it does not touch (c5beacb).
  - Test: the helper runs while an open handle is held on a modified tracked file, with a remote commit to merge. The test checks the same inode, the content, and both commits on the remote. It fails on the old helper and passes on the new one. `tests/test_step4.py`: 12 tests, 0 failed (Slurm).
  - I introduced this bug myself, in 930dc5c (I added `--autostash` to fix a pull that refused to run), and I used autostash pulls by hand in iteration 1.

**From now on.**
- I pull with `git pull --no-rebase --no-edit --ff`. This deviates from loop step 1; flagged at the top.
- At the end of each of the 4 affected runs, I'll check the parent's `seed <s> exit` lines and `metrics.json`, and log any nonzero exit together with this cause.
