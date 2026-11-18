"""Taxi: expected deliveries per round of a trained PPO policy at a given correction level (exact).

A delivery is a Taxi-v3 dropoff at the destination, the only transition that pays +20. Every round restarts
from the start distribution, so the policy's play at correction level c in round k is a forward pass of
T_sub steps from mu0 with the network's probabilities at (t, s, level c, audit flag), counted exactly. This
holds whether or not the policy ever reaches level c (a seed that hides is evaluated as if corrected once).

    .venv/bin/python experiments/step4_taxi_deliveries.py results/step4/taxi/<campaign>/<run> [--seeds 0 1 2]

Prints, per seed, the deliveries per round at level 1 (after one correction) in rounds 1-4 and at level 0
in round 0, then the honest policy's deliveries per round (the true-reward optimum of a sub-episode, the
best-response check's "honest"; the reference, about 7.1).
"""

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from step4_br import ppo_probs_at  # noqa: E402
from src.step3.dp import solve_subepisode  # noqa: E402
from src.step3.protocol import Protocol  # noqa: E402
from src.step3.tasks import get_task  # noqa: E402


def delivery_rows(tb):
    return np.isclose(tb.true[:, 0], 20.0)


def round_deliveries(tb, proto, probs_at, k, level):
    """Expected deliveries in round k with the level fixed at ``level`` (flag tracked inside the window)."""
    S, A, T = tb.n_states, tb.n_actions, proto.t_sub
    deliv, ex = delivery_rows(tb), tb.exploit
    d = np.zeros((S, 2))
    d[:, 0] = tb.mu0
    total = 0.0
    for tau in range(T):
        t = k * T + tau
        P = np.asarray(probs_at(t), float)[:, level]                     # (S, 2, A)
        win = bool(proto.in_window(t))
        nd = np.zeros((S, 2))
        for a in range(A):
            r = np.arange(S) * A + a
            w = d * P[:, :, a]                                            # (S, 2)
            if not w.any():
                continue
            total += (w.sum(axis=1) * deliv[r]).sum()
            m = w[:, :, None] * tb.prob[r][:, None, :]                    # (S, 2, F)
            f2 = np.arange(2)[None, :, None].astype(bool) | (ex[r][:, None, :] & win)
            np.add.at(nd, (tb.nxt[r][:, None, :].repeat(2, 1), f2.astype(int)), m)
        d = nd
    return total


def honest_probs_at(task, proto):
    """The true-reward optimum of one sub-episode (the best-response check's "honest" policy)."""
    S, A, T = task.tables.n_states, task.n_actions, proto.t_sub
    pol = solve_subepisode(task.tables, task.tables.true, T)            # (T, S)
    eye = np.eye(A)

    def at(t):
        return np.broadcast_to(eye[pol[t % T]][:, None, None, :], (S, proto.n_sub, 2, A))
    return at


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--seeds", type=int, nargs="*")
    args = ap.parse_args()
    from sbx import PPO
    seeds = sorted(d for d in os.listdir(args.run) if d.startswith("seed") and os.path.isdir(os.path.join(args.run, d)))
    task = proto = None
    for s in seeds:
        if args.seeds and int(s[4:]) not in args.seeds:
            continue
        sd = os.path.join(args.run, s)
        if not os.path.exists(os.path.join(sd, "model.zip")):
            continue
        with open(os.path.join(sd, "config.json")) as fh:
            cfg = json.load(fh)
        proto = Protocol(**cfg["protocol"])
        task = get_task(cfg["env"], **cfg["task"])
        model = PPO.load(os.path.join(sd, "model.zip"), device="cpu")
        n_ep = int(model.num_timesteps // (int(cfg["n_envs"]) * proto.t_ep))
        pa = ppo_probs_at(model, proto, task.tables.phi_obs, proto.n_sub, task.n_actions)
        d0 = round_deliveries(task.tables, proto, pa, 0, 0)
        d1 = [round_deliveries(task.tables, proto, pa, k, 1) for k in range(1, proto.n_sub)]
        print(f"{s} (ep {n_ep}): round 0 at level 0: {d0:.2f} deliveries; rounds 1-4 at level 1 (after one "
              f"correction): {' '.join(f'{x:.2f}' for x in d1)}")
    if task is not None:
        h = [round_deliveries(task.tables, proto, honest_probs_at(task, proto), k, 0) for k in range(proto.n_sub)]
        print(f"honest (true-reward optimum): {' '.join(f'{x:.2f}' for x in h)} deliveries per round")


if __name__ == "__main__":
    main()
