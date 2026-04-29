from collections import defaultdict
from engine.order_parser import parse_order

class SimpleResolver:
    def resolve(self, units: dict, all_orders: list[str]) -> dict:
        parsed = [parse_order(o) for o in all_orders]
        occupied = set(units.keys())
        attacks = defaultdict(list)

        for order in parsed:
            if order["type"] == "MOVE":
                attacks[order["target"]].append(order)

        new_positions = dict(units)
        results = []

        for order in parsed:
            if order["type"] == "HOLD":
                results.append((order["location"], "HOLD"))
                continue

            src = order["location"]
            dst = order["target"]

            if len(attacks[dst]) > 1:
                results.append((src, f"BOUNCE {dst}"))
                continue

            if dst in occupied:
                results.append((src, f"FAIL {dst} occupied"))
                continue

            unit = new_positions.pop(src, None)
            if unit is not None:
                unit.location = dst
                new_positions[dst] = unit
            results.append((src, f"MOVE {dst}"))

        return {"units": new_positions, "results": results}
