#!/bin/bash
# Submit one Step 3 tuning run (all of its seeds) as one Slurm job. On FarmShare, from the repo root:
#   bash scripts/farmshare/submit.sh <hours> --env tomato --run-id T1_x --seeds 0 1 2 [--set k=v ...] --hypothesis "..."
# Everything after <hours> goes to experiments/step3_ppo.py unchanged. Step 4 runs add
# --results-dir results/step4/<env>/ppo (see scripts/farmshare/step4_jobs.sh). The job gets one physical core
# per seed: 2 CPUs = the core's two hyperthreads (a worker measured 1.4 CPU-s per s inside its cgroup:
# Python plus JAX's dispatch threads), 4000 MB per CPU = 8 GB per seed (measured RSS 1.3 GB).
# --mem-per-cpu must not exceed the partition's MaxMemPerCPU (4000): above it Slurm silently adds CPUs.
# --no-requeue: after a node failure Slurm would requeue the job, which can only fail, since the run
# directory exists and runs are never overwritten. Rerun under a new run id instead (docs/step3_tuning_log.md).
# --resume (passed through to step3_ppo.py) continues an existing run from its checkpoints instead; set
# DEPENDENCY=<jobid> to start only after that job ends (afterany: a time-limited job hands over to its successor),
# DEPENDENCY=afterok:<jobid> to start only if it succeeded (e.g. after tomato_large's Phase A). Prints the job id.
set -euo pipefail
HOURS=$1; shift
args=("$@")
n=0; inseeds=0; env=""; run=""; rdir=""; resume=0
for ((i = 0; i < ${#args[@]}; i++)); do
  a=${args[i]}
  case $a in
    --env) env=${args[i+1]} ;;
    --run-id) run=${args[i+1]} ;;
    --results-dir) rdir=${args[i+1]} ;;
    --resume) resume=1 ;;
  esac
  if [[ $a == --* ]]; then inseeds=0; [[ $a == --seeds ]] && inseeds=1 && continue; fi
  (( inseeds )) && n=$((n + 1))
done
[[ -n $env && -n $run && $n -gt 0 ]] || { echo "need --env, --run-id and --seeds" >&2; exit 1; }
rdir=${rdir:-results/step3/$env/tuning}
if (( resume )); then
  [[ -d $rdir/$run ]] || { echo "$rdir/$run does not exist: nothing to resume" >&2; exit 1; }
else
  [[ -e $rdir/$run ]] && { echo "$rdir/$run exists: pick a new --run-id" >&2; exit 1; }
fi
mkdir -p logs/slurm
tag=$env; [[ $rdir == results/step4/* ]] && tag=step4_$env
job=logs/slurm/${tag}_${run}$( (( resume )) && echo "_resume$(date +%Y%m%d-%H%M%S)").sh
{
  echo "#!/bin/bash"
  echo "cd $(pwd)"
  printf '%q ' .venv/bin/python -u experiments/step3_ppo.py "${args[@]}"; echo
} > "$job"
dep=()
if [[ -n ${DEPENDENCY:-} ]]; then [[ $DEPENDENCY == *:* ]] && dep=(--dependency="$DEPENDENCY") || dep=(--dependency="afterany:$DEPENDENCY"); fi
sbatch --parsable ${dep[@]+"${dep[@]}"} --job-name="$tag:$run" --partition=normal --cpus-per-task=$((2 * n)) --mem-per-cpu=4000M --no-requeue \
  --time="${HOURS}:00:00" --output="logs/slurm/${tag}_${run}_%j.out" "$job"
