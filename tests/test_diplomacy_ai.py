from engine.ai.player import AIDiplomacyDirector
from engine.diplomacy.memory import DiplomacyMemory
from engine.game import Game
from ui.app import DiplomacyApp


def test_memory_tracks_broken_non_aggression_pact():
    game = Game()
    memory = DiplomacyMemory()
    phase = game.get_current_phase()
    memory.record_message(
        "FRANCE",
        "ENGLAND",
        "I will stay out of ENG this turn. Let's cooperate first.",
        phase,
        visibility="public",
    )

    game.set_orders("FRANCE", ["F BRE - ENG", "A PAR H", "A MAR H"])
    memory.register_order_outcomes(phase, game.state.submitted_orders)

    assert any("FRANCE broke promise" in line for line in memory.betrayals)
    assert memory.trust["ENGLAND"]["FRANCE"] < 0


def test_ai_director_falls_back_without_network():
    game = Game()
    director = AIDiplomacyDirector()

    result = director.choose_orders(game, "FRANCE")

    assert result.orders
    assert len(result.orders) == len(game.get_orderable_locations("FRANCE"))


def test_app_can_auto_submit_ai_powers():
    app = DiplomacyApp()
    app.apply_controller_selection(set())
    app.current_power_index = app._first_relevant_power_index()

    app._auto_handle_ai_turns()

    assert app.game.all_orders_submitted()
