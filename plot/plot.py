"""
plot/plot.py

Publication / presentation quality plots for trust-based 3D printing security.
"""

from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np
import os

# =========================================================
# CONFIG
# =========================================================

TRUST_THRESHOLD = 0.5
DPI = 300

DT_NAMES = {
    "dt_1": "Benign",
    "dt_2": "Command Injection",
    "dt_3": "Temperature Shock",
    "dt_4": "Extrusion Flood",
}

DT_COLORS = {
    "dt_1": "#4CAF50",   # green  — benign
    "dt_2": "#2196F3",   # blue   — command injection
    "dt_3": "#FF9800",   # orange — temperature shock
    "dt_4": "#E91E63",   # pink   — extrusion flood
}

# =========================================================
# PATH BUILDER
# =========================================================

def get_paths(base_dir):
    base = Path(base_dir)
    result_dirs = {
        "trust": base / "ProposedMethod",
        "ieee":  base / "RSAM",
        "static": base / "CBSM",
    }
    output_dir = base / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    return result_dirs, output_dir

# =========================================================
# HELPERS
# =========================================================

def first_decision_index(csv_path, stop_decisions):
    """Return the seq of the first row where decision is in stop_decisions."""
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        if row["decision"] in stop_decisions:
            return int(row["seq"])
    return None

# =========================================================
# GRAPH 1: INDIVIDUAL TRUST TRAJECTORY PER DT
#   — Full trace with threshold line and detection marker
# =========================================================

def plot_trust_only(dt_id, RESULT_DIRS, OUTPUT_DIR):
    trust_csv = RESULT_DIRS["trust"] / f"{dt_id}.csv"
    if not trust_csv.exists():
        print(f"[WARN] Missing {trust_csv}")
        return

    df = pd.read_csv(trust_csv)
    color = DT_COLORS.get(dt_id, "#333")
    name = DT_NAMES.get(dt_id, dt_id)

    fig, ax = plt.subplots(figsize=(10, 4))

    ax.plot(df["seq"], df["trust"], linewidth=1.2, color=color,
            label="Trust Score", alpha=0.85)

    # Threshold line
    ax.axhline(TRUST_THRESHOLD, linestyle="--", color="red",
               linewidth=1.4, label=f"Threshold ($T_{{min}}={TRUST_THRESHOLD}$)")

    # Mark first PAUSE with a big red X
    det_seq = first_decision_index(trust_csv, {"PAUSE"})
    if det_seq is not None:
        det_row = df[df["seq"] == det_seq]
        if not det_row.empty:
            ax.scatter(det_seq, det_row["trust"].values[0],
                       marker="X", s=200, c="red", zorder=5,
                       label=f"Detection @ cmd {det_seq}")
            # Vertical line at detection
            ax.axvline(det_seq, linestyle=":", color="red",
                       linewidth=1.0, alpha=0.5)

    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Command Sequence", fontsize=12)
    ax.set_ylabel("Trust Score", fontsize=12)
    ax.set_title(f"Trust Trajectory — {name}", fontsize=13, fontweight="bold")
    ax.legend(loc="lower left", fontsize=10)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out = OUTPUT_DIR / f"{dt_id}_trust_trajectory.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] Saved {out.name}")


# =========================================================
# GRAPH 2: COMBINED TRUST TRAJECTORY — ALL 4 DTs OVERLAID
#   — Best for presentations: one picture tells the story
# =========================================================

def plot_combined_trust(RESULT_DIRS, OUTPUT_DIR):
    fig, ax = plt.subplots(figsize=(12, 5))

    detection_annotations = []

    for dt_id in ["dt_1", "dt_2", "dt_3", "dt_4"]:
        csv_path = RESULT_DIRS["trust"] / f"{dt_id}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        color = DT_COLORS[dt_id]
        name = DT_NAMES[dt_id]
        lw = 2.0 if dt_id == "dt_1" else 1.4

        ax.plot(df["seq"], df["trust"], linewidth=lw, color=color,
                label=name, alpha=0.85)

        # Detection marker
        det_seq = first_decision_index(csv_path, {"PAUSE"})
        if det_seq is not None:
            det_row = df[df["seq"] == det_seq]
            if not det_row.empty:
                trust_val = det_row["trust"].values[0]
                ax.scatter(det_seq, trust_val,
                           marker="X", s=180, c="red", zorder=5,
                           edgecolors="darkred", linewidths=0.5)
                detection_annotations.append((det_seq, trust_val, name))

    # Threshold
    ax.axhline(TRUST_THRESHOLD, linestyle="--", color="red",
               linewidth=1.4, alpha=0.7,
               label=f"Threshold ($T_{{min}}={TRUST_THRESHOLD}$)")

    # Annotate detection points
    offsets_y = [0.06, -0.08, 0.06]
    for i, (seq, tv, nm) in enumerate(detection_annotations):
        oy = offsets_y[i % len(offsets_y)]
        ax.annotate(f"{nm}\ncmd {seq}",
                    xy=(seq, tv), fontsize=8,
                    xytext=(seq + 30, tv + oy),
                    arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.9))

    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Command Sequence", fontsize=13)
    ax.set_ylabel("Trust Score", fontsize=13)
    ax.set_title("Trust Score Trajectory — All Scenarios", fontsize=14, fontweight="bold")
    ax.legend(loc="lower left", fontsize=10, ncol=2)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out = OUTPUT_DIR / "combined_trust_trajectory.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] Saved {out.name}")


