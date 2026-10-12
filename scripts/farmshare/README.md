# Running Step 3 on Stanford FarmShare

Training moved here from the laptop on 2026-10-12. On the laptop, up to 8 runs had shared 12 cores (3-7x slowdown), and the laptop sleeps.

**Connect once per session** (password + Duo), from a normal terminal on the laptop:

    ssh -fN -o ControlMaster=yes -o ControlPath=~/.ssh/cm-%r@%h:%p -o ControlPersist=12h cody1212@login.farmshare.stanford.edu

Later `ssh -o ControlPath=~/.ssh/cm-%r@%h:%p ...` commands reuse that connection without asking again. It drops when the laptop sleeps or changes network. Slurm jobs keep running regardless.

**One-time setup** (repo at `~/reward-hacking-with-observer`, copied from the laptop with rsync): `bash scripts/farmshare/setup.sh`. It builds `.venv` with the laptop's exact package versions (`requirements.txt`, Python 3.12.13, CPU torch). The runs use CPU only: the networks are tiny and the per-step work is Python, so the GPU partition would not help.

**Submit one tuning run** (all its seeds, one job; one core per seed plus one):

    bash scripts/farmshare/submit.sh <hours> --env tomato --run-id T1_x --seeds 0 1 2 --set ppo.ent_coef=0.02 --hypothesis "..."

The arguments after `<hours>` are passed to `experiments/step3_ppo.py` unchanged. Logs go to `logs/slurm/`. The partition limits are 2 days per job and 4 GB per core.

**Bring results back to the laptop:** `bash scripts/farmshare/sync.sh`. It pulls new runs and merges `runs.csv`. It never touches a run that was trained on the laptop: FarmShare holds only a `PLACEHOLDER` for those, so their run ids cannot be reused.

Floating-point results differ between the laptop (arm64) and FarmShare (x86_64), so a given seed does not reproduce bit for bit across machines. Within one machine, runs are deterministic.
