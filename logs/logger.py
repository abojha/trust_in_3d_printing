# logs/logger.py

from pathlib import Path
from datetime import datetime


class SimulationLogger:
    """
    One log file per DT.
    Each file narrates the complete DT → Trust → Machine story.
    """

    def __init__(self, log_dir="logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._files = {}  # dt_id -> file handle

    def _get_file(self, dt_id):
        if dt_id not in self._files:
            path = self.log_dir / f"dt_{dt_id}.log"
            self._files[dt_id] = open(path, "w", encoding="utf-8")
        return self._files[dt_id]

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
        f.write(f"TRUST    : acc_cmd={acc_cmd:.3f} | acc_exec={acc_exec:.3f} | trust={trust:.3f}\n")
        f.write(f"DECISION : {decision}\n")
        f.write(f"MACHINE  : Machine-{machine_id}\n")
        f.write("-" * 60 + "\n")

        f.flush()

    def log_finish(self, dt_id, final_trust):
        f = self._get_file(dt_id)
        f.write("\n")
        f.write("=" * 60 + "\n")
        f.write(f"DT-{dt_id} FINISHED\n")
        f.write(f"FINAL TRUST: {final_trust:.3f}\n")
        f.write(f"END TIME  : {datetime.now()}\n")
        f.write("=" * 60 + "\n")
        f.flush()

    def close_all(self):
        for f in self._files.values():
            f.close()
