# physical_machine/physical_machine.py

class PhysicalMachine:
    """
    Simulated Physical Machine that executes G-code command-wise.
    """

    def __init__(self, machine_id):
        self.machine_id = machine_id
        self.state = "IDLE"      # IDLE | RUNNING | PAUSED | DONE
        self.executed_commands = []
        self.current_seq = -1

    # -----------------------------
    # Execution control
    # -----------------------------
    def pause(self):
        if self.state != "PAUSED":
            print(f"[Machine-{self.machine_id}] ⛔ PAUSED")
        self.state = "PAUSED"

    def resume(self):
        if self.state == "PAUSED":
            print(f"[Machine-{self.machine_id}] ▶ RESUMED")
        self.state = "RUNNING"

    def is_paused(self):
        return self.state == "PAUSED"

    # -----------------------------
    # Command execution
    # -----------------------------
    def execute_command(self, command):
        if command is None:
            return

        if self.state == "PAUSED":
            return   # 🚫 ignore execution

        self.state = "RUNNING"

        self.executed_commands.append({
            "seq": command["seq"],
            "dt_id": command["dt_id"],
            "gcode": command["gcode"]
        })

        self.current_seq = command["seq"]

        print(
            f"[Machine-{self.machine_id}] "
            f"Executed (DT-{command['dt_id']}, seq={command['seq']}): "
            f"{command['gcode']}"
        )

    # -----------------------------
    # Lifecycle
    # -----------------------------
    def finish(self):
        self.state = "DONE"

    def reset(self):
        self.state = "IDLE"
        self.executed_commands.clear()
        self.current_seq = -1

    def __repr__(self):
        return (
            f"PhysicalMachine(id={self.machine_id}, "
            f"state={self.state}, "
            f"executed={len(self.executed_commands)})"
        )
