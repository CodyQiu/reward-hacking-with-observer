#!/bin/bash
# Commit and push the Step 4 optimal-policy campaign's results without bloating git (docs/step4_optimal.md):
# every call stages the small files (targets, exact checks, convergence reports and curves, configs, progress,
# seed logs, runs.csv, the campaign log); a seed's large checkpoint files (logs.npz, model.zip, the round CSVs)
# only once it has finished (metrics.json), because a running seed rewrites them every 24 episodes.
#   bash scripts/farmshare/step4_commit.sh "<commit message>"
set -euo pipefail
cd "$(dirname "$0")/../.."
MSG=${1:?commit message}
# one path at a time: a missing path (tomato_large before its Phase A) fails the whole git add
for p in docs/step4_optimal_log.md results/step3/tomato_large; do [[ -e $p ]] && git add -A "$p"; done
for env in grid absent_supervisor tomato tomato_large; do
  for d in results/step4/$env/targets results/step4/$env/phase_a; do [[ -d $d ]] && git add -A "$d"; done
  o=results/step4/$env/optimal; [[ -d $o ]] || continue
  [[ -f $o/runs.csv ]] && git add "$o/runs.csv"
  for r in "$o"/*/; do
    for f in overrides.json step4_convergence.json step4_convergence.png step4_probe.json; do
      [[ -f $r$f ]] && git add "$r$f"
    done
    for l in "$r"seed*.log; do [[ -f $l ]] && git add "$l"; done
    for s in "$r"seed*/; do
      [[ -d $s ]] || continue
      if [[ -f ${s}metrics.json ]]; then git add -A "$s"
      else for f in config.json progress.json; do [[ -f $s$f ]] && git add "$s$f"; done
           [[ -d ${s}code_snapshot ]] && git add -A "${s}code_snapshot"
      fi
    done
  done
done
if git diff --cached --quiet; then echo "nothing to commit"; exit 0; fi
git commit -q -m "$MSG" && git pull -q --rebase --autostash && git push -q && git log --oneline -1
