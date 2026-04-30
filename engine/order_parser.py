from __future__ import annotations

from engine.orders import (
    BuildOrder,
    ConvoyOrder,
    DisbandOrder,
    HoldOrder,
    MoveOrder,
    Order,
    RetreatOrder,
    SupportHoldOrder,
    SupportMoveOrder,
)


def parse_order(order: str | Order) -> Order:
    if isinstance(order, Order):
        return order

    parts = order.split()

    if len(parts) == 3 and parts[2] == "H":
        return HoldOrder(unit_type=parts[0], location=parts[1])

    if len(parts) == 4 and parts[2] == "-":
        return MoveOrder(unit_type=parts[0], location=parts[1], target=parts[3])

    if len(parts) == 6 and parts[2] == "-" and parts[4:] == ["VIA", "CONVOY"]:
        return MoveOrder(
            unit_type=parts[0],
            location=parts[1],
            target=parts[3],
            via_convoy=True,
        )

    if len(parts) == 4 and parts[0] == "BUILD" and parts[2] == "AT":
        return BuildOrder(unit_type=parts[1], location=parts[3])

    if len(parts) == 4 and parts[0] == "DISBAND" and parts[2] == "AT":
        return DisbandOrder(unit_type=parts[1], location=parts[3])

    if len(parts) == 4 and parts[2] == "R":
        return RetreatOrder(unit_type=parts[0], location=parts[1], target=parts[3])

    if len(parts) == 5 and parts[2] == "S" and parts[4] != "-":
        return SupportHoldOrder(
            unit_type=parts[0],
            location=parts[1],
            supported_unit_type=parts[3],
            supported_location=parts[4],
        )

    if len(parts) == 7 and parts[2] == "S" and parts[5] == "-":
        return SupportMoveOrder(
            unit_type=parts[0],
            location=parts[1],
            supported_unit_type=parts[3],
            supported_location=parts[4],
            target=parts[6],
        )

    if len(parts) == 7 and parts[2] == "C" and parts[5] == "-":
        return ConvoyOrder(
            unit_type=parts[0],
            location=parts[1],
            convoyed_unit_type=parts[3],
            convoyed_location=parts[4],
            target=parts[6],
        )

    raise ValueError(f"Unsupported order format: {order}")