# =========================================================
# GRAPH 3: ZOOMED TRUST DROP — First 200 commands
#   — Shows the attack detection zone clearly
# =========================================================

def plot_trust_zoom(RESULT_DIRS, OUTPUT_DIR, zoom_end=200):
    fig, ax = plt.subplots(figsize=(10, 5))

    for dt_id in ["dt_1", "dt_2", "dt_3", "dt_4"]:
        csv_path = RESULT_DIRS["trust"] / f"{dt_id}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)
        df_zoom = df[df["seq"] <= zoom_end]
        color = DT_COLORS[dt_id]
        name = DT_NAMES[dt_id]

        ax.plot(df_zoom["seq"], df_zoom["trust"],
                linewidth=2.0, color=color, label=name, alpha=0.9,
                marker="o" if len(df_zoom) < 50 else None,
                markersize=4)

        # Detection marker
        det_seq = first_decision_index(csv_path, {"PAUSE"})
        if det_seq is not None and det_seq <= zoom_end:
            det_row = df[df["seq"] == det_seq]
            if not det_row.empty:
                trust_val = det_row["trust"].values[0]
                ax.scatter(det_seq, trust_val,
                           marker="X", s=250, c="red", zorder=5,
                           edgecolors="darkred", linewidths=0.8)
                ax.annotate(f"Detected @ cmd {det_seq}\n(T={trust_val:.3f})",
                            xy=(det_seq, trust_val), fontsize=9,
                            xytext=(det_seq + 8, trust_val - 0.08),
                            arrowprops=dict(arrowstyle="->", color="red", lw=1.0),
                            bbox=dict(boxstyle="round,pad=0.3", fc="#fff3e0",
                                      ec="red", alpha=0.9),
                            fontweight="bold")

    ax.axhline(TRUST_THRESHOLD, linestyle="--", color="red",
               linewidth=1.4, alpha=0.7,
               label=f"Threshold ($T_{{min}}={TRUST_THRESHOLD}$)")

    # Shade the danger zone
    ax.axhspan(0, TRUST_THRESHOLD, color="red", alpha=0.05)
    ax.text(zoom_end * 0.85, TRUST_THRESHOLD / 2, "PAUSE Zone",
            fontsize=11, color="red", alpha=0.5, ha="center",
            fontweight="bold")

    ax.set_ylim(-0.05, 1.05)
    ax.set_xlim(-2, zoom_end)
    ax.set_xlabel("Command Sequence", fontsize=13)
    ax.set_ylabel("Trust Score", fontsize=13)
    ax.set_title(f"Trust Score — Early Detection Zone (First {zoom_end} Commands)",
                 fontsize=14, fontweight="bold")
    ax.legend(loc="center right", fontsize=10)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    out = OUTPUT_DIR / "trust_trajectory_zoom.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] Saved {out.name}")


# =========================================================
# GRAPH 4: DETECTION LATENCY COMPARISON (3 Methods)
#   — Grouped horizontal bar chart with value labels
# =========================================================

