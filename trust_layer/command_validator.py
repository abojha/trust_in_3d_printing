import math


class CommandValidator:
    """
    Computes:
    acc_cmd  : command-level (design intent) deviation  [0, 1]
    acc_exec : execution-level (physical / firmware) deviation  [0, 1]
    """

    def __init__(self,
                 extrude_flood_window=3,
                 extrude_de_threshold=5.0,
                 extrude_xy_tol=2.0):
        """
        extrude_flood_window  : consecutive suspicious extrusion commands
                                needed to escalate to a full violation.
        extrude_de_threshold  : min extrusion delta (mm) per suspicious move.
        extrude_xy_tol        : max XY travel (mm) for a move to be
                                considered 'stationary' (extrusion without travel).
        """
        # Relative-E flood counter
        self.extrude_flood_count = 0
        self.extrude_flood_window = extrude_flood_window
        self.extrude_de_threshold = extrude_de_threshold
        self.extrude_xy_tol = extrude_xy_tol
        # Absolute-E flood tracker (needed when E mode is absolute)
        self._last_abs_E = None
        self._abs_E_repeat_count = 0

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------

    def validate(self, analysis, reference, machine_profile, command_index):
        """Returns (acc_cmd, acc_exec) called by SimulationController."""
        acc_exec = self.compute_acc_exec(analysis, machine_profile)
        if reference is None:
            return 0.0, acc_exec
        acc_cmd = self.compute_acc_cmd(analysis, reference)
        return acc_cmd, acc_exec

    # ------------------------------------------------------------------
    # COMMAND-LEVEL ABNORMALITY  (design intent / behavioural reference)
    # ------------------------------------------------------------------

    def compute_acc_cmd(self, analysis, reference):
        """acc_cmd in [0, 1] — max severity among command-level deviations."""
        if analysis["type"] == "comment":
            return 0.0

        cmd = analysis["cmd"]
        effects = analysis["effects"]
        deviations = []

        # 1. Semantic validity for ALL types (incl. control commands)
        #    Universal printer lifecycle commands are always semantically valid
        #    regardless of the per-layer reference (e.g. end-of-print homing,
        #    mode switches, fan/heater off).
        UNIVERSAL_CMDS = {
            "G0", "G1",       # basic motion — always valid
            "G28",            # home axes
            "G90", "G91",     # absolute / relative positioning
            "G92",            # set position (E reset) — value checked in acc_exec
            "M82", "M83",     # absolute / relative extrusion
            "M84", "M18",     # motors off
            "M104", "M109",   # nozzle temperature
            "M106", "M107",   # fan
            "M140", "M190",   # bed temperature
            "M204", "M205",   # acceleration
        }
        allowed_cmds = reference.get("commands_seen", [])
        if cmd in UNIVERSAL_CMDS or cmd in allowed_cmds:
            deviations.append(0.0)
        else:
            deviations.append(1.0)

        # Control commands: only semantic check applies
        if analysis["type"] == "control":
            return max(deviations)

        # 2. Motion-specific deviations
        if analysis["type"] == "motion":
            params = effects.get("params", {})
            motion_ref = reference.get("motion", {})
            speed_ref  = reference.get("speed", {})

            # Bounding box (10 % tolerance or 5 mm minimum)
            bbox = motion_ref.get("bbox_mm")
            # Skip bounding-box check for homing / parking moves (X=0 Y=0)
            # These are standard end-of-print sequences, not attacks.
            is_home_move = (params.get("X") == 0.0 and params.get("Y") == 0.0)
            if bbox is not None and not is_home_move:
                x_min, y_min, x_max, y_max = bbox
                x = params.get("X")
                y = params.get("Y")
                dev_bbox = 0.0
                if x is not None and y is not None:
                    bw = x_max - x_min
                    bh = y_max - y_min
                    xt = max(bw * 0.10, 5.0)
                    yt = max(bh * 0.10, 5.0)
                    dx = max((x_min - xt) - x, 0.0, x - (x_max + xt))
                    dy = max((y_min - yt) - y, 0.0, y - (y_max + yt))
                    if dx > 0 or dy > 0:
                        diag = math.hypot(bw, bh)
                        dev_bbox = math.hypot(dx, dy) / max(diag, 1e-6)
                deviations.append(min(dev_bbox, 1.0))

            # Feedrate (+-50 % tolerance)
            F = params.get("F")
            F_range = speed_ref.get("feedrate_mm_per_min")
            if F is not None and F_range and F_range[0] is not None:
                F_min, F_max = F_range
                F_min_tol = F_min * 0.50
                F_max_tol = F_max * 1.50
                dev_speed = 0.0
                if F < F_min_tol:
                    dev_speed = (F_min_tol - F) / max(F_min_tol, 1e-6)
                elif F > F_max_tol:
                    dev_speed = (F - F_max_tol) / max(F_max_tol, 1e-6)
                deviations.append(min(dev_speed, 1.0))

            # Z-height tolerance
            # Allow Z-hop of up to 2 mm above layer height (standard
            # slicer retraction-hop), plus +-20 % of layer z.
            Z = params.get("Z")
            ref_z = reference.get("z_height_mm")
            if Z is not None and ref_z:
                z_hop_allowance = 2.0          # mm above layer z
                z_tol = max(ref_z * 0.20, 0.1) + z_hop_allowance
                z_diff = abs(Z - ref_z)
                if z_diff > z_tol:
                    deviations.append(min((z_diff - z_tol) / max(ref_z, 1e-6), 1.0))
                else:
                    deviations.append(0.0)

            # Jump magnitude check
            # Compare single-move distance against the layer's total
            # travel budget (path + travel).  Moves within this budget
            # are expected (initial travel from home, repositioning, etc.).
            # Only flag moves that significantly exceed the budget.
            xy_dist = effects.get("xy_dist", 0.0)
            expected_path = motion_ref.get("path_length_mm", 0.0)
            travel_length = motion_ref.get("travel_length_mm", 0.0)
            max_single_move = max(travel_length, expected_path, 50.0)
            if xy_dist > max_single_move:
                deviations.append(
                    min((xy_dist - max_single_move) / max(max_single_move, 1e-6), 1.0))
            else:
                deviations.append(0.0)

        return max(deviations) if deviations else 0.0

    # ------------------------------------------------------------------
    # EXECUTION-LEVEL ABNORMALITY  (physical / firmware constraints)
    # ------------------------------------------------------------------

    def compute_acc_exec(self, analysis, machine_profile):
        """acc_exec in [0, 1] — max severity among execution-level violations."""
        if analysis["type"] == "comment":
            return 0.0

        deviations = []
        effects = analysis["effects"]
        cmd = analysis.get("cmd")

        # ── Firmware manipulation (control / state commands) ──────────
        if cmd in {"M92", "M221"}:
            deviations.append(1.0)

        if cmd == "G92":
            e_reset = effects.get("reset", {}).get("E")
            if e_reset is not None and abs(e_reset) > 50:
                deviations.append(1.0)

        if analysis["type"] == "control":
            return max(deviations) if deviations else 0.0

        # Unpack params depending on command type
        if analysis["type"] == "motion":
            params = effects.get("params", {})
        else:
            params = effects

        # ── 1. Feedrate capability ─────────────────────────────────────
        F = params.get("F")
        if F is not None:
            max_F = machine_profile["motion"]["max_feedrate_mm_per_min"]
            deviations.append(
                min((F - max_F) / max(max_F, 1e-6), 1.0) if F > max_F else 0.0)

        # ── 2. Extrusion checks ────────────────────────────────────────
        xy_dist = effects.get("xy_dist", 0.0)
        de      = effects.get("de",      0.0)

        if de > 0:
            effective_dist = max(xy_dist, 1e-6)
            max_e_per_mm   = machine_profile["extrusion"]["max_extrusion_per_mm"]
            max_e_rate     = machine_profile["extrusion"]["max_e_rate_mm_s"]
            max_ret        = machine_profile["extrusion"]["max_retraction_mm"]

            # Priming / de-priming exemption:
            # Stationary extrusion (xy_dist < 0.1 mm) whose magnitude
            # does not exceed max retraction distance is a normal
            # prime-after-retraction move emitted by every slicer.
            # Skip density AND rate checks for these moves.
            is_priming = (xy_dist < 0.1 and de <= max_ret)

            # 2a. Extrusion density (mm extruded / mm traveled)
            if not is_priming:
                e_per_mm = de / effective_dist
                deviations.append(
                    min((e_per_mm - max_e_per_mm) / max(max_e_per_mm, 1e-6), 1.0)
                    if e_per_mm > max_e_per_mm else 0.0)

            # 2b. Extrusion rate (mm/s)
            if F is not None and not is_priming:
                e_rate = de * (F / 60.0) / effective_dist
                deviations.append(1.0 if e_rate > max_e_rate else 0.0)

            # 2c. Relative-E flood pattern detector
            #     Fires when the SAME large relative-E move is repeated
            #     (useful when printer is in relative-E mode, M83).
            if de >= self.extrude_de_threshold and xy_dist <= self.extrude_xy_tol:
                self.extrude_flood_count += 1
            else:
                self.extrude_flood_count = 0   # non-suspicious move resets

            if self.extrude_flood_count >= self.extrude_flood_window:
                # Sustained flood — keep flagging until streak breaks
                deviations.append(1.0)

        # ── 2d. Absolute-E flood pattern detector ─────────────────────
        # In absolute-E mode (M82, default) "G1 X0.1 Y0.1 E20 F600"
        # injected repeatedly:  first command de=20, all subsequent de=0
        # (position already at E=20).  We detect by comparing the raw
        # E parameter value directly instead of relying on de.
        if analysis["type"] == "motion":
            E_param = params.get("E")
            if E_param is not None:
                is_suspicious = (xy_dist <= self.extrude_xy_tol
                                 and E_param >= self.extrude_de_threshold)
                if is_suspicious:
                    if (self._last_abs_E is not None
                            and E_param == self._last_abs_E):
                        self._abs_E_repeat_count += 1
                    else:
                        self._abs_E_repeat_count = 0
                    self._last_abs_E = E_param

                    if self._abs_E_repeat_count >= self.extrude_flood_window:
                        # Sustained absolute-E flood — full violation
                        deviations.append(1.0)
                else:
                    # Normal travelling move — reset absolute-E tracker
                    self._last_abs_E = E_param
                    self._abs_E_repeat_count = 0

        # ── 3. Retraction abuse ────────────────────────────────────────
        if de < 0:
            max_ret = machine_profile["extrusion"]["max_retraction_mm"]
            if abs(de) > max_ret:
                deviations.append(
                    min((abs(de) - max_ret) / max(max_ret, 1e-6), 1.0))
            else:
                deviations.append(0.0)

        # ── 4. Temperature shock and ceiling ──────────────────────────
        if cmd in ("M104", "M109"):
            target_temp = params.get("S")
            if target_temp is not None:
                max_temp  = machine_profile["temperature"]["max_nozzle_temp_c"]
                max_delta = machine_profile["temperature"]["max_temp_change_per_command"]

                if target_temp == 0:
                    # M104 S0 = heater-off — standard, never penalise
                    deviations.append(0.0)
                else:
                    # Absolute ceiling
                    deviations.append(
                        min((target_temp - max_temp) / max(max_temp, 1e-6), 1.0)
                        if target_temp > max_temp else 0.0)

                    # Thermal jump (only between non-zero temperatures)
                    prev_temp = effects.get("prev_temp")
                    if prev_temp is not None and prev_temp > 0:
                        delta = abs(target_temp - prev_temp)
                        deviations.append(
                            min((delta - max_delta) / max(max_delta, 1e-6), 1.0)
                            if delta > max_delta else 0.0)

        return max(deviations) if deviations else 0.0
