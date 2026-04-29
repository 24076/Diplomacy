from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    unit_type: str
    location: str


@dataclass(frozen=True)
class HoldOrder(Order):
    pass


@dataclass(frozen=True)
class MoveOrder(Order):
    target: str
    via_convoy: bool = False


@dataclass(frozen=True)
class SupportHoldOrder(Order):
    supported_unit_type: str
    supported_location: str


@dataclass(frozen=True)
class SupportMoveOrder(Order):
    supported_unit_type: str
    supported_location: str
    target: str


@dataclass(frozen=True)
class ConvoyOrder(Order):
    convoyed_unit_type: str
    convoyed_location: str
    target: str


@dataclass(frozen=True)
class RetreatOrder(Order):
    target: str


@dataclass(frozen=True)
class BuildOrder(Order):
    pass


@dataclass(frozen=True)
class DisbandOrder(Order):
    pass


def is_movement_order(order: Order) -> bool:
    return isinstance(order, (MoveOrder, RetreatOrder))
