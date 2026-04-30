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


def format_order(order: Order) -> str:
    if isinstance(order, HoldOrder):
        return f"{order.unit_type} {order.location} H"
    if isinstance(order, MoveOrder):
        suffix = " VIA CONVOY" if order.via_convoy else ""
        return f"{order.unit_type} {order.location} - {order.target}{suffix}"
    if isinstance(order, SupportHoldOrder):
        return (
            f"{order.unit_type} {order.location} S "
            f"{order.supported_unit_type} {order.supported_location}"
        )
    if isinstance(order, SupportMoveOrder):
        return (
            f"{order.unit_type} {order.location} S "
            f"{order.supported_unit_type} {order.supported_location} - {order.target}"
        )
    if isinstance(order, ConvoyOrder):
        return (
            f"{order.unit_type} {order.location} C "
            f"{order.convoyed_unit_type} {order.convoyed_location} - {order.target}"
        )
    if isinstance(order, RetreatOrder):
        return f"{order.unit_type} {order.location} R {order.target}"
    if isinstance(order, BuildOrder):
        return f"BUILD {order.unit_type} AT {order.location}"
    if isinstance(order, DisbandOrder):
        return f"DISBAND {order.unit_type} AT {order.location}"
    raise TypeError(f"Unsupported order object: {type(order).__name__}")


def hold(unit_type: str, location: str) -> str:
    return format_order(HoldOrder(unit_type=unit_type, location=location))


def move(unit_type: str, location: str, target: str, via_convoy: bool = False) -> str:
    return format_order(
        MoveOrder(unit_type=unit_type, location=location, target=target, via_convoy=via_convoy)
    )


def support_hold(
    unit_type: str,
    location: str,
    supported_unit_type: str,
    supported_location: str,
) -> str:
    return format_order(
        SupportHoldOrder(
            unit_type=unit_type,
            location=location,
            supported_unit_type=supported_unit_type,
            supported_location=supported_location,
        )
    )


def support_move(
    unit_type: str,
    location: str,
    supported_unit_type: str,
    supported_location: str,
    target: str,
) -> str:
    return format_order(
        SupportMoveOrder(
            unit_type=unit_type,
            location=location,
            supported_unit_type=supported_unit_type,
            supported_location=supported_location,
            target=target,
        )
    )


def convoy(
    unit_type: str,
    location: str,
    convoyed_unit_type: str,
    convoyed_location: str,
    target: str,
) -> str:
    return format_order(
        ConvoyOrder(
            unit_type=unit_type,
            location=location,
            convoyed_unit_type=convoyed_unit_type,
            convoyed_location=convoyed_location,
            target=target,
        )
    )


def retreat(unit_type: str, location: str, target: str) -> str:
    return format_order(RetreatOrder(unit_type=unit_type, location=location, target=target))


def build(unit_type: str, location: str) -> str:
    return format_order(BuildOrder(unit_type=unit_type, location=location))


def disband(unit_type: str, location: str) -> str:
    return format_order(DisbandOrder(unit_type=unit_type, location=location))
