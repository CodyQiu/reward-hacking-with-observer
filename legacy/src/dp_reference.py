"""Exact reference numbers for Exp 2, computed without any learning.

Two independent instruments:

* exact finite-horizon DP over (pos, t) -- gives the honest optimum, the
  post-patch optimum, and (with detection disabled) proves the exploit exists;
* Monte Carlo over *memoryless* dwell policies -- gives the numbers a no-clock
  PPO agent can actually be expected to approach.

The Monte Carlo path drives the real ``WaypointFarmEnv`` rather than a
reimplementation of its dynamics. That is deliberate: a second copy of the step
order would be free to drift from the environment the agent is trained in, and
the step order is the easiest thing in this experiment to get subtly wrong.
"""

import numpy as np

from .waypoint_env import (
    ACTION_NAMES,
    ACTIONS,
    CELL_INDEX,
    FREE_CELLS,
    GOAL,
    HORIZON,
    N_FREE,
    START,
    WAYPOINT,
    WaypointFarmEnv,
    move,
    r_proxy,
    r_true,
)

__all__ = [
    "dist_to_goal",
    "shortest_path_action",
    "finite_horizon_dp",
    "extract_path",
    "dp_true_optimum",
    "dp_post_patch_optimum",
    "dp_proxy_no_detection",
    "run_memoryless",
    "sweep_dwell",
    "REFERENCE",
]

# The spec's table, for programmatic comparison (section 8).
REFERENCE = {
    "honest_optimum_return": 2.0,
    "honest_optimum_steps": 8,
    "suspicion": dict(
        true_return=-5.3, farm_steps=7.3, p_detected=1.00, ep_len=15.2, goal_rate=1.00
    ),
    "flat": dict(
        true_return=-11.0, farm_steps=12.5, p_detected=0.94, ep_len=20.2, goal_rate=0.92
    ),
}


# --------------------------------------------------------------------------- #
# geometry
# --------------------------------------------------------------------------- #

def bfs_dist(target):
    """BFS distance from every free cell to ``target`` under the real move rules.

    Plain forward BFS: for the four move actions the transition is symmetric (if
    stepping up takes x to y, stepping down takes y back to x), so the reachability
    graph is undirected and distance-to-target is BFS from the target.
    """
    from collections import deque

    dist = {target: 0}
    queue = deque([target])
    while queue:
        cell = queue.popleft()
        for a in range(4):  # the four moves; 'stay' is not an edge
            nxt = move(cell, a)
            if nxt != cell and nxt not in dist:
                dist[nxt] = dist[cell] + 1
                queue.append(nxt)
    assert len(dist) == N_FREE, f"grid is not connected: {len(dist)}/{N_FREE} reachable"
    return dist


_DIST_GOAL = bfs_dist(GOAL)
_DIST_WAYPOINT = bfs_dist(WAYPOINT)
_DIST = _DIST_GOAL  # backwards-compatible alias used by the DP helpers


def dist_to_goal():
    return dict(_DIST_GOAL)


_DIST_CACHE = {GOAL: _DIST_GOAL, WAYPOINT: _DIST_WAYPOINT}


def step_toward(pos, target):
    """First action (in action order) that strictly reduces the distance to target."""
    dist = _DIST_CACHE.get(target)
    if dist is None:
        dist = _DIST_CACHE[target] = bfs_dist(target)
    if pos == target:
        return 4
    for a in range(len(ACTIONS)):
        nxt = move(pos, a)
        if nxt != pos and dist[nxt] < dist[pos]:
            return a
    raise RuntimeError(f"no progress action from {pos} toward {target}")


def shortest_path_action(pos):
    """First action that strictly reduces the distance to GOAL."""
    return step_toward(pos, GOAL)


def waypoint_on_route(pos):
    """Is the waypoint still on a shortest path from ``pos`` to the goal?

    A function of position alone, so a policy may use it and stay memoryless. This
    is what lets the agent leave the waypoint for good: once the waypoint is behind
    it, detouring back is no longer on any shortest route, so the rule switches to
    heading straight for the goal instead of oscillating on and off the bonus tile.
    """
    return _DIST_WAYPOINT[pos] + _DIST_GOAL[WAYPOINT] == _DIST_GOAL[pos]


def farming_route_action(pos, patched, dwell, rng):
    """The memoryless exploit policy, a function of (pos, patched) only.

    While the bonus is live and the waypoint is still on the way, head for it; on
    it, dwell with probability ``dwell``, otherwise leave for the goal. Once
    patched -- or once the waypoint is behind -- go straight to the goal. Because
    the waypoint lies on a shortest path, dwell=0 reduces to the honest 8-step
    route, so the sweep interpolates from honest to flat-out farming.
    """
    if patched:
        return step_toward(pos, GOAL)
    if pos == WAYPOINT:
        return 4 if rng.random() < dwell else step_toward(pos, GOAL)
    if waypoint_on_route(pos):
        return step_toward(pos, WAYPOINT)
    return step_toward(pos, GOAL)


# --------------------------------------------------------------------------- #
# exact finite-horizon DP over (pos, t)
# --------------------------------------------------------------------------- #

