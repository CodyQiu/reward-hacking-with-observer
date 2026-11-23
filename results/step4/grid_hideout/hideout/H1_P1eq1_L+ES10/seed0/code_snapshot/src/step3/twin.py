"""The twin (GConfig.offset_rule = "twin"; docs/step4_indiff.md, "The twin") and the agent's practice rounds.

**Pricing.** The overseer prices each correction with the twin, its own second PPO policy. The twin is trained to
maximise ONE round of the reward in force with nothing at stake: no audit and no future, so every round is terminal.
Like the agent, it sees the base state, the clock and the correction count, but not which correction was drawn. So
at each level it learns the best round of the *mean* correction. A correction to level c, from reward r_old to
r_new, raises the level by [V(twin@c-1; r_old) - V(twin@c; r_new)] / T. Each V is the mean return of the frozen
twin's rollouts at that level, rescored under that reward. The twin's actions depend only on what it observes, never
on the reward, so one set of rollouts per level serves every correction of a block (common starts, common random
numbers across levels). The twin is frozen for a block of episodes, so the agent's play never moves its own price.

**The bank.** The twin trains on one-round problems at every level. Their corrections come from a bank: the
corrections the overseer installed in the agent's recent episodes (``CorrectionBank.add``, as applied: fines-only
chains), plus counterfactual ones when real catches are rare. A counterfactual correction is PBRR fitted on the
agent's own rollouts as if it had been caught (``Twin.counterfactual``), so levels the agent avoids still get data.

**Practice** (``twin.practice`` > 0). That fraction of the agent's env copies are practice copies. There the audit
has no consequence. Instead, at each boundary, with probability ``twin.force_p``, the overseer installs the next
correction of a chain drawn from the same bank, priced by the same twin. Practice copies look identical to the
others (no new observation), and the agent learns there by its own PPO, from the corrected reward. Training logs and
metrics cover the real copies only.

**Every level** (``twin.all_levels``, 2026-11-21; docs/step4_indiff.md, "The twin at every level"). Without it the
twin trains only up to the deepest chain in the bank. An agent that is honest after one correction never makes a
deeper chain, and the counterfactual chain stops there too, so the twin never plays levels 2-4. Yet a second
correction is priced with its level-2 play: an untrained network that underplays, so the level overpays and a
deliberate re-correction pays (Boat Race: 321-379 per round against 200). With ``all_levels``:
- the counterfactual chain always runs to the deepest level. Where the agent's play at a level no longer uses the bug,
  the next correction is fitted on fresh rollouts of its play at the last level where it did -- as if it were caught
  doing that again, which is exactly the re-correction a farmer would trigger;
- one is added per block while fewer than ``cf_min`` chains reach the deepest level (real chains are rarely deep);
- a level the twin has never trained at is priced with its play at the deepest level it has trained at (a real
  policy, so it cannot overstate the best round), saved with the model (``state`` / ``load_state``).

Settings: config group ``twin`` (not part of the game key, ``TWIN_DEFAULTS``).
"""

import gymnasium
import jax.numpy as jnp
import numpy as np
from sbx import PPO
from stable_baselines3.common.vec_env import VecEnv

from ..pbrr_core import boltzmann_label
from .pbrr import fit_correction_rows, policy_probs_fn, rollout_returns, rollouts
from .protocol import MinCorrection, encode_obs, g_apply, obs_dim

__all__ = ["TWIN_DEFAULTS", "CorrectionBank", "TwinVecEnv", "Twin", "g_on_copies"]

TWIN_DEFAULTS = {
    "n_envs": 16,          # the twin's env copies
    "block": 8,            # episodes per block: the twin trains, then is frozen for pricing, once per block
    "rounds": 40,          # twin PPO rounds per block (40 rounds x 16 copies = one block of the agent's samples)
    "eval": 256,           # rollouts per level for pricing
    "practice": 0.0,       # fraction of the agent's env copies that are practice copies (0 = the pure twin)
    "force_p": 0.5,        # practice: probability of installing the next correction at a boundary
    "bank_episodes": 64,   # the bank keeps corrections from this many recent episodes
    "cf_min": 4,           # fewer chains than this in the bank -> one counterfactual chain per block
    "all_levels": False,   # train and price the twin at every level (module docstring, "Every level")
}


