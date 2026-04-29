from __future__ import annotations

from typing import Dict, Iterable, Set

POWERS = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]

SPLIT_COASTS: Dict[str, tuple[str, ...]] = {
    "BUL": ("EC", "SC"),
    "SPA": ("NC", "SC"),
    "STP": ("NC", "SC"),
}

SEA_PROVINCES: Set[str] = {
    "ADR",
    "AEG",
    "BAL",
    "BAR",
    "BLA",
    "BOT",
    "EAS",
    "ENG",
    "GOL",
    "HEL",
    "ION",
    "IRI",
    "MID",
    "NAT",
    "NRG",
    "NTH",
    "SKA",
    "TYN",
    "WES",
}

ARMY_ADJACENCY: Dict[str, Set[str]] = {
    "ALB": {"GRE", "SER", "TRI"},
    "ANK": {"ARM", "CON", "SMY"},
    "APU": {"NAP", "ROM", "VEN"},
    "ARM": {"ANK", "SEV", "SMY", "SYR"},
    "BEL": {"BUR", "HOL", "PIC", "RUH"},
    "BER": {"KIE", "MUN", "PRU", "SIL"},
    "BOH": {"GAL", "MUN", "SIL", "TYR", "VIE"},
    "BRE": {"GAS", "PAR", "PIC"},
    "BUD": {"GAL", "RUM", "SER", "TRI", "VIE"},
    "BUL": {"CON", "GRE", "RUM", "SER"},
    "BUR": {"BEL", "GAS", "MAR", "MUN", "PAR", "PIC", "RUH"},
    "CLY": {"EDI", "LVP"},
    "CON": {"ANK", "BUL", "SMY"},
    "DEN": {"KIE", "SWE"},
    "EDI": {"CLY", "LVP", "YOR"},
    "FIN": {"NWY", "STP", "SWE"},
    "GAL": {"BOH", "BUD", "RUM", "SIL", "UKR", "VIE", "WAR"},
    "GAS": {"BRE", "BUR", "MAR", "PAR", "SPA"},
    "GRE": {"ALB", "BUL", "SER"},
    "HOL": {"BEL", "KIE", "RUH"},
    "KIE": {"BER", "DEN", "HOL", "MUN", "RUH"},
    "LON": {"WAL", "YOR"},
    "LVN": {"MOS", "PRU", "STP", "WAR"},
    "LVP": {"CLY", "EDI", "WAL", "YOR"},
    "MAR": {"BUR", "GAS", "PIE", "SPA"},
    "MOS": {"LVN", "SEV", "STP", "UKR", "WAR"},
    "MUN": {"BER", "BOH", "BUR", "KIE", "RUH", "SIL", "TYR"},
    "NAF": {"TUN"},
    "NAP": {"APU", "ROM"},
    "NWY": {"FIN", "STP", "SWE"},
    "PAR": {"BRE", "BUR", "GAS", "PIC"},
    "PIC": {"BEL", "BRE", "BUR", "PAR"},
    "PIE": {"MAR", "TUS", "TYR", "VEN"},
    "POR": {"SPA"},
    "PRU": {"BER", "LVN", "SIL", "WAR"},
    "ROM": {"APU", "NAP", "TUS", "VEN"},
    "RUH": {"BEL", "BUR", "HOL", "KIE", "MUN"},
    "RUM": {"BUD", "BUL", "GAL", "SEV", "SER", "UKR"},
    "SER": {"ALB", "BUD", "BUL", "GRE", "RUM", "TRI"},
    "SEV": {"ARM", "MOS", "RUM", "UKR"},
    "SIL": {"BER", "BOH", "GAL", "MUN", "PRU", "WAR"},
    "SMY": {"ANK", "ARM", "CON", "SYR"},
    "SPA": {"GAS", "MAR", "POR"},
    "STP": {"FIN", "LVN", "MOS", "NWY"},
    "SWE": {"DEN", "FIN", "NWY"},
    "SYR": {"ARM", "SMY"},
    "TRI": {"ALB", "BUD", "SER", "TYR", "VEN", "VIE"},
    "TUN": {"NAF"},
    "TUS": {"PIE", "ROM", "VEN"},
    "TYR": {"BOH", "MUN", "PIE", "TRI", "VEN", "VIE"},
    "UKR": {"GAL", "MOS", "RUM", "SEV", "WAR"},
    "VEN": {"APU", "PIE", "ROM", "TRI", "TUS", "TYR"},
    "VIE": {"BOH", "BUD", "GAL", "TRI", "TYR"},
    "WAL": {"LON", "LVP", "YOR"},
    "WAR": {"GAL", "LVN", "MOS", "PRU", "SIL", "UKR"},
    "YOR": {"EDI", "LON", "LVP", "WAL"},
}

