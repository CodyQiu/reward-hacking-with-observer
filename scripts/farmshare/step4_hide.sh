#!/bin/bash
# Step 4: is there an environment where the no-regulariser PBRR's optimum avoids correction and the swap's does
# not? Exact self-consistent targets (experiments/step4_targets.py) over pre-registered knobs; plan, criteria and
# predictions in docs/step4_hide_env.md. No PPO. Every command is a dry run unless its last argument is "submit".
# From the repo root on FarmShare:
#   bash scripts/farmshare/step4_hide.sh submit_all [submit]   the 6 jobs below (taxi, bonus, routes x 2 variants)
#   bash scripts/farmshare/step4_hide.sh report                 the map, from whatever targets exist (no Slurm)
#   bash scripts/farmshare/step4_hide.sh run <family> <variant> one family's targets in this shell (what a job runs)
# Families: taxi (as in Step 3, bonus 10), bonus (the grid, exploit bonus 200..3200), routes (grid_routes,
# R = 1, 2, 4 spokes x bonus 100, 400, 1600). Variants: P2swap, P1eq1. Seeds 0-2. Existing seeds are skipped.
# EXCLUDE=<nodes> (e.g. EXCLUDE=barley-04) keeps the jobs off broken nodes.
set -euo pipefail
cd "$(dirname "$0")/../.."
CMD=${1:-help}; shift || true
LAST=${*: -1}; [[ ${LAST:-} == submit ]] && GO=1 || GO=0
SEEDS=(0 1 2)
BONUSES=(200 400 800 1600 3200)               # the grid's b = 100 targets exist (results/step4/grid/targets/P*)
ROUTES=(1 2 4)
ROUTE_BONUSES=(100 400 1600)
hours() { case $1 in taxi) echo 12 ;; bonus) echo 6 ;; routes) echo 8 ;; esac; }

vsets() {   # family variant -> the variant's g overrides (the grid tasks keep the grid's 100-epoch fit)
  local ep=""; [[ $1 == taxi ]] && ep=" g.epochs=1000"
  case $2 in
    P2swap) echo "g.l_minus_on=dispreferred$ep" ;;
    P1eq1) echo "g.use_regularization=False$ep" ;;
    *) echo "unknown variant $2" >&2; exit 1 ;;
  esac
}
targets() {   # env name "sets"
  # shellcheck disable=SC2086
  .venv/bin/python -u experiments/step4_targets.py --env "$1" --name "$2" --seeds "${SEEDS[@]}" --set $3
}

case $CMD in
  run)
    fam=$1 v=$2; g=$(vsets "$fam" "$v")
    case $fam in
      taxi) targets taxi "$v" "task.obs=onehot $g" ;;
      bonus) for b in "${BONUSES[@]}"; do targets grid "b${b}_$v" "task.exploit_bonus=$b $g"; done ;;
      routes) for b in "${ROUTE_BONUSES[@]}"; do for r in "${ROUTES[@]}"; do
                targets grid_routes "r${r}_b${b}_$v" "task.routes=$r task.bonus=$b $g"; done; done ;;
      *) echo "unknown family $fam" >&2; exit 1 ;;
    esac ;;
  submit_all)
    for fam in taxi bonus routes; do for v in P2swap P1eq1; do
      args=(bash scripts/farmshare/run_cmd.sh "$(hours "$fam")" 4 "hide_${fam}_$v" bash scripts/farmshare/step4_hide.sh run "$fam" "$v")
      if (( GO )); then "${args[@]}"; else [[ -n ${EXCLUDE:-} ]] && printf 'EXCLUDE=%s ' "$EXCLUDE"; printf '%q ' "${args[@]}"; echo; fi
    done; done ;;
  report)
    .venv/bin/python experiments/step4_hide_map.py ;;
  *) sed -n 2,11p "$0" ;;
esac
