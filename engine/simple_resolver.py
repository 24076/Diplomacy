from __future__ import annotations

from collections import defaultdict

from engine.convoy import convoy_routes, has_convoy_path
from engine.map_data import base_location, get_adjacency
from engine.order_parser import parse_order
from engine.orders import ConvoyOrder, DisbandOrder, HoldOrder, MoveOrder, Order, RetreatOrder, SupportHoldOrder, SupportMoveOrder


class SimpleResolver:
    def resolve(self, units: dict, all_orders: list[str | Order]) -> dict:
        parsed = [parse_order(order) for order in all_orders]
        order_by_location = {order.location: order for order in parsed if order.location in units}
        convoy_orders = [order for order in parsed if isinstance(order, ConvoyOrder)]
        initial_legal_moves, initial_illegal_reasons, initial_convoy_sources, initial_convoy_routes = self._build_legal_moves(
            units=units,
            all_orders=parsed,
            available_convoy_fleets=None,
        )
        initial_state = self._resolve_moves(
            units=units,
            order_by_location=order_by_location,
            move_orders=initial_legal_moves,
            convoy_move_sources=initial_convoy_sources,
            move_convoy_routes=initial_convoy_routes,
        )
        disrupted_convoy_fleets = {
            location
            for location in initial_state["dislodged_units"]
            if isinstance(order_by_location.get(location), ConvoyOrder)
        }
        available_convoy_fleets = {
            order.location
            for order in convoy_orders
            if order.location not in disrupted_convoy_fleets
        }
        move_orders, illegal_move_reasons, convoy_move_sources, move_convoy_routes = self._build_legal_moves(
            units=units,
            all_orders=parsed,
            available_convoy_fleets=available_convoy_fleets,
            disrupted_convoy_fleets=disrupted_convoy_fleets,
        )
        resolution = self._resolve_moves(
            units=units,
            order_by_location=order_by_location,
            move_orders=move_orders,
            convoy_move_sources=convoy_move_sources,
            move_convoy_routes=move_convoy_routes,
        )
        dislodged_units = resolution["dislodged_units"]
        dislodged_unit_objects = {
            location: units[location]
            for location in dislodged_units
        }
        retreat_options = self._find_retreat_options(
            units=units,
            legal_move_orders=move_orders,
            dislodged_units=dislodged_units,
            successful_moves=resolution["successful_moves"],
        )
        new_positions = self._apply_successful_moves(units, resolution["successful_moves"])
        results = self._build_results(
            units=units,
            order_by_location=order_by_location,
            successful_moves=resolution["successful_moves"],
            cut_supports=resolution["cut_supports"],
            dislodged_units=dislodged_units,
            convoy_orders=convoy_orders,
            legal_moves=move_orders,
            illegal_move_reasons=illegal_move_reasons,
            disrupted_convoy_fleets=disrupted_convoy_fleets,
        )

        return {
            "units": new_positions,
            "results": results,
            "dislodged": dislodged_units,
            "dislodged_units": dislodged_unit_objects,
            "retreat_options": retreat_options,
        }

    def resolve_retreats(
        self,
        units: dict,
        dislodged_units: dict[str, Order],
        retreat_options: dict[str, list[str]],
        retreat_orders: list[str | Order],
    ) -> dict:
        parsed = [parse_order(order) for order in retreat_orders]
        orders_by_location = {
            order.location: order
            for order in parsed
            if isinstance(order, (RetreatOrder, DisbandOrder))
        }
        target_counts = defaultdict(int)

        for order in orders_by_location.values():
            if isinstance(order, RetreatOrder) and order.target in retreat_options.get(order.location, []):
                target_counts[order.target] += 1

        new_positions = dict(units)
        results: list[tuple[str, str]] = []

        for location, unit in dislodged_units.items():
            order = orders_by_location.get(location)
            if isinstance(order, RetreatOrder) and order.target in retreat_options.get(location, []):
                if target_counts[order.target] == 1:
                    unit.location = order.target
                    new_positions[order.target] = unit
                    results.append((location, f"RETREAT {order.target}"))
                else:
                    results.append((location, "DISBAND retreat bounce"))
                continue

            if isinstance(order, DisbandOrder):
                results.append((location, "DISBAND"))
            else:
                results.append((location, "DISBAND no retreat"))

        return {"units": new_positions, "results": results}

    def _build_legal_moves(
        self,
        units: dict,
        all_orders: list[Order],
        available_convoy_fleets: set[str] | None,
        disrupted_convoy_fleets: set[str] | None = None,
    ) -> tuple[list[MoveOrder], dict[str, str], set[str], dict[str, list[tuple[str, ...]]]]:
        move_orders: list[MoveOrder] = []
        reasons: dict[str, str] = {}
        convoy_move_sources: set[str] = set()
        move_convoy_routes: dict[str, list[tuple[str, ...]]] = {}

        for order in all_orders:
            if not isinstance(order, MoveOrder):
                continue
            legal, reason, uses_convoy, routes = self._move_legality(
                order=order,
                units=units,
                all_orders=all_orders,
                available_convoy_fleets=available_convoy_fleets,
                disrupted_convoy_fleets=disrupted_convoy_fleets or set(),
            )
            if legal:
                move_orders.append(order)
                if uses_convoy:
                    convoy_move_sources.add(order.location)
                    move_convoy_routes[order.location] = routes
            else:
                reasons[order.location] = reason

        return move_orders, reasons, convoy_move_sources, move_convoy_routes

    def _move_legality(
        self,
        order: MoveOrder,
        units: dict,
        all_orders: list[Order],
        available_convoy_fleets: set[str] | None,
        disrupted_convoy_fleets: set[str],
    ) -> tuple[bool, str, bool, list[tuple[str, ...]]]:
        direct_move = order.target in get_adjacency(order.unit_type, order.location)
        if order.unit_type != "A":
            if direct_move and not order.via_convoy:
                return True, "ok", False, []
            return False, f"FAIL {order.target} invalid", False, []
        if order.unit_type == "A" and order.location in units:
            all_convoy_fleets = {
                convoy_order.location
                for convoy_order in all_orders
                if isinstance(convoy_order, ConvoyOrder)
                and convoy_order.convoyed_location == order.location
                and convoy_order.target == order.target
            }
            unit = units[order.location]
            has_own_convoy = any(
                units.get(fleet) is not None and units[fleet].power == unit.power
                for fleet in all_convoy_fleets
            )
            routes = convoy_routes(
                order.location,
                order.target,
                all_orders,
                available_fleets=available_convoy_fleets,
            )
            if direct_move and not order.via_convoy and not has_own_convoy:
                return True, "ok", False, []
            if routes:
                return True, "ok", True, routes
            if disrupted_convoy_fleets & all_convoy_fleets:
                return False, f"FAIL {order.target} convoy disrupted", False, []
        return False, f"FAIL {order.target} invalid", False, []

    def _resolve_moves(
        self,
        units: dict,
        order_by_location: dict[str, Order],
        move_orders: list[MoveOrder],
        convoy_move_sources: set[str],
        move_convoy_routes: dict[str, list[tuple[str, ...]]],
    ) -> dict:
        attacks_by_target = defaultdict(list)

        for order in move_orders:
            attacks_by_target[order.target].append(order)

        reciprocal_pairs = self._reciprocal_pairs(order_by_location, move_orders)
        cut_supports: set[str] = set()

        while True:
            cut_supports |= self._find_cut_supports(
                units,
                move_orders,
                order_by_location,
                move_convoy_routes,
            )
            support_hold_map, support_move_map = self._collect_supports(
                units=units,
                order_by_location=order_by_location,
                cut_supports=cut_supports,
            )

            move_strengths = {
                order.location: 1 + support_move_map.get((order.location, order.target), 0)
                for order in move_orders
            }
            defense_strengths = self._build_defense_strengths(
                units=units,
                order_by_location=order_by_location,
                support_hold_map=support_hold_map,
            )
            cycle_successes = self._find_cycle_successes(
                units=units,
                move_orders=move_orders,
                attacks_by_target=attacks_by_target,
                move_strengths=move_strengths,
                reciprocal_pairs=reciprocal_pairs,
            )
            success_cache: dict[str, bool] = {}

            def move_succeeds(order: MoveOrder) -> bool:
                cached = success_cache.get(order.location)
                if cached is not None:
                    return cached

                if order.location in cycle_successes:
                    success_cache[order.location] = True
                    return True

                if not self._is_unique_strongest(order, attacks_by_target, move_strengths):
                    success_cache[order.location] = False
                    return False

                reciprocal = reciprocal_pairs.get(order.location)
                if reciprocal is not None:
                    occupant = units.get(order.target)
                    if occupant is not None and occupant.power == units[order.location].power:
                        success_cache[order.location] = False
                        return False
                    if (
                        order.location in convoy_move_sources
                        or reciprocal.location in convoy_move_sources
                    ):
                        success_cache[order.location] = True
                        return True
                    opponent_strength = move_strengths[reciprocal.location]
                    if move_strengths[order.location] <= opponent_strength:
                        success_cache[order.location] = False
                        return False
                    success_cache[order.location] = True
                    return True

                occupant = units.get(order.target)
                if occupant is None:
                    success_cache[order.location] = True
                    return True

                occupant_order = order_by_location.get(order.target)
                occupant_vacates = False
                if isinstance(occupant_order, MoveOrder) and occupant_order.location not in reciprocal_pairs:
                    occupant_vacates = move_succeeds(occupant_order)

                if occupant_vacates:
                    success_cache[order.location] = True
                    return True

                if occupant.power == units[order.location].power:
                    success_cache[order.location] = False
                    return False

                success_cache[order.location] = (
                    move_strengths[order.location] > defense_strengths.get(order.target, 1)
                )
                return success_cache[order.location]

            successful_moves = {order.location: order for order in move_orders if move_succeeds(order)}
            dislodged_units = self._find_dislodged_units(
                units=units,
                order_by_location=order_by_location,
                successful_moves=successful_moves,
                reciprocal_pairs=reciprocal_pairs,
            )
            expanded_cut_supports = cut_supports | {
                location
                for location in dislodged_units
                if isinstance(order_by_location.get(location), (SupportHoldOrder, SupportMoveOrder))
            }
            if expanded_cut_supports == cut_supports:
                break
            cut_supports = expanded_cut_supports
        return {
            "successful_moves": successful_moves,
            "dislodged_units": dislodged_units,
            "cut_supports": cut_supports,
        }

    def _find_cut_supports(
        self,
        units: dict,
        move_orders: list[MoveOrder],
        order_by_location: dict[str, Order],
        move_convoy_routes: dict[str, list[tuple[str, ...]]],
    ) -> set[str]:
        cut_supports: set[str] = set()

        for order in order_by_location.values():
            if not isinstance(order, (SupportHoldOrder, SupportMoveOrder)):
                continue

            immune_from = order.target if isinstance(order, SupportMoveOrder) else None
            for attack in move_orders:
                if attack.target != order.location:
                    continue
                if self._convoyed_attack_support_exception(attack, order, move_convoy_routes):
                    continue
                if immune_from is not None and attack.location == immune_from:
                    continue
                attacker = units.get(attack.location)
                supporter = units.get(order.location)
                if (
                    attacker is not None
                    and supporter is not None
                    and attacker.power == supporter.power
                ):
                    continue
                cut_supports.add(order.location)
                break

        return cut_supports

    def _convoyed_attack_support_exception(
        self,
        attack: MoveOrder,
        support_order: Order,
        move_convoy_routes: dict[str, list[tuple[str, ...]]],
    ) -> bool:
        if attack.location not in move_convoy_routes:
            return False
        if not isinstance(support_order, SupportMoveOrder):
            return False
        if support_order.location != attack.target:
            return False
        targeted_fleet = support_order.target
        routes = move_convoy_routes[attack.location]
        if not any(targeted_fleet in route for route in routes):
            return False
        return all(targeted_fleet in route for route in routes)

    def _collect_supports(
        self,
        units: dict,
        order_by_location: dict[str, Order],
        cut_supports: set[str],
    ) -> tuple[dict[str, int], dict[tuple[str, str], int]]:
        support_hold_map: dict[str, int] = defaultdict(int)
        support_move_map: dict[tuple[str, str], int] = defaultdict(int)

        for order in order_by_location.values():
            if order.location in cut_supports:
                continue

            if isinstance(order, SupportHoldOrder):
                supported_unit = units.get(order.supported_location)
                supported_order = order_by_location.get(order.supported_location)
                if supported_unit is None:
                    continue
                if supported_unit.unit_type != order.supported_unit_type:
                    continue
                if isinstance(supported_order, MoveOrder):
                    continue
                support_hold_map[order.supported_location] += 1
                continue

            if isinstance(order, SupportMoveOrder):
                supported_unit = units.get(order.supported_location)
                supported_order = order_by_location.get(order.supported_location)
                if supported_unit is None or not isinstance(supported_order, MoveOrder):
                    continue
                if supported_unit.unit_type != order.supported_unit_type:
                    continue
                if supported_order.target != order.target:
                    continue
                target_unit = units.get(order.target)
                supporter = units.get(order.location)
                if (
                    target_unit is not None
                    and supporter is not None
                    and target_unit.power == supporter.power
                ):
                    continue
                support_move_map[(order.supported_location, order.target)] += 1

        return dict(support_hold_map), dict(support_move_map)

    def _build_defense_strengths(
        self,
        units: dict,
        order_by_location: dict[str, Order],
        support_hold_map: dict[str, int],
    ) -> dict[str, int]:
        defense_strengths: dict[str, int] = {}
        for location in units:
            order = order_by_location.get(location)
            support_bonus = 0 if isinstance(order, MoveOrder) else support_hold_map.get(location, 0)
            defense_strengths[location] = 1 + support_bonus
        return defense_strengths

    def _reciprocal_pairs(
        self,
        order_by_location: dict[str, Order],
        move_orders: list[MoveOrder],
    ) -> dict[str, MoveOrder]:
        reciprocal: dict[str, MoveOrder] = {}
        for order in move_orders:
            counter = order_by_location.get(order.target)
            if (
                isinstance(counter, MoveOrder)
                and counter.target == order.location
                and counter.location != order.location
            ):
                reciprocal[order.location] = counter
        return reciprocal

    def _find_cycle_successes(
        self,
        units: dict,
        move_orders: list[MoveOrder],
        attacks_by_target: dict[str, list[MoveOrder]],
        move_strengths: dict[str, int],
        reciprocal_pairs: dict[str, MoveOrder],
    ) -> set[str]:
        move_by_source = {order.location: order for order in move_orders}
        processed: set[str] = set()
        successful_cycles: set[str] = set()

        for order in move_orders:
            if order.location in processed or order.location in reciprocal_pairs:
                continue

            path: list[str] = []
            index_by_location: dict[str, int] = {}
            current = order

            while True:
                if current.location in reciprocal_pairs:
                    break
                if current.location in index_by_location:
                    cycle_locations = path[index_by_location[current.location] :]
                    if len(cycle_locations) > 2 and self._cycle_can_succeed(
                        cycle_locations=cycle_locations,
                        move_by_source=move_by_source,
                        attacks_by_target=attacks_by_target,
                        move_strengths=move_strengths,
                    ):
                        successful_cycles.update(cycle_locations)
                    break
                if current.location in processed:
                    break

                index_by_location[current.location] = len(path)
                path.append(current.location)

                target_occupant = units.get(current.target)
                if target_occupant is None:
                    break
                next_order = move_by_source.get(current.target)
                if not isinstance(next_order, MoveOrder):
                    break
                current = next_order

            processed.update(path)

        return successful_cycles

    def _cycle_can_succeed(
        self,
        cycle_locations: list[str],
        move_by_source: dict[str, MoveOrder],
        attacks_by_target: dict[str, list[MoveOrder]],
        move_strengths: dict[str, int],
    ) -> bool:
        cycle_set = set(cycle_locations)
        for location in cycle_locations:
            order = move_by_source[location]
            attacks = attacks_by_target.get(order.target, [])
            own_strength = move_strengths[location]
            for attack in attacks:
                if attack.location == location:
                    continue
                if attack.location in cycle_set:
                    if move_strengths[attack.location] >= own_strength:
                        return False
                elif move_strengths[attack.location] >= own_strength:
                    return False
            if not self._is_unique_strongest(order, attacks_by_target, move_strengths):
                return False
        return True

    def _is_unique_strongest(
        self,
        order: MoveOrder,
        attacks_by_target: dict[str, list[MoveOrder]],
        move_strengths: dict[str, int],
    ) -> bool:
        attacks = attacks_by_target.get(order.target, [])
        own_strength = move_strengths[order.location]
        strongest = max(move_strengths[attack.location] for attack in attacks)
        if own_strength != strongest:
            return False
        return sum(1 for attack in attacks if move_strengths[attack.location] == strongest) == 1

    def _find_dislodged_units(
        self,
        units: dict,
        order_by_location: dict[str, Order],
        successful_moves: dict[str, MoveOrder],
        reciprocal_pairs: dict[str, MoveOrder],
    ) -> dict[str, str]:
        dislodged: dict[str, str] = {}

        for order in successful_moves.values():
            target = order.target
            occupant = units.get(target)
            if occupant is None:
                continue

            occupant_order = order_by_location.get(target)
            occupant_vacated = False
            if isinstance(occupant_order, MoveOrder):
                occupant_vacated = target in successful_moves and occupant_order.target != order.location
                if target in reciprocal_pairs and target in successful_moves:
                    occupant_vacated = False

            if not occupant_vacated:
                dislodged[target] = order.location

        return dislodged

    def _apply_successful_moves(self, units: dict, successful_moves: dict[str, MoveOrder]) -> dict:
        new_positions = dict(units)

        for source in successful_moves:
            new_positions.pop(source, None)

        for order in successful_moves.values():
            unit = units[order.location]
            unit.location = order.target
            new_positions.pop(order.target, None)
            new_positions[order.target] = unit

        return new_positions

    def _find_retreat_options(
        self,
        units: dict,
        legal_move_orders: list[MoveOrder],
        dislodged_units: dict[str, str],
        successful_moves: dict[str, MoveOrder],
    ) -> dict[str, list[str]]:
        occupied_after_moves = {base_location(location) for location in units}
        occupied_after_moves -= {base_location(location) for location in successful_moves}
        occupied_after_moves |= {base_location(order.target) for order in successful_moves.values()}
        attacks_by_destination = defaultdict(int)
        for order in legal_move_orders:
            attacks_by_destination[base_location(order.target)] += 1

        successful_destinations = {
            base_location(order.target)
            for order in successful_moves.values()
        }
        standoff_vacancies = {
            destination
            for destination, count in attacks_by_destination.items()
            if count > 1
            and destination not in successful_destinations
            and destination not in occupied_after_moves
        }

        retreat_options: dict[str, list[str]] = {}
        for location, attacker_source in dislodged_units.items():
            unit = units[location]
            options = []
            for neighbor in sorted(get_adjacency(unit.unit_type, location)):
                neighbor_base = base_location(neighbor)
                if neighbor_base == base_location(attacker_source):
                    continue
                if neighbor_base in occupied_after_moves:
                    continue
                if neighbor_base in standoff_vacancies:
                    continue
                options.append(neighbor)
            retreat_options[location] = options
        return retreat_options

    def _build_results(
        self,
        units: dict,
        order_by_location: dict[str, Order],
        successful_moves: dict[str, MoveOrder],
        cut_supports: set[str],
        dislodged_units: dict[str, str],
        convoy_orders: list[ConvoyOrder],
        legal_moves: list[MoveOrder],
        illegal_move_reasons: dict[str, str],
        disrupted_convoy_fleets: set[str],
    ) -> list[tuple[str, str]]:
        results: list[tuple[str, str]] = []
        legal_move_sources = {order.location for order in legal_moves}

        for location in units:
            order = order_by_location.get(location)
            if isinstance(order, MoveOrder):
                if location not in legal_move_sources:
                    results.append((location, illegal_move_reasons.get(location, f"FAIL {order.target} invalid")))
                    continue
                if location in successful_moves:
                    results.append((location, f"MOVE {order.target}"))
                else:
                    results.append((location, f"BOUNCE {order.target}"))
                continue

            if isinstance(order, SupportHoldOrder):
                if location in cut_supports:
                    results.append((location, "SUPPORT CUT"))
                else:
                    results.append((location, "SUPPORT HOLD"))
                continue

            if isinstance(order, SupportMoveOrder):
                if location in cut_supports:
                    results.append((location, "SUPPORT CUT"))
                else:
                    results.append((location, f"SUPPORT MOVE {order.target}"))
                continue

            if isinstance(order, HoldOrder):
                results.append((location, "DISLODGED" if location in dislodged_units else "HOLD"))
                continue

            if isinstance(order, ConvoyOrder):
                if location in disrupted_convoy_fleets:
                    results.append((location, "CONVOY DISRUPTED"))
                else:
                    results.append((location, "CONVOY"))
                continue

            results.append((location, "HOLD"))

        return results
