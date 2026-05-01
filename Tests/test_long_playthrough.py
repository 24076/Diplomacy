from engine.game import Game
from engine.map_data import SUPPLY_CENTERS
from engine.state import Unit
from tools.run_full_test_and_report import play_multi_year_full_flow, play_rulebook_normal_flow


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


def test_long_playthrough_convoy_retreat_build_and_next_spring():
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
    spring_orders_results = game.process()

    assert game.get_current_phase() == "SPRING 1901 RETREATS"
    assert ("WAL", "MOVE BEL") in spring_orders_results
    assert ("PAR", "MOVE BUR") in spring_orders_results
    assert set(game.state.dislodged_units) == {"BUR"}
    assert "RUH" in game.state.retreat_options["BUR"]

    submit_orders(game, {"GERMANY": ["A BUR R RUH"]})
    spring_retreat_results = game.process()

    assert game.get_current_phase() == "FALL 1901 ORDERS"
    assert ("BUR", "RETREAT RUH") in spring_retreat_results
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

    submit_orders(
        game,
        {
            "ENGLAND": ["A LON - YOR", "A BEL H", "F ENG H"],
            "FRANCE": ["A BUR H", "A PIC H"],
            "GERMANY": ["A RUH H", "A MUN H"],
        },
    )
    next_spring_results = game.process()

    assert game.get_current_phase() == "FALL 1902 ORDERS"
    assert ("LON", "MOVE YOR") in next_spring_results
    assert game.state.units["YOR"].power == "ENGLAND"


def test_long_playthrough_forced_winter_disband_cycle():
    game = Game()
    game.state.year = 1903
    game.state.season = "FALL"
    game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("BRE", "FRANCE", "F"),
        ("MAR", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    game.state.supply_center_owners.update(
        {
            "PAR": "FRANCE",
            "BRE": "FRANCE",
            "MAR": "FRANCE",
        }
    )

    submit_orders(game, {"FRANCE": ["A PAR H", "F BRE H", "A MAR H", "A GAS H"]})
    fall_results = game.process()

    assert game.get_current_phase() == "WINTER 1903 ADJUSTMENTS"
    assert ("GAS", "HOLD") in fall_results
    assert game.get_adjustment_requirement("FRANCE") == -1

    submit_orders(game, {"FRANCE": ["DISBAND A AT GAS"]})
    winter_results = game.process()

    assert game.get_current_phase() == "SPRING 1904 ORDERS"
    assert ("GAS", "DISBAND A") in winter_results
    assert "GAS" not in game.state.units


def test_long_playthrough_multi_year_reaches_eighteen_supply_centers():
    game = play_multi_year_full_flow(Game())
    report = game.get_battle_report_data()

    assert game.get_current_phase() == "FALL 1903 COMPLETED"
    assert game.state.winner == "ENGLAND"
    assert game.get_supply_center_counts()["ENGLAND"] == 18
    assert report["total_phases"] == 10
    assert report["phases"][0]["phase_start"] == "SPRING 1901 ORDERS"
    assert report["phases"][-1]["phase_end"] == "FALL 1903 COMPLETED"


def test_long_playthrough_rulebook_normal_flow_reaches_winter_1902_adjustments():
    game = play_rulebook_normal_flow(Game())
    report = game.get_battle_report_data()

    assert game.get_current_phase() == "SPRING 1903 ORDERS"
    assert game.state.winner is None
    assert game.get_supply_center_counts()["AUSTRIA"] == 5
    assert game.get_supply_center_counts()["ENGLAND"] == 6
    assert game.get_supply_center_counts()["GERMANY"] == 2
    assert report["total_phases"] == 7
    assert report["phases"][4]["phase_end"] == "FALL 1902 RETREATS"
    assert "Units dislodged at HOL, MUN." in report["phases"][4]["key_events"]
