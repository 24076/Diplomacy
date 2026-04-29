from __future__ import annotations

from collections import deque

from engine.map_data import FLEET_ADJACENCY, SEA_PROVINCES, base_location
from engine.orders import ConvoyOrder, Order


def has_convoy_path(
    source: str,
    target: str,
    orders: list[Order],
    available_fleets: set[str] | None = None,
) -> bool:
    convoy_fleets = {
        order.location
        for order in orders
        if isinstance(order, ConvoyOrder)
        and order.convoyed_unit_type == "A"
        and order.convoyed_location == source
        and order.target == target
        and order.location in SEA_PROVINCES
    }

    if available_fleets is not None:
        convoy_fleets &= available_fleets

    if not convoy_fleets:
        return False

    source_base = base_location(source)
    target_base = base_location(target)

    start_nodes = {
        fleet
        for fleet in convoy_fleets
        if source_base in {base_location(neighbor) for neighbor in FLEET_ADJACENCY.get(fleet, set())}
    }
    target_neighbors = {
        fleet
        for fleet in convoy_fleets
        if target_base in {base_location(neighbor) for neighbor in FLEET_ADJACENCY.get(fleet, set())}
    }

    if not start_nodes or not target_neighbors:
        return False

    queue = deque(start_nodes)
    seen = set(start_nodes)

    while queue:
        fleet = queue.popleft()
        if fleet in target_neighbors:
            return True
        for neighbor in FLEET_ADJACENCY.get(fleet, set()):
            if neighbor in convoy_fleets and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)

    return False


def convoy_destinations_for_army(source: str, available_fleets: set[str]) -> set[str]:
    source_base = base_location(source)
    convoy_fleets = {fleet for fleet in available_fleets if fleet in SEA_PROVINCES}

    start_nodes = {
        fleet
        for fleet in convoy_fleets
        if source_base in {base_location(neighbor) for neighbor in FLEET_ADJACENCY.get(fleet, set())}
    }
    if not start_nodes:
        return set()

    queue = deque(start_nodes)
    seen = set(start_nodes)

    while queue:
        fleet = queue.popleft()
        for neighbor in FLEET_ADJACENCY.get(fleet, set()):
            if neighbor in convoy_fleets and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)

    destinations = set()
    for fleet in seen:
        for neighbor in FLEET_ADJACENCY.get(fleet, set()):
            neighbor_base = base_location(neighbor)
            if neighbor_base == source_base:
                continue
            if neighbor_base in SEA_PROVINCES:
                continue
            destinations.add(neighbor_base)

    return destinations


def convoy_routes(
    source: str,
    target: str,
    orders: list[Order],
    available_fleets: set[str] | None = None,
) -> list[tuple[str, ...]]:
    convoy_fleets = {
        order.location
        for order in orders
        if isinstance(order, ConvoyOrder)
        and order.convoyed_unit_type == "A"
        and order.convoyed_location == source
        and order.target == target
        and order.location in SEA_PROVINCES
    }

    if available_fleets is not None:
        convoy_fleets &= available_fleets
    if not convoy_fleets:
        return []

    source_base = base_location(source)
    target_base = base_location(target)
    start_nodes = [
        fleet
        for fleet in convoy_fleets
        if source_base in {base_location(neighbor) for neighbor in FLEET_ADJACENCY.get(fleet, set())}
    ]
    target_neighbors = {
        fleet
        for fleet in convoy_fleets
        if target_base in {base_location(neighbor) for neighbor in FLEET_ADJACENCY.get(fleet, set())}
    }
    if not start_nodes or not target_neighbors:
        return []

    routes: list[tuple[str, ...]] = []

    def dfs(current: str, path: list[str], seen: set[str]) -> None:
        if current in target_neighbors:
            routes.append(tuple(path))
            return
        for neighbor in sorted(FLEET_ADJACENCY.get(current, set())):
            if neighbor not in convoy_fleets or neighbor in seen:
                continue
            seen.add(neighbor)
            path.append(neighbor)
            dfs(neighbor, path, seen)
            path.pop()
            seen.remove(neighbor)

    for fleet in sorted(start_nodes):
        dfs(fleet, [fleet], {fleet})

    return routes
