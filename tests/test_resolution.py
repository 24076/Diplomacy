from engine.game import Game
from engine.order_formatter import convoy, support_hold, support_move
from engine.resolution.simple_resolver import SimpleResolver
from engine.state import Unit


def make_units(*entries):
    return {
        location: Unit(power=power, unit_type=unit_type, location=location)
        for location, power, unit_type in entries
    }


def test_supported_attack_dislodges_holding_unit():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
    )

    result = resolver.resolve(
        units,
        ["A PAR - BUR", support_move("A", "GAS", "A", "PAR", "BUR"), "A BUR H"],
    )

    assert "BUR" in result["units"]
    assert result["units"]["BUR"].power == "FRANCE"
    assert result["dislodged"] == {"BUR": "PAR"}


def test_support_is_cut_by_attack_from_other_province():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
        ("MAR", "GERMANY", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A PAR - BUR",
            support_move("A", "GAS", "A", "PAR", "BUR"),
            "A BUR H",
            "A MAR - GAS",
        ],
    )

    assert result["units"]["BUR"].power == "GERMANY"
    assert ("GAS", "SUPPORT CUT") in result["results"]


def test_attack_from_supported_target_does_not_cut_support():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A PAR - BUR",
            support_move("A", "GAS", "A", "PAR", "BUR"),
            "A BUR - GAS",
        ],
    )

    assert result["units"]["BUR"].power == "FRANCE"
    assert ("GAS", "SUPPORT MOVE BUR") in result["results"]


def test_attack_from_supported_target_cuts_support_when_supporter_is_dislodged():
    resolver = SimpleResolver()
    units = make_units(
        ("PRU", "GERMANY", "A"),
        ("SIL", "GERMANY", "A"),
        ("WAR", "RUSSIA", "A"),
        ("BOH", "RUSSIA", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A PRU - WAR",
            support_move("A", "SIL", "A", "PRU", "WAR"),
            "A WAR - SIL",
            support_move("A", "BOH", "A", "WAR", "SIL"),
        ],
    )

    assert result["units"]["WAR"].power == "GERMANY"
    assert result["units"]["SIL"].power == "RUSSIA"
    assert ("SIL", "SUPPORT CUT") in result["results"]


def test_supported_hold_blocks_attack():
    resolver = SimpleResolver()
    units = make_units(
        ("MUN", "GERMANY", "A"),
        ("RUH", "GERMANY", "A"),
        ("BUR", "FRANCE", "A"),
    )

    result = resolver.resolve(
        units,
        ["A BUR - MUN", support_hold("A", "RUH", "A", "MUN"), "A MUN H"],
    )

    assert result["units"]["MUN"].power == "GERMANY"
    assert ("BUR", "BOUNCE MUN") in result["results"]


def test_head_to_head_equal_strength_bounces():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
    )

    result = resolver.resolve(units, ["A PAR - BUR", "A BUR - PAR"])

    assert result["units"]["PAR"].power == "FRANCE"
    assert result["units"]["BUR"].power == "GERMANY"


def test_head_to_head_stronger_attack_wins():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("PIC", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
    )

    result = resolver.resolve(
        units,
        ["A PAR - BUR", support_move("A", "PIC", "A", "PAR", "BUR"), "A BUR - PAR"],
    )

    assert result["units"]["BUR"].power == "FRANCE"
    assert result["dislodged"] == {"BUR": "PAR"}


def test_equal_attacks_on_empty_province_bounce():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("PIC", "ENGLAND", "A"),
    )

    result = resolver.resolve(units, ["A PAR - BUR", "A PIC - BUR"])

    assert "BUR" not in result["units"]
    assert result["units"]["PAR"].power == "FRANCE"
    assert result["units"]["PIC"].power == "ENGLAND"


def test_three_way_rotation_succeeds():
    resolver = SimpleResolver()
    units = make_units(
        ("ANK", "TURKEY", "A"),
        ("CON", "RUSSIA", "A"),
        ("SMY", "ITALY", "A"),
    )

    result = resolver.resolve(units, ["A ANK - CON", "A CON - SMY", "A SMY - ANK"])

    assert result["units"]["CON"].power == "TURKEY"
    assert result["units"]["SMY"].power == "RUSSIA"
    assert result["units"]["ANK"].power == "ITALY"


def test_cannot_dislodge_own_unit():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("PIC", "FRANCE", "A"),
        ("BUR", "FRANCE", "A"),
    )

    result = resolver.resolve(
        units,
        ["A PAR - BUR", support_move("A", "PIC", "A", "PAR", "BUR"), "A BUR H"],
    )

    assert result["units"]["BUR"].power == "FRANCE"
    assert result["dislodged"] == {}


