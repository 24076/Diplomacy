import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from engine.map_data import SUPPLY_CENTERS, base_location
from engine.orders import HoldOrder, MoveOrder
from engine.state import Unit
from ui.app import DiplomacyApp


def make_units(*entries):
    return {
        location: Unit(power=power, unit_type=unit_type, location=location)
        for location, power, unit_type in entries
    }


def blank_supply_owners():
    return {center: None for center in SUPPLY_CENTERS}


def click_location(app: DiplomacyApp, location: str):
    app._render()
    point = app._location_center(location)
    assert point is not None
    app._handle_click(point)


def click_order(app: DiplomacyApp, order_text: str):
    app._render()
    for rect, order in app.order_option_rects:
        if order == order_text:
            app._handle_click(rect.center)
            return
    raise AssertionError(f"Order not found in UI: {order_text}")


def click_submit(app: DiplomacyApp):
    app._handle_click(app.submit_rect.center)


def click_process(app: DiplomacyApp):
    app._handle_click(app.process_rect.center)


def click_setup_power(app: DiplomacyApp, power: str):
    app._render()
    for rect, candidate in app.setup_chip_rects:
        if candidate == power:
            app._handle_click(rect.center)
            return
    raise AssertionError(f"Setup power chip not found: {power}")


@pytest.fixture
def app():
    instance = DiplomacyApp()
    yield instance
    pygame.quit()


def test_ui_click_flow_orders_to_retreats(app: DiplomacyApp):
    app.game.state.units = make_units(
        ("WAL", "ENGLAND", "A"),
        ("ENG", "ENGLAND", "F"),
        ("PAR", "FRANCE", "A"),
        ("PIC", "FRANCE", "A"),
        ("BUR", "GERMANY", "A"),
        ("MUN", "GERMANY", "A"),
    )
    app.current_power_index = app._first_relevant_power_index()
    app.game.set_orders("AUSTRIA", [])
    app.game.set_orders("ITALY", [])
    app.game.set_orders("RUSSIA", [])
    app.game.set_orders("TURKEY", [])

    app.current_power_index = 1  # ENGLAND
    click_location(app, "WAL")
    click_order(app, "A WAL - BEL")
    click_location(app, "ENG")
    click_order(app, "F ENG C A WAL - BEL")
    click_submit(app)

    click_location(app, "PAR")
    click_order(app, "A PAR - BUR")
    click_location(app, "PIC")
    click_order(app, "A PIC S A PAR - BUR")
    click_submit(app)

    click_location(app, "BUR")
    click_order(app, "A BUR H")
    click_location(app, "MUN")
    click_order(app, "A MUN H")
    click_submit(app)

    click_process(app)

    assert app.game.get_current_phase() == "SPRING 1901 RETREATS"
    assert app.current_power == "GERMANY"

    click_location(app, "BUR")
    click_order(app, "A BUR R RUH")
    click_submit(app)
    click_process(app)

    assert app.game.get_current_phase() == "FALL 1901 ORDERS"
    assert app.game.state.units["RUH"].power == "GERMANY"


def test_ui_click_flow_adjustment_build(app: DiplomacyApp):
    app.game.state.year = 1901
    app.game.state.season = "WINTER"
    app.game.state.phase = "ADJUSTMENTS"
    app.game.state.units = make_units(
        ("PAR", "FRANCE", "A"),
        ("MAR", "FRANCE", "A"),
        ("BEL", "FRANCE", "A"),
    )
    app.game.state.supply_center_owners = blank_supply_owners()
    app.game.state.supply_center_owners.update(
        {"PAR": "FRANCE", "MAR": "FRANCE", "BRE": "FRANCE", "BEL": "FRANCE"}
    )
    app.game.state.adjustment_requirements = {"FRANCE": 1}
    app.current_power_index = 2  # FRANCE

    click_location(app, "BRE")
    click_order(app, "BUILD A AT BRE")
    click_submit(app)
    click_process(app)

    assert app.game.get_current_phase() == "SPRING 1902 ORDERS"
    assert app.game.state.units["BRE"].power == "FRANCE"


