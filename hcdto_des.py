"""
hcdto_des.py -- Discrete-event implementation of Human-Centric Digital Twin Orchestration (HC-DTO).

Executes Algorithm 1 of the manuscript task by task:
  * a Poisson stream of tasks (demand, data size, deadline, origin node);
  * K heterogeneous edge nodes + one cloud node, each with capacity, energy rate,
    transmission latency, reliability and an operator-familiarity rating;
  * per-task normalized estimates L_hat, E_hat, Q_hat, node trust tau_i
    (tau_i = alpha R_i + beta H_i + gamma A_i, updated online) and human-preference
    compatibility H_ij;
  * composite score S_ij = w_L L + w_E E + w_Q Q + w_T (1 - tau_i) + w_H (1 - H_ij),
    capacity-feasible argmin placement;
  * stochastic operator intervention u_j ~ Bernoulli(g(delta_j, phi, p, kappa)) with a
    logistic g in the normalized score margin delta_j; on intervention the operator
    re-selects among the top-3 candidates by human compatibility;
  * per-decision contribution decomposition (explanation trace);
  * injected node failures; per-task trust-weighted quality Q_j.

Baselines share the same task streams, node populations and seeds:
  cloud, local, random, greedy (min projected queue), dt (same score with w_T = w_H = 0).

All model constants are module-level and reported in the manuscript.
"""
from __future__ import annotations
import numpy as np, pandas as pd
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- constants
SEED = 42
N_TRIALS = 12
NODE_COUNTS = [20, 50, 100, 200, 400]
LOAD_MAP = {"low": 0.8, "medium": 1.2, "high": 1.8, "extreme": 2.4}
FAILURE_RATES = [0.0, 0.05, 0.10, 0.20, 0.30]
TASKS_PER_NODE = 25            # tasks per run = TASKS_PER_NODE * K
UTIL_PER_LOAD = 0.6            # mean edge utilization = UTIL_PER_LOAD * load factor

# policy weight vectors  [w_L, w_E, w_Q, w_T, w_H]  (sum to 1)
POLICY_WEIGHTS = {
    "dt":                 np.array([0.35, 0.25, 0.40, 0.00, 0.00]),
    "hc_dt_balanced":     np.array([0.25, 0.20, 0.20, 0.20, 0.15]),
    "hc_dt_reliability":  np.array([0.15, 0.15, 0.20, 0.35, 0.15]),
    "hc_dt_latency":      np.array([0.45, 0.10, 0.25, 0.10, 0.10]),
    "hc_dt_energy":       np.array([0.20, 0.35, 0.20, 0.15, 0.10]),
    "hc_dt_override":     np.array([0.20, 0.15, 0.15, 0.20, 0.30]),
}
BASE_POLICIES = ["cloud", "local", "random", "greedy", "dt"]
HUMAN_ONLY = "human_only"      # operator heuristic: most familiar node among ATTENTION randomly inspected available nodes
ATTENTION = 5
HC_POLICIES = [p for p in POLICY_WEIGHTS if p.startswith("hc_")]
ALL_POLICIES = BASE_POLICIES + HC_POLICIES
ABLATIONS = {   # variants of hc_dt_balanced with one component removed (renormalized)
    "hc_dt_balanced_noenergy": np.array([0.25, 0.00, 0.20, 0.20, 0.15]),
    "hc_dt_balanced_notrust":  np.array([0.25, 0.20, 0.20, 0.00, 0.15]),
    "hc_dt_balanced_noqueue":  np.array([0.25, 0.20, 0.00, 0.20, 0.15]),
}
# trust model tau_i = ALPHA R_i + BETA H_i + GAMMA A_i
ALPHA, BETA, GAMMA = 0.5, 0.3, 0.2
EWMA_R = 0.10                   # reliability EWMA rate
# intervention model  P(u_j = 1) = sigmoid(a_p + B*(1 - delta_j) + C*phi - D*kappa)
INTERCEPT = {"hc_dt_balanced": -2.6, "hc_dt_reliability": -1.6, "hc_dt_latency": -3.2,
             "hc_dt_energy": -2.9, "hc_dt_override": -1.3}
