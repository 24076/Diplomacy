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


def test_pdf_rules_complete_year_flow_and_report_generation():
    # Aligned to the PDF's yearly sequence:
    # Spring orders -> Spring retreats -> Fall orders -> Winter adjustments.
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
    spring_results = game.process()

    assert game.get_current_phase() == "SPRING 1901 RETREATS"
    assert ("WAL", "MOVE BEL") in spring_results
    assert ("PAR", "MOVE BUR") in spring_results
    assert game.state.supply_center_owners["BEL"] is None

    submit_orders(game, {"GERMANY": ["A BUR R RUH"]})
    retreat_results = game.process()

    assert game.get_current_phase() == "FALL 1901 ORDERS"
    assert ("BUR", "RETREAT RUH") in retreat_results
    assert game.state.units["RUH"].power == "GERMANY"

    submit_orders(
        game,
        {
            "ENGLAND": ["A BEL H", "F ENG H"],
            "FRANCE": ["A BUR H", "A PIC H"],
            "GERMANY": ["A RUH H", "A MUN H"],
        },
    )
    fall_results = game.process()

    assert game.get_current_phase() == "WINTER 1901 ADJUSTMENTS"
    assert ("BEL", "HOLD") in fall_results
    assert game.state.supply_center_owners["BEL"] == "ENGLAND"
    assert game.get_adjustment_requirement("ENGLAND") == 2

    submit_orders(game, {"ENGLAND": ["BUILD A AT LON"]})
    winter_results = game.process()

    assert game.get_current_phase() == "SPRING 1902 ORDERS"
    assert ("LON", "BUILD A") in winter_results
    assert game.state.units["LON"].power == "ENGLAND"

    output_dir = Path("tests_artifacts")
    written = game.write_battle_report(output_dir, stem="pdf_rules_full_flow")
    markdown = (output_dir / "pdf_rules_full_flow.md").read_text(encoding="utf-8")

    assert written["markdown"].endswith("pdf_rules_full_flow.md")
    assert written["json"].endswith("pdf_rules_full_flow.json")
    assert "SPRING 1901 ORDERS -> SPRING 1901 RETREATS" in markdown
    assert "FALL 1901 ORDERS -> WINTER 1901 ADJUSTMENTS" in markdown
    assert "ENGLAND gained 1 supply center(s)." in markdown
