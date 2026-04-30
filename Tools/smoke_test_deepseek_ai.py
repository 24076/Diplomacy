from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.ai.player import AIDiplomacyDirector
from engine.game import Game


def main() -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("DEEPSEEK_API_KEY is not set.")
        return 1

    print("Starting live DeepSeek AI smoke test...")
    game = Game()
    director = AIDiplomacyDirector()

    print(f"client available: {director.client.available}")
    if not director.client.available:
        print("DeepSeek client is not available.")
        return 1

    incoming = "This turn I will stay out of ENG if you do not pressure the Channel."
    reply = director.receive_message(game, "FRANCE", "ENGLAND", incoming)
    result = director.choose_orders(game, "ENGLAND")

    print(f"incoming: {incoming}")
    print(f"reply: {reply}")
    print("orders:")
    for order in result.orders:
        print(f"  - {order}")
    print(f"reasoning: {result.reasoning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
