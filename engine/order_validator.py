from engine.map_data import (
    HOME_SUPPLY_CENTERS,
    SEA_PROVINCES,
    base_location,
    get_adjacency,
    is_valid_location_for_unit,
)
from engine.convoy import has_convoy_path
from engine.order_parser import parse_order
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

class OrderValidator:
    def __init__(self) -> None:
        pass

    def validate(
        self,
        order: str | Order,
        units: dict | None = None,
        context_orders: list[str | Order] | None = None,
        retreat_options: dict[str, list[str]] | None = None,
        power_name: str | None = None,
        supply_center_owners: dict[str, str | None] | None = None,
        adjustment_requirement: int | None = None,
    ):
        try:
            parsed = parse_order(order)
        except Exception as exc:
            return False, str(exc)

        if isinstance(parsed, BuildOrder):
            return self._validate_build(
                parsed,
                units,
                power_name=power_name,
                supply_center_owners=supply_center_owners,
                adjustment_requirement=adjustment_requirement,
            )
        if isinstance(parsed, DisbandOrder):
            return self._validate_disband(
                parsed,
                units,
                power_name=power_name,
                adjustment_requirement=adjustment_requirement,
            )

        basic_ok, basic_message = self._validate_existing_unit_order(parsed, units)
        if not basic_ok:
            return basic_ok, basic_message

        if isinstance(parsed, HoldOrder):
            return True, "ok"
        if isinstance(parsed, MoveOrder):
            return self._validate_move_like(
                parsed.unit_type,
                parsed.location,
                parsed.target,
                via_convoy=parsed.via_convoy,
                units=units,
                context_orders=context_orders,
            )
        if isinstance(parsed, RetreatOrder):
            return self._validate_retreat(parsed, retreat_options)
        if isinstance(parsed, SupportHoldOrder):
            return self._validate_support_hold(parsed)
        if isinstance(parsed, SupportMoveOrder):
            return self._validate_support_move(
                parsed,
                units=units,
                context_orders=context_orders,
            )
        if isinstance(parsed, ConvoyOrder):
            return self._validate_convoy(parsed)

        return False, "unsupported order"

    def _validate_existing_unit_order(self, order: Order, units: dict | None):
        if not is_valid_location_for_unit(order.unit_type, order.location):
            return False, f"invalid {order.unit_type} location: {order.location}"

        if units is None:
            return True, "ok"

        unit = units.get(order.location)
        if unit is None:
            return False, f"no unit at {order.location}"
        if unit.unit_type != order.unit_type:
            return False, f"unit at {order.location} is {unit.unit_type}, not {order.unit_type}"
        return True, "ok"

    def _validate_move_like(
        self,
        unit_type: str,
        location: str,
        target: str,
        via_convoy: bool = False,
        units: dict | None = None,
        context_orders: list[str | Order] | None = None,
    ):
        parsed_context = [parse_order(order) for order in context_orders] if context_orders is not None else []

        if target in get_adjacency(unit_type, location) and not via_convoy:
            if unit_type != "A" or units is None:
                return True, "ok"
            army = units.get(location)
            if army is None:
                return True, "ok"
            has_own_convoy = any(
                isinstance(parsed, ConvoyOrder)
                and parsed.convoyed_location == location
                and parsed.target == target
                and units.get(parsed.location) is not None
                and units[parsed.location].power == army.power
                for parsed in parsed_context
            )
            if not has_own_convoy:
                return True, "ok"
        if unit_type == "A" and context_orders is not None and has_convoy_path(location, target, parsed_context):
            return True, "ok"
        return False, f"{location} cannot move to {target}"

    def _validate_support_hold(self, order: SupportHoldOrder):
        if not is_valid_location_for_unit(order.supported_unit_type, order.supported_location):
            return False, f"invalid supported location: {order.supported_location}"
        if not self._can_support_target(order.unit_type, order.location, order.supported_location):
            return False, f"{order.location} cannot support hold at {order.supported_location}"
        return True, "ok"

    def _validate_support_move(
        self,
        order: SupportMoveOrder,
        units: dict | None = None,
        context_orders: list[str | Order] | None = None,
    ):
        if not is_valid_location_for_unit(order.supported_unit_type, order.supported_location):
            return False, f"invalid supported location: {order.supported_location}"
        move_ok, _ = self._validate_move_like(
            order.supported_unit_type,
            order.supported_location,
            order.target,
            units=units,
            context_orders=context_orders,
        )
        if not move_ok:
            return (
                False,
                f"{order.supported_location} cannot move to {order.target}",
            )
        if units is not None:
            supporter = units.get(order.location)
            target_unit = units.get(order.target)
            if (
                supporter is not None
                and target_unit is not None
                and supporter.power == target_unit.power
            ):
                return False, f"{order.location} cannot support an attack on its own unit at {order.target}"
        if not self._can_support_target(order.unit_type, order.location, order.target):
            return False, f"{order.location} cannot support into {order.target}"
        return True, "ok"

    def _validate_convoy(self, order: ConvoyOrder):
        if order.unit_type != "F":
            return False, "only fleets can convoy"
        if order.location not in SEA_PROVINCES:
            return False, "convoying fleet must be at sea"
        if order.convoyed_unit_type != "A":
            return False, "only armies can be convoyed"
        if not is_valid_location_for_unit("A", order.convoyed_location):
            return False, f"invalid convoy source: {order.convoyed_location}"
        if is_valid_location_for_unit("A", order.target) is False:
            return False, f"invalid convoy target: {order.target}"
        return True, "ok"

    def _validate_retreat(
        self,
        order: RetreatOrder,
        retreat_options: dict[str, list[str]] | None,
    ):
        if retreat_options is not None and order.target not in retreat_options.get(order.location, []):
            return False, f"{order.location} cannot retreat to {order.target}"
        return self._validate_move_like(order.unit_type, order.location, order.target)

    def _validate_build(
        self,
        order: BuildOrder,
        units: dict | None,
        power_name: str | None = None,
        supply_center_owners: dict[str, str | None] | None = None,
        adjustment_requirement: int | None = None,
    ):
        if not is_valid_location_for_unit(order.unit_type, order.location):
            return False, f"invalid {order.unit_type} build location: {order.location}"
        base = base_location(order.location)
        owner = self._home_center_owner(base)
        if owner is None:
            return False, f"{base} is not a home supply center"
        if power_name is not None and owner != power_name:
            return False, f"{base} is not a home center for {power_name}"
        if supply_center_owners is not None and power_name is not None:
            if supply_center_owners.get(base) != power_name:
                return False, f"{base} is not controlled by {power_name}"
        if adjustment_requirement is not None and adjustment_requirement <= 0:
            return False, "no builds available"
        if units is not None:
            occupied_bases = {base_location(location) for location in units}
            if base in occupied_bases:
                return False, f"{base} is already occupied"
        return True, "ok"

    def _validate_disband(
        self,
        order: DisbandOrder,
        units: dict | None,
        power_name: str | None = None,
        adjustment_requirement: int | None = None,
    ):
        if not is_valid_location_for_unit(order.unit_type, order.location):
            return False, f"invalid {order.unit_type} disband location: {order.location}"
        if adjustment_requirement is not None and adjustment_requirement >= 0:
            return False, "no disbands required"
        if units is None:
            return True, "ok"
        unit = units.get(order.location)
        if unit is None:
            return False, f"no unit at {order.location}"
        if unit.unit_type != order.unit_type:
            return False, f"unit at {order.location} is {unit.unit_type}, not {order.unit_type}"
        if power_name is not None and unit.power != power_name:
            return False, f"{order.location} does not belong to {power_name}"
        return True, "ok"

    def _home_center_owner(self, location: str):
        base = base_location(location)
        for power, centers in HOME_SUPPLY_CENTERS.items():
            if base in centers:
                return power
        return None

    def _can_support_target(self, unit_type: str, location: str, target: str) -> bool:
        adjacency = get_adjacency(unit_type, location)
        if target in adjacency:
            return True
        target_base = base_location(target)
        return target_base in {base_location(neighbor) for neighbor in adjacency}