def test_single_fleet_convoy_allows_non_adjacent_army_move():
    resolver = SimpleResolver()
    units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
    )

    result = resolver.resolve(
        units,
        ["A WAL - BEL", convoy("F", "ENG", "A", "WAL", "BEL")],
    )

    assert result["units"]["BEL"].power == "ENGLAND"
    assert ("ENG", "CONVOY") in result["results"]


def test_multi_fleet_convoy_chain_succeeds():
    resolver = SimpleResolver()
    units = make_units(
        ("LON", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
        ("MID", "ENGLAND", "F"),
    )

    result = resolver.resolve(
        units,
        [
            "A LON - POR",
            convoy("F", "ENG", "A", "LON", "POR"),
            convoy("F", "MID", "A", "LON", "POR"),
        ],
    )

    assert result["units"]["POR"].power == "ENGLAND"


def test_non_adjacent_army_move_without_convoy_fails():
    resolver = SimpleResolver()
    units = make_units(("WAL", "ENGLAND", "A"))

    result = resolver.resolve(units, ["A WAL - BEL"])

    assert result["units"]["WAL"].power == "ENGLAND"
    assert ("WAL", "FAIL BEL invalid") in result["results"]


def test_convoy_is_disrupted_when_convoying_fleet_is_dislodged():
    resolver = SimpleResolver()
    units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
        ("BEL", "FRANCE", "F"),
        ("NTH", "FRANCE", "F"),
    )

    result = resolver.resolve(
        units,
        [
            "A WAL - BRE",
            convoy("F", "ENG", "A", "WAL", "BRE"),
            "F BEL - ENG",
            support_move("F", "NTH", "F", "BEL", "ENG"),
        ],
    )

    assert result["units"]["WAL"].power == "ENGLAND"
    assert result["units"]["ENG"].power == "FRANCE"
    assert ("WAL", "FAIL BRE convoy disrupted") in result["results"]
    assert ("ENG", "CONVOY DISRUPTED") in result["results"]


def test_convoy_still_works_when_attack_on_convoy_fleet_bounces():
    resolver = SimpleResolver()
    units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
        ("BEL", "FRANCE", "F"),
    )

    result = resolver.resolve(
        units,
        [
            "A WAL - BRE",
            convoy("F", "ENG", "A", "WAL", "BRE"),
            "F BEL - ENG",
        ],
    )

    assert result["units"]["BRE"].power == "ENGLAND"
    assert ("ENG", "CONVOY") in result["results"]


def test_adjacent_army_move_can_be_forced_to_use_own_convoy_route():
    resolver = SimpleResolver()
    units = make_units(
        ("BEL", "ENGLAND", "A"),
        ("NTH", "ENGLAND", "F"),
        ("HEL", "ENGLAND", "F"),
        ("HOL", "FRANCE", "A"),
        ("RUH", "FRANCE", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A BEL - HOL",
            convoy("F", "NTH", "A", "BEL", "HOL"),
            convoy("F", "HEL", "A", "BEL", "HOL"),
            "A HOL H",
            support_hold("A", "RUH", "A", "HOL"),
        ],
    )

    assert result["units"]["BEL"].power == "ENGLAND"
    assert ("BEL", "BOUNCE HOL") in result["results"]


def test_via_convoy_can_use_foreign_convoy_route_for_adjacent_army_move():
    resolver = SimpleResolver()
    units = make_units(
        ("BEL", "ENGLAND", "A"),
        ("NTH", "FRANCE", "F"),
        ("HEL", "FRANCE", "F"),
        ("HOL", "GERMANY", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A BEL - HOL VIA CONVOY",
            convoy("F", "NTH", "A", "BEL", "HOL"),
            convoy("F", "HEL", "A", "BEL", "HOL"),
            "A HOL - BEL",
        ],
    )

    assert result["units"]["HOL"].power == "ENGLAND"
    assert result["units"]["BEL"].power == "GERMANY"


def test_convoyed_attack_does_not_cut_support_against_only_convoy_route():
    resolver = SimpleResolver()
    units = make_units(
        ("TUN", "FRANCE", "A"),
        ("TYN", "FRANCE", "F"),
        ("ION", "ITALY", "F"),
        ("NAP", "ITALY", "F"),
    )

    result = resolver.resolve(
        units,
        [
            "A TUN - NAP",
            convoy("F", "TYN", "A", "TUN", "NAP"),
            "F ION - TYN",
            support_move("F", "NAP", "F", "ION", "TYN"),
        ],
    )

    assert result["units"]["TUN"].power == "FRANCE"
    assert result["units"]["TYN"].power == "ITALY"
    assert ("NAP", "SUPPORT MOVE TYN") in result["results"]


