#!/bin/bash
# Step 4 "optimal policy" campaign on FarmShare (docs/step4_optimal.md): PPO must reach the self-consistent
# exact optimum (experiments/step4_targets.py) for the swap and the no-regulariser PBRR on the grid, Absent
# Supervisor, Tomato and tomato_large. Every command is a dry run (prints the sbatch commands) unless its last
# argument is "submit". From the repo root:
#   bash scripts/farmshare/step4_optimal.sh phase_a [submit]        tomato_large's Phase A (+ its canonical Step 4 checks)
#   bash scripts/farmshare/step4_optimal.sh targets [submit]        targets, every env x variant, seeds 0-2 and 20-22
#                                                                   (PHASEA_JOB=<id>: tomato_large's wait for Phase A)
#   bash scripts/farmshare/step4_optimal.sh wave1 [submit]          PPO wave 1: configs L, LE, LN x env x variant, seeds 0-2
#                                                                   (PHASEA_JOB=<id>: tomato_large's wait for Phase A)
#   bash scripts/farmshare/step4_optimal.sh report                  convergence verdicts of every campaign run (no Slurm)
#   bash scripts/farmshare/step4_optimal.sh resume [submit]         resubmit every campaign run with unfinished seeds and no job
#   bash scripts/farmshare/step4_optimal.sh extend <env> <run_id> <episodes> [submit]   take a run on to <episodes> in total
#   bash scripts/farmshare/step4_optimal.sh ppo <env> <variant> <tag> "<extra --set k=v ...>" [submit]   a new config
#   bash scripts/farmshare/step4_optimal.sh confirm <env> <run_id> [submit]   the run's config on fresh seeds 20-22
#   bash scripts/farmshare/step4_optimal.sh explore <env> <variant> <base_run_id> [stage2] [submit]
#                                                    exploration wave on top of a base run (rule 6b), seeds 0-2
#   bash scripts/farmshare/step4_optimal.sh br <env> <run_id> [submit]       paired best-response check of its finished seeds
#   bash scripts/farmshare/step4_optimal.sh br_missing [submit]               ... of every finished seed that lacks one
# EXCLUDE=<nodes> (e.g. EXCLUDE=barley-04) keeps every submitted job off broken nodes.
# CAMPAIGN=bonus runs every command for the update-bonus campaign instead (docs/step4_bonus.md): the received
# reward pays BONUS (default 1.0) per reward update (protocol.update_bonus); variants P2swap, P1eq1 and base
# (standard PBRR); runs B1_<variant>_<tag> in results/step4/<env>/bonus; targets <variant>_bonus<BONUS>. Its
# wave1 is each swap / no-reg cell's reference run from the optimal campaign (ref_run below) with the bonus,
# and L, LE, LN for base.
# CAMPAIGN=noreg_fail runs them for the no-regulariser campaign in the envs whose exact optimum under no-reg is not
# the desired behaviour (docs/step4_noreg_fail.md): taxi and boat_race, variant P1eq1, runs N1_P1eq1_<tag> in
# results/step4/<env>/noreg_fail, targets P1eq1 (Taxi's seeds 0-2 exist from the hide sweep and are reused).
set -euo pipefail
cd "$(dirname "$0")/../.."
CMD=${1:-help}; shift || true
LAST=${*: -1}; [[ ${LAST:-} == submit ]] && GO=1 || GO=0

ENVS=(grid absent_supervisor tomato tomato_large)
CAMPAIGN=${CAMPAIGN:-optimal}
case $CAMPAIGN in
  optimal) VARIANTS=(P2swap P1eq1); PFX=O1; EXTRA=""
           HYP="Step 4 optimal-policy campaign (docs/step4_optimal.md): PPO reaches the self-consistent exact optimum (experiments/step4_targets.py) of ENV under this PBRR variant" ;;
  bonus) BONUS=${BONUS:-1.0}; VARIANTS=(P2swap P1eq1 base); PFX=B1; EXTRA=" protocol.update_bonus=$BONUS"
         HYP="Step 4 update-bonus campaign (docs/step4_bonus.md): with +$BONUS received reward per reward update, PPO reaches the exact optimum (experiments/step4_br.py) of ENV under this PBRR variant" ;;
  noreg_fail) ENVS=(taxi boat_race); VARIANTS=(P1eq1); PFX=N1; EXTRA=""
         HYP="Step 4 no-regulariser failure campaign (docs/step4_noreg_fail.md): PPO reaches the exact optimum (experiments/step4_br.py) of ENV under no-regulariser PBRR, which is not the desired behaviour" ;;
  *) echo "unknown CAMPAIGN $CAMPAIGN" >&2; exit 1 ;;
