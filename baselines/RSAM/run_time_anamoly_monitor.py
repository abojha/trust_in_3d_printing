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

        # Track temperature changes for anomaly detection
        self.recent_temps = []
        self.last_temp = None

    # =========================================================
    # UPDATE
    # =========================================================

    def update(self, analysis):
        self.command_count += 1
        deviation = 0.0

        effects = analysis.get("effects", {})
        cmd = analysis.get("cmd")

        # ----- Temperature anomaly detection -----
        if cmd in ("M104", "M109"):
            temp = effects.get("S")
            if temp is not None and temp > 0:
                # Ignore M104 S0 (standard heater-off/shutdown)
                if self.last_temp is not None and self.last_temp > 0:
                    temp_delta = abs(temp - self.last_temp)
                    self.recent_temps.append(temp_delta)
                    if len(self.recent_temps) > self.window_size:
                        self.recent_temps.pop(0)

                    # Frequent temperature changes are anomalous
                    if len(self.recent_temps) >= 3:
                        mean_delta = sum(self.recent_temps) / len(self.recent_temps)
                        if mean_delta > 5.0:  # repeated temp swings > 5°C
                            deviation = mean_delta / 10.0

                self.last_temp = temp

        # ----- Extrusion anomaly detection -----
        de = effects.get("de", 0.0)
        xy_dist = effects.get("xy_dist", 0.0)

        # Ignore retractions and near-zero motion
        if de > 0 and xy_dist >= 0.01:
            ratio = de / xy_dist  # normalized extrusion density

            if len(self.recent_ratios) >= self.window_size:
                mean_ratio = sum(self.recent_ratios) / len(self.recent_ratios)

                if mean_ratio > 0 and ratio > self.relative_thresh * mean_ratio:
                    extrusion_dev = (ratio - mean_ratio) / mean_ratio
                    deviation = max(deviation, extrusion_dev)

            # Update history AFTER evaluation
            self.recent_ratios.append(ratio)
            if len(self.recent_ratios) > self.window_size:
                self.recent_ratios.pop(0)

        # EWMA accumulation
        self.score = self.alpha * self.score + deviation

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
