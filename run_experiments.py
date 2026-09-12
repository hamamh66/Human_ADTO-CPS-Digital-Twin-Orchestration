"""Runs the full HC-DTO discrete-event experiment grid and writes the summary files used by the manuscript."""
import time, sys, pandas as pd
from pathlib import Path
import hcdto_des as h
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "Outputs"
TAB, OTH = ROOT / "Tables", ROOT / "Others"
TAB.mkdir(parents=True, exist_ok=True); OTH.mkdir(parents=True, exist_ok=True)
t0 = time.time()
# 1. scalability (medium load, 10 % failures), all policies + human-only
sc = pd.read_csv(OTH / "scalability_raw.csv") if (OTH / "scalability_raw.csv").exists() else h.run_grid(h.NODE_COUNTS, h.LOAD_MAP["medium"], 0.10, policies=h.ALL_POLICIES + [h.HUMAN_ONLY], load_name="medium")
sc.to_csv(OTH / "scalability_raw.csv", index=False); h.summarize(sc, ["policy", "num_nodes"]).to_csv(TAB / "scalability_summary.csv", index=False)
print("scalability done", round(time.time() - t0), "s", flush=True)
# 2. workload stress (100 nodes, 10 % failures)
st = pd.concat([h.run_grid([100], lf, 0.10, load_name=ln) for ln, lf in h.LOAD_MAP.items()])
st.to_csv(OTH / "stress_raw.csv", index=False); h.summarize(st, ["policy", "load_name", "load_factor"]).to_csv(TAB / "stress_summary.csv", index=False)
print("stress done", round(time.time() - t0), "s", flush=True)
# 3. failure stress (100 nodes, medium load)
fa = pd.concat([h.run_grid([100], h.LOAD_MAP["medium"], phi, load_name="medium") for phi in h.FAILURE_RATES])
fa.to_csv(OTH / "failure_raw.csv", index=False); h.summarize(fa, ["policy", "failure_rate"]).to_csv(TAB / "failure_summary.csv", index=False)
print("failure done", round(time.time() - t0), "s", flush=True)
# 4. ablation of the Balanced profile (100 nodes, medium load, 10 % failures)
ab = h.run_grid([100], h.LOAD_MAP["medium"], 0.10, policies=["hc_dt_balanced", "dt", "greedy"] + list(h.ABLATIONS), load_name="medium")
ab.to_csv(OTH / "ablation_raw.csv", index=False); h.summarize(ab, ["policy"]).to_csv(TAB / "ablation_summary.csv", index=False)
# 5. proficiency sensitivity (kappa) for HC profiles
rows = []
for kappa in (0.0, 0.25, 0.5, 0.75, 1.0):
    for pol in h.HC_POLICIES:
        for tr in range(h.N_TRIALS):
            r = h.simulate(pol, 100, h.LOAD_MAP["medium"], 0.10, tr, kappa=kappa); r["kappa"] = kappa; rows.append(r)
ka = pd.DataFrame(rows); ka.to_csv(OTH / "kappa_raw.csv", index=False); h.summarize(ka, ["policy", "kappa"]).to_csv(TAB / "kappa_summary.csv", index=False)
print("all done", round(time.time() - t0), "s", flush=True)
