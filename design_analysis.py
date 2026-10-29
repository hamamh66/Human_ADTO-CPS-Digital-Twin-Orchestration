"""
design_analysis.py -- Multi-objective trade-off and seed-level uncertainty analysis of the HC-DTO experiment grid.

Reads only the raw per-trial results in Outputs/Others/ (written by run_experiments.py) and produces:
  Tables/ms_table_paired_vs_dt_100nodes.csv   paired differences vs the AI-only DT baseline (100 nodes),
                                              mean and 95 % t-interval over the shared-seed replications
  Tables/ms_table_pareto_frequency.csv        how often each policy is Pareto-non-dominated in
                                              (latency min, energy min, deadline success max) over all operating points
  Tables/ms_table_pareto_100nodes.csv         objective means, 95 % CI half-widths and Pareto status at 100 nodes
  Figures/ms_fig12_pareto_latency_energy.png  latency-energy plane at 100 nodes with 95 % CIs and the non-dominated set
Usage: python design_analysis.py [outputs_root]   (default ./Outputs)
"""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "Outputs"
OTH, TAB, FIG = ROOT / "Others", ROOT / "Tables", ROOT / "Figures"
TAB.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
NAMES = {'cloud':'Cloud','local':'Local','random':'Random','greedy':'Greedy','dt':'AI-only DT',
         'hc_dt_balanced':'HC-DTO Balanced','hc_dt_reliability':'HC-DTO Reliability','hc_dt_latency':'HC-DTO Latency',
         'hc_dt_energy':'HC-DTO Energy','hc_dt_override':'HC-DTO Override','human_only':'Human-only'}
OBJ = [('avg_latency', -1), ('avg_energy', -1), ('deadline_success_rate', +1)]   # sign: +1 maximize, -1 minimize

def ci_half(x):
    x = np.asarray(x, float); n = len(x)
    return stats.t.ppf(0.975, n - 1) * x.std(ddof=1) / np.sqrt(n)

def nondominated(m):
    """m: DataFrame indexed by policy with objective columns; returns set of non-dominated policies."""
    v = np.column_stack([s * m[c].values for c, s in OBJ])        # all objectives as 'maximize'
    nd = []
    for i in range(len(v)):
        dom = np.any(np.all(v >= v[i], 1) & np.any(v > v[i], 1))
        if not dom: nd.append(m.index[i])
    return set(nd)

sc = pd.read_csv(OTH / "scalability_raw.csv"); st = pd.read_csv(OTH / "stress_raw.csv"); fa = pd.read_csv(OTH / "failure_raw.csv")
print("loaded", len(sc), len(st), len(fa), "trial rows", flush=True)

# 1. paired differences vs AI-only DT at 100 nodes (shared task streams, node populations and failure events per seed)
d100 = sc[sc.num_nodes == 100]
ref = d100[d100.policy == 'dt'].set_index('trial')
rows = []
for p in NAMES:
    if p == 'dt': continue
    q = d100[d100.policy == p].set_index('trial').loc[ref.index]
    r = {'Strategy': NAMES[p]}
    for c, lab, dg in [('avg_latency', 'dLatency', 3), ('avg_energy', 'dEnergy', 3), ('deadline_success_rate', 'dSuccess', 4)]:
        diff = q[c].values - ref[c].values
        r[lab] = f"{diff.mean():+.{dg}f} [{diff.mean()-ci_half(diff):+.{dg}f}, {diff.mean()+ci_half(diff):+.{dg}f}]"
    rows.append(r)
pd.DataFrame(rows).to_csv(TAB / "ms_table_paired_vs_dt_100nodes.csv", index=False)
print("paired table written", flush=True)

# 2. Pareto frequency over all distinct operating points (medium load and phi = 0.10 at 100 nodes coincide with K = 100)
points = []
for (k,), g in sc.groupby(['num_nodes']): points.append((f"K={k}", g))
for (ln,), g in st[st.load_name != 'medium'].groupby(['load_name']): points.append((f"load={ln}", g))
for (ph,), g in fa[fa.failure_rate != 0.10].groupby(['failure_rate']): points.append((f"phi={ph}", g))
cnt = {p: 0 for p in NAMES}; npts = {p: 0 for p in NAMES}; detail = []
for name, g in points:
    m = g.groupby('policy')[[c for c, _ in OBJ]].mean()
    nd = nondominated(m)
    for p in m.index: npts[p] += 1; cnt[p] += p in nd
    detail.append((name, sorted(NAMES[p] for p in nd)))
pf = pd.DataFrame([{'Strategy': NAMES[p], 'Non-dominated': cnt[p], 'Operating points': npts[p],
                    'Share': round(cnt[p] / npts[p], 3)} for p in NAMES if npts[p]])
pf.to_csv(TAB / "ms_table_pareto_frequency.csv", index=False)
pd.DataFrame(detail, columns=['operating_point', 'non_dominated']).to_csv(TAB / "pareto_by_operating_point.csv", index=False)
print("pareto frequency over", len(points), "operating points written", flush=True)

# 3. 100-node table and latency-energy figure
g = d100.groupby('policy')
m = g[[c for c, _ in OBJ]].mean(); h = g[[c for c, _ in OBJ]].agg(ci_half)
nd = nondominated(m)
t = pd.DataFrame({'Strategy': [NAMES[p] for p in m.index],
                  'Latency': [f"{m.loc[p,'avg_latency']:.3f} ± {h.loc[p,'avg_latency']:.3f}" for p in m.index],
                  'Energy': [f"{m.loc[p,'avg_energy']:.3f} ± {h.loc[p,'avg_energy']:.3f}" for p in m.index],
                  'Success': [f"{m.loc[p,'deadline_success_rate']:.3f} ± {h.loc[p,'deadline_success_rate']:.3f}" for p in m.index],
                  'Pareto': ['yes' if p in nd else 'no' for p in m.index]})
t.to_csv(TAB / "ms_table_pareto_100nodes.csv", index=False)
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for p in m.index:
    if m.loc[p, 'avg_latency'] > 3: continue                       # cloud/local/random lie far outside the plotted window
    on = p in nd
    ax.errorbar(m.loc[p, 'avg_energy'], m.loc[p, 'avg_latency'], xerr=h.loc[p, 'avg_energy'], yerr=h.loc[p, 'avg_latency'],
                fmt='o' if on else 's', ms=7 if on else 5, color='#1E5A8A' if on else '#8A8F94', capsize=2, lw=1)
    ax.annotate(f"{NAMES[p]}\n(S={m.loc[p,'deadline_success_rate']:.3f})", (m.loc[p, 'avg_energy'], m.loc[p, 'avg_latency']),
                textcoords='offset points', xytext=(6, 4), fontsize=7)
ax.set_xlabel('Average energy per completed task (energy units)'); ax.set_ylabel('Average latency (time units)')
ax.grid(color='#e6e6e6'); ax.set_axisbelow(True)
for s in ('top', 'right'): ax.spines[s].set_visible(False)
ax.plot([], [], 'o', color='#1E5A8A', label='Non-dominated (latency, energy, success)')
ax.plot([], [], 's', color='#8A8F94', label='Dominated')
ax.legend(fontsize=8, frameon=False, loc='lower left'); fig.tight_layout(); fig.savefig(FIG / "ms_fig12_pareto_latency_energy.png", dpi=300)
print("figure written; non-dominated at 100 nodes:", sorted(NAMES[p] for p in nd), flush=True)
