# FarmShare loop prompt (from 2026-11-14)

This one `/loop` prompt runs two campaigns in one FarmShare Claude session:
- the update-bonus campaign (`docs/step4_bonus.md`);
- the no-regulariser failure campaign (`docs/step4_noreg_fail.md`).

It replaces the optimal campaign's prompt (`docs/step4_optimal.md`, "Prompt"). That campaign is paused: its running jobs finish on their own.

```
/loop You are running two Step 4 campaigns of this repo (~/reward-hacking-with-observer) on Stanford FarmShare. Read CLAUDE.md (§4f, §6 FarmShare), docs/step4_bonus.md, docs/step4_noreg_fail.md and docs/step4_optimal.md before doing anything. The two campaign docs are the source of truth for their campaigns; docs/step4_optimal.md supplies the criteria, decision rules and commands they refer to, as changed by each campaign doc. Follow them exactly.

The campaigns:
(A) CAMPAIGN=bonus: the mentor's update bonus (protocol.update_bonus=1.0: +1 received reward every time the reward function is updated), 12 cells: grid, absent_supervisor, tomato, tomato_large x swap (P2swap), no-regulariser (P1eq1), standard PBRR (base). Log: docs/step4_bonus_log.md.
(B) CAMPAIGN=noreg_fail: no-regulariser PBRR (P1eq1) in the environments where its exact optimum is not the desired behaviour (corrected, then honest): taxi and boat_race, 2 cells. Log: docs/step4_noreg_fail_log.md.
Goal in both: PPO must reach (almost exactly) its exact optimum, i.e. be within 3% of the best response to the corrections its own play induces (experiments/step4_br.py, the verdict); the self-consistent targets (experiments/step4_targets.py) give the exact end states and are the answer to report. Keep tuning (extend / ppo / explore, rule 6b) until every cell has a config CONVERGED in 3/3 tuning seeds and 3/3 fresh confirmation seeds; never close a cell as a finding.

EVERY scripts/farmshare/step4_optimal.sh command you run starts with CAMPAIGN=bonus or CAMPAIGN=noreg_fail (plus EXCLUDE=<broken nodes> while a node is broken). A command without CAMPAIGN= acts on the paused optimal campaign (results/step4/*/optimal): never run one; no resume, extend, confirm, checks or new runs there. Don't cancel any job you did not submit.

Each iteration:
0. If docs/step4_bonus_log.md does not exist yet, this is the first iteration: git pull --no-rebase --no-edit --ff; run `.venv/bin/python tests/test_step4.py` (all must pass); for each campaign dry-run, check, then submit `CAMPAIGN=<c> bash scripts/farmshare/step4_optimal.sh targets submit` and `CAMPAIGN=<c> bash scripts/farmshare/step4_optimal.sh wave1 submit` (bonus: 12 target jobs + 20 runs; noreg_fail: 2 target jobs + 6 runs; Taxi's existing seed 0-2 targets are skipped, not overwritten). Create both logs (append-only: date, what you saw, what you decided, the exact commands, job ids; keep "Flags for the user" and "Exact predictions" current at the top of each) and commit.
1. git pull --no-rebase --no-edit --ff (never --rebase or --autostash); squeue -u $USER; `CAMPAIGN=bonus bash scripts/farmshare/step4_optimal.sh report` and `CAMPAIGN=noreg_fail bash scripts/farmshare/step4_optimal.sh report`.
2. For each campaign, apply the decision rules in order: resume (runs stopped by the 48 h time limit), new targets, best-response checks (`CAMPAIGN=<c> ... br_missing submit`), finished runs (confirm / extend / plateau), wave 2, wave 3, exploration (6b), budget (bonus <= 60 jobs, noreg_fail <= 20, and all your jobs together <= 110 of the 128 allowed). Always dry-run a command (omit "submit") and check it before submitting. Log every decision and command in that campaign's log.
3. As soon as a target is computed, write it at the top of its log under "Exact predictions": bonus, with the no-bonus comparison for swap and no-reg (same seed, results/step4/<env>/targets/<variant>/) and whether base hides; noreg_fail, against honest (Taxi 125, Boat Race 50) and whether the behaviour after the correction is honest, the original bug, or a new exploit. These are the answers; never adjust environments, criteria, the bonus or targets to get a hoped-for result.
4. Commit with `bash scripts/farmshare/step4_commit.sh "<short message>"` (never git add running seeds' checkpoint files by hand; never overwrite or delete a run).
5. If something is broken (a job crashes, a script errors, a fixed point does not converge, a check fails), log it with the error text, fix only what is clearly a bug (commit the fix with a test), and otherwise flag it at the top of the log for the user instead of improvising. If a job fails or is killed by a cluster incident (not the 48 h limit), flag it for the user and don't resubmit it without the user.
Pace: wake every ~45 min while jobs run (~2 h when only long runs remain). Stop when every cell of both campaigns is DONE or the user says stop, after writing each campaign's final summary at the top of its log.
```
