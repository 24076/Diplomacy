from engine.game import Game
from engine.map_data import (
    ARMY_ADJACENCY,
    FLEET_ADJACENCY,
    HOME_SUPPLY_CENTERS,
    INITIAL_SUPPLY_CENTER_OWNERS,
    INITIAL_UNITS,
    POWERS,
    PROVINCES,
    SUPPLY_CENTERS,
    adjacency_pairs,
    base_location,
    is_valid_location_for_unit,
)


def test_supply_centers_belong_to_known_provinces():
    assert SUPPLY_CENTERS <= PROVINCES


def test_home_centers_cover_all_powers():
    assert set(HOME_SUPPLY_CENTERS) == set(POWERS)


def test_initial_supply_center_owners_cover_all_centers():
    assert set(INITIAL_SUPPLY_CENTER_OWNERS) == SUPPLY_CENTERS


def test_initial_units_use_valid_locations():
    for location, unit in INITIAL_UNITS.items():
        assert location == unit["location"]
        assert is_valid_location_for_unit(unit["unit_type"], unit["location"])
        assert base_location(unit["location"]) in PROVINCES


def test_army_adjacency_is_symmetric():
    for src, dst in adjacency_pairs(ARMY_ADJACENCY):
        assert src in ARMY_ADJACENCY.get(dst, set()), f"{src} -> {dst} missing reverse edge"


def test_fleet_adjacency_is_symmetric():
    for src, dst in adjacency_pairs(FLEET_ADJACENCY):
        assert src in FLEET_ADJACENCY.get(dst, set()), f"{src} -> {dst} missing reverse edge"


def test_stp_south_coast_orders_use_split_coast_adjacency():
    game = Game()
    orders = set(game.get_possible_orders("STP/SC"))
    assert "F STP/SC - BOT" in orders
    assert "F STP/SC - LVN" in orders
    assert "F STP/SC - BAR" not in orders


def test_validator_rejects_wrong_coast_move():
    game = Game()
    ok, message = game.validator.validate("F STP/SC - BAR", game.state.units)
    assert not ok
    assert "cannot move" in message
