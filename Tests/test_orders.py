from engine.game import Game
from engine.order_formatter import (
    build,
    convoy,
    disband,
    format_order,
    retreat,
    support_hold,
    support_move,
)
from engine.order_parser import parse_order
from engine.orders import (
    BuildOrder,
    ConvoyOrder,
    DisbandOrder,
    HoldOrder,
    MoveOrder,
    RetreatOrder,
    SupportHoldOrder,
    SupportMoveOrder,
)
from engine.state import Unit


def make_units(*entries):
    return {
        location: Unit(power=power, unit_type=unit_type, location=location)
        for location, power, unit_type in entries
    }


def test_parser_supports_extended_order_types():
    assert parse_order("A PAR S A BUR").__class__ is SupportHoldOrder
    assert parse_order("A PAR S A BUR - MUN").__class__ is SupportMoveOrder
    assert parse_order("F NTH C A YOR - BEL").__class__ is ConvoyOrder
    assert parse_order("A BEL - HOL VIA CONVOY") == MoveOrder("A", "BEL", "HOL", via_convoy=True)
    assert parse_order("A PAR R GAS").__class__ is RetreatOrder
    assert parse_order("BUILD A AT PAR").__class__ is BuildOrder
    assert parse_order("DISBAND A AT PAR").__class__ is DisbandOrder


def test_formatter_round_trips_extended_orders():
    orders = [
        SupportHoldOrder("A", "PAR", "A", "BUR"),
        SupportMoveOrder("A", "PAR", "A", "BUR", "MUN"),
        ConvoyOrder("F", "NTH", "A", "YOR", "BEL"),
        MoveOrder("A", "BEL", "HOL", via_convoy=True),
        RetreatOrder("A", "PAR", "GAS"),
        BuildOrder("A", "PAR"),
        DisbandOrder("A", "PAR"),
    ]
    for order in orders:
        assert parse_order(format_order(order)) == order


def test_validator_accepts_valid_support_and_convoy_orders():
    game = Game()
    assert game.validator.validate(support_hold("A", "PAR", "A", "BUR"), game.state.units) == (True, "ok")
    assert game.validator.validate(support_move("A", "PAR", "A", "BUR", "PIC"), game.state.units) == (True, "ok")
    assert game.validator.validate(convoy("F", "ENG", "A", "WAL", "BEL")) == (True, "ok")


def test_validator_accepts_convoyed_army_move_with_context_orders():
    game = Game()
    orders = ["A WAL - BEL", convoy("F", "ENG", "A", "WAL", "BEL")]
    assert game.validator.validate("A WAL - BEL", context_orders=orders) == (True, "ok")


def test_validator_requires_convoy_when_player_orders_adjacent_move_with_own_convoy():
    game = Game()
    game.state.units = make_units(
        ("BEL", "ENGLAND", "A"),
        ("NTH", "ENGLAND", "F"),
        ("HEL", "ENGLAND", "F"),
    )

    orders = [
        "A BEL - HOL",
        convoy("F", "NTH", "A", "BEL", "HOL"),
        convoy("F", "HEL", "A", "BEL", "HOL"),
    ]

    assert game.validator.validate("A BEL - HOL", game.state.units, context_orders=orders) == (True, "ok")
    assert game.validator.validate("A BEL - HOL VIA CONVOY", game.state.units, context_orders=orders) == (True, "ok")


def test_validator_rejects_invalid_extended_orders():
    game = Game()
    assert game.validator.validate(support_hold("A", "PAR", "A", "MUN"), game.state.units)[0] is False
    assert game.validator.validate(support_move("A", "PAR", "A", "BUR", "MOS"), game.state.units)[0] is False
    assert game.validator.validate(convoy("F", "BRE", "A", "PAR", "PIC"), game.state.units)[0] is False
    assert game.validator.validate("BUILD A AT BEL", game.state.units)[0] is False
    assert game.validator.validate(retreat("A", "PAR", "ENG"), game.state.units)[0] is False


def test_game_stores_structured_orders():
    game = Game()
    game.set_orders("FRANCE", ["A PAR - BUR", "A MAR H", "F BRE - ENG"])
    assert all(isinstance(order, (MoveOrder, HoldOrder)) for order in game.state.submitted_orders["FRANCE"])
    assert [order.location for order in game.state.submitted_orders["FRANCE"]] == ["PAR", "MAR", "BRE"]


def test_invalid_order_text_is_ignored_during_submission():
    game = Game()

    game.set_orders("FRANCE", ["A PAR - BUR", "TOTALLY INVALID ORDER", "A MAR H"])

    assert [order.location for order in game.state.submitted_orders["FRANCE"]] == ["PAR", "MAR"]


def test_build_and_disband_helpers_format_expected_strings():
    assert build("A", "PAR") == "BUILD A AT PAR"
    assert disband("A", "PAR") == "DISBAND A AT PAR"


def test_game_generates_support_orders_for_order_phase_ui():
    game = Game()
    game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
        ("MUN", "GERMANY", "A"),
    )

    orders = set(game.get_possible_orders("PAR"))

    assert "A PAR S A BUR" in orders
    assert "A PAR S A BUR - GAS" in orders


def test_game_generates_convoy_orders_for_fleet_ui():
    game = Game()
    game.state.units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
    )

    orders = set(game.get_possible_orders("ENG"))

    assert "F ENG C A WAL - BEL" in orders


def test_game_generates_convoyed_army_moves_for_ui():
    game = Game()
    game.state.units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
    )

    orders = set(game.get_possible_orders("WAL"))

    assert "A WAL - BEL" in orders
