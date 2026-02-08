"""
graphs/compare_plots.py

Comparison plots for Trust vs Baseline detectors.

Graphs generated:
1. Trust trajectory (Trust model only)
2. Detection latency bar chart
3. Detection order comparison (relative ranking)
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# =========================================================
# CONFIG
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESULT_DIRS = {
    "trust": PROJECT_ROOT / "results" / "trust",
    "ieee": PROJECT_ROOT / "results" / "ieee_baseline",
    "static": PROJECT_ROOT / "results" / "static_baseline",
}

OUTPUT_DIR = PROJECT_ROOT / "graphs" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRUST_THRESHOLD = 0.5
DPI = 300

DT_NAMES = {
    "dt_1": "Benign",
    "dt_2": "Command Injection",
    "dt_3": "Temperature Shock",
    "dt_4": "Extrusion Flood",
}

METHOD_ORDER = ["Our Method", "Run Time Anamoly Detector", "Static Constraint Safety"]

# =========================================================
# HELPERS
# =========================================================

def first_decision_index(csv_path, stop_decisions):
    if not csv_path.exists():
        return None

    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        if row["decision"] in stop_decisions:
            return int(row["seq"])
    return None

# =========================================================
# GRAPH 1: TRUST TRAJECTORY (TRUST ONLY)
# =========================================================

def plot_trust_only(dt_id):
    trust_csv = RESULT_DIRS["trust"] / f"{dt_id}.csv"
    trust_df = pd.read_csv(trust_csv)

    trust_stop = first_decision_index(trust_csv, {"PAUSE"})

    plt.figure(figsize=(8, 4))

    plt.plot(
        trust_df["seq"],
        trust_df["trust"],
        linewidth=1.6,
        label="Trust Score"
    )

    plt.axhline(
        TRUST_THRESHOLD,
        linestyle="--",
        color="gray",
        linewidth=1.2,
        label="Trust Threshold"
    )

    if trust_stop is not None:
        plt.axvline(
            trust_stop,
            linestyle="--",
            color="red",
            label="Trust Detection"
        )

    plt.ylim(0.0, 1.0)
    plt.xlabel("Command Sequence")
    plt.ylabel("Trust Score")
    plt.title(f"Trust Trajectory — {DT_NAMES[dt_id]}")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    out = OUTPUT_DIR / f"{dt_id}_trust_trajectory.png"
    plt.savefig(out, dpi=DPI)
    plt.close()

    print(f"[OK] Saved {out.name}")

# =========================================================
# GRAPH 2: DETECTION LATENCY BAR CHART
# =========================================================

def plot_detection_latency():
    rows = []

    for dt_id, name in DT_NAMES.items():
        rows.append({
            "Scenario": name,
            "Our Method": first_decision_index(
                RESULT_DIRS["trust"] / f"{dt_id}.csv", {"PAUSE"}
            ),
            "Run Time Anamoly Detector": first_decision_index(
                RESULT_DIRS["ieee"] / f"{dt_id}.csv", {"ALERT"}
            ),
            "Static Constraint Safety": first_decision_index(
                RESULT_DIRS["static"] / f"{dt_id}.csv", {"BLOCK"}
            ),
        })

    df = pd.DataFrame(rows).set_index("Scenario")

    df.plot(
        kind="bar",
        figsize=(8, 4),
        width=0.75
    )

    plt.ylabel("Detection Command Index")
    plt.title("Detection Latency Comparison")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()

    out = OUTPUT_DIR / "detection_latency_comparison.png"
    plt.savefig(out, dpi=DPI)
    plt.close()

    print(f"[OK] Saved {out.name}")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    for dt in DT_NAMES:
        plot_trust_only(dt)
    plot_detection_latency()

    print("[DONE] All comparison plots generated.")
