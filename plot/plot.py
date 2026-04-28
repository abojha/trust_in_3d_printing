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

    step = probabilities[1] - probabilities[0] if len(probabilities) > 1 else 0
    prob_tag = f"{min(probabilities):.2f}_to_{max(probabilities):.2f}_step{step:.2f}_n{len(probabilities)}"

    attack_types = sorted(set(attacks_map.values()))

    STYLES = {
        "command_injection":  {"color": "#2196F3", "marker": "o",  "ls": "-"},
        "temperature_shock":  {"color": "#FF9800", "marker": "s",  "ls": "--"},
        "extrusion_flood":    {"color": "#4CAF50", "marker": "^",  "ls": ":"},
    }

    # ── Collect data per-seed (and compute means) ───────────────────
    # attack_data_per_seed: { attack: { seed: [lat_per_prob,...] } }
    attack_data_per_seed = {}
    attack_data_mean = {}

    for attack in attack_types:
        dt_id = ATTACK_DT.get(attack)
        if dt_id is None:
            continue

        # initialize per-seed lists
        per_seed = {s: [] for s in seeds}

        for prob in probabilities:
            prob_label = f"{prob:.2f}".replace(".", "_")
            for seed in seeds:
                variant_folder = f"sweep_p{prob_label}_s{seed}"
                variant_dir = exp_root / variant_folder

                t_seq = first_decision_index(
                    variant_dir / "ProposedMethod" / f"{dt_id}.csv",
                    {"PAUSE"}
                )
                per_seed[seed].append(t_seq if t_seq is not None else float("nan"))

        # compute mean across seeds for this attack (per-probability)
        per_seed_arrs = [np.array(per_seed[s], dtype=float) for s in seeds]
        # stack into 2D (n_seeds x n_probs) and compute nanmean along axis 0
        if per_seed_arrs:
            stacked = np.vstack(per_seed_arrs)
            mean_per_prob = np.nanmean(stacked, axis=0)
            # convert to python list with nan where appropriate
            mean_list = [float(x) if not np.isnan(x) else float("nan") for x in mean_per_prob]
        else:
            mean_list = [float("nan")] * len(probabilities)

        attack_data_per_seed[attack] = per_seed
        attack_data_mean[attack] = mean_list

    # ── Save summary CSV (means across seeds) ───────────────────
    csv_rows = {"prob": probabilities}
    for attack in attack_types:
        nice = ATTACK_NICE.get(attack, attack)
        csv_rows[nice] = attack_data_mean.get(attack, [float("nan")] * len(probabilities))
    summary_df = pd.DataFrame(csv_rows)
    csv_path = output_dir / f"sweep_summary_{prob_tag}.csv"
    summary_df.to_csv(csv_path, index=False)
    print(f"[OK] Saved {csv_path}")

    # ── Plot: Detection Latency vs Attack Probability (MEAN across seeds) ─
    #
    # Layout: one subplot per attack type (rows) — lines NEVER overlap.
    # Combined overlay also saved separately with log-scale y-axis.
    # ─────────────────────────────────────────────────────────────────────

    probs_arr = np.array(probabilities)
    title_name = exp_name.replace("_", " ").title()

    # ── (A) Separate subplot per attack ─────────────────────────────────
    n_attacks = len(attack_types)
    fig, axes = plt.subplots(n_attacks, 1, figsize=(14, 3.2 * n_attacks),
                             sharex=True)
    if n_attacks == 1:
        axes = [axes]

    for idx, attack in enumerate(attack_types):
        ax = axes[idx]
        nice = ATTACK_NICE.get(attack, attack)
        style = STYLES.get(attack, {"color": "gray", "marker": "o", "ls": "-"})
        mean_lats = np.array(
            attack_data_mean.get(attack, [float("nan")] * len(probabilities)),
            dtype=float)

        # min-max band from per-seed data
        per_seed_map = attack_data_per_seed.get(attack, {})
        if per_seed_map:
            seed_arrs = [np.array(per_seed_map[s], dtype=float) for s in seeds]
            stacked = np.vstack(seed_arrs)
            min_arr = np.nanmin(stacked, axis=0)
            max_arr = np.nanmax(stacked, axis=0)
        else:
            min_arr = max_arr = mean_lats.copy()

        mask = ~np.isnan(mean_lats)
        if mask.any():
            valid_min = np.where(np.isnan(min_arr), mean_lats, min_arr)
            valid_max = np.where(np.isnan(max_arr), mean_lats, max_arr)

            ax.fill_between(probs_arr[mask], valid_min[mask], valid_max[mask],
                            color=style["color"], alpha=0.15, label="Seed range")
            ax.plot(probs_arr[mask], mean_lats[mask],
                    marker=style.get("marker", "o"),
                    linestyle=style.get("ls", "-"),
                    color=style["color"], linewidth=2.4, markersize=7,
                    markeredgecolor="white", markeredgewidth=0.8,
                    label=f"Mean ({nice})")

            # annotate EVERY valid point with its value
            valid_idx = np.where(mask)[0]
            for ki in valid_idx:
                ax.annotate(f"{mean_lats[ki]:.0f}",
                            xy=(probs_arr[ki], mean_lats[ki]),
                            textcoords="offset points", xytext=(0, 10),
                            ha="center", fontsize=7, fontweight="bold",
                            color=style["color"],
                            bbox=dict(boxstyle="round,pad=0.12",
                                      fc="white", ec=style["color"],
                                      alpha=0.7, lw=0.4))

        ax.set_ylabel("Latency\n(cmd index)", fontsize=10)
        ax.set_title(nice, fontsize=12, fontweight="bold", color=style["color"],
                     loc="left")
        ax.legend(fontsize=9, loc="upper right", framealpha=0.8)
        ax.grid(alpha=0.25)
        # nice y-limits with headroom
        yvals = mean_lats[mask] if mask.any() else np.array([0])
        y_top = max(np.nanmax(yvals) * 1.25, 1)
        ax.set_ylim(-0.5, y_top)

    axes[-1].set_xlabel("Attack Probability", fontsize=12)
    axes[-1].set_xticks(probabilities)
    axes[-1].set_xticklabels([f"{p:.2f}" for p in probabilities],
                             fontsize=7, rotation=45, ha="right")
    fig.suptitle(f"{title_name}\nDetection Latency vs Attack Probability",
                 fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()

    out_path = output_dir / f"detection_latency_vs_attack_prob_{prob_tag}.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_path}")

    # ── (B) Combined overlay with LOG y-axis (handles huge range) ───────
    fig, ax = plt.subplots(figsize=(10, 5))

    for i, attack in enumerate(attack_types):
        nice = ATTACK_NICE.get(attack, attack)
        style = STYLES.get(attack, {"color": "gray", "marker": "o", "ls": "-"})
        mean_lats = np.array(
            attack_data_mean.get(attack, [float("nan")] * len(probabilities)),
            dtype=float)
        # shift zeros to 0.5 so log scale works
        plot_lats = np.where(mean_lats == 0, 0.5, mean_lats)
        mask = ~np.isnan(mean_lats)
        if mask.any():
            ax.plot(probs_arr[mask], plot_lats[mask],
                    marker=style.get("marker", "o"),
                    linestyle=style.get("ls", "-"),
                    color=style["color"], linewidth=2.5, markersize=8,
                    label=nice, markeredgecolor="white", markeredgewidth=0.9)

    ax.set_yscale("log")
    ax.set_xlabel("Attack Probability", fontsize=13)
    ax.set_ylabel("Detection Latency (log scale, cmd index)", fontsize=12)
    ax.set_title(f"{title_name}\nDetection Latency vs Attack Probability (All Attacks)",
                 fontsize=14, fontweight="bold")
    ax.set_xticks([p for p in probabilities if p * 100 % 10 == 0]
                  if len(probabilities) > 12 else probabilities)
    if len(probabilities) > 12:
        ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()

    out_combined = output_dir / f"detection_latency_vs_attack_prob_combined_log_{prob_tag}.png"
    fig.savefig(out_combined, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Saved {out_combined}")

    # ── Per-seed plots (one PNG per seed, subplot per attack) ─────────
    for seed in seeds:
        fig, axes = plt.subplots(n_attacks, 1,
                                 figsize=(14, 3.2 * n_attacks), sharex=True)
        if n_attacks == 1:
            axes = [axes]

        any_plotted = False
        for idx, attack in enumerate(attack_types):
            ax = axes[idx]
            nice = ATTACK_NICE.get(attack, attack)
            style = STYLES.get(attack, {"color": "gray", "marker": "o", "ls": "-"})
            per_seed_lats = attack_data_per_seed.get(attack, {}).get(seed, [])

            if not per_seed_lats:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                        ha="center", va="center", fontsize=12, color="gray")
                ax.set_title(nice, fontsize=12, fontweight="bold",
                             color=style["color"], loc="left")
                continue

            lats_arr = np.array(per_seed_lats, dtype=float)
            mask = ~np.isnan(lats_arr)

            if mask.any():
                any_plotted = True
                ax.plot(probs_arr[mask], lats_arr[mask],
                        marker=style.get("marker", "o"),
                        linestyle=style.get("ls", "-"),
                        color=style["color"], linewidth=2.4, markersize=7,
                        label=nice, markeredgecolor="white",
                        markeredgewidth=0.8, alpha=0.95)

                # annotate EVERY valid point with its value
                valid_idx = np.where(mask)[0]
                for ki in valid_idx:
                    ax.annotate(f"{int(lats_arr[ki])}",
                                xy=(probs_arr[ki], lats_arr[ki]),
                                textcoords="offset points", xytext=(0, 10),
                                ha="center", fontsize=7, fontweight="bold",
                                color=style["color"],
                                bbox=dict(boxstyle="round,pad=0.12",
                                          fc="white", ec=style["color"],
                                          alpha=0.7, lw=0.4))

                yvals = lats_arr[mask]
                y_top = max(np.nanmax(yvals) * 1.25, 1)
                ax.set_ylim(-0.5, y_top)

            ax.set_ylabel("Latency\n(cmd index)", fontsize=10)
            ax.set_title(nice, fontsize=12, fontweight="bold",
                         color=style["color"], loc="left")
            ax.legend(fontsize=9, loc="upper right", framealpha=0.8)
            ax.grid(alpha=0.25)

        if not any_plotted:
            plt.close(fig)
            print(f"[WARN] No per-seed detection data for seed {seed}; skipping.")
            continue

        axes[-1].set_xlabel("Attack Probability", fontsize=12)
        axes[-1].set_xticks(probabilities)
        axes[-1].set_xticklabels([f"{p:.2f}" for p in probabilities],
                                 fontsize=7, rotation=45, ha="right")
        fig.suptitle(f"{title_name} — Seed {seed}\n"
                     f"Detection Latency vs Attack Probability",
                     fontsize=14, fontweight="bold", y=1.01)
        fig.tight_layout()

        seed_out = output_dir / f"detection_latency_vs_attack_prob_seed_{seed}_{prob_tag}.png"
        fig.savefig(seed_out, dpi=DPI, bbox_inches="tight")
        plt.close(fig)
        print(f"[OK] Saved {seed_out}")

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
