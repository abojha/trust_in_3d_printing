import argparse
import subprocess
import json
import math
import re
from pathlib import Path
from collections import defaultdict

# =========================
# CONFIG (CHANGE IF NEEDED)
# =========================

CURA_ENGINE = r"C:\Program Files\UltiMaker Cura 5.11.0\CuraEngine.exe"
CURA_RESOURCES = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources"

PRINTER_DEF = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources\definitions\ultimaker_s5.def.json"
EXTRUDER_LEFT = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources\extruders\ultimaker_s5_extruder_left.def.json"
EXTRUDER_RIGHT = r"C:\Program Files\UltiMaker Cura 5.11.0\share\cura\resources\extruders\ultimaker_s5_extruder_right.def.json"

# =========================
# GCODE PARSING REGEX
# =========================

MOVE_RE = re.compile(r'^G1\s+(.*)')
PARAM_RE = re.compile(r'([XYZEF])(-?\d+\.?\d*)')

# =========================
# UTILS
# =========================

def dist(p1, p2):
    return math.sqrt(
        (p2["X"] - p1["X"]) ** 2 +
        (p2["Y"] - p1["Y"]) ** 2
    )

# =========================
# GCODE → LAYERS
# =========================

def parse_layers(gcode_lines):
    layers = defaultdict(list)
    current_z = None

    last_pos = {"X": 0.0, "Y": 0.0, "Z": 0.0, "E": 0.0}

    for line in gcode_lines:
        line = line.strip()
        if not line or line.startswith(";"):
            continue

        # ✅ Accept both G0 and G1
        if not (line.startswith("G0") or line.startswith("G1")):
            continue

        params = dict(PARAM_RE.findall(line))
        params = {k: float(v) for k, v in params.items()}

        # ✅ Z often appears in G0
        if "Z" in params:
            current_z = params["Z"]

        # Skip until first Z is known
        if current_z is None:
            continue

        layers[current_z].append((last_pos.copy(), params, line))

        for k in params:
            last_pos[k] = params[k]

    return layers

# =========================
# LAYER ANALYSIS
# =========================

def analyze_layer(moves):
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")

    total_path = 0.0
    total_extrusion = 0.0
    feedrates = set()
    commands = set()

    for prev, curr, raw in moves:
        commands.add(raw.split()[0])

        if "X" in curr and "Y" in curr:
            min_x = min(min_x, curr["X"])
            min_y = min(min_y, curr["Y"])
            max_x = max(max_x, curr["X"])
            max_y = max(max_y, curr["Y"])
            total_path += dist(prev, curr)

        if "E" in curr:
            delta_e = curr["E"] - prev.get("E", 0.0)
            if delta_e > 0:
                total_extrusion += delta_e

        if "F" in curr:
            feedrates.add(curr["F"])

    return {
        "bbox": [round(min_x, 3), round(min_y, 3),
                 round(max_x, 3), round(max_y, 3)],
        "path_length": round(total_path, 3),
        "extrusion": round(total_extrusion, 3),
        "feedrate": [
            min(feedrates) if feedrates else None,
            max(feedrates) if feedrates else None
        ],
        "commands": sorted(commands)
    }

# =========================
# TRUST REFERENCE GENERATOR
# =========================

def generate_trust_reference(gcode_path):
    with open(gcode_path, "r") as f:
        lines = f.readlines()

    layers = parse_layers(lines)
    trust = []

    for idx, z in enumerate(sorted(layers.keys()), start=1):
        info = analyze_layer(layers[z])

        trust.append({
            "layer_index": idx,
            "z_height_mm": round(z, 3),
            "bbox_mm": {
                "outer": info["bbox"]
            },
            "expected_path_length_mm": info["path_length"],
            "path_length_tolerance_mm": max(5, info["path_length"] * 0.05),
            "expected_extrusion_mm": info["extrusion"],
            "extrusion_tolerance_mm": max(0.5, info["extrusion"] * 0.1),
            "allowed_feedrate_mm_per_min": info["feedrate"],
            "allowed_commands": info["commands"],
            "expected_temp_c": 210,
            "temp_tolerance_c": 5
        })

    return trust

# =========================
# CURA ENGINE CALL
# =========================

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

# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Input STL file")
    parser.add_argument("-o", "--output", required=True, help="Output directory")
    args = parser.parse_args()

    input_stl = Path(args.input)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    gcode_path = out_dir / "baseline.gcode"
    trust_path = out_dir / "trust_reference.json"

    print("▶ Slicing STL with CuraEngine...")
    run_cura_engine(input_stl, gcode_path)

    print("▶ Generating trust reference from G-code...")
    trust = generate_trust_reference(gcode_path)

    with open(trust_path, "w") as f:
        json.dump(trust, f, indent=2)

    print("✔ Done")
    print(f"  ├─ {gcode_path}")
    print(f"  └─ {trust_path}")

if __name__ == "__main__":
    main()