FLEET_ADJACENCY: Dict[str, Set[str]] = {
    "ADR": {"ALB", "APU", "ION", "TRI", "VEN"},
    "AEG": {"BUL/SC", "CON", "EAS", "GRE", "ION", "SMY"},
    "ALB": {"ADR", "GRE", "ION", "TRI"},
    "ANK": {"BLA", "CON", "ARM"},
    "APU": {"ADR", "ION", "NAP", "VEN"},
    "ARM": {"ANK", "BLA", "SEV"},
    "BAL": {"BER", "BOT", "DEN", "KIE", "LVN", "PRU", "SWE"},
    "BAR": {"NRG", "NWY", "STP/NC"},
    "BEL": {"ENG", "HOL", "NTH", "PIC"},
    "BER": {"BAL", "KIE", "PRU"},
    "BLA": {"ANK", "ARM", "BUL/EC", "CON", "RUM", "SEV"},
    "BOT": {"BAL", "FIN", "LVN", "STP/SC", "SWE"},
    "BRE": {"ENG", "GAS", "MID", "PIC"},
    "BUL/EC": {"BLA", "CON", "RUM"},
    "BUL/SC": {"AEG", "CON", "GRE"},
    "CLY": {"EDI", "LVP", "NAT", "NRG"},
    "CON": {"AEG", "ANK", "BLA", "BUL/EC", "BUL/SC", "SMY"},
    "DEN": {"BAL", "HEL", "KIE", "NTH", "SKA", "SWE"},
    "EAS": {"AEG", "ION", "SMY", "SYR"},
    "EDI": {"CLY", "NRG", "NTH", "YOR"},
    "ENG": {"BEL", "BRE", "IRI", "LON", "MID", "NTH", "PIC", "WAL"},
    "FIN": {"BOT", "STP/SC", "SWE"},
    "GAS": {"BRE", "MID", "SPA/NC"},
    "GOL": {"MAR", "PIE", "ROM", "SPA/SC", "TUS", "TYN", "WES"},
    "GRE": {"AEG", "ALB", "BUL/SC", "ION"},
    "HEL": {"DEN", "HOL", "KIE", "NTH"},
    "HOL": {"BEL", "HEL", "KIE", "NTH"},
    "ION": {"ADR", "AEG", "ALB", "APU", "EAS", "GRE", "NAP", "TUN", "TYN", "WES"},
    "IRI": {"ENG", "LVP", "MID", "NAT", "WAL"},
    "KIE": {"BAL", "BER", "DEN", "HEL", "HOL"},
    "LON": {"ENG", "NTH", "WAL", "YOR"},
    "LVN": {"BAL", "BOT", "PRU", "STP/SC"},
    "LVP": {"CLY", "IRI", "NAT", "WAL"},
    "MAR": {"GOL", "PIE", "SPA/SC"},
    "MID": {"BRE", "ENG", "GAS", "IRI", "NAF", "NAT", "POR", "SPA/NC", "SPA/SC", "WES"},
    "NAF": {"MID", "TUN", "WES"},
    "NAP": {"APU", "ION", "ROM", "TYN"},
    "NAT": {"CLY", "IRI", "LVP", "MID", "NRG"},
    "NRG": {"BAR", "CLY", "EDI", "NAT", "NTH", "NWY"},
    "NTH": {"BEL", "DEN", "EDI", "ENG", "HEL", "HOL", "LON", "NRG", "NWY", "SKA", "YOR"},
    "NWY": {"BAR", "NRG", "NTH", "SKA", "STP/NC", "SWE"},
    "PIC": {"BEL", "BRE", "ENG"},
    "PIE": {"GOL", "MAR", "TUS"},
    "POR": {"MID", "SPA/NC", "SPA/SC"},
    "PRU": {"BAL", "BER", "LVN"},
    "ROM": {"GOL", "NAP", "TUS", "TYN"},
    "RUM": {"BLA", "BUL/EC", "SEV"},
    "SEV": {"ARM", "BLA", "RUM"},
    "SKA": {"DEN", "NTH", "NWY", "SWE"},
    "SMY": {"AEG", "CON", "EAS"},
    "SPA/NC": {"GAS", "MID", "POR"},
    "SPA/SC": {"GOL", "MAR", "MID", "POR", "WES"},
    "STP/NC": {"BAR", "NWY"},
    "STP/SC": {"BOT", "FIN", "LVN"},
    "SWE": {"BAL", "BOT", "DEN", "FIN", "NWY", "SKA"},
    "SYR": {"EAS"},
    "TRI": {"ADR", "ALB", "VEN"},
    "TUN": {"ION", "NAF", "TYN", "WES"},
    "TUS": {"GOL", "PIE", "ROM", "TYN"},
    "TYN": {"GOL", "ION", "NAP", "ROM", "TUN", "TUS", "WES"},
    "VEN": {"ADR", "APU", "TRI"},
    "WAL": {"ENG", "IRI", "LON", "LVP"},
    "WES": {"GOL", "ION", "MID", "NAF", "SPA/SC", "TUN", "TYN"},
    "YOR": {"EDI", "LON", "NTH"},
}

