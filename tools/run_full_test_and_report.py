from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.game import Game
from engine.map_data import SUPPLY_CENTERS
from engine.state import Unit

POWERS = ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]


def make_units(*entries):
    return {
        location: Unit(power=power, unit_type=unit_type, location=location)
        for location, power, unit_type in entries
    }


def blank_supply_owners():
    return {center: None for center in SUPPLY_CENTERS}


def submit_orders(game: Game, per_power: dict[str, list[str]]):
    for power in POWERS:
        game.set_orders(power, per_power.get(power, []))


def play_rulebook_normal_flow(game: Game) -> Game:
    phases = [
        {
            "expected_phase": "SPRING 1901 ORDERS",
            "orders": {
                "AUSTRIA": ["A VIE - GAL", "A BUD - SER", "F TRI - ALB"],
                "ENGLAND": ["F EDI - NTH", "F LON - ENG", "A LVP - YOR"],
                "FRANCE": ["A PAR - BUR", "A MAR - SPA", "F BRE - MID"],
                "GERMANY": ["A BER - KIE", "A MUN - RUH", "F KIE - HOL"],
                "ITALY": ["A VEN H", "A ROM - APU", "F NAP - ION"],
                "RUSSIA": ["A WAR H", "A MOS - UKR", "F SEV H", "F STP/SC H"],
                "TURKEY": ["A CON - BUL", "A SMY H", "F ANK - CON"],
            },
        },
        {
            "expected_phase": "FALL 1901 ORDERS",
            "orders": {
                "AUSTRIA": ["A SER - GRE", "F ALB S A SER - GRE", "A GAL H"],
                "ENGLAND": ["F NTH - NWY", "F ENG - BEL", "A YOR H"],
                "FRANCE": ["A BUR H", "A SPA H", "F MID - POR"],
                "GERMANY": ["A HOL H", "A RUH H", "A KIE H"],
                "ITALY": ["A VEN H", "A APU H", "F ION - TUN"],
                "RUSSIA": ["A WAR H", "A UKR H", "F SEV H", "F STP/SC H"],
                "TURKEY": ["A BUL H", "A SMY H", "F CON H"],
            },
        },
        {
            "expected_phase": "WINTER 1901 ADJUSTMENTS",
            "orders": {
                "AUSTRIA": ["BUILD A AT VIE"],
                "ENGLAND": ["BUILD F AT LON", "BUILD A AT EDI"],
                "FRANCE": ["BUILD A AT PAR", "BUILD F AT BRE"],
                "GERMANY": ["BUILD A AT MUN"],
                "ITALY": ["BUILD A AT ROM"],
                "TURKEY": ["BUILD A AT ANK"],
            },
        },
        {
            "expected_phase": "SPRING 1902 ORDERS",
            "orders": {
                "AUSTRIA": ["A GRE H", "A GAL - BOH", "A VIE - TYR", "F ALB H"],
                "ENGLAND": ["F NWY - NTH", "F BEL H", "A YOR H", "F LON H", "A EDI H"],
                "FRANCE": ["A BUR H", "A SPA H", "F POR H", "A PAR H", "F BRE H"],
                "GERMANY": ["A HOL H", "A RUH H", "A KIE H", "A MUN H"],
                "ITALY": ["A VEN H", "A APU H", "F TUN - ION", "A ROM H"],
                "RUSSIA": ["A WAR H", "A UKR H", "F SEV H", "F STP/SC H"],
                "TURKEY": ["A BUL H", "A SMY H", "F CON H", "A ANK H"],
            },
        },
        {
            "expected_phase": "FALL 1902 ORDERS",
            "orders": {
                "AUSTRIA": ["A BOH - MUN", "A TYR S A BOH - MUN", "A GRE H", "F ALB H"],
                "ENGLAND": ["F BEL - HOL", "F NTH S F BEL - HOL", "A YOR H", "F LON H", "A EDI H"],
                "FRANCE": ["A BUR S F BEL - HOL", "A SPA H", "F POR H", "A PAR H", "F BRE H"],
                "GERMANY": ["A HOL H", "A RUH S A HOL", "A KIE H", "A MUN H"],
                "ITALY": ["A VEN H", "A APU H", "F ION H", "A ROM H"],
                "RUSSIA": ["A WAR H", "A UKR H", "F SEV H", "F STP/SC H"],
                "TURKEY": ["A BUL H", "A SMY H", "F CON H", "A ANK H"],
            },
        },
        {
            "expected_phase": "FALL 1902 RETREATS",
            "orders": {
                "GERMANY": ["A MUN R SIL"],
            },
        },
        {
            "expected_phase": "WINTER 1902 ADJUSTMENTS",
            "orders": {
                "AUSTRIA": ["BUILD A AT TRI"],
                "ENGLAND": ["BUILD A AT LVP"],
                "GERMANY": ["DISBAND A AT RUH"],
            },
        },
    ]

    for phase in phases:
        if game.get_current_phase() != phase["expected_phase"]:
            raise AssertionError(f"Expected {phase['expected_phase']}, got {game.get_current_phase()}")
        submit_orders(game, phase["orders"])
        game.process()

    return game


