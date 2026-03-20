# simulation/simulation_controller.py

from digital_twin.dt_manger import DTManager
from physical_machine.pm_manger import PMManager
from logs.logger import SimulationLogger
from trust_layer.trust_layer import TrustLayer
from trust_layer.command_analyzer import CommandAnalyzer
from trust_layer.reference_context import ReferenceContext
from trust_layer.command_validator import CommandValidator
from baselines.CBSM.constraint_monitor import ConstraintSafetyMonitor
from baselines.RSAM.run_time_anamoly_monitor import RuntimeAnomalyMonitor

import json


class SimulationController:
    """
    Orchestrates command-wise simulation:
    DT -> Trust -> Physical Machine

    IMPORTANT (Evaluation Mode):
    - Machine never pauses
    - Each method stops LOGGING when it detects an attack
    - Detection time = last logged command index
    """

    def __init__(self, mapping, cmd_reference, machine_reference, attacks=None, output_dir="results/default"):
        self.dt_manager = DTManager()
        self.pm_manager = PMManager()
        self.mapping = {}

        self.logger = SimulationLogger(base_dir=output_dir)
 
        # Attack registry (per DT)
        self.attacks = attacks or {}

        # Trust pipeline (per DT)
        self.trust_layers = {}
        self.command_analyzers = {}
        self.reference_contexts = {}
        self.command_validators = {}


        # Logging active flags (per DT, per method)
        # These flags track whether each method has ALREADY detected.
        # We continue logging AFTER detection so plots show full trajectories.
        self.trust_detected = {}
        self.static_detected = {}

        self.static_detectors = {}

        self.ieee_detectors = {}
        self.ieee_detected = {}


        self._initialize(mapping, cmd_reference, machine_reference)

    # =========================================================
    # INITIALIZATION
    # =========================================================

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


            # Logging state — not yet detected
            self.trust_detected[dt_id] = False

            # Log header
            self.logger.log_header(dt_id)

            self.static_detectors[dt_id] = ConstraintSafetyMonitor()
            self.static_detected[dt_id] = False


            self.ieee_detectors[dt_id] = RuntimeAnomalyMonitor()
            self.ieee_detected[dt_id] = False



            # Machine profile (shared)
            with open(machine_reference) as f:
                self.machine_profile = json.load(f)

    # =========================================================
    # MAIN SIMULATION LOOP
    # =========================================================

    def run(self):
        active = True

        while active:
            active = False

            for dt in self.dt_manager.get_all():
                if not dt.has_next():
                    continue

                active = True

                dt_id = dt.dt_id
                machine_id = self.mapping[dt_id]
                machine = self.pm_manager.get(machine_id)

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

                ## static detector
                static_detector = self.static_detectors[dt_id]
                static_decision = static_detector.check(analysis)


                # ================================
                # IEEE BASELINE (runtime anomaly)
                # ================================
                ieee_detector = self.ieee_detectors[dt_id]

                ieee_score = ieee_detector.update(analysis)
                ieee_decision = ieee_detector.decide()




                # -----------------------------
                # LOGGING CONTROL
                # Always log every command so plots show full trajectories.
                # The 'decision' column marks PAUSE/BLOCK/ALERT.
                # first_decision_index() in plot.py finds the first such row.
                # -----------------------------

                # Trust logging — always log; decision column carries PAUSE
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

                # CBSM baseline — always log
                self.logger.log_cbsm_baseline(
                    dt_id=dt_id,
                    seq=seq,
                    analysis=analysis,
                    decision=static_decision
                )

                # RSAM baseline — always log
                self.logger.log_rsam_baseline(
                    dt_id=dt_id,
                    seq=seq,
                    score=ieee_score,
                    decision=ieee_decision
                )



                # -----------------------------
                # ALWAYS EXECUTE (NO REAL PAUSE)
                # -----------------------------
                machine.execute_command(command)

        # =====================================================
        # FINISH
        # =====================================================
        for dt_id, trust in self.trust_layers.items():
            self.logger.log_finish(dt_id, trust.T)

        self.logger.close_all()
