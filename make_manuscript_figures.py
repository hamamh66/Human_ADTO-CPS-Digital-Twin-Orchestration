"""
Regenerates the manuscript figures and tables from the discrete-event experiment outputs.
Usage: python make_manuscript_figures.py [outputs_root]   (default ./Outputs; reads Tables/ and Others/, writes Figures/ and Tables/)
"""
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "Outputs"
IN = ROOT / "Tables"; OTH = ROOT / "Others"; OUT = ROOT / "Figures"; TAB = ROOT / "Tables"
for d in (IN, OTH, OUT, TAB): d.mkdir(parents=True, exist_ok=True)

NAMES = {'cloud':'Cloud','local':'Local','random':'Random','greedy':'Greedy','dt':'AI-only DT',
         'hc_dt_balanced':'HC-DTO Balanced','hc_dt_reliability':'HC-DTO Reliability','hc_dt_latency':'HC-DTO Latency',
         'hc_dt_energy':'HC-DTO Energy','hc_dt_override':'HC-DTO Override','human_only':'Human-only',
         'hc_dt_balanced_noenergy':'HC-DTO Balanced, no energy term','hc_dt_balanced_notrust':'HC-DTO Balanced, no trust term',
         'hc_dt_balanced_noqueue':'HC-DTO Balanced, no queue term'}
ORDER = ['cloud','local','random','greedy','dt','hc_dt_balanced','hc_dt_reliability','hc_dt_latency','hc_dt_energy','hc_dt_override']
HC = ORDER[5:]
STYLE = {'cloud':dict(color='#9AA0A6',ls='--',marker='s'),'local':dict(color='#6B7075',ls='--',marker='^'),
 'random':dict(color='#B8BDC2',ls='--',marker='v'),'greedy':dict(color='#4A4F54',ls='--',marker='D'),'dt':dict(color='#000000',ls='-',marker='o'),
 'hc_dt_balanced':dict(color='#2E5F8A',ls='-',marker='o'),'hc_dt_reliability':dict(color='#C0392B',ls='-',marker='o'),
 'hc_dt_latency':dict(color='#1E8449',ls='-',marker='o'),'hc_dt_energy':dict(color='#B7770D',ls='-',marker='o'),
 'hc_dt_override':dict(color='#7D3C98',ls='-',marker='o'),'human_only':dict(color='#1E8449',ls='-.',marker='s')}

def tidy(ax, xl, yl):
    ax.set_xlabel(xl, fontsize=10); ax.set_ylabel(yl, fontsize=10); ax.grid(color='#e6e6e6'); ax.set_axisbelow(True)
    for s in ('top','right'): ax.spines[s].set_visible(False)
def line_fig(df, xcol, ycol, xl, yl, fname, xticks=None, xlabels=None, policies=ORDER, err=True):
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for p in policies:
        d = df[df.policy == p].sort_values(xcol)
        if d.empty: continue
        x = d[xcol].values if xticks is None else np.arange(len(d))
        ax.errorbar(x, d[ycol + '_mean'], yerr=d[ycol + '_std'] if err else None, capsize=2, lw=1.6, ms=4.5, label=NAMES[p], **STYLE[p])
    if xticks is not None: ax.set_xticks(np.arange(len(xticks))); ax.set_xticklabels(xlabels)
    tidy(ax, xl, yl); ax.legend(fontsize=7.5, ncol=2, frameon=False); fig.tight_layout(); fig.savefig(OUT / fname, dpi=300); plt.close(fig)

sc = pd.read_csv(IN / "scalability_summary.csv"); st = pd.read_csv(IN / "stress_summary.csv")
fa = pd.read_csv(IN / "failure_summary.csv"); ab = pd.read_csv(IN / "ablation_summary.csv"); ka = pd.read_csv(IN / "kappa_summary.csv")
loads = ['low','medium','high','extreme']; st['load_idx'] = st.load_name.map({l:i for i,l in enumerate(loads)})
LBL = ['low (0.8)','medium (1.2)','high (1.8)','extreme (2.4)']