def play_multi_year_full_flow(game: Game) -> Game:
    game.state.units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
        ("NTH", "ENGLAND", "F"),
        ("YOR", "ENGLAND", "A"),
        ("NWY", "ENGLAND", "A"),
        ("SWE", "ENGLAND", "A"),
        ("STP", "ENGLAND", "A"),
        ("MOS", "ENGLAND", "A"),
        ("WAR", "ENGLAND", "A"),
        ("KIE", "ENGLAND", "A"),
        ("MUN", "ENGLAND", "A"),
        ("PIC", "ENGLAND", "A"),
        ("BRE", "ENGLAND", "F"),
        ("PAR", "ENGLAND", "A"),
        ("MAR", "ENGLAND", "A"),
        ("BEL", "GERMANY", "A"),
        ("HOL", "GERMANY", "A"),
        ("DEN", "GERMANY", "A"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    for center in [
        "LON",
        "EDI",
        "LVP",
        "BRE",
        "PAR",
        "MAR",
        "POR",
        "SPA",
        "NWY",
        "SWE",
        "STP",
        "MOS",
        "WAR",
        "KIE",
        "MUN",
    ]:
        game.state.supply_center_owners[center] = "ENGLAND"
    for center in ["BEL", "HOL", "DEN"]:
        game.state.supply_center_owners[center] = "GERMANY"

    phases = [
        {
            "expected_phase": "SPRING 1901 ORDERS",
            "orders": {
                "ENGLAND": [
                    "A WAL - BEL",
                    "F ENG C A WAL - BEL",
                    "F NTH S A WAL - BEL",
                ],
                "GERMANY": ["A BEL H", "A HOL H", "A DEN H"],
            },
        },
        {
            "expected_phase": "SPRING 1901 RETREATS",
            "orders": {"GERMANY": ["A BEL R BUR"]},
        },
        {
            "expected_phase": "FALL 1901 ORDERS",
            "orders": {"ENGLAND": ["A BEL H"], "GERMANY": ["A BUR H", "A HOL H", "A DEN H"]},
        },
        {
            "expected_phase": "WINTER 1901 ADJUSTMENTS",
            "orders": {"ENGLAND": ["BUILD A AT LON"]},
        },
        {
            "expected_phase": "SPRING 1902 ORDERS",
            "orders": {"ENGLAND": ["A BEL H", "A LON H"], "GERMANY": ["A BUR H", "A HOL H", "A DEN H"]},
        },
        {
            "expected_phase": "FALL 1902 ORDERS",
            "orders": {
                "ENGLAND": ["A BEL - HOL", "F NTH S A BEL - HOL"],
                "GERMANY": ["A BUR H", "A HOL H", "A DEN H"],
            },
        },
        {
            "expected_phase": "FALL 1902 RETREATS",
            "orders": {"GERMANY": ["A HOL R RUH"]},
        },
        {
            "expected_phase": "WINTER 1902 ADJUSTMENTS",
            "orders": {"ENGLAND": ["BUILD A AT EDI"]},
        },
        {
            "expected_phase": "SPRING 1903 ORDERS",
            "orders": {"ENGLAND": ["A HOL H", "A EDI H"], "GERMANY": ["A RUH H"]},
        },
        {
            "expected_phase": "FALL 1903 ORDERS",
            "orders": {"ENGLAND": ["A KIE - DEN", "F NTH S A KIE - DEN"], "GERMANY": ["A RUH H"]},
        },
    ]

    for phase in phases:
        if game.get_current_phase() != phase["expected_phase"]:
            raise AssertionError(f"Expected {phase['expected_phase']}, got {game.get_current_phase()}")
        submit_orders(game, phase["orders"])
        game.process()

    return game


def run_pytest() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def generate_sample_battle_report(output_dir: Path, stem: str = "full_verification") -> dict[str, object]:
    game = Game()
    play_rulebook_normal_flow(game)

    report_paths = game.write_battle_report(output_dir, stem=stem)
    summary = {
        "report_paths": report_paths,
        "final_phase": game.get_current_phase(),
        "winner": game.state.winner,
        "total_phases": game.get_battle_report_data()["total_phases"],
    }

    summary_path = output_dir / f"{stem}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run full tests and generate a sample battle report.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "reports"),
        help="Directory for generated report files.",
    )
    parser.add_argument(
        "--stem",
        default="full_verification",
        help="Base filename for generated artifacts.",
    )
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pytest_result = run_pytest()
    sys.stdout.write(pytest_result.stdout)
    if pytest_result.stderr:
        sys.stderr.write(pytest_result.stderr)
    if pytest_result.returncode != 0:
        return pytest_result.returncode

    summary = generate_sample_battle_report(output_dir=output_dir, stem=args.stem)
    sys.stdout.write(
        "\n".join(
            [
                "",
                "Full verification completed.",
                f"Markdown report: {summary['report_paths']['markdown']}",
                f"JSON report: {summary['report_paths']['json']}",
                f"Summary: {summary['summary_path']}",
            ]
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
