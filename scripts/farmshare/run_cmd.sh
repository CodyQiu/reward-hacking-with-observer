#!/bin/bash
# Submit any repo command as one Slurm job (exact checks, targets). From the repo root on FarmShare:
#   bash scripts/farmshare/run_cmd.sh <hours> <cpus> <name> <command ...>
#   e.g. bash scripts/farmshare/run_cmd.sh 12 4 targets_tomato_P2swap .venv/bin/python -u experiments/step4_targets.py ...
# Memory: 4000 MB per CPU (the partition's MaxMemPerCPU; above it Slurm silently adds CPUs), so <cpus> also
# sets memory (tomato_large's level DP needs ~6 GB: use 4). DEPENDENCY=<jobid> waits for that job to end
# (afterany); DEPENDENCY=afterok:<jobid> waits for it to succeed. Prints the job id.
set -euo pipefail
HOURS=$1; CPUS=$2; NAME=$3; shift 3
mkdir -p logs/slurm
job=logs/slurm/${NAME}.sh
{ echo "#!/bin/bash"; echo "cd $(pwd)"; echo 'export XLA_FLAGS=--xla_cpu_multi_thread_eigen=false OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1'
  printf '%q ' "$@"; echo; } > "$job"
dep=()
if [[ -n ${DEPENDENCY:-} ]]; then [[ $DEPENDENCY == *:* ]] && dep=(--dependency="$DEPENDENCY") || dep=(--dependency="afterany:$DEPENDENCY"); fi
sbatch --parsable ${dep[@]+"${dep[@]}"} --job-name="$NAME" --partition=normal --cpus-per-task="$CPUS" --mem-per-cpu=4000M \
  --no-requeue --time="${HOURS}:00:00" --output="logs/slurm/${NAME}_%j.out" "$job"