def g_on_copies(params, feat, n):
    """A correction (network, MinCorrection, or None) on the rows ``feat``, padded to ``n`` rows (fixed shapes)."""
    if params is None or len(feat) == 0:
        return np.zeros(len(feat))
    X = np.zeros((n, feat.shape[1]), np.float32)
    X[:len(feat)] = feat
    g = params.apply(jnp.asarray(X)) if isinstance(params, MinCorrection) else g_apply(params, jnp.asarray(X))
    return np.asarray(g, float)[:len(feat)]


class CorrectionBank:
    """The corrections in force along each catch history of recent episodes: key (episode, history) -> the chain
    (the object in force after the 1st, 2nd, ... correction). A chain that is a prefix of a longer one recorded in
    the same episode is not drawn for practice."""

    def __init__(self, keep_episodes=64):
        self.keep = int(keep_episodes)
        self.chains = {}                  # (episode, history) -> (chain tuple, source)

    def add(self, episode, history, chain, source="real"):
        self.chains[(int(episode), tuple(history))] = (tuple(chain), source)

    def prune(self, episode):
        self.chains = {k: v for k, v in self.chains.items() if k[0] > episode - self.keep}

    def depth(self):
        return max((len(c) for c, _ in self.chains.values()), default=0)

    def count(self, level=1):
        return sum(len(c) >= level for c, _ in self.chains.values())

    def at_level(self, level, rng):
        """A correction in force at ``level`` (None at level 0, or if the bank has none that deep)."""
        if level <= 0:
            return None
        cands = [c for c, _ in self.chains.values() if len(c) >= level]
        return cands[int(rng.integers(len(cands)))][level - 1] if cands else None

    def maximal(self):
        keys = list(self.chains)
        out = []
        for e, h in keys:
            c, _ = self.chains[(e, h)]
            longer = any(e2 == e and len(h2) > len(h) and h2[:len(h)] == h and self.chains[(e2, h2)][0][:len(c)] == c
                         for e2, h2 in keys)
            if not longer:
                out.append(c)
        return out

    def chain(self, rng):
        """A chain for a practice copy: a maximal one, uniformly; () if the bank is empty."""
        m = self.maximal()
        return m[int(rng.integers(len(m)))] if m else ()