line_fig(sc, 'num_nodes', 'avg_latency', 'Number of edge nodes', 'Average latency (time units)', 'ms_fig1_latency_vs_nodes.png')
line_fig(sc, 'num_nodes', 'avg_energy', 'Number of edge nodes', 'Average energy per completed task (energy units)', 'ms_fig2_energy_vs_nodes.png')
line_fig(sc, 'num_nodes', 'deadline_success_rate', 'Number of edge nodes', 'Deadline success rate', 'ms_fig3_success_vs_nodes.png')
line_fig(sc, 'num_nodes', 'task_failure_ratio', 'Number of edge nodes', 'Task failure ratio', 'ms_fig4_failure_vs_nodes.png')
line_fig(st, 'load_idx', 'avg_latency', 'Workload intensity (load factor)', 'Average latency (time units)', 'ms_fig5_latency_vs_workload.png', xticks=loads, xlabels=LBL)
line_fig(st, 'load_idx', 'deadline_success_rate', 'Workload intensity (load factor)', 'Deadline success rate', 'ms_fig6_success_vs_workload.png', xticks=loads, xlabels=LBL)
line_fig(fa, 'failure_rate', 'avg_latency', 'Node failure probability', 'Average latency (time units)', 'ms_fig7_latency_vs_failure.png')
line_fig(fa, 'failure_rate', 'deadline_success_rate', 'Node failure probability', 'Deadline success rate', 'ms_fig8_success_vs_failure.png')
line_fig(fa, 'failure_rate', 'operator_intervention_rate', 'Node failure probability', 'Operator-intervention rate', 'ms_fig9_intervention_vs_failure.png', policies=HC)
line_fig(sc, 'num_nodes', 'trust_weighted_quality', 'Number of edge nodes', 'Trust-weighted decision quality', 'ms_fig10_trust_weighted_quality.png', policies=['dt','hc_dt_balanced','hc_dt_override','human_only'])
line_fig(ka, 'kappa', 'operator_intervention_rate', 'Operator-proficiency surrogate $\\kappa$', 'Operator-intervention rate', 'ms_fig11_intervention_vs_kappa.png', policies=HC)

def pm(m, s, d=3): return f"{m:.{d}f} ± {s:.{d}f}"
t = sc[sc.num_nodes == 100].set_index('policy')
rows = [dict(Strategy=NAMES[p], Latency=pm(t.loc[p,'avg_latency_mean'], t.loc[p,'avg_latency_std'], 2), Energy=pm(t.loc[p,'avg_energy_mean'], t.loc[p,'avg_energy_std'], 3),
             Success=pm(t.loc[p,'deadline_success_rate_mean'], t.loc[p,'deadline_success_rate_std']), Failure=pm(t.loc[p,'task_failure_ratio_mean'], t.loc[p,'task_failure_ratio_std']))
        for p in ORDER + ['human_only']]
pd.DataFrame(rows).to_csv(TAB / 'ms_table_technical_100nodes.csv', index=False)
def gain(metric, low, ref):
    hc = t.loc[HC, metric]; best = hc.min() if low else hc.max(); r = t.loc[ref, metric]
    return 100 * (r - best) / r if low else 100 * (best - r) / r
g = [dict(Baseline=NAMES[ref], latency=round(gain('avg_latency_mean', True, ref), 1), energy=round(gain('avg_energy_mean', True, ref), 1),
          success=round(gain('deadline_success_rate_mean', False, ref), 1), failure=round(gain('task_failure_ratio_mean', True, ref), 1)) for ref in ['dt','greedy','random','local','cloud']]
pd.DataFrame(g).to_csv(TAB / 'ms_table_relative_gains_100nodes.csv', index=False)
hrows = [dict(Mode=NAMES[p], IR=pm(t.loc[p,'operator_intervention_rate_mean'], t.loc[p,'operator_intervention_rate_std']), AR=pm(t.loc[p,'operator_acceptance_rate_mean'], t.loc[p,'operator_acceptance_rate_std']),
              SR=pm(t.loc[p,'safety_assignment_ratio_mean'], t.loc[p,'safety_assignment_ratio_std']), EC=pm(t.loc[p,'explanation_consistency_mean'], t.loc[p,'explanation_consistency_std']),
              Q=pm(t.loc[p,'trust_weighted_quality_mean'], t.loc[p,'trust_weighted_quality_std'])) for p in ['dt'] + HC + ['human_only']]
