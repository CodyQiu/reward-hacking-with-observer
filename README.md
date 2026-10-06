# reward-hacking-with-observer

Does an RL agent learn to avoid behaviours that would get its reward function corrected, exploiting a reward bug except when it expects the overseer to look?

Step 1 setup:
- 15×15 grid with one exploit tile.
- 500-step episodes made of five 100-step sub-episodes.
- An overseer that audits the last W steps of each sub-episode and patches the reward if it sees the exploit.
- Policy and reward updates at every sub-episode boundary; the reward resets every episode.

```
.venv/bin/python tests/test_step1.py         # rules + exact DP validation
.venv/bin/python experiments/step1_dp.py     # exact optimum, sweeps, controls -> figures/
.venv/bin/python experiments/step1_ppo.py    # SBX PPO vs the exact optimum (--quick for a smoke run)
```

See `CLAUDE.md` for the model, design principles and results. The earlier project (Exp 0–4) is archived in `legacy/`.
