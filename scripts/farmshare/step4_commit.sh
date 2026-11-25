#!/bin/bash
# Commit and push the Step 4 campaigns' results without bloating git (docs/step4_optimal.md, step4_bonus.md,
# step4_noreg_fail.md, step4_comp.md, step4_indiff.md, step4_hideout.md):
# every call stages the small files (targets, exact checks, convergence reports and curves, best-response checks,
# configs, progress, seed logs, runs.csv, the campaign log); a seed's large checkpoint files (logs.npz, model.zip,
# the round CSVs) only once it has finished (metrics.json), because a running seed rewrites them every 24 episodes.
#   bash scripts/farmshare/step4_commit.sh "<commit message>"
set -euo pipefail
cd "$(dirname "$0")/../.."
MSG=${1:?commit message}
# finished = metrics.json in the seed's directory listing (the glob reads it). Not [[ -f ]]: a resumed seed renames
# metrics.json to metrics_ep<N>.json, and on the NFS home the login node can keep the old name's cached dentry for
# many minutes, so -f stays true while the seed trains and its checkpoints were committed (2026-11-15,
# docs/step4_bonus_log.md iteration 108). The listing is current.
finished() { local f; for f in "${1%/}"/*; do [[ ${f##*/} == metrics.json ]] && return 0; done; return 1; }
# one path at a time: a missing path (tomato_large before its Phase A) fails the whole git add
for p in docs/step4_optimal_log.md docs/step4_bonus_log.md docs/step4_noreg_fail_log.md docs/step4_comp_log.md \
         docs/step4_indiff_log.md docs/step4_hideout_log.md docs/step4_goal_log.md \
         results/step3/tomato_large; do
  [[ -e $p ]] && git add -A "$p"; done
for env in grid absent_supervisor tomato tomato_large taxi boat_race grid_hideout \
           grid_goal absent_supervisor_goal tomato_goal taxi_goal boat_race_goal; do
  for d in results/step4/$env/targets results/step4/$env/phase_a; do [[ -d $d ]] && git add -A "$d"; done
  for o in results/step4/$env/optimal results/step4/$env/bonus results/step4/$env/noreg_fail results/step4/$env/comp \
           results/step4/$env/indiff results/step4/$env/indiff_pool results/step4/$env/indiff_mean results/step4/$env/indiff_twin \
           results/step4/$env/indiff_twin2 results/step4/$env/indiff_twin3 results/step4/$env/hideout results/step4/$env/goal; do
  [[ -d $o ]] || continue
  [[ -f $o/runs.csv ]] && git add "$o/runs.csv"
  for r in "$o"/*/; do
    for f in overrides.json step4_convergence.json step4_convergence.png step4_probe.json; do
      [[ -f $r$f ]] && git add "$r$f"
    done
    [[ -d ${r}step4_br ]] && git add -A "${r}step4_br"
    for l in "$r"seed*.log; do [[ -f $l ]] && git add "$l"; done
    for s in "$r"seed*/; do
      [[ -d $s ]] || continue
      if finished "$s"; then git add -A "$s"
      else for f in config.json progress.json; do [[ -f $s$f ]] && git add "$s$f"; done
           [[ -d ${s}code_snapshot ]] && git add -A "${s}code_snapshot"
      fi
    done
  done
  done
done
# GitHub rejects any file over 100 MiB (GH001) and then refuses the whole push; a finished 12,288-episode run
# with 256 envs wrote a 115 MiB logs.npz (2026-11-17, docs/step4_bonus_log.md). Leave such files out, say so.
MAX_BYTES=$((99 * 1024 * 1024))
while IFS= read -r -d '' f; do
  if (( $(git cat-file -s ":$f") > MAX_BYTES )); then
    git reset -q -- "$f"; echo "not committed (over 99 MiB; GitHub rejects files over 100 MiB): $f" >&2
  fi
done < <(git diff --cached --name-only -z --diff-filter=AM)
if git diff --cached --quiet; then echo "nothing to commit"; exit 0; fi
# pull by merge, never by rebase/autostash: a stash replaces every modified tracked file with a new inode,
# and a running worker keeps writing its seed log through the old (deleted) one, so its log is lost.
# A merge leaves modified files it does not touch alone, and refuses before touching one it would change.
git commit -q -m "$MSG" && git pull -q --no-rebase --no-edit --ff && git push -q && git log --oneline -1
