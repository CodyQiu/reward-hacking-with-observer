"""PBRR for any Step 3 task: trajectories, the Eq 3 fit at the trajectory level, and
the overseer callback that runs a round whenever a copy is caught.

The objective is exactly ``src/pbrr_core.py``'s (the paper's Eq 3 as read from the
released code; see that module's docstring for every detail and source):

    mean_pairs BCE( sigmoid(R_hat(tau2) - R_hat(tau1)), label )
      + lambda * sum_pairs reg_pair,       lambda = push2zero / max(1, |D+|)  ("max1")

with R_hat(tau) = proxy(tau) + sum_t g(s_t, a_t, s_t+1). What changes is only how
the sums are formed. ``pbrr_core.fit_correction`` builds a dense (pairs x
transitions) matrix over a finite transition set. Here every *distinct* transition
row in the data is evaluated once and summed into trajectory returns with a
segment sum over (row, trajectory, count) triplets -- the same numbers, without the
pairs x transitions matrix, so it also works when the transitions are continuous.
Rows are deduplicated exactly: by transition key for tabular tasks, by identical
feature rows (e.g. an absorbing state repeated) for continuous ones.

The overseer is ``src/audit_pbrr.py``'s ``PBRROverseer`` made task-agnostic:
same Algorithm 1 round (C1 = 0), same sharing of one round between copies with an
identical catch history, same per-round and per-step logs, plus two numbers the
grid did not need -- g on the exploit's own transitions and g on the reference's
(honest) transitions, the correction's collateral damage.
"""

import time
from dataclasses import dataclass, field

import jax
import jax.numpy as jnp
import numpy as np
import optax
from stable_baselines3.common.callbacks import BaseCallback

from ..pbrr_core import GConfig, boltzmann_label, mlp_apply, mlp_init
from .protocol import encode_obs, g_apply
from .task import exploit_mask

__all__ = ["Rollout", "rollouts", "policy_probs_fn", "fit_correction_rows", "g_on_rows", "Overseer"]


# ---------------------------------------------------------------------------------
# Trajectories
# ---------------------------------------------------------------------------------


@dataclass
class Rollout:
    """One sub-episode. ``keys`` (tabular) or ``feats`` (continuous) per step."""

    keys: np.ndarray | None
    feats: np.ndarray | None
    proxy_steps: np.ndarray
    true_steps: np.ndarray
    meta: dict = field(default_factory=dict)

    @property
    def proxy(self):
        return float(self.proxy_steps.sum())

    @property
    def true(self):
        return float(self.true_steps.sum())

    @property
    def length(self):
        return len(self.proxy_steps)

    @property
    def exploit(self):
        return exploit_mask(self.proxy_steps, self.true_steps)


def rollouts(batch, policy_fn, proto, rng, t0=0, n_corr=0):
    """One sub-episode (t_sub steps from a fresh start) in each copy of ``batch``.

    ``policy_fn(batch, t, n_corr, flagged) -> (n, A)`` action probabilities. The
    audit flag the agent observes is tracked under the suite-wide rule (proxy !=
    true in the window), exactly as in the training env.
    """
    n, T = batch.n, proto.t_sub
    batch.reset()
    flagged = np.zeros(n, bool)
    nc = np.full(n, n_corr, np.int64)
    keys, feats, prx, tru = [], [], np.zeros((n, T)), np.zeros((n, T))
    for tau in range(T):
        t = t0 + tau
        probs = np.asarray(policy_fn(batch, t, nc, flagged), float)
        cum = probs.cumsum(axis=1)
        a = (rng.random((n, 1)) < cum / cum[:, -1:]).argmax(axis=1)
        out = batch.step(a)
        prx[:, tau], tru[:, tau] = out.proxy, out.true
        if out.key is not None:
            keys.append(out.key)
        else:
            feats.append(out.feat)
        if proto.in_window(t):
            flagged |= out.exploit
    K = np.stack(keys, axis=1) if keys else None
    X = np.stack(feats, axis=1) if feats else None
    return [Rollout(None if K is None else K[i], None if X is None else X[i], prx[i], tru[i])
            for i in range(n)]


