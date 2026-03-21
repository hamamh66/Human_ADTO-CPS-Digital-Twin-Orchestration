# ADTO-CPS-Digital-Twin-Orchestration

Official reproducibility repository for the paper:

**Human-Centric Digital Twin Orchestration for Industrial Cyber-Physical Systems: Trust-Aware, Explainable, and Human-in-the-Loop AI Decision Support**

---

## 📌 Overview

This repository provides the **Python implementation and experimental workflow** used to reproduce the results presented in the paper. The framework introduces a **human-centric digital twin orchestration architecture** for industrial cyber-physical systems (CPS), integrating:

- Trust-aware decision-making  
- Explainable AI (XAI) mechanisms  
- Human-in-the-loop intervention  
- Multi-policy orchestration strategies  
- Scenario-based system evaluation  

The goal is to bridge the gap between **autonomous orchestration** and **human-centered control**, enabling more reliable, interpretable, and adaptive CPS operations.

---

## 🧠 Key Features

- Hybrid **Digital Twin + Human-Centric Orchestration**
- Multi-objective optimization (latency, energy, reliability)
- Trust-aware decision scoring
- Explainability-aware orchestration decisions
- Human override and intervention modeling
- Comparative evaluation against baseline policies
- Fully reproducible simulation-based experiments

---

## 📂 Repository Structure

ADTO-CPS-Digital-Twin-Orchestration/
│
├── HC_ADTO_CPS_Human_Centric_DT.ipynb   # Main notebook (core implementation)
├── paper.pdf                            # Associated research paper
├── README.md                            # Repository documentation
├── requirements.txt                     # Python dependencies
├── results/                             # Generated outputs
│   ├── figures/
│   ├── tables/
│   └── logs/

---

## ⚙️ Installation

Clone the repository:

git clone https://github.com/hamamh66/ADTO-CPS-Digital-Twin-Orchestration.git
cd ADTO-CPS-Digital-Twin-Orchestration

Install dependencies:

pip install -r requirements.txt

---

## ▶️ Usage

Launch the notebook:

jupyter notebook HC_ADTO_CPS_Human_Centric_DT.ipynb

Run all cells sequentially to:

- Simulate CPS orchestration scenarios  
- Compare baseline and human-centric policies  
- Generate performance metrics  
- Export figures and tables  

---

## 🧪 Experimental Design

### 🔹 Baseline Policies
- Cloud
- Local
- Random
- Greedy
- Digital Twin (DT)

### 🔹 Human-Centric Policies
- HC-DT Balanced  
- HC-DT Reliability  
- HC-DT Latency  
- HC-DT Energy  
- HC-DT Override  

---

## 📊 Evaluation Scenarios

The framework evaluates system behavior under multiple conditions:

- Scalability (increasing number of nodes)
- Workload stress
- Failure and disruption scenarios
- Trust-aware decision quality
- Explanation consistency
- Ablation analysis

---

## 📈 Output

Running the notebook generates:

- Performance comparison plots  
- Latency / energy / reliability trade-offs  
- Trust-weighted decision metrics  
- Explanation usage statistics  
- Tables aligned with the paper results  

All outputs are saved in:

results/

---

## 🔁 Reproducibility

- Fixed random seeds are used for deterministic simulations  
- All experiments can be reproduced directly from the notebook  
- No external/private datasets are required  

---

## 📚 Citation

If you use this repository, please cite:

@article{hamam2026adto,
  title={Human-Centric Digital Twin Orchestration for Industrial Cyber-Physical Systems},
  author={Hamam, Habib and others},
  journal={...},
  year={2026}
}

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 👤 Contact

**Prof. Habib Hamam**  
Université de Moncton  
Email: Habib.Hamam@umoncton.ca  

---

## 🚀 Acknowledgment

This repository supports reproducible research in:

- Digital Twins  
- Industrial AI  
- Explainable AI  
- Human-in-the-loop systems  
- Smart CPS orchestration  
