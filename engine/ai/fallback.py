from __future__ import annotations

from engine.map_data import HOME_SUPPLY_CENTERS, SUPPLY_CENTERS, base_location
from engine.order_parser import parse_order
from engine.orders import BuildOrder, DisbandOrder, HoldOrder, MoveOrder, RetreatOrder


def score_order(game, power: str, order_text: str, memory) -> float:
    order = parse_order(order_text)
    score = 0.0
    trust_row = memory.trust.get(power, {})
    fear_row = memory.fear.get(power, {})

    if isinstance(order, HoldOrder):
        score += 0.15
        if _is_border_unit(game, power, order.location, fear_row):
            score += 0.75

    if isinstance(order, MoveOrder):
        target = base_location(order.target)
        score += 0.2
        if target in SUPPLY_CENTERS:
            owner = game.state.supply_center_owners.get(target)
            if owner is None:
                score += 2.1
            elif owner != power:
                score += 1.4
        if target in HOME_SUPPLY_CENTERS.get(power, set()):
            score += 0.3
        occupier = _occupier_of_base(game, target)
        if occupier and occupier != power:
            score += fear_row.get(occupier, 0.0) * 0.8
            score -= max(0.0, trust_row.get(occupier, 0.0)) * 0.9

    if isinstance(order, RetreatOrder):
        target = base_location(order.target)
        score += 0.8
        if target in SUPPLY_CENTERS:
            score += 0.7

    if isinstance(order, BuildOrder):
        score += 1.4

    if isinstance(order, DisbandOrder):
        if base_location(order.location) not in HOME_SUPPLY_CENTERS.get(power, set()):
            score += 1.0

    return score


def choose_orders(game, power: str, possible_orders: dict[str, list[str]], memory) -> list[str]:
    selected = []
    for location, orders in possible_orders.items():
        if not orders:
            continue
        ranked = sorted(
            orders,
            key=lambda candidate: (score_order(game, power, candidate, memory), candidate),
            reverse=True,
        )
        selected.append(ranked[0])
    return selected


def _occupier_of_base(game, location: str) -> str | None:
    for unit in game.state.units.values():
        if base_location(unit.location) == location:
            return unit.power
    return None


def _is_border_unit(game, power: str, location: str, fear_row: dict[str, float]) -> bool:
    for other_location, unit in game.state.units.items():
        if unit.power == power:
            continue
        if base_location(other_location) == base_location(location):
            continue
        if fear_row.get(unit.power, 0.0) > 0.25:
            return True
    return False
