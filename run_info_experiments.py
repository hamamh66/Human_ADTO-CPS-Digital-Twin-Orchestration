"""Runs the information-integration experiments (twin-state freshness, dead reckoning, and the
all-coalition attribution over information streams) and writes raw and summary files."""
import sys, time, pandas as pd
from pathlib import Path
import hcdto_des as h, hcdto_info as m
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "Outputs"
TAB, OTH = ROOT / "Tables", ROOT / "Others"
TAB.mkdir(parents=True, exist_ok=True); OTH.mkdir(parents=True, exist_ok=True)
t0 = time.time()
def stamp(msg): print(f"[{time.time() - t0:6.0f} s] {msg}", flush=True)
def cached(name, fn):
    f = OTH / name
    if f.exists(): stamp(f"{name}: reusing existing file"); return pd.read_csv(f)
    df = fn(); df.to_csv(f, index=False); stamp(f"{name}: written ({len(df)} runs)"); return df
M = ["avg_latency", "p95_latency", "avg_energy", "deadline_success_rate", "task_failure_ratio",
     "recommendation_disagreement"]
def summarize(df, keys):
    g = df.groupby(keys)[M].agg(["mean", "std"]); g.columns = [f"{a}_{b}" for a, b in g.columns]
    return g.reset_index()

m.self_check(); stamp("self-check passed")
# 1. stale-snapshot twin versus synchronization interval (100 nodes, medium load, 10 % failures)
fr = cached("freshness_raw.csv", lambda: m.run_freshness())
summarize(fr, ["policy", "twin", "sync"]).to_csv(TAB / "freshness_summary.csv", index=False)
# 2. the same sweep for the AI-only DT score at other scales and loads
def envelope():
    parts = [m.run_freshness(K=K, load=h.LOAD_MAP["medium"], policies=["dt"]) for K in (20, 400)]
    parts += [m.run_freshness(K=100, load=h.LOAD_MAP[ln], policies=["dt"]) for ln in ("low", "high")]
    return pd.concat(parts)
ev = cached("freshness_envelope_raw.csv", envelope)
summarize(ev, ["num_nodes", "load_factor", "twin", "sync"]).to_csv(TAB / "freshness_envelope_summary.csv", index=False)
# 3. dead-reckoning twin with 1, 4, 20 and 100 dispatchers
rk = cached("reckoning_raw.csv", lambda: m.run_reckoning())
summarize(rk, ["dispatchers", "sync"]).to_csv(TAB / "reckoning_summary.csv", index=False)
# 4. all-coalition attribution over the four information streams (Balanced weights, no intervention)
POINTS = {"nominal": (1.2, 0.10, 0.0), "high_load": (1.8, 0.10, 0.0), "high_failure": (1.2, 0.30, 0.0),
          "nominal_sync0.1": (1.2, 0.10, 0.1), "nominal_sync1": (1.2, 0.10, 1.0)}
def coalitions():
    parts = []
    for name, (load, phi, sync) in POINTS.items():
        d = m.run_coalitions(load=load, phi=phi, sync=sync); d["point"] = name; parts.append(d)
    return pd.concat(parts)
co = cached("coalitions_raw.csv", coalitions)
co.groupby(["point", "streams"])[M[:4]].mean().reset_index().to_csv(TAB / "coalitions_summary.csv", index=False)
sh = pd.concat([m.shapley(co[co.point == p]).assign(point=p) for p in POINTS])
sh.to_csv(TAB / "information_value_shapley.csv", index=False)
# 5. effect of the outcome-feedback convention under current state (Balanced, with intervention)
def feedback_check():
    rows = []
    for fb in ("dispatch", "completion"):
        for pol in h.HC_POLICIES:
            for tr in range(h.N_TRIALS):
                rows.append(m.simulate_info(pol, 100, h.LOAD_MAP["medium"], 0.10, tr, feedback=fb))
    return pd.DataFrame(rows)
fb = cached("feedback_convention_raw.csv", feedback_check)
fb.groupby(["policy", "feedback"])[M[:4] + ["operator_intervention_rate"]].mean().reset_index().to_csv(TAB / "feedback_convention_summary.csv", index=False)
stamp("all done")
