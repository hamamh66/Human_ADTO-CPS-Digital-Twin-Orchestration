"""
hcdto_info.py -- Information-integration experiments on top of the HC-DTO discrete-event simulator.

The base simulator (hcdto_des.py) scores every candidate node with the *current* state of every
edge twin. This module generalizes that loop along two axes while leaving the base results untouched:

  1. Twin-state freshness.  Queue state reaches the orchestrator only at synchronization epochs
     separated by `sync` time units. Three twin models are available:
       "fresh"  -- current state (the base simulator);
       "stale"  -- the snapshot taken at the last synchronization epoch;
       "reckon" -- the last snapshot corrected with the dispatches made since then by the task's
                   own dispatcher (dead reckoning). The task stream is split over `dispatchers`
                   decision points by origin node; a dispatcher knows only its own dispatches.
     Execution always uses the true node state; only the estimates used for scoring are affected.
     Node availability is assumed to be signalled immediately (heartbeat) in all twin models.
     In these experiments a task outcome enters the node's outcome history when the task completes
     (feedback = "completion"), not when it is dispatched, so that outcome history cannot serve as
     an instantaneous proxy for queue state.

  2. Information streams.  The integrated inputs of the placement decision are grouped by source:
       "queue"       -- live queue state of the edge twins (projected start time and queue term);
       "energy"      -- per-node energy model (energy term);
       "reliability" -- outcome history of each node (trust term);
       "familiarity" -- supervisory operator-familiarity rating (human-preference term).
     Static node descriptors (capacity, transmission latency) and availability are always present.
     Removing a stream removes every use of it from the score, which differs from removing a score
     term: the latency term of the base score also depends on queue state.

With sync = 0, twin = "fresh", all streams and intervention enabled, `simulate_info` reproduces
`hcdto_des.simulate` exactly (checked by `self_check`).
"""
from __future__ import annotations
import heapq, itertools, math
import numpy as np, pandas as pd
import hcdto_des as h

STREAMS = ("queue", "energy", "reliability", "familiarity")