SUPPLY_CENTERS: Set[str] = {
    "ANK",
    "BEL",
    "BER",
    "BRE",
    "BUD",
    "BUL",
    "CON",
    "DEN",
    "EDI",
    "GRE",
    "HOL",
    "KIE",
    "LON",
    "LVP",
    "MAR",
    "MOS",
    "MUN",
    "NAP",
    "NWY",
    "PAR",
    "POR",
    "ROM",
    "RUM",
    "SEV",
    "SER",
    "SMY",
    "SPA",
    "STP",
    "SWE",
    "TRI",
    "TUN",
    "VEN",
    "VIE",
    "WAR",
}

HOME_SUPPLY_CENTERS: Dict[str, Set[str]] = {
    "AUSTRIA": {"BUD", "TRI", "VIE"},
    "ENGLAND": {"EDI", "LON", "LVP"},
    "FRANCE": {"BRE", "MAR", "PAR"},
    "GERMANY": {"BER", "KIE", "MUN"},
    "ITALY": {"NAP", "ROM", "VEN"},
    "RUSSIA": {"MOS", "SEV", "STP", "WAR"},
    "TURKEY": {"ANK", "CON", "SMY"},
}

INITIAL_SUPPLY_CENTER_OWNERS: Dict[str, str | None] = {
    center: power
    for power, centers in HOME_SUPPLY_CENTERS.items()
    for center in centers
}
INITIAL_SUPPLY_CENTER_OWNERS.update(
    {
        "BEL": None,
        "BUL": None,
        "DEN": None,
        "GRE": None,
        "HOL": None,
        "NWY": None,
        "POR": None,
        "RUM": None,
        "SER": None,
        "SPA": None,
        "SWE": None,
        "TUN": None,
    }
)

