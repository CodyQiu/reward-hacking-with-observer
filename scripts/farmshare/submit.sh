#!/bin/bash
# Submit one Step 3 tuning run (all of its seeds) as one Slurm job. On FarmShare, from the repo root:
#   bash scripts/farmshare/submit.sh <hours> --env tomato --run-id T1_x --seeds 0 1 2 [--set k=v ...] --hypothesis "..."
# Everything after <hours> goes to experiments/step3_ppo.py unchanged. The job gets one core per
# seed (each seed is a single-threaded process) plus one, 4 GB per core.
set -euo pipefail
HOURS=$1; shift
args=("$@")
n=0; inseeds=0; env=""; run=""
for ((i = 0; i < ${#args[@]}; i++)); do
  a=${args[i]}
  case $a in
    --env) env=${args[i+1]} ;;
    --run-id) run=${args[i+1]} ;;
  esac
  if [[ $a == --* ]]; then inseeds=0; [[ $a == --seeds ]] && inseeds=1 && continue; fi
  (( inseeds )) && n=$((n + 1))
done
[[ -n $env && -n $run && $n -gt 0 ]] || { echo "need --env, --run-id and --seeds" >&2; exit 1; }
[[ -e results/step3/$env/tuning/$run ]] && { echo "results/step3/$env/tuning/$run exists: pick a new --run-id" >&2; exit 1; }
mkdir -p logs/slurm
job=logs/slurm/${env}_${run}.sh
{
  echo "#!/bin/bash"
  echo "cd $(pwd)"
  printf '%q ' .venv/bin/python -u experiments/step3_ppo.py "${args[@]}"; echo
} > "$job"
sbatch --job-name="$env:$run" --partition=normal --cpus-per-task=$((n + 1)) --mem-per-cpu=4G \
  --time="${HOURS}:00:00" --output="logs/slurm/${env}_${run}_%j.out" "$job"
