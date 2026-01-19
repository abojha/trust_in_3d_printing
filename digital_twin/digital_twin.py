# digital_twin/dt.py

class DigitalTwin:
    def __init__(self, dt_id, gcode_commands, attack=None):
        self.dt_id = dt_id
        self.commands = gcode_commands
        self.pointer = 0

        # 🔥 attack assigned ONLY to this DT
        self.attack = attack

    def has_next(self):
        return self.pointer < len(self.commands)

    def get_next_command(self):
        cmd = self.commands[self.pointer]
        self.pointer += 1

        original_gcode = cmd["gcode"]

        attacked = False
        attacked_gcode = original_gcode

        if self.attack is not None:
            attacked_gcode, attacked = self.attack.apply(original_gcode)

        return {
            "dt_id": self.dt_id,
            "seq": cmd["seq"],
            "gcode": attacked_gcode,          # what machine sees
            "original_gcode": original_gcode, # what reference sees
            "attacked": attacked
        }

