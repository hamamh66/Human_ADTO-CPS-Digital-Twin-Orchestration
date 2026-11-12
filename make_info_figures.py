"""
Figures and table values for the information-integration experiments
(twin-state freshness, dead reckoning, attribution over information streams).
Usage: python make_info_figures.py [outputs_root]   (default ./Outputs)
"""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "Outputs"
TAB, OTH, OUT = ROOT / "Tables", ROOT / "Others", ROOT / "Figures"
OUT.mkdir(parents=True, exist_ok=True)
UTIL = 0.6                                   # arrival rate = UTIL * load * K tasks per time unit
NAMES = {'dt': 'AI-only DT', 'greedy': 'Greedy', 'hc_dt_balanced': 'HC-DTO Balanced', 'hc_dt_latency': 'HC-DTO Latency'}
STYLE = {'greedy': dict(color='#4A4F54', ls='--', marker='D'), 'dt': dict(color='#000000', ls='-', marker='o'),
         'hc_dt_balanced': dict(color='#2E5F8A', ls='-', marker='o'), 'hc_dt_latency': dict(color='#1E8449', ls='-', marker='o')}
X0 = 0.005                                   # plotting position of the current-state case on the log axis

def tidy(ax, xl, yl):
    ax.set_xlabel(xl, fontsize=10); ax.set_ylabel(yl, fontsize=10); ax.grid(color='#e6e6e6'); ax.set_axisbelow(True)
    for s in ('top', 'right'): ax.spines[s].set_visible(False)

def random_reference(K, load):
    """Deadline success of the queue-unaware Random baseline from the base experiment grid."""
    sc = pd.read_csv(OTH / "scalability_raw.csv"); st = pd.read_csv(OTH / "stress_raw.csv")
    d = sc[(sc.policy == 'random') & (sc.num_nodes == K)] if abs(load - 1.2) < 1e-9 else \
        st[(st.policy == 'random') & (np.isclose(st.load_factor, load))]
    return float(d.deadline_success_rate.mean())

fr = pd.read_csv(TAB / "freshness_summary.csv"); ev = pd.read_csv(TAB / "freshness_envelope_summary.csv")
rk = pd.read_csv(TAB / "reckoning_summary.csv")

# ---- Fig. 13: deadline success versus synchronization interval, stale-snapshot twin
fig, ax = plt.subplots(figsize=(7.2, 4.0))
for p in ['dt', 'greedy', 'hc_dt_balanced', 'hc_dt_latency']:
    d = fr[(fr.policy == p) & (fr.twin != 'queue_blind')].sort_values('sync')
    x = d.sync.replace(0.0, X0).values
    ax.errorbar(x, d.deadline_success_rate_mean, yerr=d.deadline_success_rate_std, capsize=2, lw=1.6, ms=4.5, label=NAMES[p], **STYLE[p])
rr = random_reference(100, 1.2)
ax.axhline(rr, color='#B8BDC2', ls=':', lw=1.6, label='Random (no queue state)')
ax.set_xscale('log'); ticks = [X0, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 2, 4]
ax.set_xticks(ticks); ax.set_xticklabels(['0', '0.01', '0.02', '0.05', '0.1', '0.25', '0.5', '1', '2', '4']); ax.minorticks_off()
tidy(ax, 'Synchronization interval of the edge twins (time units)', 'Deadline success rate')
ax.legend(fontsize=7.5, frameon=False); fig.tight_layout(); fig.savefig(OUT / "ms_fig13_success_vs_sync.png", dpi=300); plt.close(fig)

