import math
class CommandValidator:
    """
    Computes:
    acc_cmd  : command-level (design intent) deviation
    acc_exec : execution-level (physical / firmware) deviation
    """

    def validate(self, analysis, reference, machine_profile, command_index):
        """
        Main entry point used by SimulationController.
        """
        if reference is None:
            return 0.0, 0.0

        acc_cmd = self.compute_acc_cmd(analysis, reference)
        acc_exec = self.compute_acc_exec(analysis, machine_profile)

        return acc_cmd, acc_exec

    # COMMAND-LEVEL ABNORMALITY (DESIGN TRUST)
    def compute_acc_cmd(self, analysis, reference):
        """
        acc_cmd ∈ [0, 1]
        MAX severity among all command-level deviations.
        """

        # Ignore comments & control commands
        if analysis["type"] in ("comment", "control"):
            return 0.0

        cmd = analysis["cmd"]
        effects = analysis["effects"]
        deviations = []
        # Command semantic validity
        allowed_cmds = reference.get("commands_seen", [])
        deviations.append(0.0 if cmd in allowed_cmds else 1.0)

        # Motion-based checks
        if analysis["type"] == "motion":
            params = effects.get("params", {})

            # 2. Bounding box deviation
            x_min, y_min, x_max, y_max = reference["motion"]["bbox_mm"]
            x = params.get("X")
            y = params.get("Y")

            dev_bbox = 0.0
            if x is not None and y is not None:
                dx = max(x_min - x, 0.0, x - x_max)
                dy = max(y_min - y, 0.0, y - y_max)
                if dx > 0 or dy > 0:
                    diag = math.hypot(x_max - x_min, y_max - y_min)
                    dev_bbox = math.hypot(dx, dy) / max(diag, 1e-6)

            deviations.append(min(dev_bbox, 1.0))

            # 3. Feedrate deviation (design intent)
            dev_speed = 0.0
            F = params.get("F")
            if F is not None:
                F_min, F_max = reference["speed"]["feedrate_mm_per_min"]
                if F < F_min:
                    dev_speed = (F_min - F) / max(F_min, 1e-6)
                elif F > F_max:
                    dev_speed = (F - F_max) / max(F_max, 1e-6)

            deviations.append(min(dev_speed, 1.0))

            # 4. Z-height integrity
            dev_z = 0.0
            Z = params.get("Z")
            if Z is not None:
                ref_z = reference["z_height_mm"]
                dev_z = abs(Z - ref_z) / max(ref_z, 1e-6)

            deviations.append(min(dev_z, 1.0))

            # 5. Single-command jump magnitude
            xy_dist = effects.get("xy_dist", 0.0)
            expected_path = reference["motion"]["path_length_mm"]
            dev_jump = xy_dist / max(expected_path, 1e-6)
            deviations.append(min(dev_jump, 1.0))

        return max(deviations)

    # EXECUTION-LEVEL ABNORMALITY (PHYSICAL TRUST)
    def compute_acc_exec(self, analysis, machine_profile):
        """
        acc_exec ∈ [0, 1]

        Measures whether the command violates
        physical / firmware constraints of the machine.
        """

        # Ignore comments & non-executable commands
        if analysis["type"] in ("comment", "control"):
            return 0.0

        deviations = []
        effects = analysis["effects"]
        params = effects.get("params", {})

        # 1. Feedrate capability violation (mm/min)
        F = params.get("F")
        if F is not None:
            max_F = machine_profile["motion"]["max_feedrate_mm_per_min"]
            if F > max_F:
                dev_F = (F - max_F) / max(max_F, 1e-6)
                deviations.append(min(dev_F, 1.0))
            else:
                deviations.append(0.0)

        # 2. Extrusion flooding & extrusion rate
        xy_dist = effects.get("xy_dist", 0.0)
        de = effects.get("de", 0.0)

        if de > 0:
            effective_dist = max(xy_dist, 1e-6)

            # Extrusion per mm (pressure / clog risk)
            e_per_mm = de / effective_dist
            max_e_per_mm = machine_profile["extrusion"]["max_extrusion_per_mm"]

            if e_per_mm > max_e_per_mm:
                dev_e = (e_per_mm - max_e_per_mm) / max(max_e_per_mm, 1e-6)
                deviations.append(min(dev_e, 1.0))
            else:
                deviations.append(0.0)

            # Extrusion rate (mm/s)
            if F is not None:
                e_rate = de * (F / 60.0) / effective_dist
                max_e_rate = machine_profile["extrusion"]["max_e_rate_mm_s"]

                if e_rate > max_e_rate:
                    deviations.append(1.0)
                else:
                    deviations.append(0.0)

        # 3. Retraction abuse
        if de < 0:
            max_ret = machine_profile["extrusion"]["max_retraction_mm"]
            if abs(de) > max_ret:
                dev_ret = (abs(de) - max_ret) / max(max_ret, 1e-6)
                deviations.append(min(dev_ret, 1.0))
            else:
                deviations.append(0.0)

        # 4. Temperature shock & ceiling
        if analysis["cmd"] in ("M104", "M109"):
            target_temp = params.get("S")
            if target_temp is not None:
                max_temp = machine_profile["temperature"]["max_nozzle_temp_c"]
                max_delta = machine_profile["temperature"]["max_temp_change_per_command"]

                # Absolute ceiling
                if target_temp > max_temp:
                    dev_temp = (target_temp - max_temp) / max(max_temp, 1e-6)
                    deviations.append(min(dev_temp, 1.0))
                else:
                    deviations.append(0.0)

                # Thermal jump
                prev_temp = effects.get("prev_temp")
                if prev_temp is not None:
                    delta = abs(target_temp - prev_temp)
                    if delta > max_delta:
                        dev_jump = (delta - max_delta) / max(max_delta, 1e-6)
                        deviations.append(min(dev_jump, 1.0))
                    else:
                        deviations.append(0.0)

        if not deviations:
            return 0.0

        return max(deviations)