esac
# each env's frozen Step 3 PPO config (CLAUDE.md 4e; tomato_large starts from Tomato's) and wave-1 length
frozen() { case $1 in absent_supervisor) echo "ppo.ent_coef=0.1" ;; tomato|tomato_large|boat_race) echo "ppo.ent_coef=0.03" ;;
                      taxi) echo "ppo.ent_coef=0.03" ;; *) echo "" ;; esac; }
ent3() { case $1 in grid) echo 0.03 ;; absent_supervisor) echo 0.3 ;; taxi|boat_race) echo 0.09 ;; *) echo 0.1 ;; esac; }  # 3x the frozen entropy
# 4x (2x for AS) Step 3's; Taxi 1x its frozen 768 (an exploiting seed took 47 h for 768 episodes: PBRR fits dominate)
episodes() { case $1 in absent_supervisor) echo 3072 ;; taxi) echo 768 ;; *) echo 1536 ;; esac; }
ANNEAL="anneal.last=0.25 anneal.floor=0.1"
BR_DRAWS=12                                                       # overseer draws of the best-response check
br_hours() { case $1 in tomato_large) echo 12 ;; tomato|taxi) echo 6 ;; *) echo 2 ;; esac; }
TUNE_SEEDS=(0 1 2)
CONFIRM_SEEDS=(20 21 22)

gsets() {   # the variant's PBRR overrides (the grid keeps Step 2's 100-epoch fit, as in its Phase A and earlier runs)
  local env=$1 v=$2 ep=""   # plus, in the bonus campaign, the update bonus (part of the game, like the g fit)
  [[ $env != grid ]] && ep=" g.epochs=1000"
  [[ $env == taxi ]] && printf 'task.obs=onehot '              # Taxi's frozen Step 3 observation: part of its game
  case $v in
    P2swap) echo "g.l_minus_on=dispreferred$ep$EXTRA" ;;
    P1eq1) echo "g.use_regularization=False$ep$EXTRA" ;;
    base) echo "${ep# }$EXTRA" ;;                                # standard PBRR (max1), as in Steps 2-3
    *) echo "unknown variant $v" >&2; exit 1 ;;
  esac
}
rdir() { echo "results/step4/$1/$CAMPAIGN"; }
tname() { if [[ $CAMPAIGN == bonus ]]; then echo "${1}_bonus${BONUS%.0}"; else echo "$1"; fi; }
# bonus campaign, wave 1: each swap / no-reg cell starts from the optimal campaign's run that converged
# (the cell's DONE config) or, for an open cell, its tuning run with the smallest mean best-response gap
# (as of 2026-11-13), at that run's length; same seeds, so each bonus run pairs with its no-bonus run
ref_run() { case $1:$2 in
  grid:P2swap) echo "O1_P2swap_LE+NET+ENT3 1536" ;;               # DONE
  grid:P1eq1) echo "O1_P1eq1_LN+LR 6144" ;;                       # open: 3/3 at 6144, confirmation 0/3
  absent_supervisor:P2swap) echo "O1_P2swap_LN 3072" ;;           # DONE
  absent_supervisor:P1eq1) echo "O1_P1eq1_LN+RS 6144" ;;          # DONE
  tomato:P2swap) echo "O1_P2swap_LN+ES10+N4 1536" ;;              # DONE
  tomato:P1eq1) echo "O1_P1eq1_LN 6144" ;;                        # DONE
  tomato_large:P2swap) echo "O1_P2swap_LE 1536" ;;                # open: 3/3 at 1536, confirmation running
  tomato_large:P1eq1) echo "O1_P1eq1_LN+ES10 1536" ;;             # open: 0/3 (best mean gap 0.045)
  *) echo "no reference run for $1 $2" >&2; exit 1 ;;