INITIAL_UNITS: Dict[str, dict[str, str]] = {
    "VIE": {"power": "AUSTRIA", "unit_type": "A", "location": "VIE"},
    "BUD": {"power": "AUSTRIA", "unit_type": "A", "location": "BUD"},
    "TRI": {"power": "AUSTRIA", "unit_type": "F", "location": "TRI"},
    "LON": {"power": "ENGLAND", "unit_type": "F", "location": "LON"},
    "EDI": {"power": "ENGLAND", "unit_type": "F", "location": "EDI"},
    "LVP": {"power": "ENGLAND", "unit_type": "A", "location": "LVP"},
    "PAR": {"power": "FRANCE", "unit_type": "A", "location": "PAR"},
    "MAR": {"power": "FRANCE", "unit_type": "A", "location": "MAR"},
    "BRE": {"power": "FRANCE", "unit_type": "F", "location": "BRE"},
    "BER": {"power": "GERMANY", "unit_type": "A", "location": "BER"},
    "MUN": {"power": "GERMANY", "unit_type": "A", "location": "MUN"},
    "KIE": {"power": "GERMANY", "unit_type": "F", "location": "KIE"},
    "ROM": {"power": "ITALY", "unit_type": "A", "location": "ROM"},
    "VEN": {"power": "ITALY", "unit_type": "A", "location": "VEN"},
    "NAP": {"power": "ITALY", "unit_type": "F", "location": "NAP"},
    "MOS": {"power": "RUSSIA", "unit_type": "A", "location": "MOS"},
    "WAR": {"power": "RUSSIA", "unit_type": "A", "location": "WAR"},
    "SEV": {"power": "RUSSIA", "unit_type": "F", "location": "SEV"},
    "STP/SC": {"power": "RUSSIA", "unit_type": "F", "location": "STP/SC"},
    "ANK": {"power": "TURKEY", "unit_type": "F", "location": "ANK"},
    "CON": {"power": "TURKEY", "unit_type": "A", "location": "CON"},
    "SMY": {"power": "TURKEY", "unit_type": "A", "location": "SMY"},
}


def base_location(location: str) -> str:
    return location.split("/", 1)[0]


def is_sea(location: str) -> bool:
    return base_location(location) in SEA_PROVINCES


def is_split_coast(location: str) -> bool:
    return "/" in location


def coast_locations(base: str) -> tuple[str, ...]:
    return tuple(f"{base}/{coast}" for coast in SPLIT_COASTS.get(base, ()))


def _build_province_types() -> Dict[str, str]:
    province_types: Dict[str, str] = {province: "INLAND" for province in ARMY_ADJACENCY}
    for province in SEA_PROVINCES:
        province_types[province] = "SEA"
    for province in _coastal_bases():
        province_types[province] = "COASTAL"
    return province_types


def _coastal_bases() -> Set[str]:
    bases = set()
    for location in FLEET_ADJACENCY:
        if location in SEA_PROVINCES:
            continue
        bases.add(base_location(location))
    return bases


PROVINCE_TYPES = _build_province_types()
PROVINCES: Set[str] = set(PROVINCE_TYPES)
COASTAL_PROVINCES: Set[str] = {p for p, kind in PROVINCE_TYPES.items() if kind == "COASTAL"}
INLAND_PROVINCES: Set[str] = {p for p, kind in PROVINCE_TYPES.items() if kind == "INLAND"}
FLEET_LOCATIONS: Set[str] = set(FLEET_ADJACENCY)


def is_valid_location_for_unit(unit_type: str, location: str) -> bool:
    if unit_type == "A":
        return location in PROVINCES and not is_sea(location) and not is_split_coast(location)
    if unit_type == "F":
        return location in FLEET_LOCATIONS
    return False


def get_adjacency(unit_type: str, location: str) -> Set[str]:
    if unit_type == "A":
        return set(ARMY_ADJACENCY.get(location, set()))
    if unit_type == "F":
        return set(FLEET_ADJACENCY.get(location, set()))
    return set()


def get_all_named_locations() -> Set[str]:
    return set(PROVINCES) | set(FLEET_LOCATIONS)


def canonical_home_center_owners() -> Dict[str, str]:
    return {center: owner for center, owner in INITIAL_SUPPLY_CENTER_OWNERS.items() if owner is not None}


def adjacency_pairs(graph: Dict[str, Set[str]]) -> Iterable[tuple[str, str]]:
    for src, targets in graph.items():
        for dst in targets:
            yield src, dst
