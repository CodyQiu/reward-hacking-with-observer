# AGENTS.md

See **[CLAUDE.md](CLAUDE.md)**. It is the single source of truth for project context, the training protocol and formal model, the load-bearing design principles, experiment status and results, repo layout, and working conventions. Add project context to CLAUDE.md only.

**Current direction (October 2026).** Does an RL agent, trained across episodes, learn to avoid behaviours that would get its reward function corrected? The protocol: 500-step episodes split into five 100-step sub-episodes; policy and reward updates at every sub-episode boundary; the reward resets each episode, the policy does not. Step 1 is a 15×15 grid with one exploit tile, and an overseer that audits the last W steps of each sub-episode.

The previous project (Exp 0–4, concealment and PBRR reward repair) is archived in **`legacy/`**, with its own context file `legacy/README.md`. It is frozen; do not extend it.
