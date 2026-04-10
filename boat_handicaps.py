"""Portsmouth Yardstick (PY) handicap numbers for dinghy classes.

To add a new class, add an entry to the HANDICAPS dict below.
Higher numbers indicate slower boats.
"""

HANDICAPS: dict[str, int] = {
    "BritishMoth":  1165,
    "Topper":       1369,
    "Topper4.2":    1425,
    "ILCA7":        1102,
    "ILCA6":        1154,
    "ILCA4":        1213,
    "Laser2000":    1118,
    "Comet":        1210,
    "Zest":         1270,
    "Mirror":       1370,
    "Wayfarer":     1109,
    "Enterprise":   1133,
    "Byte":         1217,
    "Lightning368": 1160,
    "Miracle":      1200,
    "Optimist":     1628,
    "Solo":         1142,
    "Streaker":     1124,
}


ILCA_ALIASES: dict[str, str] = {
    "ILCA7": "Laser",
    "ILCA6": "Laser Radial",
    "ILCA4": "Laser 4.7",
}


def get_handicap(boat_class: str) -> int | None:
    return HANDICAPS.get(boat_class)


def boat_names() -> list[str]:
    return list(HANDICAPS.keys())


def display_name(boat_class: str) -> str:
    """Return class name with legacy alias, e.g. 'ILCA7 (Laser)'."""
    alias = ILCA_ALIASES.get(boat_class)
    return f"{boat_class} ({alias})" if alias else boat_class
