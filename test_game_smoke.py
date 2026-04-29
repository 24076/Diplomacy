from engine.game import Game

def test_game_api():
    game = Game()
    assert "SPRING" in game.get_current_phase()
    assert "PAR" in game.get_orderable_locations("FRANCE")
    assert any(order.startswith("A PAR") for order in game.get_possible_orders("PAR"))
