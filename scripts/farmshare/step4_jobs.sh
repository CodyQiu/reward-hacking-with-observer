#!/bin/bash
# Step 4 on FarmShare: the long Step 3 tasks x the three PBRR variants, one Slurm job per run (3 seeds).
#   bash scripts/farmshare/step4_jobs.sh            # dry run: print the submit commands
#   bash scripts/farmshare/step4_jobs.sh submit     # submit them (skips runs that already exist)
# Each task uses its frozen Step 3 PPO config (CLAUDE.md 4e) and seeds 10-12, so every run pairs with
# the Step 3 baseline on the same seeds. Hours: generous (1000-epoch fits make PBRR rounds slower;
# the partition allows 48 h and does not preempt).
# The short tasks (grid, absent_supervisor, boat_race) run on the laptop. g is fitted for 1000 epochs
# (Step 3's E.1 choice, 50-200, under-fits the swap's raise: results/step4/<env>/phase_a/*_ep1000).
set -euo pipefail
cd "$(dirname "$0")/../.."
MODE=${1:-dry}

# task | hours | frozen Step 3 overrides
TASKS=(
  "taxi|40|task.obs=onehot ppo.ent_coef=0.03 episodes=768"
  "tomato|16|ppo.ent_coef=0.03"
  "mountain_car|30|protocol.clock=scalar episodes=768"
  "lunar_lander|24|"
)
# variant | PBRR overrides | what it tests
VARIANTS=(
  "P2swap_ep1000|g.l_minus_on=dispreferred g.epochs=1000|mentor's swap: L- on the dispreferred trajectory, L+ kept; g fit 1000 epochs"
  "P2swapNoLplus_ep1000|g.l_minus_on=dispreferred g.l_plus=False g.epochs=1000|the swap without L+; g fit 1000 epochs"
  "P1eq1_ep1000|g.use_regularization=False g.epochs=1000|no regulariser at all (Eq 1); g fit 1000 epochs"
)

for t in "${TASKS[@]}"; do
  IFS='|' read -r env hours base <<< "$t"
  for v in "${VARIANTS[@]}"; do
    IFS='|' read -r name gset what <<< "$v"
    run="S4_${name}_seeds10-12"
    rdir="results/step4/$env/ppo"
    if [[ -e $rdir/$run ]]; then echo "skip $env/$run (exists)"; continue; fi
    # shellcheck disable=SC2206
    sets=($base $gset)
    cmd=(bash scripts/farmshare/submit.sh "$hours" --env "$env" --run-id "$run" --seeds 10 11 12
         --results-dir "$rdir" --set "${sets[@]}"
         --hypothesis "Step 4 $name ($what) on $env with its frozen Step 3 PPO config. Exact check: results/step4/$env/phase_a/$name (lunar_lander: none, scripted). Readouts R1-R4: experiments/step4_readout.py.")
    if [[ $MODE == submit ]]; then "${cmd[@]}"; else printf '%q ' "${cmd[@]}"; echo; fi
  done
done