def policy_probs_fn(model, proto, n_actions):
    """The PPO policy as ``policy_fn`` for ``rollouts`` (reads the live parameters)."""
    state = model.policy.actor_state

    def fn(batch, t, n_corr, flagged):
        obs = encode_obs(proto, batch.obs(), t, n_corr, flagged)
        p = np.asarray(state.apply_fn(state.params, obs).probs_parameter(), float)[:, :n_actions]
        p = np.clip(p, 0.0, None)
        return p / p.sum(axis=1, keepdims=True)
    return fn


# ---------------------------------------------------------------------------------
# Eq 3 at the trajectory level
# ---------------------------------------------------------------------------------


def _bucket(n, lo=64):
    s = lo
    while s < n:
        s *= 2
    return s


def _rows_and_triplets(trajs, task):
    """Distinct transition rows of ``trajs`` and (row, traj, count) triplets."""
    if trajs[0].keys is not None:
        allk = np.concatenate([t.keys for t in trajs])
        tid = np.concatenate([np.full(t.length, i) for i, t in enumerate(trajs)])
        ukeys, inv = np.unique(allk, return_inverse=True)
        X = task.g_rows_from_keys(ukeys)
    else:
        allx = np.concatenate([t.feats for t in trajs])
        tid = np.concatenate([np.full(t.length, i) for i, t in enumerate(trajs)])
        X, inv = np.unique(allx, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
    pair = inv.astype(np.int64) * len(trajs) + tid
    up, cnt = np.unique(pair, return_counts=True)
    return X.astype(np.float32), up // len(trajs), up % len(trajs), cnt.astype(np.float64)


_FIT = {}


def _compiled(cfg):
    key = (cfg.lr, cfg.weight_decay, cfg.epochs)
    if key in _FIT:
        return _FIT[key]
    tx = optax.chain(optax.add_decayed_weights(cfg.weight_decay), optax.adam(cfg.lr)) \
        if cfg.weight_decay > 0 else optax.adam(cfg.lr)

    def loss(params, X, row, traj, cnt, proxy, i1, i2, y, pmask, reg, coef, n_pairs):
        g = mlp_apply(params, X)
        R = proxy + jax.ops.segment_sum(cnt * g[row], traj, num_segments=proxy.shape[0])
        d = R[i2] - R[i1]
        bce = jnp.sum(pmask * (jnp.logaddexp(0.0, d) - y * d)) / n_pairs
        return bce + coef * jnp.sum(reg * g * g)

    grad = jax.grad(loss)

    @jax.jit
    def fit(params, *args):
        state = tx.init(params)

        def body(_, carry):
            p, s = carry
            upd, s = tx.update(grad(p, *args), s, p)
            return optax.apply_updates(p, upd), s

        p, _ = jax.lax.fori_loop(0, cfg.epochs, body, (params, state))
        return p, loss(p, *args)

    _FIT[key] = fit
    return fit


def fit_correction_rows(pairs, task, cfg=GConfig(), seed=0):
    """Refit g from scratch on ``pairs`` = [(tau1, tau2, label)] (tau1 from the agent,
    tau2 from the reference, label 1 = tau2 preferred). Returns (params, info)."""
    if not pairs:
        raise ValueError("no preferences")
    trajs, index = [], {}
    for t1, t2, _ in pairs:
        for t in (t1, t2):
            if id(t) not in index:
                index[id(t)] = len(trajs)
                trajs.append(t)
    X, row, traj, cnt = _rows_and_triplets(trajs, task)
    n_tr, P = len(trajs), len(pairs)
    i1 = np.array([index[id(a)] for a, _, _ in pairs])
    i2 = np.array([index[id(b)] for _, b, _ in pairs])
    y = np.array([lab for _, _, lab in pairs], float)
    proxy = np.array([t.proxy for t in trajs])
    length = np.array([t.length for t in trajs], float)
    n_reg = np.zeros(n_tr)
    det = (proxy[i2] > proxy[i1]).astype(float)          # code: argmax([p1, p2]), ties -> tau1
    agree = det == y
    np.add.at(n_reg, i1[agree], 1.0)
    np.add.at(n_reg, i2[agree], 1.0)
    pref = np.where(y == 1.0, i2, i1)[~agree]
    np.add.at(n_reg, pref, 1.0)
    n_agree = int(agree.sum())
    reg = np.bincount(row, weights=cnt * n_reg[traj] / length[traj], minlength=len(X))
    if not cfg.use_regularization:
        coef = 0.0
    elif n_agree == 0:
        coef = 0.0 if cfg.no_agree == "skip" else cfg.push2zero
    else:
        coef = cfg.push2zero / n_agree

    R_, T_, N_, P_ = _bucket(len(X)), _bucket(len(row)), _bucket(n_tr, 16), _bucket(P)
    pad = lambda a, m, dt: np.concatenate([np.asarray(a, dt), np.zeros(m - len(a), dt)])
    Xp = np.zeros((R_, X.shape[1]), np.float32)
    Xp[:len(X)] = X
    args = (Xp, pad(row, T_, np.int32), pad(traj, T_, np.int32), pad(cnt, T_, np.float32),
            pad(proxy, N_, np.float32), pad(i1, P_, np.int32), pad(i2, P_, np.int32),
            pad(y, P_, np.float32), pad(np.ones(P), P_, np.float32), pad(reg, R_, np.float32),
            np.float32(coef), np.float32(P))
    sizes = [X.shape[1]] + [cfg.width] * (cfg.n_layers - 1) + [1]
    params = mlp_init(jax.random.PRNGKey(seed), sizes, cfg.init)
    params, final = _compiled(cfg)(params, *args)
    g_rows = np.asarray(g_apply(params, jnp.asarray(X)), float)
    info = {"loss": float(final), "n_pairs": P, "n_agree": n_agree, "n_disagree": P - n_agree,
            "reg_coef": float(coef), "n_rows": len(X), "n_trajs": n_tr}
    return params, {**info, "g_rows": g_rows, "rows": X}


def g_on_rows(params, X, chunk=65_536):
    """Evaluate a correction network on many rows (chunked, padded to fixed shapes)."""
    X = np.asarray(X, np.float32)
    out = np.zeros(len(X))
    for i in range(0, len(X), chunk):
        part = X[i:i + chunk]
        P = np.zeros((_bucket(len(part)), X.shape[1]), np.float32)
        P[:len(part)] = part
        out[i:i + len(part)] = np.asarray(g_apply(params, jnp.asarray(P)), float)[:len(part)]
    return out


def _traj_rows(trajs, task):
    if trajs[0].keys is not None:
        return task.g_rows_from_keys(np.concatenate([t.keys for t in trajs]))
    return np.concatenate([t.feats for t in trajs])


# ---------------------------------------------------------------------------------
# The overseer
# ---------------------------------------------------------------------------------


class Overseer(BaseCallback):
    """Runs the PBRR rounds owed at each sub-episode boundary and logs training.

    One PPO rollout is exactly one sub-episode of every copy (n_steps = t_sub), so
    ``_on_rollout_end`` is the boundary. Logs per round (sub-episode) and copy:
    received / original-proxy / true return, caught; per step whether the copy
    exploited; per step the env-mean of the three rewards.
    """

    def __init__(self, task, proto, venv, ref_trajs, gcfg=GConfig(), k=19, beta=1.0, seed=0,
                 verbose=False):
        super().__init__()
        self.task, self.proto, self.venv = task, proto, venv
        self.ref_trajs, self.gcfg, self.k, self.beta = ref_trajs, gcfg, k, beta
        self.rng = np.random.default_rng(seed)
        self.batch = task.make_batch(k, seed=seed + 31_337)
        self.verbose = verbose
        self.cache = {}              # (episode, history) -> D
        self.rounds, self.rows = [], []
        self.env_received, self.env_proxy, self.env_true = [], [], []
        self.on_exploit, self.caught = [], []
        self.step_received, self.step_proxy, self.step_true = [], [], []
        self._ref_rows = _traj_rows(ref_trajs, task)

    def _on_rollout_start(self):
        v, T = self.venv, self.proto.t_sub
        assert v.t % T == 0, f"rollout misaligned with sub-episodes: t = {v.t}"
        n = v.num_envs
        self._k = v.t // T
        self._ncorr = v.n_corr.copy()
        self._rec, self._prx, self._tru = np.zeros(n), np.zeros(n), np.zeros(n)
        self._on = np.zeros((T, n), np.uint8)
        self._sr, self._sp, self._st = np.zeros(T), np.zeros(T), np.zeros(T)
        self._det = np.zeros(n, np.uint8)
        self._i = 0

    def _on_step(self):
        L = self.venv.last
        self._rec += L["received"]
        self._prx += L["proxy"]
        self._tru += L["true"]
        self._on[self._i] = L["exploit"]
        self._det |= L["detected"].astype(np.uint8)
        self._sr[self._i] = L["received"].mean()
        self._sp[self._i] = L["proxy"].mean()
        self._st[self._i] = L["true"].mean()
        self._i += 1
        return True

    def _on_rollout_end(self):
        assert self._i == self.proto.t_sub, f"a round must be {self.proto.t_sub} steps, got {self._i}"
        for lst, arr in ((self.env_received, self._rec), (self.env_proxy, self._prx),
                         (self.env_true, self._tru), (self.on_exploit, self._on), (self.caught, self._det),
                         (self.step_received, self._sr), (self.step_proxy, self._sp),
                         (self.step_true, self._st)):
            lst.append(arr.copy())
        self.rows.append({"round": len(self.rows), "timesteps": int(self.num_timesteps), "k": self._k,
                          "received_return": float(self._rec.mean()), "proxy_return": float(self._prx.mean()),
                          "true_return": float(self._tru.mean()), "caught": float(self._det.mean()),
                          "mean_n_corr": float(self._ncorr.mean())})
        self.run_pending_rounds()

    def run_pending_rounds(self):
        v = self.venv
        pending = np.flatnonzero(v.pending)
        if len(pending) == 0:
            return
        groups = {}
        for j in pending:
            groups.setdefault(v.state_key(j), []).append(int(j))
        policy = policy_probs_fn(self.model, self.proto, self.task.n_actions)
        for (episode, history), members in groups.items():
            t0 = time.time()
            D_prev = self.cache.get((episode, history[:-1]), [])
            k = history[-1]
            agent = rollouts(self.batch, policy, self.proto, self.rng, t0=k * self.proto.t_sub,
                             n_corr=len(history) - 1)
            new = [(a, r, boltzmann_label(a, r, self.rng, self.beta)) for a in agent for r in self.ref_trajs]
            D = D_prev + new
            params, info = fit_correction_rows(D, self.task, self.gcfg, seed=int(self.rng.integers(2 ** 31)))
            self.cache[(episode, history)] = D
            v.set_correction(members, params)
            rec = {"timesteps": int(self.num_timesteps), "episode": int(episode), "k": int(k),
                   "n_round": len(history), "n_envs": len(members), "n_pairs": info["n_pairs"],
                   "n_agree": info["n_agree"], "fit_loss": info["loss"],
                   "max_g": float(info["g_rows"].max()), "min_g": float(info["g_rows"].min()),
                   "agent_proxy_mean": float(np.mean([a.proxy for a in agent])),
                   "agent_true_mean": float(np.mean([a.true for a in agent]))}
            rec.update(self._g_summary(params, agent))
            rec["seconds"] = time.time() - t0
            self.rounds.append(rec)
            if self.verbose:
                print(f"    PBRR ep {episode} k {k} round {len(history)} envs {len(members)}: |D| "
                      f"{info['n_pairs']} |D+| {info['n_agree']} g(exploit) {rec['g_exploit']:+.2f} "
                      f"g(ref) {rec['g_ref']:+.2f} ({rec['seconds']:.1f}s)", flush=True)
        cur = v.episode
        self.cache = {key: d for key, d in self.cache.items() if key[0] == cur}

    def _g_summary(self, params, agent):
        """Mean g per step on the agent's exploit transitions, on its other transitions,
        and on the reference's transitions (collateral damage to honest behaviour)."""
        rows = _traj_rows(agent, self.task)
        ex = np.concatenate([a.exploit for a in agent])
        g = g_on_rows(params, rows)
        g_ref = g_on_rows(params, self._ref_rows)
        return {"g_exploit": float(g[ex].mean()) if ex.any() else float("nan"),
                "g_other": float(g[~ex].mean()) if (~ex).any() else float("nan"),
                "g_ref": float(g_ref.mean()), "agent_exploit_frac": float(ex.mean())}
