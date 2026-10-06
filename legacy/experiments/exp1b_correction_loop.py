"""Exp 1b (EXTENSION) -- the correction loop over repeated episodes.

Exp 1 asks what a patient agent does once. This asks what the overseer ends up
with after many rounds. The environment becomes episodic (an episode ends at GOAL
or after ``HORIZON`` steps) and the patch persists across episodes, so corrections
accumulate: episode k starts in whatever patch state episode k-1 ended in.

Choosing the true-objective metric is the whole difficulty here, and the obvious
choice is wrong. "Did the agent reach GOAL within the horizon" does *not* separate
the regimes: a farming agent gets patched partway through an episode and then walks
to GOAL with the time it has left, and an agent solving the finite-horizon problem
exactly will farm and *then* collect the one-time R_goal on its last few steps,
because that bonus is free money once the horizon is in sight. Both finish. What
farming destroys is not completion, it is *promptness* -- the task takes 4 moves
and the farmer delivers it around step 20. So the true objective here is

    prompt completion: reached GOAL within PROMPT_STEPS steps

and the raw completion rate is reported alongside it to show why it is the wrong
instrument.

Proxy returns are only comparable between runs that share a reward function
(CLAUDE.md 7). The hiding runs and the no-gap control differ *only* in the
observation model, so their proxy returns sit on one panel. The deterrence run has
a different reward function (R_goal raised), so it appears only where the metric is
the true objective.

Run:  python experiments/exp1b_correction_loop.py
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.environments import (
    CORRIDOR_BASE,
    FARM_POS,
    GOAL_POS,
    N_POS,
    START_POS,
    build_corridor_mdp,
    state_of,
)
from src.plotting import SERIES, plot_lines
from src.report import CheckLog
from src.solver import finite_horizon, policy_iteration

GAMMA = 0.95
HORIZON = 25
N_EPISODES = 40
N_RUNS = 400
SEED = 20260725

# START -> GOAL is 4 moves. Six allows slack without allowing a farming detour.
PROMPT_STEPS = 6

# The deterrence regime: blind spot left wide open, but the task made worth doing.
# Exp 1 located that threshold at R_goal ~ 17.44, so 20 is comfortably past it.
R_GOAL_DETERRENCE = 20.0
# A blind spot deep enough that evasion lasts many rounds rather than half of one.
P_UNWATCH_DEEP = 0.005


def simulate_episodes(
    R, P, policy, horizon, n_episodes, n_runs, seed, time_indexed=False
):
    """Roll the policy through consecutive episodes with a persistent patch.

    Transitions are sampled from the same ``P`` the solver was given, so the
    simulation cannot drift from the model that was solved. ``policy`` is either
    stationary (S,) or time-indexed (horizon, S) when ``time_indexed``.
    """
    rng = np.random.default_rng(seed)
    cdf = P.cumsum(axis=2)
    completed = np.zeros((n_runs, n_episodes), dtype=bool)
    steps = np.full((n_runs, n_episodes), horizon + 1, dtype=int)
    proxy = np.zeros((n_runs, n_episodes))
    farm_steps = np.zeros((n_runs, n_episodes), dtype=int)
    patched_start = np.zeros((n_runs, n_episodes), dtype=int)
    first_correction = np.full(n_runs, -1, dtype=int)

    for run in range(n_runs):
        patched = 0
        for ep in range(n_episodes):
            patched_start[run, ep] = patched
            pos = START_POS
            for t in range(horizon):
                s = state_of(pos, patched)
                a = int(policy[t, s]) if time_indexed else int(policy[s])
                proxy[run, ep] += R[s, a]
                if pos in FARM_POS and patched == 0:
                    farm_steps[run, ep] += 1
                u = rng.random()
                s_next = int(np.searchsorted(cdf[s, a], u))
                pos, patched = s_next % N_POS, s_next // N_POS
                if patched == 1 and first_correction[run] < 0:
                    first_correction[run] = ep
                if pos == GOAL_POS:
                    completed[run, ep] = True
                    steps[run, ep] = t + 1
                    break

    prompt = steps <= PROMPT_STEPS
    return {
        "completed": completed,
        "steps": steps,
        "prompt": prompt,
        "proxy": proxy,
        "farm_steps": farm_steps,
        "patched_start": patched_start,
        "first_correction": first_correction,
        "completion_rate": completed.mean(axis=0),
        "prompt_rate": prompt.mean(axis=0),
        "proxy_mean": proxy.mean(axis=0),
        "farm_mean": farm_steps.mean(axis=0),
    }


def regime(name, policy_kind="discounted", **params):
    p = {**CORRIDOR_BASE, **params}
    R, P, _ = build_corridor_mdp(**p)
    if policy_kind == "discounted":
        _, policy, _, _ = policy_iteration(R, P, GAMMA)
        sim = simulate_episodes(R, P, policy, HORIZON, N_EPISODES, N_RUNS, SEED)
    else:
        _, policy = finite_horizon(R, P, GAMMA, HORIZON)
        sim = simulate_episodes(
            R, P, policy, HORIZON, N_EPISODES, N_RUNS, SEED, time_indexed=True
        )
    corrected = sim["first_correction"] >= 0
    sim.update(
        name=name,
        params=p,
        R=R,
        P=P,
        policy=policy,
        mean_first_correction=(
            float(sim["first_correction"][corrected].mean())
            if corrected.any()
            else float("nan")
        ),
        never_corrected=float((~corrected).mean()),
        total_prompt=float(sim["prompt"].sum(axis=1).mean()),
        total_completions=float(sim["completed"].sum(axis=1).mean()),
        total_proxy=float(sim["proxy"].sum(axis=1).mean()),
        total_farm=float(sim["farm_steps"].sum(axis=1).mean()),
    )
    return sim


def main():
    log = CheckLog("EXPERIMENT 1b (EXTENSION) -- the correction loop over episodes")
    log.note(
        f"gamma={GAMMA}, horizon={HORIZON} steps/episode, {N_EPISODES} episodes, "
        f"{N_RUNS} runs, seed={SEED}; the patch persists across episodes"
    )
    log.note(
        f"true objective = prompt completion (GOAL within {PROMPT_STEPS} steps; "
        "the shortest path is 4 moves)"
    )

    hiding = regime("hiding ($p_{unwatch}$=0.05)")
    deep = regime(
        f"hiding, deep blind spot ($p_{{unwatch}}$={P_UNWATCH_DEEP:g})",
        p_unwatch=P_UNWATCH_DEEP,
    )
    control = regime(
        "CONTROL: no blind spot ($p_{unwatch}=p_{watch}$=0.6)",
        p_unwatch=CORRIDOR_BASE["p_watch"],
    )
    deter = regime(
        f"deterrence ($R_{{goal}}$={R_GOAL_DETERRENCE:g}, blind spot open)",
        R_goal=R_GOAL_DETERRENCE,
    )

    for r in (hiding, deep, control, deter):
        log.note(
            f"{r['name']}: prompt ep0 = {r['prompt_rate'][0]:.3f}, "
            f"prompt episodes = {r['total_prompt']:.1f}/{N_EPISODES}, "
            f"raw completions = {r['total_completions']:.1f}/{N_EPISODES}, "
            f"first correction at episode {r['mean_first_correction']:.2f}, "
            f"farmed steps = {r['total_farm']:.1f}"
        )

    # ---------------------------------------------------------------- #
    # 1. why raw completion is the wrong instrument
    # ---------------------------------------------------------------- #
    log.check(
        "raw completion does NOT separate hiding from the control (motivating promptness)",
        hiding["total_completions"] > 0.95 * N_EPISODES
        and control["total_completions"] > 0.95 * N_EPISODES,
        f"raw completions {hiding['total_completions']:.1f} (hiding) vs "
        f"{control['total_completions']:.1f} (control) out of {N_EPISODES} -- "
        "a farming agent gets patched mid-episode and finishes with the time left",
    )
    log.finding(
        "raw task completion is not a usable true-objective metric in the episodic "
        "setting: the farmer is corrected partway through an episode and still "
        "reaches GOAL, so completion saturates in every regime. Promptness is what "
        "exploitation actually costs the overseer."
    )

    # ---------------------------------------------------------------- #
    # 2. the contrast that is the deliverable
    # ---------------------------------------------------------------- #
    log.check(
        "deterrence regime: the true objective is met promptly in every episode",
        deter["prompt_rate"].min() == 1.0,
        f"min prompt rate over episodes = {deter['prompt_rate'].min():.3f}",
    )
    log.check(
        "hiding regime: the true objective is missed in the first episode",
        hiding["prompt_rate"][0] < 0.05,
        f"episode-0 prompt rate = {hiding['prompt_rate'][0]:.3f} "
        f"(mean {hiding['steps'][:, 0].mean():.1f} steps to finish, vs 4 optimal)",
    )
    log.check(
        "hiding regime: strictly more proxy reward is extracted than in the control",
        hiding["proxy"][:, 0].mean() > 2.0 * control["proxy"][:, 0].mean(),
        f"episode-0 proxy return {hiding['proxy'][:, 0].mean():.2f} vs "
        f"{control['proxy'][:, 0].mean():.2f} for the control "
        "(identical reward function, so this is a fair comparison)",
    )
    log.check(
        "deep blind spot: correction is evaded for many consecutive rounds",
        deep["mean_first_correction"] > 5.0
        and control["total_prompt"] - deep["total_prompt"] > 8.0,
        f"first correction at episode {deep['mean_first_correction']:.1f} "
        f"(control: {control['mean_first_correction']:.2f}); "
        f"{control['total_prompt'] - deep['total_prompt']:.1f} fewer prompt "
        f"deliveries than the control over {N_EPISODES} episodes",
    )
    log.check_control(
        "no blind spot: the objective is met promptly from episode 0 and always after",
        control["prompt_rate"][0] > 0.8 and control["prompt_rate"][1:].min() > 0.99,
        f"episode-0 prompt rate {control['prompt_rate'][0]:.3f} "
        f"(vs {hiding['prompt_rate'][0]:.3f} with the blind spot), "
        f"min over later episodes {control['prompt_rate'][1:].min():.3f}",
    )
    log.check_control(
        "no blind spot: correction lands strictly sooner, and far less is farmed",
        control["mean_first_correction"] < hiding["mean_first_correction"]
        and control["total_farm"] < hiding["total_farm"],
        f"first correction at episode {control['mean_first_correction']:.2f} vs "
        f"{hiding['mean_first_correction']:.2f}; farmed steps "
        f"{control['total_farm']:.1f} vs {hiding['total_farm']:.1f}",
    )
    log.check_control(
        "no blind spot: deep evasion disappears -- the exploit is caught at once "
        "and barely any reward is extracted",
        control["mean_first_correction"] < 1.0
        and deep["mean_first_correction"] > 5.0
        and control["total_farm"] < deep["total_farm"] / 20.0,
        f"first correction episode {control['mean_first_correction']:.2f} (no gap) vs "
        f"{deep['mean_first_correction']:.1f} (deep gap); farmed steps "
        f"{control['total_farm']:.1f} vs {deep['total_farm']:.1f} "
        f"({deep['total_farm'] / max(control['total_farm'], 1e-9):.0f}x)",
    )

    # ---------------------------------------------------------------- #
    # 3. robustness: the exact finite-horizon optimal policy
    # ---------------------------------------------------------------- #
    fh = regime("hiding, finite-horizon optimal", policy_kind="finite_horizon")
    log.check(
        "conclusion survives under the exact finite-horizon optimal policy",
        fh["prompt_rate"][0] < 0.05 and fh["total_prompt"] < control["total_prompt"],
        f"episode-0 prompt rate {fh['prompt_rate'][0]:.3f}, "
        f"prompt in {fh['total_prompt']:.1f}/{N_EPISODES} episodes "
        f"(discounted policy gave {hiding['total_prompt']:.1f})",
    )
    log.finding(
        f"the finite-horizon optimum farms and *then* banks the one-time task reward "
        f"({fh['total_completions']:.1f}/{N_EPISODES} raw completions, but prompt in "
        f"only {fh['total_prompt']:.1f}) -- exploitation and apparent task success are "
        "not mutually exclusive once the episode ends, which is precisely why the "
        "overseer needs a timing- or cost-sensitive true metric, not a success flag."
    )

    # ---------------------------------------------------------------- #
    # 4. how deep must the blind spot be?
    # ---------------------------------------------------------------- #
    pus = np.array([0.6, 0.4, 0.25, 0.15, 0.1, 0.05, 0.03, 0.02, 0.01, 0.005, 0.002])
    firsts, prompts, proxies = [], [], []
    for pu in pus:
        r = regime(f"pu={pu}", p_unwatch=float(pu))
        firsts.append(r["mean_first_correction"] if r["never_corrected"] < 1 else np.nan)
        prompts.append(r["total_prompt"])
        proxies.append(r["total_proxy"])
    firsts, prompts, proxies = np.array(firsts), np.array(prompts), np.array(proxies)
    log.check(
        "the durability of hiding scales with the depth of the blind spot",
        np.all(np.diff(firsts[~np.isnan(firsts)]) >= -1e-9)
        and np.all(np.diff(prompts) <= 1e-9),
        f"first correction slips from episode {np.nanmin(firsts):.2f} (no blind spot) "
        f"to {np.nanmax(firsts):.2f} (p_unwatch={pus[-1]:g}); prompt episodes fall "
        f"from {prompts[0]:.1f} to {prompts[-1]:.1f}",
    )
    log.finding(
        f"at the base p_unwatch = {CORRIDOR_BASE['p_unwatch']:g} the blind spot buys "
        f"only about {hiding['mean_first_correction']:.1f} episodes of evasion -- "
        f"{HORIZON} steps at 5% per step is {1 - 0.95 ** (HORIZON - 3):.0%} cumulative "
        f"exposure per episode, so the correction loop still closes fast. Sustained "
        f"evasion needs a *deep* blind spot: at p_unwatch = {pus[-1]:g} the first "
        f"correction slips to episode {firsts[-1]:.1f} and the task is delivered "
        f"promptly in only {prompts[-1]:.1f} of {N_EPISODES} episodes."
    )

    # ---------------------------------------------------------------- #
    # 5. figures
    # ---------------------------------------------------------------- #
    episodes = np.arange(N_EPISODES)
    colors = {
        deter["name"]: SERIES[0],
        control["name"]: SERIES[1],
        hiding["name"]: SERIES[2],
    }
    log.figure(
        plot_lines(
            episodes,
            [
                (
                    "TRUE objective\nprompt completions (rate)",
                    {
                        deter["name"]: deter["prompt_rate"],
                        control["name"]: control["prompt_rate"],
                        hiding["name"]: hiding["prompt_rate"],
                    },
                ),
                (
                    "PROXY reward per episode\n(comparable regimes only)",
                    {
                        control["name"]: control["proxy_mean"],
                        hiding["name"]: hiding["proxy_mean"],
                    },
                ),
            ],
            "exp1b_correction_loop.png",
            "Exp 1b  ·  does the overseer's objective get met over repeated rounds?",
            "episode",
            colors=colors,
            subtitle=(
                f"mean of {N_RUNS} runs; the patch persists across episodes. Episode 0 "
                "is the divergence: the hiding agent banks proxy reward while the task "
                "goes undelivered. The deterrence run is absent from the lower panel on "
                "purpose -- its reward function differs, so its proxy return is not "
                "comparable."
            ),
        )
    )

    log.figure(
        plot_lines(
            pus,
            [
                ("mean episode of\nfirst correction", {"first correction": firsts}),
                (
                    f"prompt completions\nin {N_EPISODES} episodes",
                    {"prompt": prompts},
                ),
                ("total proxy reward\nextracted", {"proxy": proxies}),
            ],
            "exp1b_blindspot_depth.png",
            "Exp 1b  ·  how deep the blind spot must be to evade correction for long",
            "detection rate on the unwatched tile  $p_{unwatch}$  "
            "(log scale; no blind spot at the right)",
            colors={"first correction": SERIES[0], "prompt": SERIES[0], "proxy": SERIES[0]},
            markers={"first correction": "o", "prompt": "o", "proxy": "o"},
            logx=True,
            show_legend=False,
            subtitle=(
                "one series per panel, so no legend is needed. A shallow blind spot is "
                "closed within a round or two; the evasion that actually costs the "
                "overseer needs the overseer to be nearly blind."
            ),
        )
    )

    return log.summary()


if __name__ == "__main__":
    main()
