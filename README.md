# HC-DTO: Human-Centric Digital Twin Orchestration for Industrial Cyber-Physical Systems

Reproducible, simulation-based design workflow for orchestration policies in industrial cyber-physical systems (CPS). A seeded discrete-event digital twin executes a weighted multi-criteria task allocator (latency, energy, queueing delay, node trust, human-preference compatibility) task by task, together with a stylized operator-intervention model, a safety check and per-decision explanation traces. All strategies are compared on identical node populations, task streams and failure events.

This repository accompanies the article *Simulation-Based Design and Evaluation of Human-Centric Digital Twin Orchestration for Industrial Cyber-Physical Systems*. Every figure and table value in the article is regenerated from the files here.

## Contents

| File | Purpose |
|---|---|
| `hcdto_des.py` | Discrete-event simulator: nodes, Poisson task stream, failure injection, composite score, trust update, operator model, safety check, explanation trace, baselines |
| `run_experiments.py` | Full experiment grid: scalability (20–400 nodes), workload (4 levels), node failures (0–30 %), ablation, operator proficiency; 12 seeded replications each |
| `make_manuscript_figures.py` | Figures 1–11 and the summary tables |
| `design_analysis.py` | Multi-objective non-dominance analysis over the operating points, paired 95 % confidence intervals versus the AI-only DT baseline, latency–energy trade-off figure |
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
```

Delete `Outputs/Others/*.csv` first to re-simulate from scratch. In Colab, open the notebook and run all cells; outputs go to `MyDrive/Outputs/HC_DTO/`.

## Scope

The operator is a stylized model (logistic intervention in the normalized score margin, familiarity ratings drawn per node). Human-centric indicators produced here are emergent outcomes of that model, not measurements of real operators. Results are in model time and energy units.

## Citation

See `CITATION.cff`. An archived release with a DOI is available on Zenodo.

## License

MIT