B_MARGIN, C_FAIL, D_PROF = 2.0, 3.0, 1.0
KAPPA = 0.5                     # operator-proficiency surrogate (0..1)
TOPK_REVIEW = 3
# decision quality  Q_j = LC C_j + LT tau + LH H
LC, LT, LH = 0.5, 0.3, 0.2
TAU_SAFE = 0.60                 # safety-preserving assignment: tau_i >= TAU_SAFE and projected finish <= deadline
# node population
CLOUD_CAP_PER_NODE, CLOUD_TX, CLOUD_E = 1.0, 3.0, 1.6   # cloud capacity = CLOUD_CAP_PER_NODE * K (elastic data centre), tx latency, energy per work unit
BW = 2.0                        # data units per time unit for edge transmission
FAIL_EPOCH, FAIL_SCALE = 2.0, 0.5   # outage epochs (time units) and per-epoch outage probability = phi * FAIL_SCALE
EXPLAIN = ["latency", "energy", "queue", "trust", "human_preference"]


@dataclass
class Nodes:
    K: int
    cap: np.ndarray; erate: np.ndarray; tx: np.ndarray; rel: np.ndarray; fam: np.ndarray
    free_at: np.ndarray = field(default=None)
    R: np.ndarray = field(default=None); Hh: np.ndarray = field(default=None)
    n_done: np.ndarray = field(default=None); n_ok: np.ndarray = field(default=None)
    down_until: np.ndarray = field(default=None)

def make_nodes(K: int, rng: np.random.Generator) -> Nodes:
    cap = rng.lognormal(mean=0.0, sigma=0.35, size=K + 1)          # ~1 work unit / time unit
    erate = rng.uniform(0.6, 1.4, size=K + 1)
    tx = rng.uniform(0.05, 0.6, size=K + 1)
    rel = rng.uniform(0.70, 0.99, size=K + 1)
    fam = rng.beta(2.5, 2.0, size=K + 1)                             # operator familiarity / preference rating
    cap[K], tx[K], erate[K], rel[K], fam[K] = CLOUD_CAP_PER_NODE * K, CLOUD_TX, CLOUD_E, 0.97, 0.5   # last index = cloud
    n = Nodes(K, cap, erate, tx, rel, fam)
    n.free_at = np.zeros(K + 1); n.R = rel.copy(); n.Hh = rel.copy()
    n.n_done = np.zeros(K + 1); n.n_ok = np.zeros(K + 1); n.down_until = np.full(K + 1, -1.0)
    return n

def make_tasks(K: int, load: float, rng: np.random.Generator):
    M = TASKS_PER_NODE * K
    # arrival rate scaled so that mean utilization of the edge population ~ load
    mean_demand = 1.0
    rate = UTIL_PER_LOAD * load * K / mean_demand   # tasks per time unit
    arr = np.cumsum(rng.exponential(1.0 / rate, size=M))
    demand = rng.lognormal(mean=-0.1, sigma=0.4, size=M)
    data = rng.uniform(0.2, 1.5, size=M)
    deadline = arr + rng.uniform(2.0, 6.0, size=M) * demand.clip(0.5, None)
    origin = rng.integers(0, K, size=M)
    return arr, demand, data, deadline, origin

def _sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