def simulate_info(policy: str, K: int, load: float, phi: float, trial: int, weights=None,
                  kappa: float = h.KAPPA, sync: float = 0.0, twin: str = "fresh",
                  dispatchers: int = 1, streams=STREAMS, intervention: bool = True,
                  feedback: str = "dispatch") -> dict:
    """One scenario with configurable twin-state freshness and information streams.

    feedback = "dispatch"   -- the task outcome enters the node's outcome history when the task is
                               dispatched (the convention of the base simulator);
    feedback = "completion" -- the outcome enters the history when the task completes or fails, so
                               that outcome history cannot anticipate the queue state."""
    assert twin in ("fresh", "stale", "reckon") and feedback in ("dispatch", "completion")
    rng = np.random.default_rng(h.SEED + 1000 * trial + K)
    nodes = h.make_nodes(K, rng)
    arr, demand, data, deadline, origin = h.make_tasks(K, load, rng)
    fail_rng = np.random.default_rng(h.SEED + 7919 * trial + 31 * K + 1)
    pol_id = sum(ord(ch) for ch in policy) % 1000
    dec_rng = np.random.default_rng(h.SEED + 104729 * trial + 17 * K + pol_id)
    M = len(arr)
    if weights is None and policy in h.POLICY_WEIGHTS: weights = h.POLICY_WEIGHTS[policy]
    assert policy == "greedy" or weights is not None, "score-based policy or greedy expected"
    use_q, use_e = "queue" in streams, "energy" in streams
    use_r, use_f = "reliability" in streams, "familiarity" in streams
    w = None
    if weights is not None:
        w = np.array(weights, dtype=float).copy()
        if not use_e: w[1] = 0.0
        if not use_q: w[2] = 0.0
        if not use_r: w[3] = 0.0
        if not use_f: w[4] = 0.0
        w = w / w.sum()
    is_hc = policy.startswith("hc_") and intervention
    a_p = h.INTERCEPT.get(policy, -2.6)
    G = max(1, int(dispatchers))
    fresh = (twin == "fresh") or sync <= 0.0

    lat = np.zeros(M); en = np.zeros(M); ok = np.zeros(M, bool); failed = np.zeros(M, bool)
    interv = np.zeros(M, bool); accepted = np.ones(M, bool); safe = np.zeros(M, bool)
    Qual = np.zeros(M); disagree = np.zeros(M, bool); age = np.zeros(M)
    idx_all = np.arange(K + 1)
    next_epoch = 0.0
    next_sync, last_sync = 0.0, 0.0
    est = np.zeros((G, K + 1))                      # per-dispatcher estimate of free_at
    pending = []                                    # (report time, sequence, node, outcome) awaiting completion

    def register(i, outcome):
        nodes.n_done[i] += 1; nodes.n_ok[i] += outcome
        nodes.R[i] = (1 - h.EWMA_R) * nodes.R[i] + h.EWMA_R * outcome
        nodes.Hh[i] = nodes.n_ok[i] / nodes.n_done[i]

    def norm(x):
        lo, hi = x.min(), x.max(); return (x - lo) / (hi - lo + 1e-9)

    def score(free_view, t, j, tau, H, feasible):
        """Scores and recommendation computed from a given view of the node queues."""
        ready = t + nodes.tx + data[j] / h.BW
        start = np.maximum(ready, free_view) if use_q else ready
        L_raw = start + demand[j] / nodes.cap - t
        Q_raw = np.maximum(free_view - t, 0.0) if use_q else np.zeros(K + 1)
        if policy == "greedy":
            q = np.where(feasible, Q_raw, np.inf)
            return None, None, int(np.argmin(q))
        E_raw = nodes.erate * demand[j] + 0.1 * data[j] * (idx_all == K)
        terms = np.stack([norm(L_raw), norm(E_raw), norm(Q_raw), 1 - tau, 1 - H], axis=1) * w
        S = terms.sum(axis=1); S[~feasible] = np.inf
        order = np.argsort(S)
        return S, order, int(order[0])

    for j in range(M):
        t = arr[j]
        while t >= next_epoch:
            if phi > 0:
                down = fail_rng.random(K) < phi * h.FAIL_SCALE
                nodes.down_until[:K] = np.where(down, next_epoch + fail_rng.uniform(1.0, 3.0, size=K), nodes.down_until[:K])
            next_epoch += h.FAIL_EPOCH
        if not fresh:
            while t >= next_sync:                    # synchronization epoch: every dispatcher receives the true state
                est[:] = nodes.free_at; last_sync = next_sync; next_sync += sync
        while pending and pending[0][0] <= t:       # outcomes of tasks that have completed by now
            _, _, i_p, o_p = heapq.heappop(pending); register(i_p, o_p)
        avail = nodes.down_until < t
        feasible = avail.copy()
        A = avail.astype(float)
        tau = h.ALPHA * nodes.R + h.BETA * nodes.Hh + h.GAMMA * A
        H = nodes.fam
        g = int(origin[j]) % G
        view = nodes.free_at if fresh else est[g]
        age[j] = 0.0 if fresh else t - last_sync
        S, order, i = score(view, t, j, tau, H, feasible)
        if not fresh:                                # recommendation that current state would have produced
            _, _, i_ref = score(nodes.free_at, t, j, tau, H, feasible)
            disagree[j] = (i_ref != i)
        if is_hc:
            s0, s1 = S[order[0]], S[order[1]] if len(order) > 1 else S[order[0]]
            delta = float(np.clip((s1 - s0) / (abs(s0) + 1e-9), 0, 1))
            p_int = h._sigmoid(a_p + h.B_MARGIN * (1 - delta) + h.C_FAIL * phi - h.D_PROF * kappa)
            if dec_rng.random() < p_int:
                interv[j] = True
                topk = order[:h.TOPK_REVIEW]; topk = topk[np.isfinite(S[topk])]
                i_h = int(topk[np.argmax(H[topk])])
                accepted[j] = (i_h == i); i = i_h
        # ---- execution on the true node state
        ready_i = t + nodes.tx[i] + data[j] / h.BW
        service_i = demand[j] / nodes.cap[i]
        finish_i = max(ready_i, nodes.free_at[i]) + service_i
        E_i = nodes.erate[i] * demand[j] + (0.1 * data[j] if i == K else 0.0)
        if not avail[i]:
            failed[j] = True; lat[j] = np.nan; en[j] = np.nan
        else:
            if fail_rng.random() < phi * 1.5 * (1 - nodes.rel[i]):
                failed[j] = True; lat[j] = np.nan; en[j] = np.nan
            else:
                lat[j] = finish_i - t; en[j] = E_i; ok[j] = finish_i <= deadline[j]
            nodes.free_at[i] = finish_i
            if twin == "reckon" and not fresh:       # the dispatcher logs its own dispatch
                est[g, i] = max(ready_i, est[g, i]) + service_i
        outcome = 0.0 if failed[j] else (1.0 if ok[j] else 0.5)
        if feedback == "dispatch" or not avail[i]:  # a refused dispatch is known at once
            register(i, outcome)
        else:
            heapq.heappush(pending, (finish_i, j, i, outcome))
        safe[j] = (tau[i] >= h.TAU_SAFE) and (not failed[j]) and (finish_i <= deadline[j])
        Qual[j] = h.LC * outcome + h.LT * tau[i] + h.LH * H[i]

    done = ~failed
    return dict(policy=policy, num_nodes=K, load_factor=load, failure_rate=phi, trial=trial,
                sync=sync, twin="fresh" if fresh else twin, dispatchers=G,
                streams="+".join(s for s in STREAMS if s in streams) or "none",
                intervention=bool(is_hc), feedback=feedback,
                avg_latency=float(np.nanmean(lat)), p95_latency=float(np.nanpercentile(lat, 95)),
                avg_energy=float(np.nanmean(en)),
                deadline_success_rate=float(ok.mean()), task_failure_ratio=float(failed.mean()),
                operator_intervention_rate=float(interv.mean()),
                operator_acceptance_rate=float(accepted.mean()),
                safety_assignment_ratio=float(safe.mean()), trust_weighted_quality=float(Qual.mean()),
                recommendation_disagreement=float(disagree.mean()), mean_state_age=float(age.mean()))


