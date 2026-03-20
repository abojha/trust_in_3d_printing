# baselines/constraint_safety/constraint_monitor.py

from baselines.CBSM.dangerous_gcode import DANGEROUS_COMMANDS


class ConstraintSafetyMonitor:
    """
    Constraint-Based Safety Monitor (CBSM).

    Intentionally weak, static, rule-based safety baseline.
    Enforces only absolute, single-command safety violations.

    Does NOT reason about:
    - history
    - accumulation
    - design intent
    - semantic behavior
    """

    def __init__(
        self,
        max_extrusion_per_cmd=50.0,   # extremely loose
        max_temperature=280           # hard firmware ceiling
    ):
        self.max_extrusion_per_cmd = max_extrusion_per_cmd
        self.max_temperature = max_temperature

    def check(self, analysis):
        cmd = analysis.get("cmd")
        effects = analysis.get("effects", {})

        # ------------------------------------------------
        # 1. Hard-blacklisted firmware commands
        # ------------------------------------------------
        if cmd in DANGEROUS_COMMANDS:
            return "BLOCK"

        # ------------------------------------------------
        # 2. G92 coordinate reset with suspicious E value
        #    (legitimate resets use small values like E0)
        # ------------------------------------------------
        if cmd == "G92":
            reset_params = effects.get("reset", {})
            e_reset = reset_params.get("E")
            if e_reset is not None and e_reset > 10.0:
                return "BLOCK"

        # ------------------------------------------------
        # 3. Absolute temperature ceiling ONLY
        # ------------------------------------------------
        if cmd in ("M104", "M109"):
            temperature = effects.get("S")
            if temperature is not None and temperature > self.max_temperature:
                return "BLOCK"
            return "ALLOW"

        # ------------------------------------------------
        # 4. Gross extrusion flooding (single command)
        # ------------------------------------------------
        de = effects.get("de", 0.0)
        if de > self.max_extrusion_per_cmd:
            return "BLOCK"

        # ------------------------------------------------
        # DEFAULT: ALLOW
        # ------------------------------------------------
        return "ALLOW"
