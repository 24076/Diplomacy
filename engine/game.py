from engine.state import GameState, Unit
from engine.battle_reporter import BattleReporter
from engine.phase_manager import PhaseManager
from engine.order_formatter import build, disband, hold, move, retreat
from engine.order_parser import parse_order
from engine.orders import BuildOrder, DisbandOrder
from engine.validation.order_validator import OrderValidator
from engine.resolution.simple_resolver import SimpleResolver
from engine.convoy import convoy_destinations_for_army
from engine.map_data import (
    COASTAL_PROVINCES,
    HOME_SUPPLY_CENTERS,
    INITIAL_UNITS,
    POWERS,
    SPLIT_COASTS,
    SUPPLY_CENTERS,
    base_location,
    coast_locations,
    get_adjacency,
    is_valid_location_for_unit,
    is_sea,
)
from engine.order_formatter import convoy, support_hold, support_move

class Game:
    def __init__(self):
        self.state = GameState(
            units={
                location: Unit(data["power"], data["unit_type"], data["location"])
                for location, data in INITIAL_UNITS.items()
            }
        )
        self.phase_manager = PhaseManager()
        self.validator = OrderValidator()
        self.resolver = SimpleResolver()
        self.battle_reporter = BattleReporter()

    def get_current_phase(self):
        return f"{self.state.season} {self.state.year} {self.state.phase}"

    def get_orderable_locations(self, power_name: str):
        if self.state.phase == "RETREATS":
            return [
                loc
                for loc, unit in self.state.dislodged_units.items()
                if unit.power == power_name
            ]
        if self.state.phase == "ADJUSTMENTS":
            requirement = self.get_adjustment_requirement(power_name)
            if requirement > 0:
                return self.get_buildable_locations(power_name)
            if requirement < 0:
                return [
                    loc
                    for loc, unit in self.state.units.items()
                    if unit.power == power_name
                ]
            return []
        return [loc for loc, unit in self.state.units.items() if unit.power == power_name]

    def get_possible_orders(self, location: str, power_name: str | None = None):
        if self.state.phase == "RETREATS":
            unit = self.state.dislodged_units.get(location)
            if unit is None:
                return []
            orders = [
                retreat(unit.unit_type, location, dst)
                for dst in self.state.retreat_options.get(location, [])
            ]
            orders.append(disband(unit.unit_type, location))
            return orders

        if self.state.phase == "ADJUSTMENTS":
            if power_name is None:
                return []
            requirement = self.get_adjustment_requirement(power_name)
            if requirement > 0 and location in self.get_buildable_locations(power_name):
                return self._get_build_orders_for_location(location)
            if requirement < 0:
                unit = self.state.units.get(location)
                if unit is not None and unit.power == power_name:
                    return [disband(unit.unit_type, location)]
            return []

        unit = self.state.units.get(location)
        if unit is None:
            return []
        return self._get_order_phase_orders(unit)

    def get_all_possible_orders(self):
        if self.state.phase == "ADJUSTMENTS":
            locations = {
                loc
                for power in POWERS
                for loc in self.get_orderable_locations(power)
            }
            return {loc: self.get_possible_orders(loc) for loc in locations}
        return {loc: self.get_possible_orders(loc) for loc in self.state.units.keys()}

    def get_adjustment_requirement(self, power_name: str) -> int:
        return self.state.adjustment_requirements.get(power_name, 0)

    def get_supply_center_counts(self) -> dict[str, int]:
        counts = {power: 0 for power in POWERS}
        for owner in self.state.supply_center_owners.values():
            if owner in counts:
                counts[owner] += 1
        return counts

    def get_buildable_locations(self, power_name: str) -> list[str]:
        occupied = {base_location(loc) for loc in self.state.units}
        buildable = []
        for center in sorted(HOME_SUPPLY_CENTERS[power_name]):
            if self.state.supply_center_owners.get(center) != power_name:
                continue
            if center in occupied:
                continue
            buildable.append(center)
        return buildable

    def set_orders(self, power_name: str, orders: list[str]):
        parsed_orders = []
        for order in orders:
            try:
                parsed_orders.append(parse_order(order))
            except ValueError:
                continue
        valid = []
        max_orders = None
        if self.state.phase == "ADJUSTMENTS":
            requirement = self.get_adjustment_requirement(power_name)
            max_orders = abs(requirement)
        for order in parsed_orders:
            ok, _ = self.validator.validate(
                order,
                self.state.dislodged_units if self.state.phase == "RETREATS" else self.state.units,
                context_orders=parsed_orders,
                retreat_options=self.state.retreat_options if self.state.phase == "RETREATS" else None,
                power_name=power_name,
                supply_center_owners=self.state.supply_center_owners,
                adjustment_requirement=self.get_adjustment_requirement(power_name)
                if self.state.phase == "ADJUSTMENTS"
                else None,
            )
            if ok:
                if self.state.phase == "ADJUSTMENTS":
                    if self.get_adjustment_requirement(power_name) > 0 and not isinstance(order, BuildOrder):
                        continue
                    if self.get_adjustment_requirement(power_name) < 0 and not isinstance(order, DisbandOrder):
                        continue
                    if isinstance(order, BuildOrder):
                        order_base = base_location(order.location)
                        if any(
                            isinstance(existing, BuildOrder)
                            and base_location(existing.location) == order_base
                            for existing in valid
                        ):
                            continue
                    elif any(existing.location == order.location for existing in valid):
                        continue
                    if max_orders is not None and len(valid) >= max_orders:
                        continue
                valid.append(order)
        self.state.submitted_orders[power_name] = valid

    def all_orders_submitted(self):
        if self.state.phase == "RETREATS":
            retreat_powers = {
                unit.power
                for unit in self.state.dislodged_units.values()
            }
            return all(power in self.state.submitted_orders for power in retreat_powers)
        if self.state.phase == "ADJUSTMENTS":
            adjustment_powers = {
                power
                for power, requirement in self.state.adjustment_requirements.items()
                if requirement != 0
            }
            return all(power in self.state.submitted_orders for power in adjustment_powers)
        return all(power in self.state.submitted_orders for power in POWERS)

    def process(self):
        if self.state.phase == "COMPLETED":
            return []
        if self.state.phase == "RETREATS":
            return self._process_retreats()
        if self.state.phase == "ADJUSTMENTS":
            return self._process_adjustments()

        phase_start = self.get_current_phase()
        submitted_orders = {
            power: list(orders)
            for power, orders in self.state.submitted_orders.items()
        }
        snapshot_before = self.battle_reporter.snapshot(self)
        all_orders = []
        for power in POWERS:
            power_orders = list(self.state.submitted_orders.get(power, []))
            issued_locs = {o.location for o in power_orders}
            for loc in self.get_orderable_locations(power):
                if loc not in issued_locs:
                    unit = self.state.units[loc]
                    power_orders.append(hold(unit.unit_type, loc))
            all_orders.extend(power_orders)

        result = self.resolver.resolve(self.state.units, all_orders)
        self.state.units = result["units"]
        self.state.submitted_orders = {}
        self.state.dislodged_units = result["dislodged_units"]
        self.state.retreat_options = result["retreat_options"]
        needs_adjustments = False
        if not self.state.dislodged_units and self.state.season == "FALL":
            needs_adjustments = self._finalize_fall_turn()
            if self.state.phase == "COMPLETED":
                self.battle_reporter.record_phase(
                    phase_start=phase_start,
                    phase_end=self.get_current_phase(),
                    submitted_orders=submitted_orders,
                    results=result["results"],
                    snapshot_before=snapshot_before,
                    snapshot_after=self.battle_reporter.snapshot(self),
                    dislodged_units=self.state.dislodged_units,
                    retreat_options=self.state.retreat_options,
                )
                return result["results"]
        self.state.year, self.state.season, self.state.phase = self.phase_manager.next_phase(
            self.state.year,
            self.state.season,
            self.state.phase,
            has_retreats=bool(self.state.dislodged_units),
            needs_adjustments=needs_adjustments,
        )
        self.battle_reporter.record_phase(
            phase_start=phase_start,
            phase_end=self.get_current_phase(),
            submitted_orders=submitted_orders,
            results=result["results"],
            snapshot_before=snapshot_before,
            snapshot_after=self.battle_reporter.snapshot(self),
            dislodged_units=self.state.dislodged_units,
            retreat_options=self.state.retreat_options,
        )
        return result["results"]

    def _process_retreats(self):
        phase_start = self.get_current_phase()
        submitted_orders = {
            power: list(orders)
            for power, orders in self.state.submitted_orders.items()
        }
        snapshot_before = self.battle_reporter.snapshot(self)
        retreat_orders = []
        for power in POWERS:
            power_orders = list(self.state.submitted_orders.get(power, []))
            issued_locs = {o.location for o in power_orders}
            for loc in self.get_orderable_locations(power):
                if loc not in issued_locs:
                    unit = self.state.dislodged_units[loc]
                    power_orders.append(parse_order(disband(unit.unit_type, loc)))
            retreat_orders.extend(power_orders)

        result = self.resolver.resolve_retreats(
            units=self.state.units,
            dislodged_units=self.state.dislodged_units,
            retreat_options=self.state.retreat_options,
            retreat_orders=retreat_orders,
        )
        self.state.units = result["units"]
        self.state.submitted_orders = {}
        self.state.dislodged_units = {}
        self.state.retreat_options = {}
        needs_adjustments = False
        if self.state.season == "FALL":
            needs_adjustments = self._finalize_fall_turn()
            if self.state.phase == "COMPLETED":
                self.battle_reporter.record_phase(
                    phase_start=phase_start,
                    phase_end=self.get_current_phase(),
                    submitted_orders=submitted_orders,
                    results=result["results"],
                    snapshot_before=snapshot_before,
                    snapshot_after=self.battle_reporter.snapshot(self),
                    dislodged_units={},
                    retreat_options={},
                )
                return result["results"]
        self.state.year, self.state.season, self.state.phase = self.phase_manager.next_phase(
            self.state.year,
            self.state.season,
            "RETREATS",
            has_retreats=False,
            needs_adjustments=needs_adjustments,
        )
        self.battle_reporter.record_phase(
            phase_start=phase_start,
            phase_end=self.get_current_phase(),
            submitted_orders=submitted_orders,
            results=result["results"],
            snapshot_before=snapshot_before,
            snapshot_after=self.battle_reporter.snapshot(self),
            dislodged_units={},
            retreat_options={},
        )
        return result["results"]

    def _process_adjustments(self):
        phase_start = self.get_current_phase()
        submitted_orders = {
            power: list(orders)
            for power, orders in self.state.submitted_orders.items()
        }
        snapshot_before = self.battle_reporter.snapshot(self)
        results = []

        for power in POWERS:
            requirement = self.get_adjustment_requirement(power)
            orders = list(self.state.submitted_orders.get(power, []))
            if requirement > 0:
                build_orders = [order for order in orders if isinstance(order, BuildOrder)][:requirement]
                for order in build_orders:
                    self.state.units[order.location] = Unit(power, order.unit_type, order.location)
                    results.append((order.location, f"BUILD {order.unit_type}"))
                continue

            if requirement < 0:
                disband_count = abs(requirement)
                disband_orders = [order for order in orders if isinstance(order, DisbandOrder)]
                disband_locations = [order.location for order in disband_orders]
                if len(disband_locations) < disband_count:
                    fallback_units = self._default_disband_locations(
                        power,
                        excluded_locations=set(disband_locations),
                    )
                    disband_locations.extend(fallback_units[: disband_count - len(disband_locations)])

                for location in disband_locations[:disband_count]:
                    unit = self.state.units.pop(location, None)
                    if unit is not None:
                        results.append((location, f"DISBAND {unit.unit_type}"))

        self.state.submitted_orders = {}
        self.state.adjustment_requirements = {}
        self.state.year, self.state.season, self.state.phase = self.phase_manager.next_phase(
            self.state.year,
            self.state.season,
            "ADJUSTMENTS",
            has_retreats=False,
            needs_adjustments=False,
        )
        self.battle_reporter.record_phase(
            phase_start=phase_start,
            phase_end=self.get_current_phase(),
            submitted_orders=submitted_orders,
            results=results,
            snapshot_before=snapshot_before,
            snapshot_after=self.battle_reporter.snapshot(self),
            dislodged_units={},
            retreat_options={},
        )
        return results

    def get_battle_report_data(self) -> dict:
        return self.battle_reporter.to_dict(self)

    def get_battle_report_json(self) -> str:
        return self.battle_reporter.to_json(self)

    def get_battle_report_markdown(self) -> str:
        return self.battle_reporter.to_markdown(self)

    def write_battle_report(self, output_dir: str, stem: str = "battle_report") -> dict[str, str]:
        return self.battle_reporter.write_files(self, output_dir=output_dir, stem=stem)

    def _finalize_fall_turn(self) -> bool:
        self._update_supply_center_owners()
        self._update_winner()
        if self.state.winner is not None:
            self.state.phase = "COMPLETED"
            return False
        self._compute_adjustment_requirements()
        return any(self.state.adjustment_requirements.values())

    def _update_supply_center_owners(self):
        for center in SUPPLY_CENTERS:
            occupant = self._find_unit_by_base_location(center)
            if occupant is not None:
                self.state.supply_center_owners[center] = occupant.power

    def _compute_adjustment_requirements(self):
        supply_counts = self.get_supply_center_counts()
        unit_counts = {power: 0 for power in POWERS}
        for unit in self.state.units.values():
            unit_counts[unit.power] += 1
        self.state.adjustment_requirements = {
            power: supply_counts[power] - unit_counts[power]
            for power in POWERS
            if supply_counts[power] - unit_counts[power] != 0
        }

    def _update_winner(self):
        for power, count in self.get_supply_center_counts().items():
            if count >= 18:
                self.state.winner = power
                return
        self.state.winner = None

    def _find_unit_by_base_location(self, location: str):
        for unit in self.state.units.values():
            if base_location(unit.location) == location:
                return unit
        return None

    def _default_disband_locations(
        self,
        power_name: str,
        excluded_locations: set[str] | None = None,
    ) -> list[str]:
        excluded = excluded_locations or set()
        home_centers = HOME_SUPPLY_CENTERS[power_name]

        def distance_key(location: str) -> tuple[float, int, str]:
            unit = self.state.units[location]
            return (
                -self._distance_to_home_center(location, home_centers),
                0 if unit.unit_type == "F" else 1,
                location,
            )

        candidates = [
            loc
            for loc, unit in self.state.units.items()
            if unit.power == power_name and loc not in excluded
        ]
        return sorted(candidates, key=distance_key)

    def _distance_to_home_center(self, start: str, home_centers: set[str]) -> float:
        frontier = [(start, 0)]
        seen = {start}

        while frontier:
            location, distance = frontier.pop(0)
            if base_location(location) in home_centers:
                return float(distance)
            unit = self.state.units.get(start)
            if unit is None:
                break
            for neighbor in sorted(get_adjacency(unit.unit_type, location)):
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                frontier.append((neighbor, distance + 1))

        return float("inf")

    def _get_build_orders_for_location(self, location: str) -> list[str]:
        orders = []
        if is_valid_location_for_unit("A", location):
            orders.append(build("A", location))

        if location in SPLIT_COASTS:
            for coast in coast_locations(location):
                if is_valid_location_for_unit("F", coast):
                    orders.append(build("F", coast))
            return orders

        if location in COASTAL_PROVINCES and is_valid_location_for_unit("F", location):
            orders.append(build("F", location))
        return orders

    def _get_order_phase_orders(self, unit: Unit) -> list[str]:
        orders: list[str] = [hold(unit.unit_type, unit.location)]
        direct_targets = sorted(get_adjacency(unit.unit_type, unit.location))
        orders.extend(move(unit.unit_type, unit.location, dst) for dst in direct_targets)

        if unit.unit_type == "A":
            orders.extend(self._get_convoy_move_orders(unit))

        orders.extend(self._get_support_hold_orders(unit))
        orders.extend(self._get_support_move_orders(unit))

        if unit.unit_type == "F" and is_sea(unit.location):
            orders.extend(self._get_convoy_orders(unit))

        seen = set()
        unique_orders = []
        for order in orders:
            if order not in seen:
                seen.add(order)
                unique_orders.append(order)
        return unique_orders

    def _get_support_hold_orders(self, unit: Unit) -> list[str]:
        reachable_bases = {base_location(dst) for dst in get_adjacency(unit.unit_type, unit.location)}
        orders = []
        for other in self.state.units.values():
            if other.location == unit.location:
                continue
            if base_location(other.location) in reachable_bases:
                orders.append(
                    support_hold(
                        unit.unit_type,
                        unit.location,
                        other.unit_type,
                        other.location,
                    )
                )
        return orders

    def _get_support_move_orders(self, unit: Unit) -> list[str]:
        reachable_bases = {base_location(dst) for dst in get_adjacency(unit.unit_type, unit.location)}
        orders = []
        for other in self.state.units.values():
            if other.location == unit.location:
                continue
            for target in self._get_move_targets_for_unit(other):
                if base_location(target) not in reachable_bases:
                    continue
                orders.append(
                    support_move(
                        unit.unit_type,
                        unit.location,
                        other.unit_type,
                        other.location,
                        target,
                    )
                )
        return orders

    def _get_convoy_orders(self, unit: Unit) -> list[str]:
        reachable_bases = {base_location(dst) for dst in get_adjacency(unit.unit_type, unit.location)}
        orders = []
        for other in self.state.units.values():
            if other.unit_type != "A":
                continue
            if base_location(other.location) not in reachable_bases:
                continue
            for target in sorted(reachable_bases):
                if target == base_location(other.location):
                    continue
                if not is_sea(target):
                    orders.append(
                        convoy(
                            unit.unit_type,
                            unit.location,
                            other.unit_type,
                            other.location,
                            target,
                        )
                    )
        return orders

    def _get_convoy_move_orders(self, unit: Unit) -> list[str]:
        direct_bases = {base_location(dst) for dst in get_adjacency(unit.unit_type, unit.location)}
        available_fleets = {
            fleet.location
            for fleet in self.state.units.values()
            if fleet.unit_type == "F" and is_sea(fleet.location)
        }
        convoy_targets = sorted(convoy_destinations_for_army(unit.location, available_fleets) - direct_bases)
        return [move(unit.unit_type, unit.location, dst) for dst in convoy_targets]

    def _get_move_targets_for_unit(self, unit: Unit) -> list[str]:
        targets = list(sorted(get_adjacency(unit.unit_type, unit.location)))
        if unit.unit_type == "A":
            direct_bases = {base_location(dst) for dst in targets}
            available_fleets = {
                fleet.location
                for fleet in self.state.units.values()
                if fleet.unit_type == "F" and is_sea(fleet.location)
            }
            convoy_targets = sorted(convoy_destinations_for_army(unit.location, available_fleets) - direct_bases)
            targets.extend(convoy_targets)
        return targets
