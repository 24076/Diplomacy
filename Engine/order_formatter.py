def hold(unit_type: str, location: str) -> str:
    return f"{unit_type} {location} H"

def move(unit_type: str, location: str, target: str) -> str:
    return f"{unit_type} {location} - {target}"
