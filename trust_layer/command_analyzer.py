# trust_layer/command_analyzer.py

import math
import re

PARAM_RE = re.compile(r'([A-Z])(-?\d+\.?\d*)')


class CommandAnalyzer:
    """
    Classifies G-code commands and extracts physical/state effects.
    """
    def __init__(self):
        self.pos = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}
        self.xyz_mode = "absolute"   # G90 / G91
        self.e_mode = "absolute"     # M82 / M83
        self.nozzle_temp = None      # track last nozzle temperature

    def analyze(self, gcode_line: str):
        line = gcode_line.strip()

        # ----------------------------
        # Comment
        # ----------------------------
        if not line or line.startswith(";"):
            return {
                "type": "comment",
                "cmd": None,
                "effects": {}
            }

        tokens = line.split()
        cmd = tokens[0]
        params = dict(PARAM_RE.findall(line))
        params = {k: float(v) for k, v in params.items()}

        # ----------------------------
        # Control commands
        # ----------------------------
        if cmd == "G90":
            self.xyz_mode = "absolute"
            return {"type": "control", "cmd": cmd, "effects": {"xyz_mode": "absolute"}}

        if cmd == "G91":
            self.xyz_mode = "relative"
            return {"type": "control", "cmd": cmd, "effects": {"xyz_mode": "relative"}}

        if cmd == "M82":
            self.e_mode = "absolute"
            return {"type": "control", "cmd": cmd, "effects": {"e_mode": "absolute"}}

        if cmd == "M83":
            self.e_mode = "relative"
            return {"type": "control", "cmd": cmd, "effects": {"e_mode": "relative"}}

        if cmd == "G92":
            for k in params:
                if k in self.pos:
                    self.pos[k] = params[k]
            return {"type": "control", "cmd": cmd, "effects": {"reset": params}}

        # Motion commands
        if cmd in ("G0", "G1"):
            prev = self.pos.copy()
            curr = self.pos.copy()

            # XYZ
            for axis in ("X", "Y", "Z"):
                if axis in params:
                    if self.xyz_mode == "absolute":
                        curr[axis] = params[axis]
                    else:
                        curr[axis] += params[axis]

            # Extrusion
            if "E" in params:
                if self.e_mode == "absolute":
                    curr["E"] = params["E"]
                else:
                    curr["E"] += params["E"]

            dx = curr["X"] - prev["X"]
            dy = curr["Y"] - prev["Y"]
            dz = curr["Z"] - prev["Z"]
            de = curr["E"] - prev["E"]

            xy_dist = math.sqrt(dx * dx + dy * dy)

            self.pos = curr

            return {
                "type": "motion",
                "cmd": cmd,
                "effects": {
                    "dx": dx,
                    "dy": dy,
                    "dz": dz,
                    "de": de,
                    "xy_dist": xy_dist,
                    "params": params
                }
            }

        # State / process commands
        if cmd.startswith("M"):
            effects = params.copy()

            # Track nozzle temperature for M104/M109
            if cmd in ("M104", "M109") and "S" in params:
                effects["prev_temp"] = self.nozzle_temp
                self.nozzle_temp = params["S"]

            return {
                "type": "state",
                "cmd": cmd,
                "effects": effects
            }


        return {
            "type": "unknown",
            "cmd": cmd,
            "effects": params
        }
