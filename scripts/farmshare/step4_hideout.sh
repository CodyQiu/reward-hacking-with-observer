#!/bin/bash
# Step 4, the mentor's hideout grid (docs/step4_hideout.md): exact self-consistent targets (experiments/step4_targets.py)
# over the pre-registered sweep, hideout {near, mid, start} (1, 7, 13 steps from the exploit tile) x exploit bonus
# {100, 400, 1600}, for standard PBRR (base), no regulariser (P1eq1), the swap (P2swap) and the twin (indiff_twin: the
# converged twin, the target the indiff_twin2 PPO runs share). Seeds 0-2, and 20-22 at the PPO runs' setting (start, 100). Every command is a dry run unless its last
# argument is "submit". From the repo root on FarmShare:
#   bash scripts/farmshare/step4_hideout.sh submit_all [submit]   4 jobs, one per variant (27 targets each)
#   bash scripts/farmshare/step4_hideout.sh report                 the map, from whatever targets exist (no Slurm)
#   bash scripts/farmshare/step4_hideout.sh run <variant>          one variant's targets in this shell (what a job runs)
# Targets: results/step4/grid_hideout/targets/h<hideout>_b<bonus>_<variant>/seed<s>.json (existing seeds skipped).
# EXCLUDE=<nodes> keeps the jobs off broken nodes. The grid's 100-epoch g fit, as in every grid run.
set -euo pipefail
cd "$(dirname "$0")/../.."
CMD=${1:-help}; shift || true
LAST=${*: -1}; [[ ${LAST:-} == submit ]] && GO=1 || GO=0
SEEDS=(0 1 2)
VARIANTS=(base P1eq1 P2swap indiff_twin)
HIDEOUTS=("near 4 10" "mid 8 12" "start 0 0")      # = src/step3/tasks/grid_hideout.py HIDEOUTS
BONUSES=(100 400 1600)

vsets() {
  case $1 in
    base) echo "" ;;                                                     # standard PBRR (max1)
    P1eq1) echo "g.use_regularization=False" ;;
    P2swap) echo "g.l_minus_on=dispreferred" ;;
    indiff_twin) echo "g.fine_only=True g.offset=True g.offset_rule=twin" ;;
    *) echo "unknown variant $1" >&2; exit 1 ;;
  esac
}

case $CMD in
  run)
    v=$1; g=$(vsets "$v")
    for b in "${BONUSES[@]}"; do for h in "${HIDEOUTS[@]}"; do
      read -r name row col <<< "$h"
      seeds=("${SEEDS[@]}")
      [[ $name == start && $b == 100 ]] && seeds+=(20 21 22)   # the PPO runs' setting: also their confirmation seeds
      # shellcheck disable=SC2086
      .venv/bin/python -u experiments/step4_targets.py --env grid_hideout --name "h${name}_b${b}_$v" \
        --seeds "${seeds[@]}" --set task.h_row=$row task.h_col=$col task.exploit_bonus=$b $g
    done; done ;;
  submit_all)
    for v in "${VARIANTS[@]}"; do
      args=(bash scripts/farmshare/run_cmd.sh 6 4 "hideout_targets_$v" bash scripts/farmshare/step4_hideout.sh run "$v")
      if (( GO )); then "${args[@]}"; else [[ -n ${EXCLUDE:-} ]] && printf 'EXCLUDE=%s ' "$EXCLUDE"; printf '%q ' "${args[@]}"; echo; fi
    done ;;
  report)
    .venv/bin/python experiments/step4_hideout_map.py ;;
  *) sed -n 2,11p "$0" ;;
esac
