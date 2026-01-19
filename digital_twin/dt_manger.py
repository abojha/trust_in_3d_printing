# digital_twin/dt_manager.py

from digital_twin.digital_twin import DigitalTwin


# digital_twin/dt_manager.py



class DTManager:
    def __init__(self):
        self.dts = {}

    def add_dt(self, dt_id, gcode_path, attack=None):
        commands = self._load_gcode(gcode_path)
        self.dts[dt_id] = DigitalTwin(
            dt_id=dt_id,
            gcode_commands=commands,
            attack=attack
        )

    def get_all(self):
        return self.dts.values()

    def _load_gcode(self, path):
        commands = []
        with open(path) as f:
            for i, line in enumerate(f):
                commands.append({
                    "seq": i,
                    "gcode": line.strip()
                })
        return commands

