# trust_layer/reference_context.py

import json
import re


class ReferenceContext:
    """
    Tracks current layer and provides layer reference.
    """

    LAYER_RE = re.compile(r";\s*LAYER\s*:\s*(\d+)")

    def __init__(self, reference_path):
        with open(reference_path, "r") as f:
            layers = json.load(f)

        self.layer_map = {l["layer_index"]: l for l in layers}
        self.current_layer = "INIT"
        self.command_count = 0

    def observe(self, gcode_line):
        match = self.LAYER_RE.search(gcode_line)
        if match:
            self.current_layer = int(match.group(1))
            self.command_count = 0

    def next_command(self):
        self.command_count += 1

    def get_reference(self):
        if self.current_layer == "INIT":
            return None
        return self.layer_map.get(self.current_layer)