# ---- Fig. 14: (a) operating envelope against placements per snapshot; (b) dead-reckoning twin
fig, (a, b) = plt.subplots(1, 2, figsize=(9.6, 3.9))
cases = [(20, 1.2, '#B7770D', 's'), (100, 0.8, '#2E5F8A', '^'), (100, 1.2, '#000000', 'o'), (100, 1.8, '#C0392B', 'v'), (400, 1.2, '#7D3C98', 'D')]
rows = []
for K, load, col, mk in cases:
    if K == 100 and abs(load - 1.2) < 1e-9:
        d = fr[(fr.policy == 'dt') & (fr.twin == 'stale')].sort_values('sync')
    else:
        d = ev[(ev.num_nodes == K) & np.isclose(ev.load_factor, load) & (ev.twin == 'stale')].sort_values('sync')
    n = UTIL * load * K * d.sync.values
    a.plot(n, d.deadline_success_rate_mean, color=col, marker=mk, lw=1.5, ms=4, label=f'{K} nodes, load {load}')
    ref = random_reference(K, load); a.plot([n.min(), n.max()], [ref, ref], color=col, ls=':', lw=0.9)
    s = d.deadline_success_rate_mean.values; above = np.where(s >= ref)[0]; k = above.max()
    rows.append(dict(num_nodes=K, load_factor=load, random_success=ref, last_sync_above=d.sync.values[k], success_there=s[k],
                     first_sync_below=d.sync.values[k + 1], success_below=s[k + 1],
                     placements_per_snapshot_low=n[k], placements_per_snapshot_high=n[k + 1]))
a.set_xscale('log'); tidy(a, 'Placements per snapshot (arrival rate $\\times$ interval)', 'Deadline success rate')
a.legend(fontsize=7, frameon=False); a.set_title('(a) Stale-snapshot twin, AI-only DT score', fontsize=9)
pd.DataFrame(rows).to_csv(TAB / "ms_table_sync_breakeven.csv", index=False)
for G, col, mk in [(1, '#1E8449', 'o'), (4, '#2E5F8A', 's'), (20, '#B7770D', '^'), (100, '#C0392B', 'v')]:
    d = rk[rk.dispatchers == G].sort_values('sync')
    b.errorbar(d.sync, d.deadline_success_rate_mean, yerr=d.deadline_success_rate_std, capsize=2, color=col, marker=mk, lw=1.5, ms=4,
               label=f'{G} dispatcher' + ('s' if G > 1 else ''))
d = fr[(fr.policy == 'dt') & (fr.twin == 'stale')].sort_values('sync')
b.plot(d.sync, d.deadline_success_rate_mean, color='#000000', ls='--', lw=1.2, label='snapshot only')
b.axhline(rr, color='#B8BDC2', ls=':', lw=1.6, label='Random')
b.set_xscale('log'); b.set_xticks([0.01, 0.1, 1, 4]); b.set_xticklabels(['0.01', '0.1', '1', '4'])
tidy(b, 'Synchronization interval (time units)', 'Deadline success rate'); b.legend(fontsize=7, frameon=False)
b.set_title('(b) Dead-reckoning twin, 100 nodes, medium load', fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "ms_fig14_envelope_and_reckoning.png", dpi=300); plt.close(fig)

# ---- manuscript tables
piv = lambda col: fr.pivot_table(index='sync', columns=['policy', 'twin'], values=col)
piv('deadline_success_rate_mean').round(3).to_csv(TAB / "ms_table_success_vs_sync.csv")
piv('recommendation_disagreement_mean').round(3).to_csv(TAB / "ms_table_disagreement_vs_sync.csv")
piv('p95_latency_mean').round(2).to_csv(TAB / "ms_table_p95_latency_vs_sync.csv")
rk.pivot_table(index='sync', columns='dispatchers', values='deadline_success_rate_mean').round(3).to_csv(TAB / "ms_table_reckoning.csv")
co = pd.read_csv(TAB / "coalitions_summary.csv")
co.pivot_table(index='streams', columns='point', values='deadline_success_rate').round(3).to_csv(TAB / "ms_table_coalitions_success.csv")
co.pivot_table(index='streams', columns='point', values='avg_energy').round(3).to_csv(TAB / "ms_table_coalitions_energy.csv")
sh = pd.read_csv(TAB / "information_value_shapley.csv")
sh[sh.metric != 'avg_latency'].round(4).to_csv(TAB / "ms_table_information_value.csv", index=False)
print("information-integration figures and tables written to", ROOT)
