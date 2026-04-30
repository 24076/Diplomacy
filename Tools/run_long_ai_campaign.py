from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.ai.player import AIDiplomacyDirector
from engine.ai.fallback import choose_orders as choose_fallback_orders
from engine.game import Game
from engine.map_data import POWERS


def run_campaign(order_mode: str = "model"):
    game = Game()
    director = AIDiplomacyDirector()
    ai_powers = set(POWERS)
    acting_powers = set()
    phase_log = []

    while game.get_current_phase() != "SPRING 1902 ORDERS":
        phase_name = game.get_current_phase()
        phase_log.append(phase_name)
        print(f"\n=== {phase_name} ===")

        summaries = director.ensure_phase_negotiation(
            game,
            ai_powers,
            reciprocal_replies=True,
            reply_via_model=False,
        )
        for summary in summaries:
            print(f"[talk] {summary}")

        for power in POWERS:
            if power in game.state.submitted_orders:
                continue
            orderable = game.get_orderable_locations(power)
            if not orderable:
                continue
            if order_mode == "model":
                result = director.choose_orders(game, power)
                orders = result.orders
                reasoning = result.reasoning
            else:
                possible_orders = {
                    location: game.get_possible_orders(location, power)
                    for location in orderable
                }
                orders = choose_fallback_orders(game, power, possible_orders, director.memory)
                reasoning = "Fallback campaign orders."
            game.set_orders(power, orders)
            if orders:
                acting_powers.add(power)
            print(f"[orders] {power}: {', '.join(orders) if orders else '(none)'}")
            print(f"[why] {reasoning}")

        if not game.all_orders_submitted():
            raise RuntimeError(f"Not all orders submitted in {phase_name}")

        director.register_submitted_orders(game)
        results = game.process()
        for src, outcome in results[:12]:
            print(f"[resolve] {src}: {outcome}")

    total_messages = len(director.memory.messages)
    active_speakers = len({message.sender for message in director.memory.messages})
    print("\n=== Summary ===")
    print(f"Reached phase: {game.get_current_phase()}")
    print(f"Processed phases: {', '.join(phase_log)}")
    print(f"Acting powers: {sorted(acting_powers)}")
    print(f"Total diplomatic messages: {total_messages}")
    print(f"Unique speakers: {active_speakers}")
    print("Recent diplomacy:")
    for line in director.memory.recent_public_lines(limit=10):
        print(f"  - {line}")

    if len(acting_powers) < 6:
        raise AssertionError(f"Expected at least 6 acting powers, got {len(acting_powers)}")
    if total_messages < 20:
        raise AssertionError(f"Expected at least 20 diplomatic messages, got {total_messages}")
    if active_speakers < 6:
        raise AssertionError(f"Expected at least 6 unique speakers, got {active_speakers}")


def main() -> int:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("DEEPSEEK_API_KEY is not set.")
        return 1
    order_mode = "model"
    if len(sys.argv) > 1 and sys.argv[1] in {"fallback", "model"}:
        order_mode = sys.argv[1]
    print(f"Order mode: {order_mode}")
    run_campaign(order_mode=order_mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
