# logs/logger.py

from pathlib import Path
from datetime import datetime


class SimulationLogger:
    """
    One log file per DT (human-readable narration)
    + CSV logs for quantitative analysis and plotting.
    """

    def __init__(self, log_dir="logs", result_dir="results"):
        # ---------- TEXT LOGS ----------
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._files = {}  # dt_id -> .log file handle

        # ---------- CSV RESULTS ----------
        self.result_dir = Path(result_dir)
        self.result_dir.mkdir(parents=True, exist_ok=True)
        self._csv_files = {}  # (category, dt_id) -> csv file handle

    # =========================================================
    # INTERNAL HELPERS
    # =========================================================

    def _get_file(self, dt_id):
        if dt_id not in self._files:
            path = self.log_dir / f"dt_{dt_id}.log"
            self._files[dt_id] = open(path, "w", encoding="utf-8")
        return self._files[dt_id]

    def _get_csv(self, category, dt_id, header):
        key = (category, dt_id)

        if key not in self._csv_files:
            category_dir = self.result_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            path = category_dir / f"dt_{dt_id}.csv"
            f = open(path, "w", encoding="utf-8")
            f.write(header + "\n")
            self._csv_files[key] = f

        return self._csv_files[key]

    # =========================================================
    # TEXT LOGGING (HUMAN READABLE)
    # =========================================================

    def log_header(self, dt_id):
        f = self._get_file(dt_id)
        f.write("=" * 60 + "\n")
        f.write(f"DT-{dt_id} SIMULATION LOG\n")
        f.write(f"START TIME: {datetime.now()}\n")
        f.write("=" * 60 + "\n\n")
        f.flush()

    def log_command(
        self,
        *,
        dt_id,
        machine_id,
        seq,
        layer,
        gcode,
        acc_cmd,
        acc_exec,
        trust,
        decision="ALLOW"
    ):
        f = self._get_file(dt_id)

        f.write(f"[SEQ {seq}] [LAYER {layer}]\n")
        f.write(f"CMD      : {gcode}\n")
        f.write(
            f"TRUST    : acc_cmd={acc_cmd:.3f} | "
            f"acc_exec={acc_exec:.3f} | trust={trust:.3f}\n"
        )
        f.write(f"DECISION : {decision}\n")
        f.write(f"MACHINE  : Machine-{machine_id}\n")
        f.write("-" * 60 + "\n")
        f.flush()

        # ---------- CSV (TRUST) ----------
        self.log_trust_csv(
            dt_id=dt_id,
            seq=seq,
            acc_cmd=acc_cmd,
            acc_exec=acc_exec,
            trust=trust,
            decision=decision
        )

    def log_finish(self, dt_id, final_trust):
        f = self._get_file(dt_id)
        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write(f"DT-{dt_id} FINISHED\n")
        f.write(f"FINAL TRUST: {final_trust:.3f}\n")
        f.write(f"END TIME  : {datetime.now()}\n")
        f.write("=" * 60 + "\n")
        f.flush()

    # =========================================================
    # BASELINE LOGGING (CORRECTED)
    # =========================================================

    def log_static_baseline(self, *, dt_id, seq, analysis, decision):
        """
        Logs the exact command evaluated by the static baseline.
        This avoids misattribution when attacks inject commands.
        """
        f = self._get_file(dt_id)

        cmd = analysis.get("cmd")
        effects = analysis.get("effects", {})

        f.write(f"[SEQ {seq}] [STATIC-BASELINE]\n")
        f.write(f"CMD      : {cmd} | effects={effects}\n")
        f.write(f"DECISION : {decision}\n")
        f.write("-" * 60 + "\n")
        f.flush()

        # ---------- CSV ----------
        self.log_static_baseline_csv(
            dt_id=dt_id,
            seq=seq,
            decision=decision
        )

    def log_ieee_baseline(self, *, dt_id, seq, score, decision):
        f = self._get_file(dt_id)

        f.write(f"[SEQ {seq}] [IEEE-BASELINE]\n")
        f.write(f"SCORE    : anomaly_score={score:.3f}\n")
        f.write(f"DECISION : {decision}\n")
        f.write("-" * 60 + "\n")
        f.flush()

        # ---------- CSV ----------
        csv = self._get_csv(
            category="ieee_baseline",
            dt_id=dt_id,
            header="seq,anomaly_score,decision"
        )
        csv.write(f"{seq},{score:.6f},{decision}\n")
        csv.flush()

    # =========================================================
    # CSV LOGGING (UNCHANGED FORMAT)
    # =========================================================

    def log_trust_csv(self, *, dt_id, seq, acc_cmd, acc_exec, trust, decision):
        f = self._get_csv(
            category="trust",
            dt_id=dt_id,
            header="seq,acc_cmd,acc_exec,trust,decision"
        )
        f.write(
            f"{seq},"
            f"{acc_cmd:.6f},"
            f"{acc_exec:.6f},"
            f"{trust:.6f},"
            f"{decision}\n"
        )
        f.flush()

    def log_static_baseline_csv(self, *, dt_id, seq, decision):
        f = self._get_csv(
            category="static_baseline",
            dt_id=dt_id,
            header="seq,decision"
        )
        f.write(f"{seq},{decision}\n")
        f.flush()

    # =========================================================
    # CLEANUP
    # =========================================================

    def close_all(self):
        for f in self._files.values():
            f.close()
        for f in self._csv_files.values():
            f.close()
