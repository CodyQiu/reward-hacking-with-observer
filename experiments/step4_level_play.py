"""What a trained PPO policy does at each correction level, read exactly from its saved model.

For each seed directory (with model.zip), the policy's own play in round k at correction level c (audit flag 0,
from the start distribution, every action at its probability) gives:
- its true return;
- for Taxi, its deliveries and repeat pickups per round (honest play: about 7.1 deliveries, no repeats);
- for the grid, P(at the goal by the end of the round).

The levels are (k, c) = (0, 0), (1, 1) and (3, 1): before the correction, the round after it, and later at the
same level. Used for the twin campaign's Taxi log (docs/step4_indiff.md, "The twin": the skill deficit).

    .venv/bin/python experiments/step4_level_play.py "results/step4/taxi/indiff_twin/*/seed*"
"""

import glob
import json
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step4_br import ppo_probs_at  # noqa: E402
from src.step3.protocol import Protocol  # noqa: E402
from src.step3.tasks import get_task  # noqa: E402


def play(at, tb, T, k, c):
    """True return, exploit steps, deliveries (true reward +20), repeat pickups (proxy > true), final state dist."""
    S, A = tb.n_states, tb.n_actions
    d = tb.mu0.copy()
    tot = ex = dl = pk = 0.0
    for tau in range(T):
        p = np.asarray(at(k * T + tau), float)[:, c, 0]                   # (S, A), audit flag 0
        m = (d[:, None] * p).reshape(-1)[:, None] * tb.prob               # rows s * A + a, in order
        tot += (m * tb.true).sum()
        ex += (m * tb.exploit).sum()
        dl += (m * (tb.true == 20)).sum()
        pk += (m * ((tb.proxy - tb.true) > 0)).sum()
        d = np.bincount(tb.nxt.ravel(), weights=m.ravel(), minlength=S)
    return tot, ex, dl, pk, d


def main():
    from sbx import PPO
    for pat in sys.argv[1:]:
        for sd in sorted(glob.glob(pat)):
            if not os.path.exists(os.path.join(sd, "model.zip")):
                continue
            with open(os.path.join(sd, "config.json")) as fh:
                cfg = json.load(fh)
            P, task = Protocol(**cfg["protocol"]), get_task(cfg["env"], **cfg["task"])
            tb, T = task.tables, P.t_sub
            model = PPO.load(os.path.join(sd, "model.zip"), device="cpu")
            ep = model.num_timesteps // (cfg["n_envs"] * P.t_ep)
            at = ppo_probs_at(model, P, tb.phi_obs, P.n_sub, task.n_actions)
            out = []
            for k, c in ((0, 0), (1, 1), (3, 1)):
                tot, ex, dl, pk, d = play(at, tb, T, k, c)
                s = f"k{k} lvl{c}: true {tot:7.1f}"
                if cfg["env"] == "taxi":
                    s += f" deliveries {dl:4.1f} repeat pickups {pk:4.1f}"
                if cfg["env"] == "grid" and tb.absorbing.any():
                    s += f" P(goal) {d[tb.absorbing].sum():.2f}"
                out.append(s)
            print(f"{os.path.relpath(sd):60s} ep{ep:5d} | " + " | ".join(out), flush=True)


if __name__ == "__main__":
    main()