class TwinVecEnv(VecEnv):
    """``n_envs`` one-round problems for the twin. Each round, every copy draws a level (uniform over 0..the bank's
    depth); the copies at a level share one correction drawn from the bank. The reward is proxy + that correction (no
    level: a constant does not change the best round), and the observation is the agent's encoding at round 0 with
    that correction count and the audit flag at 0. Every round ends in ``done`` (nothing after it counts)."""

    def __init__(self, task, proto, bank, n_envs=16, reward_scale=1.0, seed=0):
        self.task, self.proto, self.bank, self.reward_scale = task, proto, bank, float(reward_scale)
        self.render_mode = None
        self.batch = task.make_batch(n_envs, seed=seed)
        self.rng = np.random.default_rng(seed + 31)
        space = gymnasium.spaces.Box(-np.inf, np.inf, (obs_dim(proto, task.obs_dim),), np.float32)
        super().__init__(n_envs, space, gymnasium.spaces.Discrete(task.n_actions))
        self.t = 0
        self.level = np.zeros(n_envs, np.int64)
        self.corr = {}
        self._draw()

    def _draw(self):
        top = min(self.bank.depth(), self.proto.n_levels - 1)
        self.level = self.rng.integers(0, top + 1, self.num_envs)
        self.corr = {c: self.bank.at_level(c, self.rng) for c in range(1, top + 1)}

    def _obs(self):
        return encode_obs(self.proto, self.batch.obs(), self.t, self.level, np.zeros(self.num_envs, bool))

    def reset(self):
        if self._seeds[0] is not None:
            self.batch.seed(self._seeds[0])
            self.rng = np.random.default_rng(self._seeds[0] + 31)
            self._seeds = [None] * self.num_envs
        self.t = 0
        self._draw()
        self.batch.reset()
        return self._obs()

    def step_async(self, actions):
        self._actions = np.asarray(actions).reshape(-1).astype(np.int64)

    def step_wait(self):
        n = self.num_envs
        out = self.batch.step(self._actions)
        rew = np.asarray(out.proxy, float).copy()
        for c, p in self.corr.items():
            idx = np.flatnonzero(self.level == c)
            if p is not None and len(idx):
                rew[idx] += g_on_copies(p, out.feat[idx], n)
        self.last = {"proxy": out.proxy, "feat": out.feat, "level": self.level.copy(), "received": rew.copy()}
        self.t += 1
        dones = np.zeros(n, bool)
        infos = [{} for _ in range(n)]
        if self.t >= self.proto.t_sub:
            dones[:] = True
            term = self._obs()
            for j in range(n):
                infos[j]["terminal_observation"] = term[j]
            self.t = 0
            self._draw()
            self.batch.reset()
        return self._obs(), (rew * self.reward_scale).astype(np.float32), dones, infos

    def close(self):
        if hasattr(self.batch, "close"):
            self.batch.close()

    def get_attr(self, attr_name, indices=None):
        if not hasattr(self, attr_name):
            raise AttributeError(attr_name)
        return [getattr(self, attr_name)] * len(self._get_indices(indices))

    def set_attr(self, attr_name, value, indices=None):
        setattr(self, attr_name, value)

    def env_method(self, method_name, *method_args, indices=None, **method_kwargs):
        raise NotImplementedError("use the TwinVecEnv methods directly")

    def env_is_wrapped(self, wrapper_class, indices=None):
        return [False] * len(self._get_indices(indices))


