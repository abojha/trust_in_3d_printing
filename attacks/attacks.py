# attacks/command_injection.py

import random
class CommandInjectionAttack:
    """
    Injects an unauthorized G-code command
    with a given probability.
    """
    def __init__(
        self,
        *,
        injection_prob=1,
        injected_commands=None,
        seed=None
    ):
        """
        injection_prob: probability of attack per command
        injected_commands: list of malicious G-code strings
        """
        self.injection_prob = injection_prob

        self.injected_commands = injected_commands or [
            "M221 S200",        # flow rate manipulation
            "G92 E1000",        # extrusion reset
            "M92 E2000",        # steps/mm corruption
        ]

        if seed is not None:
            random.seed(seed)

    def apply(self, gcode):
        """
        Returns:
          (new_gcode, attacked: bool)
        """
        if random.random() > self.injection_prob:
            return gcode, False

        malicious_cmd = random.choice(self.injected_commands)

        # Strategy: replace original command
        return malicious_cmd, True

class ExtrusionFloodAttack:
    """
    Causes excessive extrusion in a single move.
    """

    def __init__(self, *, injection_prob=0.1, seed=None):
        self.injection_prob = injection_prob
        if seed is not None:
            random.seed(seed)

    def apply(self, gcode):
        if random.random() > self.injection_prob:
            return gcode, False

        # Large extrusion over tiny movement
        malicious_cmd = "G1 X0.1 Y0.1 E20 F600"

        return malicious_cmd, True
    
# class TemperatureShockAttack:
#     """
#     Abruptly changes nozzle temperature.
#     """

#     def __init__(self, *, injection_prob=0.1, seed=None):
#         self.injection_prob = injection_prob
#         if seed is not None:
#             random.seed(seed)

#     def apply(self, gcode):
#         if random.random() > self.injection_prob:
#             return gcode, False

#         malicious_cmd = random.choice([
#             "M104 S300",  # above safe limit
#             "M104 S50",   # sudden cooldown
#         ])

#         return malicious_cmd, True


import random

class TemperatureShockAttack:
    """
    Stealthy temperature oscillation attack.

    Stays within hard safety limits to evade
    static and constraint-based baselines,
    but creates repeated abnormal thermal behavior
    detectable via trust accumulation.
    """

    def __init__(
        self,
        *,
        injection_prob=0.3,
        base_temp=210,       # normal PLA temp
        delta=10,            # <= machine delta (15)
        seed=None
    ):
        self.injection_prob = injection_prob
        self.base_temp = base_temp
        self.delta = delta
        self.toggle = False

        if seed is not None:
            random.seed(seed)

    def apply(self, gcode):
        if random.random() > self.injection_prob:
            return gcode, False

        # Alternate temperature up/down
        self.toggle = not self.toggle

        if self.toggle:
            target_temp = self.base_temp + self.delta
        else:
            target_temp = self.base_temp - self.delta

        # Always within safe limits:
        # 200–220°C range, delta = 10°C
        malicious_cmd = f"M104 S{target_temp}"

        return malicious_cmd, True




class SlowExtrusionDriftAttack:
    """
    Gradually increases extrusion over time without
    violating hard limits.
    """

    def __init__(self, *, injection_prob=0.3, drift_factor=1.03, seed=None):
        self.injection_prob = injection_prob
        self.drift_factor = drift_factor
        self.current_multiplier = 1.0

        if seed is not None:
            random.seed(seed)

    def apply(self, gcode):
        if random.random() > self.injection_prob:
            return gcode, False

        # Only modify extrusion moves
        if "E" not in gcode or not gcode.startswith("G1"):
            return gcode, False

        self.current_multiplier *= self.drift_factor

        # naive but effective E scaling
        parts = gcode.split()
        new_parts = []
        for p in parts:
            if p.startswith("E"):
                e_val = float(p[1:])
                new_e = e_val * self.current_multiplier
                new_parts.append(f"E{new_e:.4f}")
            else:
                new_parts.append(p)

        return " ".join(new_parts), True
