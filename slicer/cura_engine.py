import argparse
import subprocess
import json
import math
import re
from pathlib import Path
from collections import defaultdict

# =========================
# CONFIG
# =========================

CURA_ENGINE = r"C:\Program Files\UltiMaker Cura 5.11.0\CuraEngine.exe"
CURA_RESOURCES = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources"

PRINTER_DEF = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources\definitions\ultimaker_s5.def.json"
EXTRUDER_LEFT = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources\extruders\ultimaker_s5_extruder_left.def.json"
EXTRUDER_RIGHT = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources\extruders\ultimaker_s5_extruder_right.def.json"

PARAM_RE = re.compile(r'([XYZEF])(-?\d+\.?\d*)')

# UTILS
def dist_xy(p1, p2):
    return math.hypot(p2["X"] - p1["X"], p2["Y"] - p1["Y"])

# GCODE → LAYERS (COMMENT-BASED)
def parse_gcode_layers(lines):
    layers = defaultdict(list)

    state = {
        "xyz_mode": "absolute",   # G90 / G91
        "e_mode": "absolute",     # M82 / M83
        "pos": {"X": 0.0, "Y": 0.0, "Z": None, "E": 0.0},
    }

    current_layer = None
    current_layer_z = None
    current_type = "UNKNOWN"

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        # -------- LAYER MARKER (KEY POINT) --------
        if line.startswith(";LAYER:"):
            current_layer = int(line.split(":")[1])
            current_layer_z = None
            current_type = "UNKNOWN"
            continue

        # Ignore everything before first layer
        if current_layer is None:
            continue

        # -------- TYPE MARKER --------
        if line.startswith(";TYPE:"):
            current_type = line.split(":", 1)[1]
            continue

        # Ignore other comments
        if line.startswith(";"):
            continue

        cmd = line.split()[0]
        params = dict(PARAM_RE.findall(line))
        params = {k: float(v) for k, v in params.items()}

        # -------- MODES --------
        if cmd == "G90":
            state["xyz_mode"] = "absolute"
            continue
        if cmd == "G91":
            state["xyz_mode"] = "relative"
            continue
        if cmd == "M82":
            state["e_mode"] = "absolute"
            continue
        if cmd == "M83":
            state["e_mode"] = "relative"
            continue

        # -------- RESET --------
        if cmd == "G92":
            for k in params:
                state["pos"][k] = params[k]
            continue

        # -------- NON-MOTION --------
        if cmd not in ("G0", "G1"):
            layers[current_layer].append({
                "cmd": cmd,
                "type": current_type
            })
            continue

        prev = state["pos"].copy()
        new = state["pos"].copy()

        # XYZ update
        for axis in ("X", "Y", "Z"):
            if axis in params:
                if state["xyz_mode"] == "absolute":
                    new[axis] = params[axis]
                else:
                    new[axis] += params[axis]

        if "Z" in params:
            current_layer_z = new["Z"]

        # Extrusion update
        if "E" in params:
            if state["e_mode"] == "absolute":
                new["E"] = params["E"]
            else:
                new["E"] += params["E"]

        layers[current_layer].append({
            "cmd": cmd,
            "prev": prev,
            "curr": new,
            "params": params,
            "z": current_layer_z,
            "type": current_type
        })

        state["pos"] = new

    return layers


# LAYER ANALYSIS
def analyze_layer(moves):
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    path_len = 0.0
    travel_len = 0.0
    extrusion = 0.0

    feedrates = set()
    commands = set()

    for m in moves:
        cmd = m.get("cmd")
        commands.add(cmd)

        if cmd not in ("G0", "G1"):
            continue

        prev = m["prev"]
        curr = m["curr"]

        dx = curr["X"] - prev["X"]
        dy = curr["Y"] - prev["Y"]
        dxy = math.hypot(dx, dy)
        de = curr["E"] - prev["E"]

        if dxy > 0:
            if de > 0:
                path_len += dxy
                extrusion += de
            else:
                travel_len += dxy

            min_x = min(min_x, curr["X"])
            min_y = min(min_y, curr["Y"])
            max_x = max(max_x, curr["X"])
            max_y = max(max_y, curr["Y"])

        if "F" in m["params"]:
            feedrates.add(m["params"]["F"])

    bbox = None
    if min_x != float("inf"):
        bbox = [
            round(min_x, 3),
            round(min_y, 3),
            round(max_x, 3),
            round(max_y, 3)
        ]

    return {
        "bbox_mm": bbox,
        "path_length_mm": round(path_len, 3),
        "travel_length_mm": round(travel_len, 3),
        "extrusion_mm": round(extrusion, 3),
        "feedrate_range": [
            min(feedrates) if feedrates else None,
            max(feedrates) if feedrates else None
        ],
        "commands": sorted(commands)
    }

