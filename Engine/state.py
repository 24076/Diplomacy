from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class Unit:
    power: str
    unit_type: str
    location: str

@dataclass
class GameState:
    year: int = 1901
    season: str = "SPRING"
    phase: str = "ORDERS"
    units: Dict[str, Unit] = field(default_factory=dict)
    submitted_orders: Dict[str, List[str]] = field(default_factory=dict)
