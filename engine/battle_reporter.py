from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engine.map_data import POWERS
from engine.order_formatter import format_order
from engine.orders import Order
from engine.state import Unit


@dataclass
class PhaseSnapshot:
    phase: str
    supply_centers: dict[str, int]
    unit_counts: dict[str, int]
    units: dict[str, dict[str, str]]
    winner: str | None


@dataclass
class PhaseReport:
    phase_index: int
    phase_start: str
    phase_end: str
    phase_summary: list[str]
    submitted_orders: dict[str, list[str]]
    results: list[dict[str, str]]
    key_events: list[str]
    dislodged_units: list[str]
    retreat_options: dict[str, list[str]]
    result_groups: dict[str, list[str]]
    supply_center_changes: list[str]
    unit_count_changes: list[str]
    position_changes: list[str]
    snapshot_before: PhaseSnapshot
    snapshot_after: PhaseSnapshot


@dataclass
class BattleReport:
    game_name: str
    winner: str | None
    total_phases: int
    final_phase: str
    phases: list[PhaseReport] = field(default_factory=list)


class BattleReporter:
    def __init__(self, game_name: str = "Diplomacy Test Run"):
        self.game_name = game_name
        self._phases: list[PhaseReport] = []

    def snapshot(self, game) -> PhaseSnapshot:
        units = {
            location: {
                "power": unit.power,
                "unit_type": unit.unit_type,
                "location": unit.location,
            }
            for location, unit in sorted(game.state.units.items())
        }
        return PhaseSnapshot(
            phase=game.get_current_phase(),
            supply_centers=game.get_supply_center_counts(),
            unit_counts=self._unit_counts(game.state.units),
            units=units,
            winner=game.state.winner,
        )

    def record_phase(
        self,
        *,
        phase_start: str,
        phase_end: str,
        submitted_orders: dict[str, list[Order]],
        results: list[tuple[str, str]],
        snapshot_before: PhaseSnapshot,
        snapshot_after: PhaseSnapshot,
        dislodged_units: dict[str, Unit],
        retreat_options: dict[str, list[str]],
    ) -> None:
        self._phases.append(
            PhaseReport(
                phase_index=len(self._phases) + 1,
                phase_start=phase_start,
                phase_end=phase_end,
                phase_summary=self._build_phase_summary(
                    phase_start=phase_start,
                    phase_end=phase_end,
                    results=results,
                    before=snapshot_before,
                    after=snapshot_after,
                    dislodged_units=dislodged_units,
                    retreat_options=retreat_options,
                ),
                submitted_orders={
                    power: [format_order(order) for order in orders]
                    for power, orders in sorted(submitted_orders.items())
                },
                results=[
                    {"location": location, "result": outcome}
                    for location, outcome in results
                ],
                key_events=self._build_key_events(
                    phase_start=phase_start,
                    phase_end=phase_end,
                    results=results,
                    before=snapshot_before,
                    after=snapshot_after,
                    dislodged_units=dislodged_units,
                ),
                dislodged_units=sorted(dislodged_units),
                retreat_options={loc: list(options) for loc, options in sorted(retreat_options.items())},
                result_groups=self._group_results(results),
                supply_center_changes=self._describe_count_changes(
                    snapshot_before.supply_centers,
                    snapshot_after.supply_centers,
                    label_suffix=" supply center(s)",
                ),
                unit_count_changes=self._describe_count_changes(
                    snapshot_before.unit_counts,
                    snapshot_after.unit_counts,
                    label_suffix=" unit(s)",
                ),
                position_changes=self._describe_position_changes(snapshot_before, snapshot_after),
                snapshot_before=snapshot_before,
                snapshot_after=snapshot_after,
            )
        )

    def build_report(self, game) -> BattleReport:
        return BattleReport(
            game_name=self.game_name,
            winner=game.state.winner,
            total_phases=len(self._phases),
            final_phase=game.get_current_phase(),
            phases=list(self._phases),
        )

    def to_dict(self, game) -> dict:
        return asdict(self.build_report(game))

    def to_json(self, game) -> str:
        return json.dumps(self.to_dict(game), indent=2, ensure_ascii=False)

    def to_markdown(self, game) -> str:
        report = self.build_report(game)
        lines = [
            f"# {report.game_name}",
            "",
            f"- Final Phase: {report.final_phase}",
            f"- Winner: {report.winner or 'None'}",
            f"- Total Recorded Phases: {report.total_phases}",
            "",
        ]

        for phase in report.phases:
            lines.extend(
                [
                    f"## Phase {phase.phase_index}: {phase.phase_start} -> {phase.phase_end}",
                    "",
                    "### Summary",
                ]
            )
            for item in phase.phase_summary:
                lines.append(f"- {item}")

            lines.extend(
                [
                    "",
                    "### Orders",
                ]
            )
            if phase.submitted_orders:
                for power, orders in phase.submitted_orders.items():
                    rendered = ", ".join(orders) if orders else "No submitted orders"
                    lines.append(f"- {power}: {rendered}")
            else:
                lines.append("- No submitted orders")

            lines.extend(["", "### Results"])
            for item in phase.results:
                lines.append(f"- {item['location']}: {item['result']}")

            lines.extend(["", "### Result Breakdown"])
            for title, items in (
                ("Successful actions", phase.result_groups["success"]),
                ("Contested or failed actions", phase.result_groups["failed"]),
                ("Supports and convoys", phase.result_groups["support"]),
                ("Holds and passive outcomes", phase.result_groups["hold"]),
            ):
                rendered = "; ".join(items) if items else "None"
                lines.append(f"- {title}: {rendered}")

            lines.extend(["", "### Key Events"])
            if phase.key_events:
                for event in phase.key_events:
                    lines.append(f"- {event}")
            else:
                lines.append("- No major events recorded")

            lines.extend(["", "### Position Changes"])
            if phase.position_changes:
                for item in phase.position_changes:
                    lines.append(f"- {item}")
            else:
                lines.append("- No unit position changes")

            if phase.retreat_options:
                lines.extend(["", "### Retreat Options"])
                for location, options in phase.retreat_options.items():
                    rendered = ", ".join(options) if options else "No legal retreat"
                    lines.append(f"- {location}: {rendered}")

            lines.extend(
                [
                    "",
                    "### Supply Centers",
                    f"- Before: {self._render_counts(phase.snapshot_before.supply_centers)}",
                    f"- After: {self._render_counts(phase.snapshot_after.supply_centers)}",
                    f"- Delta: {self._render_delta_list(phase.supply_center_changes)}",
                    "",
                    "### Units",
                    f"- Before: {self._render_counts(phase.snapshot_before.unit_counts)}",
                    f"- After: {self._render_counts(phase.snapshot_after.unit_counts)}",
                    f"- Delta: {self._render_delta_list(phase.unit_count_changes)}",
                    "",
                ]
            )

        return "\n".join(lines).strip() + "\n"

    def write_files(self, game, output_dir: str | Path, stem: str = "battle_report") -> dict[str, str]:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        json_path = output_path / f"{stem}.json"
        md_path = output_path / f"{stem}.md"
        json_path.write_text(self.to_json(game), encoding="utf-8")
        md_path.write_text(self.to_markdown(game), encoding="utf-8")

        return {"json": str(json_path), "markdown": str(md_path)}

    def _build_key_events(
        self,
        *,
        phase_start: str,
        phase_end: str,
        results: list[tuple[str, str]],
        before: PhaseSnapshot,
        after: PhaseSnapshot,
        dislodged_units: dict[str, Unit],
    ) -> list[str]:
        events: list[str] = []

        move_count = sum(1 for _, outcome in results if outcome.startswith("MOVE "))
        retreat_count = sum(1 for _, outcome in results if outcome.startswith("RETREAT "))
        build_count = sum(1 for _, outcome in results if outcome.startswith("BUILD "))
        disband_count = sum(1 for _, outcome in results if outcome.startswith("DISBAND"))

        if move_count:
            events.append(f"{move_count} successful moves resolved.")
        if dislodged_units:
            events.append(f"Units dislodged at {', '.join(sorted(dislodged_units))}.")
        if retreat_count:
            events.append(f"{retreat_count} retreats completed.")
        if build_count:
            events.append(f"{build_count} builds completed.")
        if disband_count:
            events.append(f"{disband_count} disbands completed.")

        for power in POWERS:
            delta = after.supply_centers.get(power, 0) - before.supply_centers.get(power, 0)
            if delta > 0:
                events.append(f"{power} gained {delta} supply center(s).")
            elif delta < 0:
                events.append(f"{power} lost {-delta} supply center(s).")

        if after.winner and after.winner != before.winner:
            events.append(f"{after.winner} wins the game in {phase_end}.")

        if not events and phase_start != phase_end:
            events.append(f"Phase advanced from {phase_start} to {phase_end}.")

        return events

    def _build_phase_summary(
        self,
        *,
        phase_start: str,
        phase_end: str,
        results: list[tuple[str, str]],
        before: PhaseSnapshot,
        after: PhaseSnapshot,
        dislodged_units: dict[str, Unit],
        retreat_options: dict[str, list[str]],
    ) -> list[str]:
        summary = []
        successful = sum(
            1
            for _, outcome in results
            if outcome.startswith(("MOVE ", "RETREAT ", "BUILD "))
        )
        failed = sum(
            1
            for _, outcome in results
            if outcome.startswith(("BOUNCE ", "FAIL ", "DISLODGED"))
        )
        summary.append(f"Phase advanced from {phase_start} to {phase_end}.")
        summary.append(f"Successful actions: {successful}; contested or failed actions: {failed}.")

        gains = self._describe_count_changes(before.supply_centers, after.supply_centers, " supply center(s)")
        if gains:
            summary.append(f"Supply center swing: {', '.join(gains)}.")
        else:
            summary.append("Supply center ownership stayed flat this phase.")

        if dislodged_units:
            retreat_text = ", ".join(
                f"{loc} -> {', '.join(options) if options else 'no legal retreat'}"
                for loc, options in sorted(retreat_options.items())
            )
            summary.append(f"Dislodged units: {', '.join(sorted(dislodged_units))}. Retreat map: {retreat_text}.")

        if after.winner and after.winner != before.winner:
            summary.append(f"{after.winner} secured the win at the end of this phase.")
        return summary

    def _group_results(self, results: list[tuple[str, str]]) -> dict[str, list[str]]:
        grouped = {"success": [], "failed": [], "support": [], "hold": []}
        for location, outcome in results:
            item = f"{location} {outcome}"
            if outcome.startswith(("MOVE ", "RETREAT ", "BUILD ")):
                grouped["success"].append(item)
            elif outcome.startswith(("BOUNCE ", "FAIL ", "DISLODGED", "DISBAND")):
                grouped["failed"].append(item)
            elif outcome.startswith(("SUPPORT ", "CONVOY")):
                grouped["support"].append(item)
            else:
                grouped["hold"].append(item)
        return grouped

    def _describe_count_changes(
        self,
        before: dict[str, int],
        after: dict[str, int],
        label_suffix: str,
    ) -> list[str]:
        changes = []
        for power in POWERS:
            delta = after.get(power, 0) - before.get(power, 0)
            if delta > 0:
                changes.append(f"{power} +{delta}{label_suffix}")
            elif delta < 0:
                changes.append(f"{power} {delta}{label_suffix}")
        return changes

    def _describe_position_changes(
        self,
        before: PhaseSnapshot,
        after: PhaseSnapshot,
    ) -> list[str]:
        before_units = before.units
        after_units = after.units
        lines = []

        for location, unit in before_units.items():
            unit_key = (unit["power"], unit["unit_type"], unit["location"])
            if location not in after_units:
                destination = next(
                    (
                        dst
                        for dst, other in after_units.items()
                        if (other["power"], other["unit_type"], other["location"]) == unit_key
                    ),
                    None,
                )
                if destination is not None:
                    lines.append(f"{unit['power']} {unit['unit_type']} moved {location} -> {destination}.")
                else:
                    lines.append(f"{unit['power']} {unit['unit_type']} at {location} left the board.")

        for location, unit in after_units.items():
            unit_key = (unit["power"], unit["unit_type"], unit["location"])
            if location not in before_units:
                existed_before = any(
                    (other["power"], other["unit_type"], other["location"]) == unit_key
                    for other in before_units.values()
                )
                if not existed_before:
                    lines.append(f"{unit['power']} {unit['unit_type']} entered play at {location}.")

        return lines

    def _render_delta_list(self, items: list[str]) -> str:
        return ", ".join(items) if items else "No change"

    def _unit_counts(self, units: dict[str, Unit]) -> dict[str, int]:
        counts = {power: 0 for power in POWERS}
        for unit in units.values():
            counts[unit.power] += 1
        return counts

    def _render_counts(self, counts: dict[str, int]) -> str:
        return ", ".join(f"{power}={counts.get(power, 0)}" for power in POWERS)