def test_submit_message_does_not_claim_all_powers_submitted_too_early(app: DiplomacyApp):
    app.current_power_index = 6  # TURKEY

    click_submit(app)

    assert app.message_log != ["All powers submitted. Click Process Phase."]
    assert app.current_power == "AUSTRIA"


def test_order_preview_contains_submitted_and_default_holds(app: DiplomacyApp):
    app.game.state.units = make_units(
        ("LON", "ENGLAND", "A"),
        ("EDI", "ENGLAND", "F"),
        ("PAR", "FRANCE", "A"),
        ("BER", "GERMANY", "A"),
        ("VIE", "AUSTRIA", "A"),
        ("ROM", "ITALY", "A"),
        ("WAR", "RUSSIA", "A"),
        ("ANK", "TURKEY", "F"),
    )

    app.power_drafts["ENGLAND"] = ["A LON - WAL"]
    app.game.set_orders("ENGLAND", app.power_drafts["ENGLAND"])
    for power in ("FRANCE", "GERMANY", "AUSTRIA", "ITALY", "RUSSIA", "TURKEY"):
        app.game.set_orders(power, [])

    preview = app._preview_orders()

    assert app.game.all_orders_submitted()
    assert any(
        power == "ENGLAND"
        and isinstance(order, MoveOrder)
        and order.location == "LON"
        and order.target == "WAL"
        for power, order in preview
    )
    assert any(
        power == "ENGLAND" and isinstance(order, HoldOrder) and order.location == "EDI"
        for power, order in preview
    )


def test_start_match_does_not_run_ai_synchronously(monkeypatch):
    app = DiplomacyApp(start_in_setup=True)
    started = {"called": False}

    def fake_start():
        started["called"] = True

    monkeypatch.setattr(app, "_start_ai_turns_async", fake_start)
    app._render()
    app._handle_click(app.setup_start_rect.center)

    assert app.mode == "GAME"
    assert started["called"] is True
    pygame.quit()


def test_setup_click_flow_toggles_powers_and_starts(monkeypatch):
    app = DiplomacyApp(start_in_setup=True)
    started = {"called": False}

    def fake_start():
        started["called"] = True

    monkeypatch.setattr(app, "_start_ai_turns_async", fake_start)

    assert app.mode == "SETUP"
    assert app.setup_human_powers == {"FRANCE"}

    click_setup_power(app, "ENGLAND")
    click_setup_power(app, "FRANCE")
    app._handle_click(app.setup_start_rect.center)

    assert started["called"] is True
    assert app.mode == "GAME"
    assert app.human_powers == {"ENGLAND"}
    assert "FRANCE" in app.ai_powers
    pygame.quit()


def test_game_click_flow_can_send_chat_to_ai(monkeypatch):
    app = DiplomacyApp()
    app.apply_controller_selection({"FRANCE"})
    app.current_power_index = 2  # FRANCE
    app._render()
    app._handle_click(app.chat_button_rect.center)
    app._render()

    captured = {}

    def fake_receive_message(game, sender, recipient, content):
        captured["sender"] = sender
        captured["recipient"] = recipient
        captured["content"] = content
        return "We can cooperate, but stay out of ENG."

    monkeypatch.setattr(app.ai_director, "receive_message", fake_receive_message)
    app.chat_input = "I will stay out of ENG this turn."

    target_rect = next(rect for rect, recipient in app.recipient_rects if recipient == "ENGLAND")
    app._handle_click(target_rect.center)
    app._handle_click(app.send_rect.center)
    assert app.chat_thread is not None
    app.chat_thread.join(timeout=1)
    app._poll_chat_worker()

    assert captured == {
        "sender": "FRANCE",
        "recipient": "ENGLAND",
        "content": "I will stay out of ENG this turn.",
    }
    assert app.message_log[0].startswith("ENGLAND replied:")
    assert app.chat_input == ""
    pygame.quit()
