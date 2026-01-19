# simulation/simulation_controller.py

from digital_twin.dt_manger import DTManager
from physical_machine.pm_manger import PMManager
from logs.logger import SimulationLogger
from trust_layer.trust_layer import TrustLayer
from trust_layer.command_analyzer import CommandAnalyzer
from trust_layer.reference_context import ReferenceContext
from trust_layer.command_validator import CommandValidator
import json


class SimulationController:
    """
    Orchestrates command-wise simulation:
    DT -> Trust -> Physical Machine
    """
    def __init__(self, mapping, cmd_reference, machine_reference, attacks=None):
        """
        mapping: list of dicts
        attacks: dict { dt_id : AttackInstance }
        """
        self.dt_manager = DTManager()
        self.pm_manager = PMManager()
        self.mapping = {}

        self.logger = SimulationLogger()

        # Attack registry (per DT)
        self.attacks = attacks or {}

        # One pipeline per DT
        self.trust_layers = {}
        self.command_analyzers = {}
        self.reference_contexts = {}
        self.command_validators = {}

        self._initialize(mapping, cmd_reference, machine_reference)

    # INITIALIZATION
    def _initialize(self, mapping, cmd_reference, machine_reference):
        for entry in mapping:
            dt_id = entry["dt_id"]
            machine_id = entry["machine_id"]
            gcode_path = entry["gcode_path"]

            # DT & Machine
            attack = self.attacks.get(dt_id)
            self.dt_manager.add_dt(dt_id, gcode_path, attack=attack)



            self.pm_manager.add_machine(machine_id)
            self.mapping[dt_id] = machine_id

            # Trust pipeline
            self.trust_layers[dt_id] = TrustLayer()
            self.command_analyzers[dt_id] = CommandAnalyzer()
            self.reference_contexts[dt_id] = ReferenceContext(cmd_reference)
            self.command_validators[dt_id] = CommandValidator()

            # Per-DT log header
            self.logger.log_header(dt_id)
            with open(machine_reference) as f:
                self.machine_profile = json.load(f)


    # MAIN SIMULATION LOOP
    def run(self):
        active = True

        while active:
            active = False

            for dt in self.dt_manager.get_all():
                if not dt.has_next():
                    continue

                dt_id = dt.dt_id
                machine_id = self.mapping[dt_id]
                machine = self.pm_manager.get(machine_id)

                # DO NOT FETCH COMMANDS IF MACHINE IS PAUSED
                if machine.is_paused():
                    continue

                active = True

                # -----------------------------
                # FETCH COMMAND
                # -----------------------------
                command = dt.get_next_command()
                seq = command["seq"]

                # -----------------------------
                # TRUST PIPELINE
                # -----------------------------
                analyzer = self.command_analyzers[dt_id]
                trust = self.trust_layers[dt_id]
                ref_ctx = self.reference_contexts[dt_id]
                validator = self.command_validators[dt_id]

                original_gcode = command["original_gcode"]
                gcode = command["gcode"]

                ref_ctx.observe(original_gcode)
                analysis = analyzer.analyze(gcode)
                ref_ctx.next_command()
                cmd_reference = ref_ctx.get_reference()

                acc_cmd, acc_exec = validator.validate(
                    analysis,
                    cmd_reference,
                    self.machine_profile,
                    ref_ctx.command_count
                )

                trust_out = trust.update_from_deviation(acc_cmd, acc_exec)

                # LOG
                self.logger.log_command(
                    dt_id=dt_id,
                    machine_id=machine_id,
                    seq=seq,
                    layer=ref_ctx.current_layer,
                    gcode=gcode,
                    acc_cmd=acc_cmd,
                    acc_exec=acc_exec,
                    trust=trust_out["trust"],
                    decision=trust_out["decision"]
                )

                # ENFORCE DECISION
                if trust_out["decision"] == "PAUSE":
                    machine.pause()
                else:
                    machine.execute_command(command)

        # FINISH
        for dt_id, trust in self.trust_layers.items():
            self.logger.log_finish(dt_id, trust.T)

        self.logger.close_all()
