from simulation.simulation_controller import SimulationController
from attacks.attacks import TemperatureShockAttack, ExtrusionFloodAttack, CommandInjectionAttack
def main():
    cmd_injection_attack = CommandInjectionAttack(
        injection_prob=0.5,
        seed=42
    )
    temp_shock_attack = TemperatureShockAttack(
        injection_prob=0.5,
        seed=42
    )
    extrusion_flood_attack = ExtrusionFloodAttack(
        injection_prob=0.5,
        seed=42
    )

    # DT  Machine  G-code mapping
    mapping = [
        { "dt_id": 1, "machine_id": 1, "gcode_path": "references/baseline.gcode" },
        { "dt_id": 2, "machine_id": 2, "gcode_path": "references/baseline.gcode" }, 
        { "dt_id": 3, "machine_id": 3, "gcode_path": "references/baseline.gcode" }, 
        { "dt_id": 4, "machine_id": 4, "gcode_path": "references/baseline.gcode" }, 
    ]

    attacks = {
        2: cmd_injection_attack,   
        3: temp_shock_attack,  
        4: extrusion_flood_attack,  
    }

    sim = SimulationController(
        mapping=mapping,
        cmd_reference="references/trust_reference.json",
        machine_reference="references/machine_reference.json",
        attacks=attacks
    )

    sim.run()

if __name__ == "__main__":
    main()
