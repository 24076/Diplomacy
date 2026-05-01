import json
from pathlib import Path

from engine.game import Game
from engine.map_data import SUPPLY_CENTERS
from engine.state import Unit


def make_units(*entries):
    return {
        location: Unit(power=power, unit_type=unit_type, location=location)
        for location, power, unit_type in entries
    }


def blank_supply_owners():
    return {center: None for center in SUPPLY_CENTERS}


def submit_orders(game: Game, per_power: dict[str, list[str]]):
    for power in ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]:
        game.set_orders(power, per_power.get(power, []))


def test_battle_report_exports_markdown_and_json():
    game = Game()
    game.state.units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
        ("PAR", "FRANCE", "A"),
        ("PIC", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
        ("MUN", "GERMANY", "A"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    game.state.supply_center_owners.update(
        {
            "LON": "ENGLAND",
            "EDI": "ENGLAND",
            "LVP": "ENGLAND",
            "PAR": "FRANCE",
            "BRE": "FRANCE",
            "MAR": "FRANCE",
            "BER": "GERMANY",
            "KIE": "GERMANY",
            "MUN": "GERMANY",
            "BEL": None,
        }
    )

    submit_orders(
        game,
        {
            "ENGLAND": ["A WAL - BEL", "F ENG C A WAL - BEL"],
            "FRANCE": ["A PAR - BUR", "A PIC S A PAR - BUR"],
            "GERMANY": ["A BUR H", "A MUN H"],
        },
    )
    game.process()

    submit_orders(game, {"GERMANY": ["A BUR R RUH"]})
    game.process()

    submit_orders(
        game,
        {
            "ENGLAND": ["A BEL H", "F ENG H"],
            "FRANCE": ["A BUR H", "A PIC H"],
            "GERMANY": ["A RUH H", "A MUN H"],
        },
    )
    game.process()

    submit_orders(game, {"ENGLAND": ["BUILD A AT LON"]})
    game.process()

    report = game.get_battle_report_data()
    markdown = game.get_battle_report_markdown()
    output_dir = Path("tests_artifacts")
    written = game.write_battle_report(output_dir, stem="integration_run")

    assert report["total_phases"] == 4
    assert report["phases"][0]["phase_start"] == "SPRING 1901 ORDERS"
    assert report["phases"][0]["phase_end"] == "SPRING 1901 RETREATS"
    assert "ENGLAND gained 1 supply center(s)." in report["phases"][2]["key_events"]
    assert "## Phase 3: FALL 1901 ORDERS -> WINTER 1901 ADJUSTMENTS" in markdown
    assert "A WAL - BEL" in markdown

    json_data = json.loads((output_dir / "integration_run.json").read_text(encoding="utf-8"))
    md_text = (output_dir / "integration_run.md").read_text(encoding="utf-8")

    assert written["json"].endswith("integration_run.json")
    assert written["markdown"].endswith("integration_run.md")
    assert json_data["final_phase"] == "SPRING 1902 ORDERS"
    assert "# Diplomacy Test Run" in md_text


def test_retreat_bounce_disbands_both_units_and_records_phase():
    game = Game()
    game.state.season = "SPRING"
    game.state.phase = "RETREATS"
    game.state.units = make_units(("BUR", "FRANCE", "A"))
    game.state.dislodged_units = {
        "BEL": Unit(power="ENGLAND", unit_type="A", location="BEL"),
        "HOL": Unit(power="GERMANY", unit_type="A", location="HOL"),
    }
    game.state.retreat_options = {
        "BEL": ["RUH"],
        "HOL": ["RUH"],
    }

    submit_orders(
        game,
        {
            "ENGLAND": ["A BEL R RUH"],
            "GERMANY": ["A HOL R RUH"],
        },
    )
    results = game.process()
    report = game.get_battle_report_data()

    assert ("BEL", "DISBAND retreat bounce") in results
    assert ("HOL", "DISBAND retreat bounce") in results
    assert "RUH" not in game.state.units
    assert game.get_current_phase() == "FALL 1901 ORDERS"
    assert report["phases"][0]["phase_start"] == "SPRING 1901 RETREATS"
    assert report["phases"][0]["phase_end"] == "FALL 1901 ORDERS"
    assert "2 disbands completed." in report["phases"][0]["key_events"]
