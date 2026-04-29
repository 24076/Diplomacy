from engine.order_parser import parse_order

class OrderValidator:
    def __init__(self, adjacency: dict[str, list[str]]) -> None:
        self.adjacency = adjacency

    def validate(self, order: str):
        try:
            parsed = parse_order(order)
        except Exception as exc:
            return False, str(exc)

        if parsed["type"] == "HOLD":
            return True, "ok"

        if parsed["type"] == "MOVE":
            src = parsed["location"]
            dst = parsed["target"]
            if dst in self.adjacency.get(src, []):
                return True, "ok"
            return False, f"{src} cannot move to {dst}"

        return False, "unsupported order"