def test_convoyed_attack_cuts_support_against_alternate_convoy_route():
    resolver = SimpleResolver()
    units = make_units(
        ("TUN", "FRANCE", "A"),
        ("TYN", "FRANCE", "F"),
        ("ION", "FRANCE", "F"),
        ("ROM", "ITALY", "F"),
        ("NAP", "ITALY", "F"),
    )

    result = resolver.resolve(
        units,
        [
            "A TUN - NAP",
            convoy("F", "TYN", "A", "TUN", "NAP"),
            convoy("F", "ION", "A", "TUN", "NAP"),
            "F ROM - TYN",
            support_move("F", "NAP", "F", "ROM", "TYN"),
        ],
    )

    assert result["units"]["NAP"].power == "ITALY"
    assert result["units"]["TYN"].power == "FRANCE"
    assert ("NAP", "SUPPORT CUT") in result["results"]


def test_convoy_allows_exchange_of_places():
    resolver = SimpleResolver()
    units = make_units(
        ("LON", "ENGLAND", "A"),
        ("BEL", "FRANCE", "A"),
        ("NTH", "ENGLAND", "F"),
        ("ENG", "FRANCE", "F"),
    )

    result = resolver.resolve(
        units,
        [
            "A LON - BEL",
            convoy("F", "NTH", "A", "LON", "BEL"),
            "A BEL - LON",
            convoy("F", "ENG", "A", "BEL", "LON"),
        ],
    )

    assert result["units"]["BEL"].power == "ENGLAND"
    assert result["units"]["LON"].power == "FRANCE"


def test_attack_on_own_unit_does_not_cut_support():
    resolver = SimpleResolver()
    units = make_units(
        ("BUR", "FRANCE", "A"),
        ("PAR", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
        ("MUN", "GERMANY", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A BUR H",
            support_hold("A", "PAR", "A", "BUR"),
            "A GAS - PAR",
            "A MUN - BUR",
        ],
    )

    assert result["units"]["BUR"].power == "FRANCE"
    assert ("PAR", "SUPPORT HOLD") in result["results"]
    assert ("MUN", "BOUNCE BUR") in result["results"]


def test_country_cannot_support_foreign_attack_on_own_unit():
    resolver = SimpleResolver()
    units = make_units(
        ("PAR", "FRANCE", "A"),
        ("BUR", "FRANCE", "A"),
        ("PIC", "GERMANY", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A PIC - PAR",
            support_move("A", "BUR", "A", "PIC", "PAR"),
            "A PAR H",
        ],
    )

    assert result["units"]["PAR"].power == "FRANCE"
    assert result["dislodged"] == {}
    assert ("PIC", "BOUNCE PAR") in result["results"]


def test_retreat_can_use_province_that_was_attacked_without_standoff():
    resolver = SimpleResolver()
    units = make_units(
        ("BUL", "TURKEY", "A"),
        ("RUM", "RUSSIA", "A"),
        ("SER", "RUSSIA", "A"),
        ("BUD", "AUSTRIA", "A"),
        ("GAL", "RUSSIA", "A"),
        ("VIE", "RUSSIA", "A"),
    )

    result = resolver.resolve(
        units,
        [
            "A BUL - RUM",
            support_move("A", "SER", "A", "RUM", "BUL"),
            "A RUM - BUL",
            "A GAL - BUD",
            support_move("A", "VIE", "A", "GAL", "BUD"),
            "A BUD H",
        ],
    )

    assert result["dislodged"] == {"BUD": "GAL", "BUL": "RUM"}
    assert "RUM" in result["retreat_options"]["BUD"]


def test_game_enters_retreat_phase_after_dislodgement():
    game = Game()
    game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
    )

    game.set_orders("FRANCE", ["A PAR - BUR", "A GAS S A PAR - BUR"])
    game.set_orders("GERMANY", ["A BUR H"])
    for power in ["AUSTRIA", "ENGLAND", "ITALY", "RUSSIA", "TURKEY"]:
        game.set_orders(power, [])

    game.process()

    assert game.state.phase == "RETREATS"
    assert set(game.state.dislodged_units) == {"BUR"}
    assert "MUN" in game.state.retreat_options["BUR"]
    assert "PAR" not in game.state.retreat_options["BUR"]


def test_game_resolves_retreat_and_advances_phase():
    game = Game()
    game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("GAS", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
    )

    game.set_orders("FRANCE", ["A PAR - BUR", "A GAS S A PAR - BUR"])
    game.set_orders("GERMANY", ["A BUR H"])
    for power in ["AUSTRIA", "ENGLAND", "ITALY", "RUSSIA", "TURKEY"]:
        game.set_orders(power, [])
    game.process()

    game.set_orders("GERMANY", ["A BUR R MUN"])
    retreat_results = game.process()

    assert ("BUR", "RETREAT MUN") in retreat_results
    assert game.state.phase == "ORDERS"
    assert game.state.season == "FALL"
    assert game.state.units["MUN"].power == "GERMANY"
