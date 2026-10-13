"""Step 2: the audit grid with PBRR as the overseer's correction mechanism.

Same grid, same 500-step episodes of five 100-step sub-episodes, same overseer that
audits the last W steps of each sub-episode. What changes is what happens when the
agent is caught: instead of Step 1's oracle patch, the overseer runs one round of
Preference-Based Reward Repair (src/pbrr_core.py) for that environment.

Per-environment reward functions (as in Step 1): each of the parallel envs has its
own correction g and its own preference data D. Both reset to empty at every
episode end (the reward function returns to the original proxy). The policy never
resets.

One PBRR round for an env caught at the end of sub-episode k (Algorithm 1, C1 = 0):
  1. tau1 ~ pi*_rhat: K fresh rollouts of the CURRENT policy in that env's
     pre-update situation (sub-episode k, its correction count) -- the policy being
     trained for the current repaired reward is the paper's pi*_rhat;
  2. tau2 ~ pi_ref: the fixed reference set (the released code collects the
     reference rollouts once and reuses them every iteration);
  3. all K x K cross pairs, Boltzmann labels on the true return, appended to D;
  4. g refit from scratch on all of D (this env, this episode); the new reward
     r_proxy + g is in force from the next sub-episode.

Envs whose catch history in the current episode is identical have identical
reward state, hence statistically identical PBRR data, so one round is run per
distinct history and its correction is shared by those envs (one data draw instead
of several i.i.d. ones -- documented approximation, saves most of the compute).

The agent observes the clock and its own correction count (one-hot 0..4) in place
of Step 1's patched bit; it never observes g itself.
"""

import time

import gymnasium
import numpy as np
from stable_baselines3.common.callbacks import BaseCallback

from .audit_grid import ACTIONS, BASE, build_tables
from .pbrr_core import GConfig, boltzmann_label, fit_correction
from .pbrr_grid import make_traj, rollout_subepisode, transition_features

__all__ = ["N_LEVELS", "obs_dim2", "encode_obs2", "PBRRAuditEnv", "PBRROverseer"]

N_A = len(ACTIONS)
N_LEVELS = BASE.n_sub          # correction count 0..4 (no correction after the last audit)


def obs_dim2(cfg=BASE):
    return cfg.n_pos + cfg.t_sub + cfg.n_sub + N_LEVELS + 1


