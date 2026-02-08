DANGEROUS_COMMANDS = {
    # Flow / speed scaling (global manipulation)
    "M220",

    # EEPROM write
    "M500",
    "M501",
    "M502",

    # Motor current / power
    "M907",

    # Firmware / system reset
    "M999",
}
