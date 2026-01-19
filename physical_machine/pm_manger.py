# physical_machine/pm_manager.py

from physical_machine.physical_machine import PhysicalMachine

class PMManager:
    def __init__(self):
        self.machines = {}

    def add_machine(self, machine_id):
        self.machines[machine_id] = PhysicalMachine(machine_id)

    def get(self, machine_id):
        return self.machines.get(machine_id)

    def get_all(self):
        return self.machines.values()
