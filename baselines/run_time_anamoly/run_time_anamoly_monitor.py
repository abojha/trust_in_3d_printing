# baselines/runtime_anomaly/runtime_anomaly_monitor.py

class RuntimeAnomalyMonitor:
    """
    Runtime Statistical Anomaly Monitor (RSAM).

    A lightweight anomaly detection baseline that monitors
    runtime execution behavior using normalized extrusion statistics.

    Characteristics:
    - Uses only recent execution history
    - No design intent or reference model
    - No physical constraint awareness
    - No enforcement authority (alert-only)

    This baseline represents typical runtime anomaly detection
    approaches used in CPS and DT security literature.
    """

    def __init__(
        self,
        alpha=0.9,
        window_size=10,
        min_commands=20,
        relative_thresh=2.5,
        persistence_required=3
    ):
        self.alpha = alpha
        self.window_size = window_size
        self.min_commands = min_commands
        self.relative_thresh = relative_thresh
        self.persistence_required = persistence_required

        self.score = 0.0
        self.command_count = 0
        self.alerted = False
        self.consecutive_violations = 0

        # Store normalized extrusion ratios (E / XY distance)
        self.recent_ratios = []

    # =========================================================
    # UPDATE
    # =========================================================

    def update(self, analysis):
        self.command_count += 1
        deviation = 0.0

        effects = analysis.get("effects", {})
        de = effects.get("de", 0.0)
        xy_dist = effects.get("xy_dist", 0.0)

        # Ignore retractions and near-zero motion
        if de <= 0 or xy_dist < 0.01:
            self.score *= self.alpha
            return self.score

        ratio = de / xy_dist  # normalized extrusion density

        if len(self.recent_ratios) >= self.window_size:
            mean_ratio = sum(self.recent_ratios) / len(self.recent_ratios)

            if mean_ratio > 0 and ratio > self.relative_thresh * mean_ratio:
                deviation = (ratio - mean_ratio) / mean_ratio
            else:
                deviation = 0.0

        # EWMA accumulation
        self.score = self.alpha * self.score + deviation

        # Update history AFTER evaluation
        self.recent_ratios.append(ratio)
        if len(self.recent_ratios) > self.window_size:
            self.recent_ratios.pop(0)

        return self.score

    # =========================================================
    # DECISION
    # =========================================================

    def decide(self):
        if self.command_count < self.min_commands:
            return "ALLOW"

        if self.score >= self.relative_thresh:
            self.consecutive_violations += 1
        else:
            self.consecutive_violations = 0

        if not self.alerted and self.consecutive_violations >= self.persistence_required:
            self.alerted = True
            return "ALERT"

        return "ALLOW"
