# HC-DTO: Human-Centric Digital Twin Orchestration for Industrial Cyber-Physical Systems

Reproducible simulation study of task orchestration in industrial cyber-physical systems (CPS) as an information-integration problem. A seeded discrete-event digital twin executes a weighted multi-criteria task allocator (latency, energy, queueing delay, node trust, human-preference compatibility) task by task, together with a stylized operator-intervention model, a safety check and per-decision explanation traces. All strategies are compared on identical node populations, task streams and failure events.

This repository accompanies the article *Integrating Edge Digital Twin State and Operator Policy for Industrial Task Orchestration: A Simulation Study of Information Value and Freshness*. Every figure and table value in the article is regenerated from the files here.

## Contents

| File | Purpose |
|---|---|
| `hcdto_des.py` | Discrete-event simulator: nodes, Poisson task stream, failure injection, composite score, trust update, operator model, safety check, explanation trace, baselines |
| `run_experiments.py` | Full experiment grid: scalability (20–400 nodes), workload (4 levels), node failures (0–30 %), ablation, operator proficiency; 12 seeded replications each |
| `make_manuscript_figures.py` | Figures 1–11 and the summary tables |
| `design_analysis.py` | Multi-objective non-dominance analysis over the operating points, paired 95 % confidence intervals versus the AI-only DT baseline, latency–energy trade-off figure |
| `hcdto_info.py` | Information-integration experiments: twin synchronization models (current state, snapshot, dead reckoning with several dispatchers), removal of information streams, exact Shapley attribution, and a self-check that the module reproduces `hcdto_des.py` at its default settings |
| `run_info_experiments.py` | Freshness sweep, operating envelope, dead reckoning, and all 16 combinations of the four information streams; 12 seeded replications each |
| `make_info_figures.py` | Figures 13-14 and the table values of the information-value and freshness analyses |
| `HC_DTO_DES_Experiments.ipynb` | Colab notebook running all of the above end to end |
| `Outputs/Others/` | Raw per-trial results (CSV) |
| `Outputs/Tables/` | Summary tables and article table values (CSV) |
| `Outputs/Figures/` | Article figures (PNG, 300 dpi) |

## Strategies

Baselines: Cloud, Local, Random, Greedy (minimum projected queue), AI-only DT (same score without trust and human terms), and a stylized Human-only mode. HC-DTO profiles: Balanced, Reliability, Latency, Energy, Override (weight vectors listed in `hcdto_des.py`).

## Reproduce

```bash
pip install -r requirements.txt
python run_experiments.py          # about 7 min on one CPU core; skips families whose raw CSV already exists
python make_manuscript_figures.py
python design_analysis.py
python run_info_experiments.py     # about 6 min on one CPU core
python make_info_figures.py
```

Delete `Outputs/Others/*.csv` first to re-simulate from scratch. In Colab, open the notebook and run all cells; outputs go to `MyDrive/Outputs/HC_DTO/`.

## Information-integration experiments

The placement decision integrates four information streams: queue state of the edge twins, device energy models, node outcome history, and an operator-familiarity rating. `hcdto_info.py` measures (i) what each stream contributes, by simulating all 16 combinations and attributing the difference with the Shapley value, and (ii) how current the queue state must be, by delivering it only at synchronization epochs and comparing a snapshot twin with a dead-reckoning twin that logs its own dispatches. In these experiments a task outcome enters the outcome history at task completion, and node availability is always current.

## Scope

The operator is a stylized model (logistic intervention in the normalized score margin, familiarity ratings drawn per node). Human-centric indicators produced here are emergent outcomes of that model, not measurements of real operators. Results are in model time and energy units.

## Citation

See `CITATION.cff`. Archived releases on Zenodo (all versions): [doi:10.5281/zenodo.23774877](https://doi.org/10.5281/zenodo.23774877).

## License

MIT