# TRUST REFERENCE
def generate_trust_reference(gcode_path):
    with open(gcode_path) as f:
        lines = f.readlines()

    layers = parse_gcode_layers(lines)
    trust = []

    for layer_idx in sorted(layers.keys()):
        info = analyze_layer(layers[layer_idx])

        z_height = next(
            (m["z"] for m in layers[layer_idx] if m.get("z") is not None),
            0.0
        )

        trust.append({
            "layer_index": layer_idx,
            "z_height_mm": round(z_height, 3),
            "motion": {
                "bbox_mm": info["bbox_mm"],
                "path_length_mm": info["path_length_mm"],
                "travel_length_mm": info["travel_length_mm"]
            },
            "extrusion": {
                "material_mm": info["extrusion_mm"]
            },
            "speed": {
                "feedrate_mm_per_min": info["feedrate_range"]
            },
            "commands_seen": info["commands"],
            "tolerances": {
                "path_length_mm": max(5, info["path_length_mm"] * 0.05),
                "extrusion_mm": max(0.5, info["extrusion_mm"] * 0.1)
            }
        })

    return trust

# CURA ENGINE 
def run_cura_engine(stl_path, gcode_path):
    cmd = [
        CURA_ENGINE, "slice",
        "-d", CURA_RESOURCES,
        "-j", PRINTER_DEF,
        "-j", EXTRUDER_LEFT,
        "-j", EXTRUDER_RIGHT,
        "-s", "layer_height=0.2",
        "-s", "infill_line_distance=6",
        "-s", "top_layers=4",
        "-s", "bottom_layers=4",
        "-s", "initial_bottom_layers=4",
        "-s", "roofing_layer_count=0",
        "-s", "flooring_layer_count=0",
        "-s", "support_enable=false",
        "-s", "ironing_enabled=false",
        "-l", str(stl_path),
        "-o", str(gcode_path)
    ]
    subprocess.run(cmd, check=True)

def generate_experiment_config(stl_files, output_path):
    experiments = []
    print(stl_files)

    for stl_file in stl_files:
        name = stl_file.stem

        experiments.append({
            "name": f"{name}_experiment",
            "gcode_path": f"references/g_code/{name}.gcode",
            "reference_path": f"references/behavioral_references/{name}_br.json",
            "machine_reference": "references/physical_references/physical_references.json",
            "result_dir" : "results/f{name}_experiment",
            "num_dts": 4,
            "attacks": {
                "2": "command_injection",
                "3": "temperature_shock",
                "4": "extrusion_flood"
            },
        })

    config = {
        "probability_sweep": [0.0, 0.1, 0.25, 0.5, 0.75, 1.0],
        "seeds": [42],
        "experiments": experiments
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n📄 Config generated: {output_path}")


# MAIN
def main():
    base_path = Path("references")

    stl_folder = base_path / "stl"
    gcode_folder = base_path / "g_code"
    ref_folder = base_path / "behavioral_references"

    # Create folders if not exist
    gcode_folder.mkdir(parents=True, exist_ok=True)
    ref_folder.mkdir(parents=True, exist_ok=True)

    stl_files = list(stl_folder.glob("*.stl"))

    if not stl_files:
        print("No STL files found in references/stl/")
        return

    print(f"🔍 Found {len(stl_files)} STL files")

    for stl_file in stl_files:
        name = stl_file.stem

        gcode_path = gcode_folder / f"{name}.gcode"
        trust_path = ref_folder / f"{name}_br.json"

        print(f"\n🚀 Processing: {name}")

        # =========================
        # STEP 1: STL → GCODE
        # =========================
        try:
            print("  ▶ Generating G-code...")
            run_cura_engine(stl_file, gcode_path)
        except Exception as e:
            print(f"  ❌ Cura failed for {name}: {e}")
            continue

        # =========================
        # STEP 2: GCODE → TRUST REF
        # =========================
        try:
            print("  ▶ Generating behavioral reference...")
            trust = generate_trust_reference(gcode_path)

            with open(trust_path, "w") as f:
                json.dump(trust, f, indent=2)

        except Exception as e:
            print(f"  ❌ Reference generation failed for {name}: {e}")
            continue

        print(f"  ✅ Done: {name}")


    generate_experiment_config(
    stl_files,
    Path("experiments") / "experiments_config.json"
    )


    print("\n🎯 ALL FILES PROCESSED SUCCESSFULLY")


if __name__ == "__main__":
    main()