pd.DataFrame(hrows).to_csv(TAB / 'ms_table_human_centric_100nodes.csv', index=False)
crows = [dict(Policy=NAMES[p], **{c.split('_',1)[1]: round(t.loc[p, c + '_mean'], 3) for c in ['contrib_latency','contrib_energy','contrib_queue','contrib_trust','contrib_human_preference']}) for p in ['dt'] + HC]
pd.DataFrame(crows).to_csv(TAB / 'ms_table_contribution_shares_100nodes.csv', index=False)
a = ab.set_index('policy')
arows = [dict(Variant=NAMES[p], Latency=pm(a.loc[p,'avg_latency_mean'], a.loc[p,'avg_latency_std'], 2), Energy=pm(a.loc[p,'avg_energy_mean'], a.loc[p,'avg_energy_std'], 3),
              Success=pm(a.loc[p,'deadline_success_rate_mean'], a.loc[p,'deadline_success_rate_std']), Failure=pm(a.loc[p,'task_failure_ratio_mean'], a.loc[p,'task_failure_ratio_std']),
              Q=pm(a.loc[p,'trust_weighted_quality_mean'], a.loc[p,'trust_weighted_quality_std'])) for p in ['hc_dt_balanced','hc_dt_balanced_noenergy','hc_dt_balanced_notrust','hc_dt_balanced_noqueue','dt','greedy']]
pd.DataFrame(arows).to_csv(TAB / 'ms_table_ablation.csv', index=False)
f = fa[fa.policy.isin(HC)].pivot(index='policy', columns='failure_rate', values='operator_intervention_rate_mean').loc[HC].round(3); f.index=[NAMES[p] for p in f.index]; f.to_csv(TAB/'ms_table_intervention_vs_failure.csv')
q = sc.pivot(index='policy', columns='num_nodes', values='trust_weighted_quality_mean').loc[['dt','hc_dt_balanced','hc_dt_override','human_only']].round(3); q.index=[NAMES[p] for p in q.index]; q.to_csv(TAB/'ms_table_twq_vs_nodes.csv')
k = ka.pivot(index='policy', columns='kappa', values='operator_intervention_rate_mean').loc[HC].round(3); k.index=[NAMES[p] for p in k.index]; k.to_csv(TAB/'ms_table_intervention_vs_kappa.csv')
# dominant explanation reason counts (from raw scalability)
raw = pd.read_csv(OTH / "scalability_raw.csv"); ex = raw[raw.policy.isin(['dt']+HC)].groupby(['policy','top_explanation_reason']).size().unstack(fill_value=0)
ex.index=[NAMES[p] for p in ex.index]; ex.to_csv(TAB/'ms_table_dominant_reason_counts.csv')
for name in sorted(TAB.glob('*.csv')): print('==', name.name); print(pd.read_csv(name).to_string(index=False))

# ---- weighted multi-metric ranking of the HC profiles (Section 3.9 of the manuscript)
W = dict(avg_latency=(0.22, False), avg_energy=(0.14, False), deadline_success_rate=(0.20, True),
         trust_weighted_quality=(0.22, True), safety_assignment_ratio=(0.14, True), operator_intervention_rate=(0.08, False))
r = sc[sc.policy.isin(HC)].copy()
for col, (wgt, hib) in W.items():
    g = r.groupby('num_nodes')[col + '_mean']
    lo, hi = g.transform('min'), g.transform('max')
    r['s_' + col] = ((r[col + '_mean'] - lo) / (hi - lo + 1e-9)) if hib else ((hi - r[col + '_mean']) / (hi - lo + 1e-9))
r['composite'] = sum(W[c][0] * r['s_' + c] for c in W)
rank = r.groupby('policy')[['s_' + c for c in W] + ['composite']].mean().loc[HC].sort_values('composite', ascending=False).round(3)
rank.index = [NAMES[p] for p in rank.index]; rank.to_csv(TAB / 'ms_table_policy_ranking.csv'); print(rank.to_string())