# --------------------------------------------------------------------------- experiment families
SYNC_GRID = [0.0, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0]
FRESH_POLICIES = ["dt", "hc_dt_balanced", "hc_dt_latency", "greedy"]
DISPATCHER_GRID = [1, 4, 20, 100]


def run_freshness(K=100, load=1.2, phi=0.10, trials=h.N_TRIALS, sync_grid=SYNC_GRID,
                  policies=FRESH_POLICIES, verbose=True) -> pd.DataFrame:
    """Stale-snapshot twin versus synchronization interval, with the queue-blind reference."""
    rows = []
    for pol in policies:
        for sync in sync_grid:
            for tr in range(trials):
                rows.append(simulate_info(pol, K, load, phi, tr, sync=sync, twin="stale", feedback="completion"))
            if verbose: print(f"  freshness K={K} load={load} {pol:16s} sync={sync:<5} done", flush=True)
        if pol != "greedy":                          # greedy uses queue state only; it has no queue-blind form
            for tr in range(trials):
                r = simulate_info(pol, K, load, phi, tr, streams=[s for s in STREAMS if s != "queue"], feedback="completion")
                r["twin"] = "queue_blind"; rows.append(r)
    return pd.DataFrame(rows)


def run_reckoning(K=100, load=1.2, phi=0.10, trials=h.N_TRIALS, sync_grid=SYNC_GRID,
                  dispatcher_grid=DISPATCHER_GRID, policy="dt", verbose=True) -> pd.DataFrame:
    """Dead-reckoning twin: snapshot plus the dispatcher's own dispatch log."""
    rows = []
    for G in dispatcher_grid:
        for sync in sync_grid:
            if sync == 0.0: continue
            for tr in range(trials):
                rows.append(simulate_info(policy, K, load, phi, tr, sync=sync, twin="reckon", dispatchers=G, feedback="completion"))
        if verbose: print(f"  reckoning K={K} {policy} dispatchers={G} done", flush=True)
    return pd.DataFrame(rows)


