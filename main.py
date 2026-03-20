import json
import os
import sys

from simulation.simulation_controller import SimulationController
from attacks.attacks import (
    TemperatureShockAttack,
    ExtrusionFloodAttack,
    CommandInjectionAttack,
)
from plot.plot import generate_all_plots, generate_sweep_plots


def create_attack(name, params):
    if name == "command_injection":
        return CommandInjectionAttack(**params)
    elif name == "temperature_shock":
        return TemperatureShockAttack(**params)
    elif name == "extrusion_flood":
        return ExtrusionFloodAttack(**params)
    return None


def run_experiment(config, attack_params, result_dir):
    gcode_path = config["gcode_path"]
    reference_path = config["reference_path"]
    machine_reference = config["machine_reference"]
    num_dts = config["num_dts"]
    attack_config = config["attacks"]

    os.makedirs(os.path.join(result_dir, "logs"), exist_ok=True)

    mapping = [
        {"dt_id": i, "machine_id": i, "gcode_path": gcode_path}
        for i in range(1, num_dts + 1)
    ]

    attacks = {}
    for dt_id_str, attack_name in attack_config.items():
        dt_id = int(dt_id_str)
        attack_obj = create_attack(attack_name, attack_params)
        if attack_obj:
            attacks[dt_id] = attack_obj

    sim = SimulationController(
        mapping=mapping,
        cmd_reference=reference_path,
        machine_reference=machine_reference,
        attacks=attacks,
        output_dir=result_dir,
    )
    sim.run()


def run_all_experiments(config_path="experiments/experiments_config.json"):
    with open(config_path) as f:
        config = json.load(f)

    probabilities = config.get("probability_sweep", [0.5])
    seeds = config.get("seeds", [42])
    experiments = config["experiments"]

    total = len(experiments) * len(probabilities) * len(seeds)
    count = 0

    print("=" * 60)
    print("  Trust in 3D Printing - Unified Pipeline")
    for e in experiments:
        print("  Experiment: " + e["name"])
    print("  Probabilities: " + str(probabilities))
    print("  Seeds:         " + str(seeds))
    print("  Total runs:    " + str(total))
    print("=" * 60)

    for exp in experiments:
        exp_name = exp["name"]
        exp_root = os.path.join("results", exp_name)

        for prob in probabilities:
            for seed in seeds:
                count += 1

                p_str = "{:.2f}".format(prob).replace(".", "_")
                folder = "sweep_p" + p_str + "_s" + str(seed)
                result_dir = os.path.join(exp_root, folder)

                # if os.path.exists(os.path.join(result_dir, "logs")):
                #     msg = "[{}/{}] Skip: {}/{}".format(count, total, exp_name, folder)
                #     print(msg)
                #     continue

                msg = "[{}/{}] {} prob={} seed={}".format(count, total, exp_name, prob, seed)
                print(msg)

                ap = {"injection_prob": prob, "seed": seed}
                try:
                    run_experiment(exp, ap, result_dir)
                    # Generate per-variant comparison plots (trust trajectory + bar chart)
                    try:
                        generate_all_plots(result_dir)
                    except Exception as _e:
                        print(f"  [WARN] Failed to generate per-variant plots for {folder}: {_e}")
                    print("  Done: " + folder)
                except Exception as e:
                    print("  ERROR: " + str(e))

    print("")
    print("=" * 60)
    print("  Generating sweep comparison graphs...")
    print("=" * 60)

    for exp in experiments:
        generate_sweep_plots(
            exp_name=exp["name"],
            attacks_map=exp["attacks"],
            probabilities=probabilities,
            seeds=seeds,
        )

    print("")
    print("All experiments and graphs complete!")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: python main.py [config.json]")
        sys.exit(1)

    cfg = "experiments/experiments_config.json"
    if len(sys.argv) == 2:
        cfg = sys.argv[1]
    run_all_experiments(cfg)
