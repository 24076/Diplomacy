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


def submit_empty_orders(game: Game):
    for power in ["AUSTRIA", "ENGLAND", "FRANCE", "GERMANY", "ITALY", "RUSSIA", "TURKEY"]:
        if power not in game.state.submitted_orders:
            game.set_orders(power, [])


def test_fall_updates_supply_centers_and_enters_adjustments():
    game = Game()
    game.state.season = "FALL"
    game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("MAR", "FRANCE", "A"),
        ("BEL", "FRANCE", "A"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    game.state.supply_center_owners.update(
        {"PAR": "FRANCE", "MAR": "FRANCE", "BRE": "FRANCE", "BEL": None}
    )

    submit_empty_orders(game)
    game.process()

    assert game.state.supply_center_owners["BEL"] == "FRANCE"
    assert game.state.season == "WINTER"
    assert game.state.phase == "ADJUSTMENTS"
    assert game.get_adjustment_requirement("FRANCE") == 1


def test_adjustments_build_unit_and_advance_to_next_year():
    game = Game()
    game.state.season = "WINTER"
    game.state.phase = "ADJUSTMENTS"
    game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("MAR", "FRANCE", "A"),
        ("BEL", "FRANCE", "A"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    game.state.supply_center_owners.update(
        {"PAR": "FRANCE", "MAR": "FRANCE", "BRE": "FRANCE", "BEL": "FRANCE"}
    )
    game.state.adjustment_requirements = {"FRANCE": 1}

    game.set_orders("FRANCE", ["BUILD A AT BRE"])
    results = game.process()

    assert ("BRE", "BUILD A") in results
    assert game.state.year == 1902
    assert game.state.season == "SPRING"
    assert game.state.phase == "ORDERS"
    assert game.state.units["BRE"].power == "FRANCE"


def test_adjustments_cannot_build_in_occupied_split_coast_home_center():
    game = Game()
    game.state.season = "WINTER"
    game.state.phase = "ADJUSTMENTS"
    game.state.units = make_units(
        ("MOS", "RUSSIA", "A"),
        ("WAR", "RUSSIA", "A"),
        ("SEV", "RUSSIA", "F"),
        ("STP/SC", "RUSSIA", "F"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    game.state.supply_center_owners.update(
        {
            "MOS": "RUSSIA",
            "WAR": "RUSSIA",
            "SEV": "RUSSIA",
            "STP": "RUSSIA",
            "RUM": "RUSSIA",
        }
    )
    game.state.adjustment_requirements = {"RUSSIA": 1}

    game.set_orders("RUSSIA", ["BUILD A AT STP"])
    results = game.process()

    assert results == []
    assert "STP" not in game.state.units
    assert sorted(loc for loc, unit in game.state.units.items() if unit.power == "RUSSIA") == [
        "MOS",
        "SEV",
        "STP/SC",
        "WAR",
    ]


def test_adjustments_cannot_build_two_units_in_same_split_coast_home_center():
    game = Game()
    game.state.season = "WINTER"
    game.state.phase = "ADJUSTMENTS"
    game.state.units = make_units(
        ("MOS", "RUSSIA", "A"),
        ("WAR", "RUSSIA", "A"),
        ("SEV", "RUSSIA", "F"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    game.state.supply_center_owners.update(
        {
            "MOS": "RUSSIA",
            "WAR": "RUSSIA",
            "SEV": "RUSSIA",
            "STP": "RUSSIA",
            "RUM": "RUSSIA",
            "SWE": "RUSSIA",
        }
    )
    game.state.adjustment_requirements = {"RUSSIA": 2}

    game.set_orders("RUSSIA", ["BUILD A AT STP", "BUILD F AT STP/NC"])
    results = game.process()

    assert len(results) == 1
    assert results[0] in {("STP", "BUILD A"), ("STP/NC", "BUILD F")}
    assert len([loc for loc, unit in game.state.units.items() if unit.power == "RUSSIA"]) == 4
    assert not {"STP", "STP/NC"} <= set(game.state.units.keys())


def test_adjustments_disband_unit_and_advance_to_next_year():
    game = Game()
    game.state.season = "WINTER"
    game.state.phase = "ADJUSTMENTS"
    game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("MAR", "FRANCE", "A"),
        ("BRE", "FRANCE", "A"),
        ("BEL", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
    )
    game.state.supply_center_owners = blank_supply_owners()
    game.state.supply_center_owners.update(
        {"PAR": "FRANCE", "MAR": "FRANCE", "BRE": "FRANCE", "BEL": "FRANCE"}
    )
    game.state.adjustment_requirements = {"FRANCE": -1}

    game.set_orders("FRANCE", ["DISBAND A AT GAS"])
    results = game.process()

    assert ("GAS", "DISBAND A") in results
    assert "GAS" not in game.state.units
    assert game.state.year == 1902
    assert game.state.season == "SPRING"
    assert game.state.phase == "ORDERS"


def test_adjustments_missing_disband_uses_deterministic_fallback_order():
    game = Game()
    game.state.season = "WINTER"
    game.state.phase = "ADJUSTMENTS"
    game.state.units = make_units(
        ("LON", "ENGLAND", "F"),
        ("EDI", "ENGLAND", "F"),
        ("LVP", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
    )
    game.state.adjustment_requirements = {"ENGLAND": -1}

    results = game.process()

    assert ("ENG", "DISBAND F") in results
    assert "ENG" not in game.state.units
    assert game.state.phase == "ORDERS"


def test_fall_victory_marks_game_complete():
    game = Game()
    game.state.season = "FALL"
    game.state.units = make_units(("PAR", "FRANCE", "A"))
    game.state.supply_center_owners = blank_supply_owners()
    winning_centers = sorted(SUPPLY_CENTERS)[:18]
    for center in winning_centers:
        game.state.supply_center_owners[center] = "FRANCE"

    submit_empty_orders(game)
    game.process()

    assert game.state.winner == "FRANCE"
    assert game.state.phase == "COMPLETED"