def run_coalitions(policy="hc_dt_balanced", K=100, load=1.2, phi=0.10, trials=h.N_TRIALS,
                   sync=0.0, verbose=True) -> pd.DataFrame:
    """All 16 coalitions of the four information streams (operator intervention disabled)."""
    rows = []
    for r_ in range(len(STREAMS) + 1):
        for S in itertools.combinations(STREAMS, r_):
            for tr in range(trials):
                rows.append(simulate_info(policy, K, load, phi, tr, sync=sync,
                                          twin="stale" if sync > 0 else "fresh",
                                          streams=S, intervention=False, feedback="completion"))
    if verbose: print(f"  coalitions {policy} K={K} load={load} phi={phi} sync={sync} done", flush=True)
    return pd.DataFrame(rows)


def shapley(df: pd.DataFrame, metrics=("deadline_success_rate", "avg_latency", "avg_energy")) -> pd.DataFrame:
    """Per-trial Shapley value of each stream; mean and 95 % CI over trials. Also returns the
    efficiency residual  sum_i phi_i - (v(all) - v(none)), which must vanish."""
    from scipy import stats
    n = len(STREAMS); out = []
    key = lambda S: "+".join(s for s in STREAMS if s in S) or "none"
    for m in metrics:
        v = df.pivot(index="trial", columns="streams", values=m)
        phi = {}
        for s in STREAMS:
            others = [x for x in STREAMS if x != s]; acc = 0.0
            for r_ in range(n):
                for S in itertools.combinations(others, r_):
                    wgt = math.factorial(len(S)) * math.factorial(n - len(S) - 1) / math.factorial(n)
                    acc = acc + wgt * (v[key(S + (s,))] - v[key(S)])
            phi[s] = acc
        total = v[key(STREAMS)] - v["none"]
        resid = float(np.abs(sum(phi.values()) - total).max())
        T = len(v); tcrit = stats.t.ppf(0.975, T - 1)
        for s in STREAMS:
            x = phi[s].values; half = tcrit * x.std(ddof=1) / np.sqrt(T)
            out.append(dict(metric=m, stream=s, shapley_mean=x.mean(), ci_low=x.mean() - half,
                            ci_high=x.mean() + half, v_none=v["none"].mean(), v_all=v[key(STREAMS)].mean(),
                            efficiency_residual=resid))
    return pd.DataFrame(out)


def self_check(trials=3) -> None:
    """(i) default settings reproduce the base simulator; (ii) a single dispatcher with a
    dead-reckoning twin is equivalent to current state for any synchronization interval."""
    keys = ["avg_latency", "avg_energy", "deadline_success_rate", "task_failure_ratio",
            "operator_intervention_rate", "operator_acceptance_rate", "safety_assignment_ratio",
            "trust_weighted_quality"]
    for pol in ["dt", "greedy"] + h.HC_POLICIES:
        for tr in range(trials):
            a = h.simulate(pol, 100, 1.2, 0.10, tr); b = simulate_info(pol, 100, 1.2, 0.10, tr)
            for k in keys:
                assert abs(a[k] - b[k]) < 1e-12, (pol, tr, k, a[k], b[k])
    for tr in range(trials):
        a = simulate_info("dt", 100, 1.2, 0.10, tr)
        b = simulate_info("dt", 100, 1.2, 0.10, tr, sync=2.0, twin="reckon", dispatchers=1)
        for k in keys: assert abs(a[k] - b[k]) < 1e-12, ("reckon", tr, k)
        assert b["recommendation_disagreement"] == 0.0
    print("self_check passed: base simulator reproduced; single-dispatcher dead reckoning equals current state")


if __name__ == "__main__":
    self_check()