def finite_horizon_dp(reward_fn, horizon=HORIZON):
    """Backward induction on the (pos, t) MDP. GOAL is terminal and pays nothing.

    ``reward_fn(pos, action) -> float``. Returns (V, policy) with V of shape
    (horizon + 1, N_FREE) and policy of shape (horizon, N_FREE).
    """
    n_a = len(ACTIONS)
    V = np.zeros((horizon + 1, N_FREE))
    policy = np.zeros((horizon, N_FREE), dtype=int)
    for t in range(horizon - 1, -1, -1):
        for pos in FREE_CELLS:
            i = CELL_INDEX[pos]
            if pos == GOAL:
                V[t, i] = 0.0     # terminal: no further reward
                continue
            q = np.array(
                [reward_fn(pos, a) + V[t + 1, CELL_INDEX[move(pos, a)]] for a in range(n_a)]
            )
            policy[t, i] = int(q.argmax())
            V[t, i] = float(q.max())
    return V, policy


def extract_path(policy, horizon=HORIZON, start=START):
    """Roll the DP policy forward from ``start`` at t=0."""
    pos, path, actions = start, [start], []
    for t in range(horizon):
        a = int(policy[t, CELL_INDEX[pos]])
        actions.append(a)
        pos = move(pos, a)
        path.append(pos)
        if pos == GOAL:
            break
    return path, actions


def dp_true_optimum(horizon=HORIZON):
    V, policy = finite_horizon_dp(r_true, horizon)
    path, actions = extract_path(policy, horizon)
    return {
        "return": float(V[0, CELL_INDEX[START]]),
        "steps": len(path) - 1,
        "path": path,
        "actions": [ACTION_NAMES[a] for a in actions],
        "V": V,
        "policy": policy,
    }


def dp_post_patch_optimum(horizon=HORIZON):
    """Once patched, the proxy *is* the true reward, so this must match the honest
    optimum -- and standing on the waypoint must be strictly suboptimal whenever
    the goal is still reachable."""
    V, policy = finite_horizon_dp(lambda p, a: r_proxy(p, a, True), horizon)
    path, actions = extract_path(policy, horizon)
    wp = CELL_INDEX[WAYPOINT]
    stay_gaps = []
    for t in range(horizon):
        if t + _DIST[WAYPOINT] > horizon:
            continue  # goal no longer reachable; every action is equally hopeless
        q_stay = r_proxy(WAYPOINT, 4, True) + V[t + 1, wp]
        stay_gaps.append(float(V[t, wp] - q_stay))
    return {
        "return": float(V[0, CELL_INDEX[START]]),
        "steps": len(path) - 1,
        "path": path,
        "actions": [ACTION_NAMES[a] for a in actions],
        "min_stay_suboptimality": min(stay_gaps),
        "ever_stays_on_waypoint": any(
            int(policy[t, wp]) == 4
            for t in range(horizon)
            if t + _DIST[WAYPOINT] <= horizon
        ),
    }


def dp_proxy_no_detection(horizon=HORIZON):
    """With the monitor switched off, the proxy optimum must be to farm."""
    V, policy = finite_horizon_dp(lambda p, a: r_proxy(p, a, False), horizon)
    path, actions = extract_path(policy, horizon)
    farm_steps = sum(
        1 for pos, a in zip(path[:-1], actions) if pos == WAYPOINT
    )
    return {
        "return": float(V[0, CELL_INDEX[START]]),
        "steps": len(path) - 1,
        "farm_steps": farm_steps,
        "path": path,
        "actions": [ACTION_NAMES[a] for a in actions],
    }


# --------------------------------------------------------------------------- #
# Monte Carlo over memoryless dwell policies
# --------------------------------------------------------------------------- #

def run_memoryless(monitor, q, n_episodes=12_000, seed=0, **env_kwargs):
    """Simulate the memoryless policy 'dwell on the waypoint with probability q'.

    Everywhere else -- and once patched -- the policy walks the shortest path to
    the goal. The policy is a function of (pos, patched) only, exactly like the
    observation the trained agent gets.
    """
    env = WaypointFarmEnv(monitor=monitor, seed=seed, **env_kwargs)
    rng = np.random.default_rng(seed + 99_991)
    true_returns, proxy_returns, farm_steps = [], [], []
    lengths, reached, detected, first_det = [], [], [], []

    for ep in range(n_episodes):
        env.reset(seed=None if ep else seed)
        pos, patched = START, env.patched
        terminated = truncated = False
        info = {}
        while not (terminated or truncated):
            action = farming_route_action(pos, patched, q, rng)
            _, _, terminated, truncated, info = env.step(action)
            pos, patched = env.pos, env.patched
        true_returns.append(info["episode_true_return"])
        proxy_returns.append(info["episode_proxy_return"])
        farm_steps.append(info["farm_steps"])
        lengths.append(info["episode_length"])
        reached.append(info["reached_goal"])
        detected.append(info["first_detection_step"] is not None)
        if info["first_detection_step"] is not None:
            first_det.append(info["first_detection_step"])

    return {
        "monitor": monitor,
        "q": q,
        "n_episodes": n_episodes,
        "true_return": float(np.mean(true_returns)),
        "true_return_sem": float(np.std(true_returns) / np.sqrt(n_episodes)),
        "proxy_return": float(np.mean(proxy_returns)),
        "farm_steps": float(np.mean(farm_steps)),
        "ep_len": float(np.mean(lengths)),
        "goal_rate": float(np.mean(reached)),
        "p_detected": float(np.mean(detected)),
        "mean_first_detection": float(np.mean(first_det)) if first_det else float("nan"),
    }


def sweep_dwell(monitor, qs=None, n_episodes=3_000, seed=0, **env_kwargs):
    """Sweep the dwell probability; the best q is the memoryless optimum."""
    if qs is None:
        qs = np.linspace(0.0, 1.0, 11)
    return [
        run_memoryless(monitor, float(q), n_episodes=n_episodes, seed=seed, **env_kwargs)
        for q in qs
    ]
