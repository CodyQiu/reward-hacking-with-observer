#!/bin/bash
# Laptop side. Pull every tuning run trained on FarmShare into results/step3/ and merge runs.csv.
#   bash scripts/farmshare/sync.sh
# Needs the shared SSH connection (scripts/farmshare/README.md). A run is pulled only if it
# does not exist here yet or was pulled from FarmShare before (marker file .farmshare), so a
# run trained on the laptop is never touched. runs.csv rows are merged, never dropped.
set -euo pipefail
cd "$(dirname "$0")/../.."
HOST=cody1212@login.farmshare.stanford.edu
REPO=reward-hacking-with-observer
SSHCMD=(ssh -o "ControlPath=$HOME/.ssh/cm-%r@%h:%p" -o BatchMode=yes)
E="ssh -o ControlPath=$HOME/.ssh/cm-%r@%h:%p -o BatchMode=yes"
TMP=$(mktemp -d)
# remote runs: env/run for every run directory without a PLACEHOLDER (laptop runs are placeholders there)
runs=$("${SSHCMD[@]}" "$HOST" "cd $REPO/results/step3 && for d in */tuning/*/; do [ -e \$d/PLACEHOLDER ] || echo \${d%/}; done")
for r in $runs; do
  env=${r%%/*}; run=${r##*/}; local_dir=results/step3/$env/tuning/$run
  if [[ -d $local_dir && ! -e $local_dir/.farmshare ]]; then continue; fi   # trained here
  mkdir -p "$local_dir"
  rsync -az -e "$E" --exclude __pycache__ "$HOST:$REPO/$local_dir/" "$local_dir/"
  touch "$local_dir/.farmshare"
  echo "pulled $env/$run"
done
for env in tomato taxi absent_supervisor mountain_car lunar_lander; do
  rsync -az -e "$E" "$HOST:$REPO/results/step3/$env/tuning/runs.csv" "$TMP/$env.csv" 2>/dev/null || true
done
.venv/bin/python - "$TMP" <<'PY'
import csv, os, sys
tmp = sys.argv[1]
for env in ["tomato", "taxi", "absent_supervisor", "mountain_car", "lunar_lander"]:
    remote, local = os.path.join(tmp, f"{env}.csv"), f"results/step3/{env}/tuning/runs.csv"
    if not os.path.exists(remote):
        continue
    rows, fields = [], None
    for path in [local, remote]:
        if os.path.exists(path):
            with open(path) as fh:
                r = csv.DictReader(fh)
                fields = fields or r.fieldnames
                rows += list(r)
    seen, merged = set(), []
    for row in sorted(rows, key=lambda r: r["finished"]):
        key = (row["run_id"], row["seeds"], row["finished"])
        if key not in seen:
            seen.add(key)
            merged.append(row)
    with open(local, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(merged)
    print(f"{env}: runs.csv {len(merged)} rows")
PY
rm -rf "$TMP"