def encode_obs2(cfg, t, pos, n_corr, flagged):
    """One-hot Box: pos | tau | k | correction count | audit flag. Broadcasts."""
    t, pos, n_corr, flagged = np.broadcast_arrays(
        np.asarray(t), np.asarray(pos), np.asarray(n_corr), np.asarray(flagged))
    shape = t.shape
    t, pos, n_corr, flagged = (x.reshape(-1) for x in (t, pos, n_corr, flagged))
    out = np.zeros((t.size, obs_dim2(cfg)), np.float32)
    rows = np.arange(t.size)
    out[rows, pos] = 1.0
    off = cfg.n_pos
    out[rows, off + t % cfg.t_sub] = 1.0
    off += cfg.t_sub
    out[rows, off + np.minimum(t // cfg.t_sub, cfg.n_sub - 1)] = 1.0
    off += cfg.n_sub
    out[rows, off + np.minimum(n_corr, N_LEVELS - 1)] = 1.0
    out[:, off + N_LEVELS] = flagged
    return out.reshape(shape + (out.shape[-1],))


class PBRRAuditEnv(gymnasium.Env):
    """Reward = r_proxy + g (g is set by the overseer). Detection exactly as Step 1:
    arriving on the exploit tile inside the audit window flags the sub-episode; at
    the boundary a flagged sub-episode is detected with probability p, which
    increments the correction count immediately (so the observation PPO bootstraps
    from already shows it) and marks a PBRR round as pending."""

    metadata = {"render_modes": []}

    def __init__(self, cfg=BASE, reward_scale=1.0, seed=None):
        super().__init__()
        self.cfg, self.reward_scale = cfg, reward_scale
        self.tables = build_tables(cfg)
        self.observation_space = gymnasium.spaces.Box(0.0, 1.0, (obs_dim2(cfg),), np.float32)
        self.action_space = gymnasium.spaces.Discrete(N_A)
        self._rng = np.random.default_rng(seed)
        self.t = cfg.t_ep
        self.pos = self.tables.start
        self.episode = -1
        self._reset_reward()

    def _reset_reward(self):
        self.g = np.zeros((self.cfg.n_pos, N_A))
        self.n_corr = 0
        self.flagged = False
        self.pending = False          # a PBRR round is owed for the sub-episode just ended
        self.history = ()             # sub-episode indices at which this env was caught

    # -- called by the overseer -------------------------------------------------
    def set_correction(self, g_table):
        self.g = np.asarray(g_table, float).reshape(self.cfg.n_pos, N_A)
        self.pending = False

    def state_key(self):
        return self.episode, self.history

    def _obs(self):
        return encode_obs2(self.cfg, self.t, self.pos, self.n_corr, self.flagged)

    def reset(self, *, seed=None, options=None):
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        if self.t >= self.cfg.t_ep:            # new episode: reward function and data reset
            self.t = 0
            self.episode += 1
            self._reset_reward()
        self.pos = self.tables.start
        return self._obs(), {}

    def step(self, action):
        cfg, tb = self.cfg, self.tables
        a = int(action)
        proxy = float(tb.reward[self.pos, a, 0])
        received = proxy + float(self.g[self.pos, a])
        true = float(tb.true[self.pos, a])
        on_exploit = bool(tb.bonus[self.pos, a, 0])
        in_window = cfg.in_window(self.t)
        if in_window and on_exploit:
            self.flagged = True
        self.pos = int(tb.next_pos[self.pos, a])
        self.t += 1
        info = {"received_reward": received, "proxy_reward": proxy, "true_reward": true,
                "on_exploit": on_exploit, "in_window": in_window, "detected": False}
        terminated = False
        if self.t % cfg.t_sub == 0:
            k = self.t // cfg.t_sub - 1
            detected = self.flagged and self._rng.random() < cfg.p_detect
            info["detected"] = bool(detected)
            if detected and self.t < cfg.t_ep:           # the last audit has nothing to correct
                self.n_corr += 1
                self.history = self.history + (k,)
                self.pending = True
            self.flagged = False
            self.pos = tb.start
            terminated = self.t >= cfg.t_ep
        return self._obs(), received * self.reward_scale, terminated, False, info


class PBRROverseer(BaseCallback):
    """Runs the PBRR rounds owed at each sub-episode boundary and logs training.

    One PPO rollout is exactly one sub-episode of every env (n_steps = t_sub), so
    ``_on_rollout_end`` is the boundary. Logs, per round (sub-episode) and env:
    received / original-proxy / true return, whether the env was caught, and per
    step whether it was on the exploit tile.
    """

    def __init__(self, cfg, ref_trajs, gcfg=GConfig(), k=19, beta=1.0, seed=0, verbose=False):
        super().__init__()
        self.cfg, self.ref_trajs, self.gcfg, self.k, self.beta = cfg, ref_trajs, gcfg, k, beta
        self.tables = build_tables(cfg)
        self.X = transition_features(cfg)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        self.verbose = verbose
        self.cache = {}              # (episode, history) -> (D, g_table)
        self.rounds = []             # one record per PBRR round
        self.rows = []               # one record per sub-episode (round of training)
        self.env_received, self.env_proxy, self.env_true = [], [], []
        self.on_exploit = []         # (n_rounds, t_sub, n_envs) uint8
        self.step_received, self.step_proxy, self.step_true = [], [], []   # (n_rounds, t_sub) env means
        self.caught = []             # (n_rounds, n_envs) uint8

    # -- logging ------------------------------------------------------------------
    def _on_rollout_start(self):
        env = self.training_env
        ts = env.get_attr("t")
        assert all(t % self.cfg.t_sub == 0 for t in ts), f"rollout misaligned: {ts}"
        n = env.num_envs
        self._k = int(ts[0]) // self.cfg.t_sub
        self._ncorr = np.array(env.get_attr("n_corr"))
        self._rec, self._prx, self._tru = np.zeros(n), np.zeros(n), np.zeros(n)
        self._on = np.zeros((self.cfg.t_sub, n), np.uint8)
        self._sr, self._sp, self._st = (np.zeros(self.cfg.t_sub) for _ in range(3))
        self._det = np.zeros(n, np.uint8)
        self._i = 0

    def _on_step(self):
        for j, info in enumerate(self.locals["infos"]):
            self._rec[j] += info["received_reward"]
            self._prx[j] += info["proxy_reward"]
            self._tru[j] += info["true_reward"]
            self._on[self._i, j] = info["on_exploit"]
            self._det[j] = max(self._det[j], int(info["detected"]))
        infos = self.locals["infos"]
        self._sr[self._i] = np.mean([i["received_reward"] for i in infos])
        self._sp[self._i] = np.mean([i["proxy_reward"] for i in infos])
        self._st[self._i] = np.mean([i["true_reward"] for i in infos])
        self._i += 1
        return True

    def _on_rollout_end(self):
        assert self._i == self.cfg.t_sub
        self.env_received.append(self._rec.copy())
        self.env_proxy.append(self._prx.copy())
        self.env_true.append(self._tru.copy())
        self.on_exploit.append(self._on.copy())
        self.caught.append(self._det.copy())
        self.step_received.append(self._sr.copy())
        self.step_proxy.append(self._sp.copy())
        self.step_true.append(self._st.copy())
        self.rows.append({"round": len(self.rows), "timesteps": int(self.num_timesteps), "k": self._k,
                          "received_return": float(self._rec.mean()), "proxy_return": float(self._prx.mean()),
                          "true_return": float(self._tru.mean()), "caught": float(self._det.mean()),
                          "mean_n_corr": float(self._ncorr.mean())})
        self._run_pending_rounds()

    # -- PBRR ---------------------------------------------------------------------
    def _policy_fn(self, n_corr):
        state = self.model.policy.actor_state
        cfg = self.cfg

        def fn(t, pos, flagged):
            obs = encode_obs2(cfg, t, pos, n_corr, flagged)
            p = np.asarray(state.apply_fn(state.params, obs).probs_parameter(), float)[:, :N_A]
            p = np.clip(p, 0.0, None)
            return p / p.sum(axis=1, keepdims=True)
        return fn

    def _run_pending_rounds(self):
        env = self.training_env
        pending = np.array(env.get_attr("pending"))
        if not pending.any():
            return
        keys = env.env_method("state_key")
        groups = {}
        for j in np.flatnonzero(pending):
            groups.setdefault(keys[j], []).append(int(j))
        for (episode, history), members in groups.items():
            prev = (episode, history[:-1])
            D_prev = self.cache[prev][0] if prev in self.cache else []
            k = history[-1]
            t0 = time.time()
            P, A = rollout_subepisode(self._policy_fn(len(history) - 1), self.k, self.rng,
                                      self.cfg, self.tables, t0=k * self.cfg.t_sub)
            agent = [make_traj(p, a, self.cfg, self.tables) for p, a in zip(P, A)]
            new = [(t1, t2, boltzmann_label(t1, t2, self.rng, self.beta))
                   for t1 in agent for t2 in self.ref_trajs]
            D = D_prev + new
            g, info = fit_correction(D, self.X, self.gcfg,
                                     seed=int(self.rng.integers(2 ** 31)))
            self.cache[(episode, history)] = (D, g)
            env.env_method("set_correction", g, indices=members)
            G = g.reshape(self.cfg.n_pos, N_A)
            E = self.cfg.idx(self.cfg.exploit)
            rec = {"timesteps": int(self.num_timesteps), "episode": int(episode), "k": int(k),
                   "n_round": len(history), "n_envs": len(members), "n_pairs": info["n_pairs"],
                   "n_agree": info["n_agree"], "g_dwell_E": float(G[E, 0]),
                   "max_g": float(g.max()), "min_g": float(g.min()),
                   "agent_proxy_mean": float(np.mean([t.proxy for t in agent])),
                   "agent_true_mean": float(np.mean([t.true for t in agent])),
                   "fit_loss": info["loss"], "seconds": time.time() - t0}
            self.rounds.append(rec)
            if self.verbose:
                print(f"    PBRR ep {episode} k {k} round {len(history)} envs {len(members)}: "
                      f"|D| {info['n_pairs']} |D+| {info['n_agree']} g(E) {G[E, 0]:+.0f} "
                      f"max g {g.max():+.1f} ({rec['seconds']:.1f}s)", flush=True)
        # forget other episodes' data (D resets every episode)
        cur = keys[0][0]
        self.cache = {key: v for key, v in self.cache.items() if key[0] == cur}