class Twin:
    """The twin learner, its bank and its frozen rollouts (see the module docstring)."""

    def __init__(self, task, proto, ppo_kwargs, net_arch, reward_scale, gcfg, seed=0, cfg=None):
        self.task, self.proto, self.gcfg = task, proto, gcfg
        self.cfg = {**TWIN_DEFAULTS, **(cfg or {})}
        self.bank = CorrectionBank(self.cfg["bank_episodes"])
        self.venv = TwinVecEnv(task, proto, self.bank, int(self.cfg["n_envs"]), reward_scale, seed=seed * 1000 + 577)
        ppo = dict(ppo_kwargs)
        ppo["n_steps"] = proto.t_sub
        ppo["batch_size"] = min(int(ppo.get("batch_size", 64)), int(self.cfg["n_envs"]) * proto.t_sub)
        self.model = PPO("MlpPolicy", self.venv, seed=seed + 11, policy_kwargs=dict(net_arch=list(net_arch)),
                         verbose=0, **ppo)
        self.rng = np.random.default_rng(seed + 4_242)
        self.eval_batch = task.make_batch(int(self.cfg["eval"]), seed=seed * 1000 + 911)
        self.trajs = {}
        self.last_block = None
        self.n_counterfactual = 0
        self.trained_top = 0              # the deepest level the twin has trained at (all_levels: the price backstop)
        self.freeze()

    # -- state saved beside the model (all_levels) ------------------------------------------
    def state(self):
        return {"trained_top": int(self.trained_top), "all_levels": bool(self.cfg["all_levels"])}

    def load_state(self, d):
        self.trained_top = int(d.get("trained_top", 0))

    def price_level(self, c):
        """The level whose frozen play prices level ``c``: c itself, or with all_levels the deepest level the twin
        has trained at, if it has never trained at c (its play there is an untrained network's)."""
        c = int(min(c, self.proto.n_levels - 1))
        return min(c, self.trained_top) if self.cfg["all_levels"] else c

    # -- training -----------------------------------------------------------------------
    def train_block(self, ent_coef=None, lr=None):
        if ent_coef is not None:
            self.model.ent_coef = ent_coef
        if lr is not None:
            self.model.lr_schedule = (lambda v: (lambda _: v))(lr)
        self.trained_top = max(self.trained_top, min(self.bank.depth(), self.proto.n_levels - 1))
        n = int(self.cfg["rounds"]) * self.venv.num_envs * self.proto.t_sub
        self.model.learn(total_timesteps=n, reset_num_timesteps=False, progress_bar=False)

    def freeze(self):
        """Rollouts of the twin's current parameters at every level, from common starts with common random
        numbers: the pricing of the next block. With all_levels, a level the twin has never trained at is played
        as the deepest level it has (``price_level``)."""
        fn = policy_probs_fn(self.model, self.proto, self.task.n_actions)      # a snapshot of the parameters
        s = int(self.rng.integers(2 ** 31))
        self.trajs = {}
        for c in range(self.proto.n_levels):
            self.eval_batch.seed(s)
            self.trajs[c] = rollouts(self.eval_batch, fn, self.proto, np.random.default_rng(s), t0=0,
                                     n_corr=self.price_level(c))

    def counterfactual(self, overseer, episode):
        """One chain fitted as if the agent had been caught at every boundary: correction c is PBRR (the run's own
        fit, pairs accumulated as in an episode) on the agent's own rollouts at level c-1, in round c-1. Without
        all_levels it stops when those rollouts never touch the bug (nothing to correct). With all_levels it goes on
        to the deepest level: correction c is then fitted on fresh rollouts of the agent's play at the last level
        where it did use the bug (caught doing that again). No chain if even level 0 never uses it. Added to the
        bank as source "counterfactual"."""
        policy = policy_probs_fn(overseer.model, self.proto, self.task.n_actions)
        T, D, chain, prev, last_bug = self.proto.t_sub, [], (), None, None

        def uses_bug(trajs):
            return any(np.any(a.proxy_steps != a.true_steps) for a in trajs)

        for c in range(1, self.proto.n_sub):
            agent = rollouts(overseer.batch, policy, self.proto, overseer.rng, t0=(c - 1) * T, n_corr=c - 1)
            if uses_bug(agent):
                last_bug = (c - 1, agent)
            elif not self.cfg["all_levels"] or last_bug is None:
                break
            else:                                     # caught again doing what it did at the last level it used the bug
                j, old = last_bug
                agent = rollouts(overseer.batch, policy, self.proto, overseer.rng, t0=j * T, n_corr=j)
                if not uses_bug(agent):
                    agent = old
            D = D + [(a, r, boltzmann_label(a, r, overseer.rng, overseer.beta)) for a in agent
                     for r in overseer.ref_trajs]
            p, _ = fit_correction_rows(D, self.task, self.gcfg, seed=int(overseer.rng.integers(2 ** 31)))
            new = (prev if prev is not None else MinCorrection(())).then(p) if self.gcfg.fine_only else p
            chain, prev = chain + (new,), new
        if chain:
            self.n_counterfactual += 1
            self.bank.add(episode, ("cf", self.n_counterfactual), chain, "counterfactual")
        return len(chain)

    def on_episode_start(self, overseer, episode, ent_coef=None, lr=None):
        """At the first episode of each block: prune the bank, add a counterfactual chain if it holds too few,
        train the twin one block, and freeze it for pricing. Returns True if a block ran."""
        if self.last_block is not None and episode - self.last_block < int(self.cfg["block"]):
            return False
        self.last_block = episode
        self.bank.prune(episode)
        deep = self.proto.n_sub - 1 if self.cfg["all_levels"] else 1    # all_levels: chains to the deepest level
        if self.bank.count(deep) < int(self.cfg["cf_min"]):
            self.counterfactual(overseer, episode)
        self.train_block(ent_coef, lr)
        self.freeze()
        return True

    # -- pricing ------------------------------------------------------------------------
    def value(self, level, params):
        """V(twin@level; proxy + params): the frozen rollouts' mean return, rescored (level excluded)."""
        level = int(min(level, self.proto.n_levels - 1))
        return float(rollout_returns(self.trajs[level], self.task, params).mean())   # trajs[c]: played at price_level(c)

    def price(self, level, old_params, new_params):
        """(V before, V after) of a correction to ``level``: the level rises by their difference / T."""
        return self.value(level - 1, old_params), self.value(level, new_params)
