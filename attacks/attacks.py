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
    
class TemperatureShockAttack:
    """
    Abruptly changes nozzle temperature.
    """

    def __init__(self, *, injection_prob=0.1, seed=None):
        self.injection_prob = injection_prob
        if seed is not None:
            random.seed(seed)

    def apply(self, gcode):
        if random.random() > self.injection_prob:
            return gcode, False

        malicious_cmd = random.choice([
            "M104 S300",  # above safe limit
            "M104 S50",   # sudden cooldown
        ])

        return malicious_cmd, True
