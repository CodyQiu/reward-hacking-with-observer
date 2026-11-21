# FarmShare loop prompt (from 2026-11-21)

This one `/loop` prompt runs every active Step 4 campaign in one FarmShare Claude session. It replaces the 2026-11-16 prompt (bonus, noreg_fail, comp), to which the indifference campaigns had been added by message. If the old loop is still running, stop it first; this prompt picks up where it left off (the last pushed iteration was indiff 104 / comp 128, 2026-11-18 15:02).

What changed on 2026-11-21:
- **New: `CAMPAIGN=indiff_twin2`,** the twin trained and priced at every correction level (`docs/step4_indiff.md`, "The twin at every level"). It supersedes `indiff_twin`.
- **New: `CAMPAIGN=hideout`,** the mentor's hideout grid (`docs/step4_hideout.md`): an exact sweep plus PPO wave 1.
- **Superseded campaigns** (`indiff_twin`, `indiff_pool`, `indiff_mean`, `indiff`, `comp`) get no new runs. Their running jobs finish and their finished seeds are checked.

```
/loop You are running the Step 4 campaigns of this repo (~/reward-hacking-with-observer) on Stanford FarmShare. Read CLAUDE.md (§4f, §6 FarmShare), docs/step4_optimal.md (criteria, decision rules, commands), docs/step4_indiff.md (especially "The twin" and "The twin at every level"), docs/step4_hideout.md, docs/step4_bonus.md and docs/step4_noreg_fail.md before doing anything. The campaign docs are the source of truth for their campaigns; docs/step4_optimal.md supplies the criteria, decision rules and commands they refer to. Follow them exactly.

Campaigns, in priority order for job slots (all your jobs together <= 110 of the 128 allowed; when slots are short, fill them in this order):
1. CAMPAIGN=indiff_twin2 (new): the twin trained and priced at every correction level (twin.all_levels=True). Two arms, I5_indiff_twin2_* and I5_indiff_twin2_practice_*, all six envs, treated as separate cells that share the indiff_twin targets (results/step4/<env>/targets/indiff_twin/). Budget <= 50 jobs. Log: docs/step4_indiff_log.md, in a new indiff_twin2 table.
2. CAMPAIGN=hideout (new): the mentor's hideout grid (env grid_hideout). The exact sweep is scripts/farmshare/step4_hideout.sh (4 target jobs); PPO wave 1 is the default setting (12 runs). Budget <= 24 jobs. Log: docs/step4_hideout_log.md (create it).
3. CAMPAIGN=bonus (<= 60) and CAMPAIGN=noreg_fail (<= 20): continue under their docs' rules.
4. Superseded: CAMPAIGN=indiff_twin, indiff_pool, indiff_mean, indiff and comp. Let their running jobs finish; run best-response checks of their finished seeds (br_missing) and indiff_twin's remaining tomato_large targets, and record them in their logs. Submit nothing else there: no new runs, extensions, confirmations or resumes.
The optimal campaign stays paused. EVERY scripts/farmshare/step4_optimal.sh command you run starts with CAMPAIGN=<campaign> (plus EXCLUDE=barley-04,wheat-06, or whatever nodes are broken now). A command without CAMPAIGN= acts on the paused optimal campaign: never run one. Don't cancel any job you did not submit.

First iteration:
a. git pull --no-rebase --no-edit --ff; run `.venv/bin/python tests/test_step4.py` (must be 50/50) and `.venv/bin/python tests/test_step3.py` (13/13).
b. squeue -u $USER and sacct for the last 3 days. Bring every log up to date with what finished since the last commit: run the missing checks (`CAMPAIGN=<c> ... br_missing submit` for every campaign with finished seeds, within the priorities), resume the bonus/noreg_fail/indiff_twin2/hideout runs stopped by the 48 h limit (`CAMPAIGN=<c> ... resume submit`; not the superseded campaigns), and commit.
c. Dry-run, check, then submit:
   - `CAMPAIGN=indiff_twin2 EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh wave1 submit`: 36 runs. Submit the 6 Taxi runs first; if slots are short, submit the rest as they free up, before anything of lower priority.
   - `EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_hideout.sh submit_all submit`: 4 target jobs.
   - `CAMPAIGN=hideout EXCLUDE=barley-04,wheat-06 bash scripts/farmshare/step4_optimal.sh wave1 submit`: 12 runs.
d. Create docs/step4_hideout_log.md (append-only: date, what you saw, what you decided, the exact commands, job ids; keep "Flags for the user" and "Exact predictions" current at the top) and commit.

Each iteration:
1. git pull --no-rebase --no-edit --ff (never --rebase or --autostash); squeue -u $USER; `CAMPAIGN=<c> bash scripts/farmshare/step4_optimal.sh report` for indiff_twin2, hideout, bonus and noreg_fail.
2. Apply docs/step4_optimal.md's decision rules in order to indiff_twin2, hideout, bonus and noreg_fail: resume (runs stopped by the 48 h limit), best-response checks (`br_missing`), finished runs (confirm / extend / plateau), wave 2, wave 3, exploration (6b), budget. Always dry-run a command (omit "submit") and check it before submitting. Log every decision and command, with job ids, in that campaign's log.
3. indiff_twin2: for every check, record in its table the gap and verdict, PPO's corrections and true by round, and the best response's corrections. Note whether the best response still takes extra corrections under the run's own twin (the flaw this campaign fixes), against the same env/arm/config row of indiff_twin. For Taxi also record PPO's deliveries per round after one correction (`.venv/bin/python experiments/step4_level_play.py "<run>/seed*"`; honest 7.1). Check that each run's seed directories hold twin_state.json with trained_top = 4 once it has trained a few blocks; if not, flag it.
4. hideout: when the sweep's targets are in, paste `bash scripts/farmshare/step4_hideout.sh report` under "Exact predictions" in docs/step4_hideout_log.md, compare it with the predictions in docs/step4_hideout.md, and flag the result for the user (it answers the mentor's question). Wave 2 is automatic, as the doc says: for each setting where no regulariser is not honest by the end in some seed (at most 3 settings), submit its no-regulariser PPO at that setting (tags h<hideout>_b<b>_L / _LE / _LN, with the doc's --set words).
5. Commit with `bash scripts/farmshare/step4_commit.sh "<short message>"` (never git add running seeds' checkpoint files by hand; never overwrite or delete a run).
6. If something is broken (a job crashes, a script errors, a fixed point does not converge, a check fails), log it with the error text, fix only what is clearly a bug (commit the fix with a test), and otherwise flag it at the top of the log for the user instead of improvising. If a job fails or is killed by a cluster incident (not the 48 h limit), flag it for the user and don't resubmit it without the user. Never change environments, settings, criteria, mechanisms or targets to get a hoped-for result; never close a cell as a finding: keep tuning (extend / ppo / explore, rule 6b) until every cell has a config CONVERGED in 3/3 tuning and 3/3 confirmation seeds.
Pace: wake every ~45 min while jobs run (~2 h when only long runs remain). Stop when every cell of the active campaigns is DONE or the user says stop, after writing each campaign's summary at the top of its log.
```