def simulate(policy: str, K: int, load: float, phi: float, trial: int, weights=None,
             kappa: float = KAPPA) -> dict:
    """Run one scenario. Returns the metric dictionary used by the manuscript."""
    rng = np.random.default_rng(SEED + 1000 * trial + K)          # shared node/task stream across policies
    nodes = make_nodes(K, rng)
    arr, demand, data, deadline, origin = make_tasks(K, load, rng)
    fail_rng = np.random.default_rng(SEED + 7919 * trial + 31 * K + 1)   # failure events shared across policies
    pol_id = sum(ord(ch) for ch in policy) % 1000                     # deterministic policy offset
    dec_rng = np.random.default_rng(SEED + 104729 * trial + 17 * K + pol_id)  # policy-specific draws
    M = len(arr)
    if weights is None and policy in POLICY_WEIGHTS: weights = POLICY_WEIGHTS[policy]
    if weights is None and policy in ABLATIONS: weights = ABLATIONS[policy]
    w = None if weights is None else weights / weights.sum()
    is_hc = policy.startswith("hc_")
    a_p = INTERCEPT.get(policy.replace("_noenergy", "").replace("_notrust", "").replace("_noqueue", ""), -2.6)

    lat = np.zeros(M); en = np.zeros(M); ok = np.zeros(M, bool); failed = np.zeros(M, bool)
    interv = np.zeros(M, bool); accepted = np.ones(M, bool); safe = np.zeros(M, bool)
    Q = np.zeros(M); contrib = np.zeros((M, 5)); top = np.empty(M, dtype=object)
    idx_all = np.arange(K + 1)
    next_epoch = 0.0

    for j in range(M):
        t = arr[j]
        # ---- node failure injection: at every epoch of FAIL_EPOCH time units each node goes down
        #      with probability phi * FAIL_SCALE for a random outage of 1-3 time units
        while t >= next_epoch:
            if phi > 0:
                down = fail_rng.random(K) < phi * FAIL_SCALE
                nodes.down_until[:K] = np.where(down, next_epoch + fail_rng.uniform(1.0, 3.0, size=K), nodes.down_until[:K])
            next_epoch += FAIL_EPOCH
        avail = nodes.down_until < t
        # ---- candidate estimates
        start = np.maximum(t + nodes.tx + data[j] / BW, nodes.free_at)
        service = demand[j] / nodes.cap
        finish = start + service
        L_raw = finish - t
        E_raw = nodes.erate * demand[j] + 0.1 * data[j] * (idx_all == K)
        Q_raw = np.maximum(nodes.free_at - t, 0.0)
        A = avail.astype(float)
        tau = ALPHA * nodes.R + BETA * nodes.Hh + GAMMA * A
        H = nodes.fam
        def norm(x):
            lo, hi = x.min(), x.max(); return (x - lo) / (hi - lo + 1e-9)
        Lh, Eh, Qh = norm(L_raw), norm(E_raw), norm(Q_raw)
        feasible = avail.copy()
        # ---- placement
        if policy == "cloud":
            i = K
        elif policy == "local":
            i = origin[j]
        elif policy == "random":
            cands = idx_all[:K][feasible[:K]]; i = dec_rng.choice(cands) if len(cands) else origin[j]
        elif policy == "greedy":
            q = np.where(feasible, Q_raw, np.inf); i = int(np.argmin(q))
        elif policy == HUMAN_ONLY:
            # operator heuristic with bounded attention: inspect ATTENTION random available nodes, pick the most familiar idle one
            cands = idx_all[:K][feasible[:K]]
            if len(cands) == 0: i = origin[j]
            else:
                look = dec_rng.choice(cands, size=min(ATTENTION, len(cands)), replace=False)
                idle = look[Q_raw[look] <= 0.0]          # operator prefers idle nodes, then the most familiar one
                i = int(idle[np.argmax(H[idle])]) if len(idle) else int(look[np.argmin(Q_raw[look])])
            interv[j] = True; accepted[j] = False
        else:
            terms = np.stack([Lh, Eh, Qh, 1 - tau, 1 - H], axis=1) * w          # (K+1, 5)
            S = terms.sum(axis=1); S[~feasible] = np.inf
            order = np.argsort(S); i = int(order[0])
            # explanation trace of the AI recommendation
            c = terms[i]; contrib[j] = c / (c.sum() + 1e-12); top[j] = EXPLAIN[int(np.argmax(c))]
            # operator intervention (HC policies only)
            if is_hc:
                s0, s1 = S[order[0]], S[order[1]] if len(order) > 1 else S[order[0]]
                delta = float(np.clip((s1 - s0) / (abs(s0) + 1e-9), 0, 1))   # normalized score margin
                p_int = _sigmoid(a_p + B_MARGIN * (1 - delta) + C_FAIL * phi - D_PROF * kappa)
                if dec_rng.random() < p_int:
                    interv[j] = True
                    topk = order[:TOPK_REVIEW]; topk = topk[np.isfinite(S[topk])]
                    i_h = int(topk[np.argmax(H[topk])])
                    accepted[j] = (i_h == i); i = i_h
        # ---- execute
        if not avail[i]:
            failed[j] = True; lat[j] = np.nan; en[j] = np.nan
        else:
            # failure during service
            if fail_rng.random() < phi * 1.5 * (1 - nodes.rel[i]):
                failed[j] = True; lat[j] = np.nan; en[j] = np.nan
                nodes.free_at[i] = finish[i]
            else:
                nodes.free_at[i] = finish[i]
                lat[j] = L_raw[i]; en[j] = E_raw[i]; ok[j] = finish[i] <= deadline[j]
        # ---- trust update and quality
        outcome = 0.0 if failed[j] else (1.0 if ok[j] else 0.5)
        nodes.n_done[i] += 1; nodes.n_ok[i] += outcome
        nodes.R[i] = (1 - EWMA_R) * nodes.R[i] + EWMA_R * outcome
        nodes.Hh[i] = nodes.n_ok[i] / nodes.n_done[i]
        safe[j] = (tau[i] >= TAU_SAFE) and (not failed[j]) and (finish[i] <= deadline[j])
        Q[j] = LC * outcome + LT * tau[i] + LH * H[i]

    done = ~failed
    horizon = arr[-1] - arr[0]
    out = dict(policy=policy, num_nodes=K, load_factor=load, failure_rate=phi, trial=trial,
               avg_latency=float(np.nanmean(lat)), avg_energy=float(np.nanmean(en)),
               deadline_success_rate=float(ok.mean()), task_failure_ratio=float(failed.mean()),
               throughput=float(done.sum() / horizon),
               operator_intervention_rate=float(interv.mean()) if (is_hc or policy == HUMAN_ONLY) else 0.0,
               # AI-recommendation retention rate (ARR in the manuscript): fraction of ALL tasks
               # for which the AI recommendation was retained (either not reviewed, or reviewed and accepted).
               operator_acceptance_rate=float(accepted.mean()) if (is_hc or policy == HUMAN_ONLY) else 1.0,
               safety_assignment_ratio=float(safe.mean()),
               trust_weighted_quality=float(Q.mean()))
    if w is not None:
        cs = contrib.mean(axis=0)
        for k, name in enumerate(EXPLAIN): out[f"contrib_{name}"] = float(cs[k])
        vals, counts = np.unique(top[top != None].astype(str), return_counts=True)
        out["top_explanation_reason"] = str(vals[np.argmax(counts)]) if len(vals) else "none"
        out["explanation_consistency"] = float(counts.max() / counts.sum()) if len(vals) else 0.0
    else:
        for name in EXPLAIN: out[f"contrib_{name}"] = 0.0
        out["top_explanation_reason"] = "not_applicable"; out["explanation_consistency"] = 0.0
    return out


def run_grid(node_counts, load, phi, policies=None, trials=N_TRIALS, weights_map=None, load_name=None):
    rows = []
    policies = ALL_POLICIES if policies is None else policies
    for K in node_counts:
        for pol in policies:
            for tr in range(trials):
                wm = None if weights_map is None else weights_map.get(pol)
                r = simulate(pol, K, load, phi, tr, weights=wm); r["load_name"] = load_name; rows.append(r)
    return pd.DataFrame(rows)

def summarize(df, keys):
    num = [c for c in df.select_dtypes(include="number").columns if c not in keys + ["trial"]]
    g = df.groupby(keys)[num].agg(["mean", "std"])
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    return g.reset_index()
