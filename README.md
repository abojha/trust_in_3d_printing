# Trust-Based Security Framework for 3D Printing Digital Twins

A real-time trust enforcement framework for securing G-code execution in digital twin–managed additive manufacturing systems. The Trust Layer sits between the digital twin and the physical printer, evaluating every G-code command against immutable behavioral and physical references to detect attacks such as **command injection**, **temperature shock**, and **extrusion flooding**.

The proposed method achieves **100% detection rate** with **zero false positives** across all attack types and print models, detecting attacks within **0–22 commands**.

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (One Command)](#quick-start-one-command)
- [Manual Step-by-Step Setup](#manual-step-by-step-setup)
- [What the Pipeline Does](#what-the-pipeline-does)
- [Expected Output](#expected-output)
- [Configuration](#configuration)
- [Trust Model Parameters](#trust-model-parameters)
- [Baselines](#baselines)
- [Troubleshooting](#troubleshooting)

---

## Overview

The framework introduces a **Trust Layer** that treats each digital twin as a semi-trusted source. Trust is computed using two reference specifications:

- **Physical Reference (PR):** Hardware-level safety constraints (Ultimaker S5 profile)
- **Behavioral Reference (BR):** Expected layer-wise execution behavior generated from the sliced G-code

Every command is validated at both the **command level** (design-intent deviation) and **execution level** (physical constraint violation). Deviations are accumulated over time to compute a trust score. When trust falls below `T_min = 0.50`, execution is **paused**.

### Attack Scenarios

| DT | Role | Attack |
|----|------|--------|
| DT-1 | Benign | None |
| DT-2 | Malicious | Command injection (`M221 S200`, `G92 E1000`, `M92 E2000`) |
| DT-3 | Malicious | Temperature shock (oscillates between 200°C and 220°C) |
| DT-4 | Malicious | Extrusion flood (`G1 X0.1 Y0.1 E20 F600`) |

---

## Project Structure

```
trust_in_3d_printing/
├── main.py                          # Entry point — runs all experiments
├── runner.sh                        # One-command pipeline (venv + install + run)
├── requirements.txt                 # Python dependencies
├── experiments/
│   └── experiments_config.json      # Experiment definitions & sweep parameters
├── trust_layer/                     # Core trust evaluation
│   ├── trust_layer.py               # Trust score computation (T = ω·T + (1−ω)·E)
│   ├── command_validator.py         # acc_cmd and acc_exec computation
│   ├── command_analyzer.py          # G-code state tracking
│   ├── reference_loader.py          # Loads behavioral & physical references
│   └── reference_context.py         # Per-layer reference lookup
├── attacks/
│   └── attacks.py                   # Command injection, temp shock, extrusion flood
├── baselines/
│   ├── CBSM/                        # Constraint-Based Safety Monitor
│   │   ├── constraint_monitor.py
│   │   └── dangerous_gcode.py
│   └── RSAM/                        # Runtime Statistical Anomaly Monitor
│       └── run_time_anamoly_monitor.py
├── digital_twin/
│   ├── digital_twin.py              # Digital twin abstraction
│   └── dt_manger.py                 # DT lifecycle management
├── physical_machine/
│   ├── physical_machine.py          # Physical machine abstraction
│   └── pm_manger.py                 # PM lifecycle management
├── simulation/
│   └── simulation_controller.py     # Orchestrates DTs, PMs, trust, baselines
├── plot/
│   └── plot.py                      # 5 plot types + sweep comparison plots
├── logs/
│   └── logger.py                    # Logging utilities
├── slicer/
│   └── cura_engine.py               # (Optional) G-code generation from STL via CuraEngine
├── references/
│   ├── behavioral_references/       # Per-model behavioral references (JSON)
│   │   ├── cuboid_br.json
│   │   ├── cylinder_br.json
│   │   └── flatplate_br.json
│   ├── physical_references/
│   │   └── physical_references.json # Ultimaker S5 machine profile
│   ├── g_code/                      # Pre-sliced G-code files
│   ├── stl/                         # STL model files
│   └── ultimaker_s5/                # Printer definition
└── results/                         # Generated experiment outputs (gitignored)
    ├── cuboid_experiment/
    ├── cylinder_experiment/
    └── flatplate_experiment/
```

---

## Prerequisites

- **Python 3.10+** (tested with Python 3.14)
- **Git**
- **Bash** (Git Bash on Windows, or any Linux/macOS terminal)

> **Note:** CuraEngine is **not required** to run experiments. All G-code and behavioral references are pre-generated and included in the repository.

---

## Quick Start (One Command)

```bash
git clone https://github.com/abojha/trust_in_3d_printing.git
cd trust_in_3d_printing
chmod +x runner.sh
./runner.sh
```

The `runner.sh` script will:
1. Create a Python virtual environment (`.venv`)
2. Install all dependencies from `requirements.txt`
3. *(Optional)* Run the Cura slicer pipeline — **will skip gracefully if CuraEngine is not installed**
4. Run all 18 experiments (3 models × 6 attack probabilities)
5. Generate all plots

---

## Manual Step-by-Step Setup

If you prefer to run each step manually:

### 1. Clone the Repository

```bash
git clone https://github.com/abojha/trust_in_3d_printing.git
cd trust_in_3d_printing
```

### 2. Create and Activate a Virtual Environment

**Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (Git Bash):**
```bash
python -m venv .venv
source .venv/Scripts/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run All Experiments

```bash
python main.py experiments/experiments_config.json
```

Or simply:
```bash
python main.py
```

This runs **18 experiment variants** (3 print models × 6 attack probabilities), each with 4 digital twins. Total: **72 simulation runs**.

---

## What the Pipeline Does

For each experiment variant (e.g., `cuboid_experiment` at `p=0.25`, `seed=42`):

1. **Loads** the G-code file and behavioral reference for the print model
2. **Creates** 4 digital twins: DT-1 (benign), DT-2 (command injection), DT-3 (temperature shock), DT-4 (extrusion flood)
3. **Simulates** G-code execution command-by-command
4. At each command, the **Trust Layer** evaluates:
   - `acc_cmd`: deviation from expected behavior (semantic match, bounding box, feedrate, Z-height, jump distance)
   - `acc_exec`: deviation from physical constraints (firmware manipulation, flood patterns, extrusion density, temperature, retraction)
5. **Baselines** (CBSM and RSAM) also evaluate each command independently
6. **Logs** all trust scores, decisions, and baseline results to CSV files
7. **Generates plots**: trust trajectories, zoomed views, accusation timelines, detection latency comparisons

---

## Expected Output

After a successful run, the `results/` directory will contain:

```
results/
├── cuboid_experiment/
│   ├── sweep_p0_00_s42/          # p=0.0 (no attacks — baseline)
│   │   ├── ProposedMethod/
│   │   │   ├── dt_1.csv          # Trust scores for benign DT
│   │   │   ├── dt_2.csv          # Trust scores for command injection DT
│   │   │   ├── dt_3.csv          # Trust scores for temperature shock DT
│   │   │   └── dt_4.csv          # Trust scores for extrusion flood DT
│   │   ├── CBSM/
│   │   │   └── dt_*.csv          # CBSM baseline results
│   │   ├── RSAM/
│   │   │   └── dt_*.csv          # RSAM baseline results
│   │   ├── logs/
│   │   │   └── dt_*.log          # Execution logs
│   │   └── plots/
│   │       ├── combined_trust_trajectory.png
│   │       ├── trust_trajectory_zoom.png
│   │       ├── accusation_timeline.png
│   │       ├── detection_latency_comparison.png
│   │       └── dt_*_trust_trajectory.png
│   ├── sweep_p0_10_s42/
│   ├── sweep_p0_25_s42/
│   ├── sweep_p0_50_s42/
│   ├── sweep_p0_75_s42/
│   ├── sweep_p1_00_s42/
│   └── sweep_plots/              # Cross-probability comparison plots
│       └── detection_latency_vs_attack_prob.png
├── cylinder_experiment/          # Same structure
└── flatplate_experiment/         # Same structure
```

**Expected totals:** ~225 CSV files, ~146 PNG plots.

### Console Output

You will see progress like:
```
============================================================
  Trust in 3D Printing - Unified Pipeline
  Experiment: cuboid_experiment
  Experiment: cylinder_experiment
  Experiment: flatplate_experiment
  Probabilities: [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
  Seeds:         [42]
  Total runs:    18
============================================================
[1/18] cuboid_experiment prob=0.0 seed=42
  Done: sweep_p0_00_s42
[2/18] cuboid_experiment prob=0.1 seed=42
  Done: sweep_p0_10_s42
...
[18/18] flatplate_experiment prob=1.0 seed=42
  Done: sweep_p1_00_s42

============================================================
  Generating sweep comparison graphs...
============================================================
All experiments and graphs complete!
```

---

## Configuration

All experiment parameters are in `experiments/experiments_config.json`:

```json
{
  "probability_sweep": [0.0, 0.1, 0.25, 0.5, 0.75, 1.0],
  "seeds": [42],
  "experiments": [
    {
      "name": "cuboid_experiment",
      "gcode_path": "references/g_code/cuboid.gcode",
      "reference_path": "references/behavioral_references/cuboid_br.json",
      "machine_reference": "references/physical_references/physical_references.json",
      "num_dts": 4,
      "attacks": { "2": "command_injection", "3": "temperature_shock", "4": "extrusion_flood" }
    }
  ]
}
```

| Parameter | Description |
|-----------|-------------|
| `probability_sweep` | List of attack injection probabilities |
| `seeds` | Random seeds for reproducibility |
| `num_dts` | Number of digital twins per experiment (4: 1 benign + 3 attacked) |
| `attacks` | Mapping of DT ID → attack type |

---

## Trust Model Parameters

| Parameter | Symbol | Value | Description |
|-----------|--------|-------|-------------|
| Decay factor | θ | 0.6 | Accusation memory decay |
| Mapping steepness | α | 3.0 | Exponential mapping sensitivity |
| Trust inertia | ω | 0.4 | Smoothing weight for trust updates |
| Initial trust | T_init | 0.75 | Starting trust score |
| Pause threshold | T_min | 0.50 | Trust below this → PAUSE |

**Trust update equation:**
```
S_cmd(t) = θ · S_cmd(t-1) + acc_cmd(t)
CCT = exp(-α · S_cmd)
EFCT = exp(-α · S_exec)
E = min(CCT, EFCT)
T(t) = ω · T(t-1) + (1 - ω) · E
Decision: PAUSE if T < T_min
```

---

## Baselines

### CBSM (Constraint-Based Safety Monitor)
- Static blacklist matching (`M221`, `M92`, `G92 E>10`, etc.)
- Temperature ceiling: 280°C
- Max extrusion per command: 50mm
- **Limitation:** Detects only command injection (33% overall)

### RSAM (Runtime Statistical Anomaly Monitor)
- EWMA-based anomaly detection (α=0.9, window=10)
- Requires 20-command warm-up (burn-in)
- Persistence: 3 consecutive violations before alert
- **Limitation:** Misses command injection; slow detection (47% overall)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `python` not found | Ensure Python 3.10+ is on your PATH |
| `runner.sh` fails at Cura step | This is expected if CuraEngine is not installed. The script will exit, but G-code files are already in the repo. Run `python main.py` directly instead. |
| `matplotlib` rendering errors | Install/upgrade matplotlib: `pip install --upgrade matplotlib`. On headless servers, set `export MPLBACKEND=Agg` before running. |
| Permission denied on `runner.sh` | Run `chmod +x runner.sh` first |
| Import errors | Make sure you're in the project root directory and your venv is activated |

---

## Key Results

| Metric | Proposed | CBSM | RSAM |
|--------|----------|------|------|
| False Positive Rate | **0%** | 0% | 0% |
| Overall Detection Rate | **100%** | 33% | 47% |
| Latency Range (commands) | **0–22** | 0–3* | 21–136* |
| Enforcement Action | PAUSE | BLOCK | ALERT only |

*Latency ranges shown only for cases where detection occurred.

---

## License

This project is part of academic research on trust-based security for additive manufacturing systems.

---

## Citation

If you use this framework in your research, please cite the associated paper.
