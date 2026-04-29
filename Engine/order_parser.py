def parse_order(order: str) -> dict:
    parts = order.split()
    if len(parts) >= 3 and parts[2] == "H":
        return {"type": "HOLD", "location": parts[1]}
    if len(parts) >= 4 and parts[2] == "-":
        return {"type": "MOVE", "location": parts[1], "target": parts[3]}
    raise ValueError(f"Unsupported order format: {order}")