esac; }
run() { if (( GO )); then "$@"; else [[ -n ${DEPENDENCY:-} ]] && printf 'DEPENDENCY=%s ' "$DEPENDENCY"
          [[ -n ${EXCLUDE:-} ]] && printf 'EXCLUDE=%s ' "$EXCLUDE"; printf '%q ' "$@"; echo; fi; }
br_submit() {   # env run_dir
  run bash scripts/farmshare/run_cmd.sh "$(br_hours "$1")" 4 "br_$1_$(basename "$2")" .venv/bin/python -u \
    experiments/step4_br.py "$2" --finished-only --draws "$BR_DRAWS"
}
running() { squeue -h -u "$USER" -o %j 2>/dev/null | grep -Fxq "$1"; }

ppo_submit() {   # env run_id "sets" seeds...
  local env=$1 id=$2 sets=$3; shift 3
  local dep=""
  [[ $env == tomato_large && -n ${PHASEA_JOB:-} ]] && dep="afterok:$PHASEA_JOB"
  # shellcheck disable=SC2206
  local s=($sets)
  DEPENDENCY=$dep run bash scripts/farmshare/submit.sh 48 --env "$env" --run-id "$id" --seeds "$@" \
    --results-dir "$(rdir "$env")" --set "${s[@]}" \
    --hypothesis "${HYP//ENV/$env}"
}