def plot_detection_latency(RESULT_DIRS, OUTPUT_DIR):
    rows = []
    for dt_id, name in DT_NAMES.items():
        if dt_id == "dt_1":
            continue  # skip benign — no detection expected
        rows.append({
            "Scenario": name,
            "Our Method": first_decision_index(
                RESULT_DIRS["trust"] / f"{dt_id}.csv", {"PAUSE"}),
            "RSAM": first_decision_index(
                RESULT_DIRS["ieee"] / f"{dt_id}.csv", {"ALERT"}),
            "CBSM": first_decision_index(
                RESULT_DIRS["static"] / f"{dt_id}.csv", {"BLOCK"}),
        })

    df = pd.DataFrame(rows).set_index("Scenario")
    df = df.apply(pd.to_numeric, errors="coerce")

    if df.dropna(how="all").empty:
        print("[WARN] No detection data available to plot.")
        return

    # Replace NaN with a sentinel for "not detected"
    max_val = df.max().max()
    if np.isnan(max_val):
        max_val = 100

    METHOD_COLORS = {
        "Our Method": "#2196F3",
        "RSAM": "#FF9800",
        "CBSM": "#4CAF50",
    }

    scenarios = df.index.tolist()
    methods = df.columns.tolist()
    n_scenarios = len(scenarios)
    n_methods = len(methods)
    bar_height = 0.22
    y_positions = np.arange(n_scenarios)

    fig, ax = plt.subplots(figsize=(10, 4))

    for i, method in enumerate(methods):
        vals = df[method].values.copy()
        is_nd = np.isnan(vals)
        display_vals = np.where(is_nd, max_val * 1.15, vals)

        bars = ax.barh(y_positions + i * bar_height, display_vals,
                       height=bar_height,
                       color=METHOD_COLORS.get(method, "gray"),
                       alpha=0.85, label=method,
                       edgecolor="white", linewidth=0.5)

        # Value labels
        for j, (bar, v, nd) in enumerate(zip(bars, vals, is_nd)):
            if nd:
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                        "ND", va="center", fontsize=9, color="gray",
                        fontstyle="italic")
            else:
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                        f"{int(v)}", va="center", fontsize=10, fontweight="bold")

    ax.set_yticks(y_positions + bar_height * (n_methods - 1) / 2)
    ax.set_yticklabels(scenarios, fontsize=11)
    ax.set_xlabel("Detection Latency (Command Index)", fontsize=12)
    ax.set_title("Detection Latency Comparison — All Methods",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    ax.invert_yaxis()
    fig.tight_layout()

    out = OUTPUT_DIR / "detection_latency_comparison.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] Saved {out.name}")


# =========================================================
# GRAPH 5: ACCUSATION TIMELINE (acc_cmd + acc_exec + trust)
#   — Shows WHERE anomalies happen in the trace
# =========================================================

def plot_accusation_timeline(RESULT_DIRS, OUTPUT_DIR):
    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)

    attack_dts = [("dt_2", "Command Injection"),
                  ("dt_3", "Temperature Shock"),
                  ("dt_4", "Extrusion Flood")]

    for ax, (dt_id, name) in zip(axes, attack_dts):
        csv_path = RESULT_DIRS["trust"] / f"{dt_id}.csv"
        if not csv_path.exists():
            continue

        df = pd.read_csv(csv_path)

        ax.fill_between(df["seq"], df["acc_cmd"], alpha=0.4,
                        color="#2196F3", label="acc_cmd")
        ax.fill_between(df["seq"], df["acc_exec"], alpha=0.4,
                        color="#E91E63", label="acc_exec")
        ax.plot(df["seq"], df["trust"], linewidth=1.5,
                color="#333", label="Trust Score")

        ax.axhline(TRUST_THRESHOLD, linestyle="--", color="red",
                   linewidth=1.0, alpha=0.6)

        det_seq = first_decision_index(csv_path, {"PAUSE"})
        if det_seq is not None:
            ax.axvline(det_seq, linestyle=":", color="red",
                       linewidth=1.5, alpha=0.7)
            ax.text(det_seq + 5, 0.85, f"Det @ {det_seq}",
                    fontsize=9, color="red", fontweight="bold")

        ax.set_ylim(-0.05, 1.05)
        ax.set_ylabel(name, fontsize=11, fontweight="bold")
        ax.legend(loc="center right", fontsize=8, ncol=3)
        ax.grid(alpha=0.2)

    axes[-1].set_xlabel("Command Sequence", fontsize=12)
    axes[0].set_title("Accusation Scores & Trust — Attack Scenarios",
                      fontsize=14, fontweight="bold")
    fig.tight_layout()

    out = OUTPUT_DIR / "accusation_timeline.png"
    fig.savefig(out, dpi=DPI)
    plt.close(fig)
    print(f"[OK] Saved {out.name}")


# =========================================================
# MAIN FUNCTION
# =========================================================

def generate_all_plots(base_dir):
    RESULT_DIRS, OUTPUT_DIR = get_paths(base_dir)
    print(f"📊 Generating plots for: {base_dir}")

    # Individual trust trajectories
    for dt in DT_NAMES:
        plot_trust_only(dt, RESULT_DIRS, OUTPUT_DIR)

    # Combined overlay
    plot_combined_trust(RESULT_DIRS, OUTPUT_DIR)

    # Zoomed first-200-commands view
    plot_trust_zoom(RESULT_DIRS, OUTPUT_DIR, zoom_end=200)

    # Detection latency comparison (3 methods)
    plot_detection_latency(RESULT_DIRS, OUTPUT_DIR)

    # Accusation timeline (acc_cmd + acc_exec + trust)
    plot_accusation_timeline(RESULT_DIRS, OUTPUT_DIR)

    print("[DONE] All comparison plots generated.")


