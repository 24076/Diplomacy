from engine.ai.player import AIDiplomacyDirector
from engine.game import Game
from engine.map_data import POWERS


def simulate_until_spring_1902():
    game = Game()
    director = AIDiplomacyDirector()
    ai_powers = set(POWERS)
    acting_powers = set()

    while game.get_current_phase() != "SPRING 1902 ORDERS":
        director.ensure_phase_negotiation(game, ai_powers)
        for power in POWERS:
            if power in game.state.submitted_orders:
                continue
            orderable = game.get_orderable_locations(power)
            if not orderable:
                continue
            result = director.choose_orders(game, power)
            game.set_orders(power, result.orders)
            if result.orders:
                acting_powers.add(power)

        assert game.all_orders_submitted()
        director.register_submitted_orders(game)
        game.process()

    return director, acting_powers


def test_ai_long_campaign_reaches_one_year_with_broad_participation():
    director, acting_powers = simulate_until_spring_1902()

    assert len(acting_powers) >= 6
    assert len(director.memory.messages) >= 20
    assert len({message.sender for message in director.memory.messages}) >= 6
