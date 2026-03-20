DANGEROUS_COMMANDS = {
    # Flow / speed scaling (global manipulation)
    "M220",
    "M221",   # flow rate override (used by injection attack)

    # Steps per mm corruption
    "M92",    # recalibrate steps/mm (stealth firmware attack)

    # EEPROM write
    "M500",
    "M501",
    "M502",

    # Motor current / power
    "M907",

    # Firmware / system reset
    "M999",
}