# =========================================================
# SWEEP COMPARISON GRAPHS (Probability vs Detection)
# =========================================================

ATTACK_DT = {
    "command_injection": "dt_2",
    "temperature_shock": "dt_3",
    "extrusion_flood":   "dt_4",
}

ATTACK_NICE = {
    "command_injection": "Command Injection",
    "temperature_shock": "Temperature Shock",
    "extrusion_flood":   "Extrusion Flood",
}


def generate_sweep_plots(exp_name, attacks_map, probabilities, seeds):
    """
    Generate sweep graphs per experiment:
      - Detection latency vs attack probability (line chart)
      - Saved to results/{exp_name}/sweep_plots/
    """
    exp_root = Path("results") / exp_name
    output_dir = exp_root / "sweep_plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    attack_types = sorted(set(attacks_map.values()))

    STYLES = {
        "command_injection":  {"color": "#2196F3", "marker": "o",  "ls": "-"},
        "temperature_shock":  {"color": "#FF9800", "marker": "s",  "ls": "--"},
        "extrusion_flood":    {"color": "#4CAF50", "marker": "^",  "ls": ":"},
    }

    # ── Collect data ────────────────────────────────────────
    attack_data = {}

    for attack in attack_types:
        dt_id = ATTACK_DT.get(attack)
        if dt_id is None:
            continue

        latencies_per_prob = []

        for prob in probabilities:
            seed_latencies = []
            for seed in seeds:
                prob_label = f"{prob:.2f}".replace(".", "_")
                variant_folder = f"sweep_p{prob_label}_s{seed}"
                variant_dir = exp_root / variant_folder

                t_seq = first_decision_index(
                    variant_dir / "ProposedMethod" / f"{dt_id}.csv",
                    {"PAUSE"}
                )
                seed_latencies.append(t_seq if t_seq is not None else float("nan"))

            mean_lat = np.nanmean(seed_latencies) if any(
                not np.isnan(v) for v in seed_latencies
            ) else float("nan")
            latencies_per_prob.append(mean_lat)

        attack_data[attack] = latencies_per_prob

    # ── Save summary CSV ────────────────────────────────────
    csv_rows = {"prob": probabilities}
    for attack in attack_types:
        nice = ATTACK_NICE.get(attack, attack)
        csv_rows[nice] = attack_data.get(attack, [float("nan")] * len(probabilities))
    summary_df = pd.DataFrame(csv_rows)
    csv_path = output_dir / "sweep_summary.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"[OK] Saved {csv_path}")

    # ── Plot: Detection Latency vs Attack Probability ───────
    fig, ax = plt.subplots(figsize=(9, 5))

    for attack in attack_types:
        nice = ATTACK_NICE.get(attack, attack)
        style = STYLES.get(attack, {"color": "gray", "marker": "x", "ls": "-"})
        lats = attack_data.get(attack, [])

        probs_arr = np.array(probabilities)
        lats_arr = np.array(lats)
        mask = ~np.isnan(lats_arr)

        if mask.any():
            ax.plot(probs_arr[mask], lats_arr[mask],
                    marker=style["marker"], linestyle=style["ls"],
                    color=style["color"], linewidth=2.5, markersize=10,
                    label=nice, markeredgecolor="white", markeredgewidth=1)

            # Value labels on each point
            for p, l in zip(probs_arr[mask], lats_arr[mask]):
                ax.annotate(f"{int(l)}", (p, l),
                            textcoords="offset points", xytext=(0, 12),
                            ha="center", fontsize=9, fontweight="bold")

    ax.set_xlabel("Attack Probability", fontsize=13)
    ax.set_ylabel("Detection Latency (Command Index)", fontsize=13)

    title_name = exp_name.replace("_", " ").title()
    ax.set_title(f"{title_name}\nDetection Latency vs Attack Probability",
                 fontsize=14, fontweight="bold")
    ax.set_xticks(probabilities)
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    out_path = output_dir / "detection_latency_vs_attack_prob.png"
    fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    print(f"[OK] Saved {out_path}")

    print(f"Sweep graph saved to: {output_dir}/")


# =========================================================
# CLI SUPPORT
# =========================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python plot.py <experiment_result_dir>")
        sys.exit(1)
    generate_all_plots(sys.argv[1])
