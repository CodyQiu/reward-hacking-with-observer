# Step 4 optimal-policy campaign: log

This log is append-only. The procedure, criteria and decision rules are in `docs/step4_optimal.md`. The newest entries are at the bottom; the two sections at the top are kept current.

## Flags for the user

- None open.

## Exact predictions (targets; the answer to the hypothesis)

The targets are not computed yet: the target jobs are queued (2026-11-04).

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
