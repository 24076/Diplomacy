from dataclasses import dataclass, field
from typing import Dict, List
from engine.map_data import INITIAL_SUPPLY_CENTER_OWNERS
from engine.orders import Order

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
    submitted_orders: Dict[str, List[Order]] = field(default_factory=dict)
    dislodged_units: Dict[str, Unit] = field(default_factory=dict)
    retreat_options: Dict[str, List[str]] = field(default_factory=dict)
    supply_center_owners: Dict[str, str | None] = field(
        default_factory=lambda: dict(INITIAL_SUPPLY_CENTER_OWNERS)
    )
    adjustment_requirements: Dict[str, int] = field(default_factory=dict)
    winner: str | None = None