case $CMD in
  phase_a)
    run bash scripts/farmshare/run_cmd.sh 24 4 phase_a_tomato_large .venv/bin/python -u experiments/step3_check.py --env tomato_large
    echo "# then, with PHASEA_JOB=<the id above> (they need Phase A's g config):"
    for v in P2swap_ep1000:"l_minus_on=dispreferred epochs=1000" P2swapNoLplus_ep1000:"l_minus_on=dispreferred l_plus=False epochs=1000" \
             P1eq1_ep1000:"use_regularization=False epochs=1000"; do
      # shellcheck disable=SC2086
      DEPENDENCY=${PHASEA_JOB:+afterok:$PHASEA_JOB} run bash scripts/farmshare/run_cmd.sh 12 4 "phase_a_tomato_large_${v%%:*}" \
        .venv/bin/python -u experiments/step3_check.py --env tomato_large --variant "${v%%:*}" --g-set ${v#*:}
    done ;;
  targets)
    for env in "${ENVS[@]}"; do for v in "${VARIANTS[@]}"; do
      dep=""; [[ $env == tomato_large && -n ${PHASEA_JOB:-} ]] && dep="afterok:$PHASEA_JOB"
      # shellcheck disable=SC2046
      DEPENDENCY=$dep run bash scripts/farmshare/run_cmd.sh 36 4 "targets_${env}_$(tname "$v")" .venv/bin/python -u experiments/step4_targets.py \
        --env "$env" --name "$(tname "$v")" --seeds "${TUNE_SEEDS[@]}" "${CONFIRM_SEEDS[@]}" --set $(gsets "$env" "$v")
    done; done ;;
  wave1)
    for env in "${ENVS[@]}"; do for v in "${VARIANTS[@]}"; do
      if [[ $CAMPAIGN == bonus && $v != base ]]; then            # the cell's reference run, with the bonus
        read -r old eps <<< "$(ref_run "$env" "$v")"
        words=$(.venv/bin/python scripts/farmshare/run_sets.py "results/step4/$env/optimal/$old")
        words=$(tr ' ' '\n' <<< "$words" | grep -v '^episodes=' | tr '\n' ' ')
        ppo_submit "$env" "${PFX}_${v}_${old#O1_${v}_}" "${words}episodes=$eps$EXTRA" "${TUNE_SEEDS[@]}"
        continue
      fi
      base="$(frozen "$env") $(gsets "$env" "$v") episodes=$(episodes "$env") $ANNEAL"
      ppo_submit "$env" "${PFX}_${v}_L" "$base" "${TUNE_SEEDS[@]}"
      ppo_submit "$env" "${PFX}_${v}_LE" "$base ppo.ent_coef=$(ent3 "$env")" "${TUNE_SEEDS[@]}"
      ppo_submit "$env" "${PFX}_${v}_LN" "$base n_envs=64 ppo.batch_size=1600" "${TUNE_SEEDS[@]}"
    done; done ;;
  report)
    for env in "${ENVS[@]}"; do
      d=$(rdir "$env"); [[ -d $d ]] || continue
      for r in "$d"/*/; do [[ -d $r ]] && .venv/bin/python experiments/step4_convergence.py "${r%/}" 2>/dev/null || true; done
    done ;;
  resume)
    for env in "${ENVS[@]}"; do
      d=$(rdir "$env"); [[ -d $d ]] || continue
      for r in "$d"/*/; do
        id=$(basename "$r"); todo=()
        for s in "$r"seed*/; do
          [[ -d $s && $(basename "$s") != *_nockpt_* ]] || continue
          [[ -e $s/metrics.json ]] || todo+=("$(basename "$s" | sed 's/^seed//')")
        done
        (( ${#todo[@]} )) || continue
        if running "step4_$env:$id"; then echo "# $env/$id: job still queued/running"; continue; fi
        run bash scripts/farmshare/submit.sh 48 --env "$env" --run-id "$id" --seeds "${todo[@]}" --results-dir "$d" --resume
      done
    done ;;
  extend)
    env=$1 id=$2 eps=$3; d=$(rdir "$env")
    seeds=($(ls -d "$d/$id"/seed*/ | grep -v _nockpt_ | xargs -n1 basename | sed 's/^seed//'))
    run bash scripts/farmshare/submit.sh 48 --env "$env" --run-id "$id" --seeds "${seeds[@]}" --results-dir "$d" \
      --resume --extend-to "$eps" ;;
  ppo)
    env=$1 v=$2 tag=$3 extra=$4
    base="$(frozen "$env") $(gsets "$env" "$v") episodes=$(episodes "$env") $ANNEAL $extra"
    ppo_submit "$env" "${PFX}_${v}_$tag" "$base" "${TUNE_SEEDS[@]}" ;;
  confirm)
    env=$1 id=$2; d=$(rdir "$env")
    sets=$(.venv/bin/python scripts/farmshare/run_sets.py "$d/$id")
    ppo_submit "$env" "${id}_confirm" "$sets" "${CONFIRM_SEEDS[@]}" ;;
  explore)
    env=$1 v=$2 base=$3 stage=${4:-}; d=$(rdir "$env")
    [[ $stage == stage2 ]] || stage=""
    [[ $base == ${PFX}_${v}_* ]] || { echo "$base is not a ${PFX}_${v}_* run" >&2; exit 1; }
    lines=$(.venv/bin/python scripts/farmshare/explore_sets.py "$d/$base" "$(episodes "$env")" $stage)
    while IFS=$'\t' read -r tag sets; do
      if [[ -e $d/${base}+$tag ]]; then echo "# $env/${base}+$tag exists: skipped"; continue; fi
      ppo_submit "$env" "${base}+$tag" "$sets" "${TUNE_SEEDS[@]}"
    done <<< "$lines" ;;
  br)
    env=$1 id=$2
    br_submit "$env" "$(rdir "$env")/$id" ;;
  br_missing)
    for env in "${ENVS[@]}"; do
      d=$(rdir "$env"); [[ -d $d ]] || continue
      for r in $(.venv/bin/python experiments/step4_br.py --missing "$d"/*/ 2>/dev/null); do
        if running "br_${env}_$(basename "$r")"; then echo "# $env/$(basename "$r"): check still queued/running"; continue; fi
        br_submit "$env" "$r"
      done
    done ;;
  *) sed -n 2,20p "$0" ;;
esac
