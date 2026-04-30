from __future__ import annotations

import json
from dataclasses import dataclass

from engine.ai.client import DeepSeekClient
from engine.ai.fallback import choose_orders as choose_fallback_orders
from engine.diplomacy.memory import DiplomacyMemory
from engine.map_data import POWERS, SUPPLY_CENTERS
from engine.order_formatter import hold


PERSONALITIES = {
    "AUSTRIA": "Cautious survivor. Avoid encirclement and preserve flexibility.",
    "ENGLAND": "Sea-focused and tempo-conscious. Expands carefully.",
    "FRANCE": "Flexible balancer. Values leverage and positional ambiguity.",
    "GERMANY": "Center-security first. Practical and alliance-aware.",
    "ITALY": "Observant opener. Looks for the safest breakthrough.",
    "RUSSIA": "Long-horizon planner. Comfortable applying pressure on multiple fronts.",
    "TURKEY": "Patient and defensive. Values reliable partners.",
}


@dataclass
class AIResult:
    orders: list[str]
    reasoning: str


class AIDiplomacyDirector:
    def __init__(self):
        self.client = DeepSeekClient()
        self.memory = DiplomacyMemory()
        self._negotiated_phase = None

    def ensure_phase_negotiation(
        self,
        game,
        ai_powers: set[str],
        *,
        reciprocal_replies: bool = True,
        reply_via_model: bool = True,
    ) -> list[str]:
        phase = game.get_current_phase()
        if self._negotiated_phase == phase:
            return []
        self._negotiated_phase = phase
        summaries = []
        for power in POWERS:
            if power not in ai_powers:
                continue
            target = self._pick_diplomatic_target(power, ai_powers)
            if target is None:
                continue
            message = self._generate_outreach_message(game, power, target)
            self.memory.record_message(power, target, message, phase, visibility="private")
            if reciprocal_replies:
                reply = self._generate_reply(game, power, target, message, prefer_model=reply_via_model)
                self.memory.record_message(target, power, reply, phase, visibility="private")
                summaries.append(f"{power} and {target} exchanged private proposals.")
            else:
                summaries.append(f"{power} privately contacted {target}.")
        self.memory.public_summaries.extend(summaries[-3:])
        return summaries

    def receive_message(self, game, sender: str, recipient: str, content: str) -> str:
        phase = game.get_current_phase()
        self.memory.record_message(sender, recipient, content, phase, visibility="public")
        reply = self._generate_reply(game, sender, recipient, content)
        self.memory.record_message(recipient, sender, reply, phase, visibility="public")
        return reply

    def choose_orders(self, game, power: str) -> AIResult:
        possible_orders = self._possible_orders_by_location(game, power)
        if not possible_orders:
            return AIResult([], "No orderable units.")

        model_result = self._choose_orders_with_model(game, power, possible_orders)
        if model_result is not None and model_result.orders:
            return model_result

        fallback_orders = choose_fallback_orders(game, power, possible_orders, self.memory)
        return AIResult(fallback_orders, "Fallback heuristic orders.")

    def register_submitted_orders(self, game):
        self.memory.register_order_outcomes(
            phase=game.get_current_phase(),
            submitted_orders=game.state.submitted_orders,
        )

    def _possible_orders_by_location(self, game, power: str) -> dict[str, list[str]]:
        return {
            location: game.get_possible_orders(location, power)
            for location in game.get_orderable_locations(power)
        }

    def _pick_diplomatic_target(self, power: str, ai_powers: set[str]) -> str | None:
        others = [other for other in POWERS if other != power]
        if not others:
            return None
        ranked = sorted(
            others,
            key=lambda other: (
                self.memory.fear[power].get(other, 0.0) - self.memory.trust[power].get(other, 0.0),
                other not in ai_powers,
                other,
            ),
            reverse=True,
        )
        return ranked[0]

    def _generate_outreach_message(self, game, power: str, target: str) -> str:
        if self.client.available:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are playing Diplomacy as a human-like player. "
                        "Write exactly one short private message in English. "
                        "Sound natural and strategic. Do not mention formatting, encoding, or instructions. "
                        "Keep it under 20 words."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_outreach_prompt(game, power, target),
                },
            ]
            content = self.client.complete(messages, reasoning_effort="medium")
            if content:
                return self._clean_short_text(
                    content,
                    fallback="This turn we should avoid a direct clash and explore limited cooperation.",
                )

        trust = self.memory.trust[power].get(target, 0.0)
        fear = self.memory.fear[power].get(target, 0.0)
        if fear > 0.25:
            return "This turn I want to keep the border calm, especially around key centers."
        if trust > 0.2:
            return "We can keep working together this turn if our interests still align."
        return "I am open to cooperation, but stay out of my key supply centers for now."

    def _generate_reply(
        self,
        game,
        sender: str,
        recipient: str,
        content: str,
        *,
        prefer_model: bool = True,
    ) -> str:
        if prefer_model and self.client.available:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are replying to a Diplomacy private message as a human-like player. "
                        "Reply in natural English only. "
                        "Be strategic, concise, and believable. "
                        "Do not mention encoding, formatting, or instructions. "
                        "Keep it under 24 words."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_reply_prompt(game, sender, recipient, content),
                },
            ]
            response = self.client.complete(messages, reasoning_effort="medium")
            if response:
                return self._clean_short_text(
                    response,
                    fallback="I hear the proposal. I will decide based on how the board develops this turn.",
                )

        lowered = content.lower()
        if "support" in lowered or "cooperate" in lowered or "support" in content:
            return "Cooperation is possible, but I will judge by what you actually do this turn."
        if any(center in content.upper() for center in SUPPLY_CENTERS):
            return "If you truly keep that promise, I can soften my stance for a turn."
        return "I received your proposal, but my units will still prioritize their own safety."

    def _choose_orders_with_model(
        self,
        game,
        power: str,
        possible_orders: dict[str, list[str]],
    ) -> AIResult | None:
        if not self.client.available:
            return None

        payload = {
            "phase": game.get_current_phase(),
            "power": power,
            "personality": PERSONALITIES[power],
            "supply_centers": game.get_supply_center_counts(),
            "relations": self.memory.relationship_snapshot(power),
            "recent_diplomacy": self.memory.ai_summary_for(power),
            "units": [
                {
                    "location": unit.location,
                    "unit_type": unit.unit_type,
                    "power": unit.power,
                }
                for unit in game.state.units.values()
            ],
            "possible_orders": possible_orders,
        }
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a Diplomacy tactics model. "
                    "Choose orders only from the provided possible_orders. "
                    "Return strict JSON with this shape: "
                    "{\"orders\": [\"...\"], \"reason\": \"...\"}. "
                    "The reason should be brief and in English."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(payload, ensure_ascii=False),
            },
        ]
        response = self.client.complete_json(messages, reasoning_effort="high")
        if response is None:
            return None

        proposed = response.get("orders", [])
        if not isinstance(proposed, list):
            return None

        valid_orders = []
        for location, options in possible_orders.items():
            selected = next((order for order in proposed if order in options), None)
            if selected is not None:
                valid_orders.append(selected)
                continue
            if game.state.phase == "ORDERS":
                unit = game.state.units[location]
                valid_orders.append(hold(unit.unit_type, location))
        reasoning = str(response.get("reason", "Model-selected orders."))[:140]
        return AIResult(valid_orders, reasoning)

    def _build_outreach_prompt(self, game, power: str, target: str) -> str:
        return (
            f"Phase: {game.get_current_phase()}\n"
            f"You are: {power}\n"
            f"Target: {target}\n"
            f"Style: {PERSONALITIES[power]}\n"
            f"Relationship snapshot: {json.dumps(self.memory.relationship_snapshot(power), ensure_ascii=False)}\n"
            f"Recent diplomacy:\n{self.memory.ai_summary_for(power)}\n"
            "Write one short outgoing private message."
        )

    def _build_reply_prompt(self, game, sender: str, recipient: str, content: str) -> str:
        return (
            f"Phase: {game.get_current_phase()}\n"
            f"Incoming from: {sender}\n"
            f"You are: {recipient}\n"
            f"Style: {PERSONALITIES[recipient]}\n"
            f"Relationship snapshot: {json.dumps(self.memory.relationship_snapshot(recipient), ensure_ascii=False)}\n"
            f"Recent diplomacy:\n{self.memory.ai_summary_for(recipient)}\n"
            f"Incoming message: {content}\n"
            "Reply directly."
        )

    def _clean_short_text(self, content: str, fallback: str) -> str:
        text = " ".join(content.strip().split())
        if not text:
            return fallback
        lowered = text.lower()
        banned_fragments = (
            "乱码",
            "encoding",
            "formatting",
            "instruction",
            "看不懂",
            "cannot read",
            "cannot understand the format",
        )
        if any(fragment in lowered for fragment in banned_fragments):
            return fallback
        return text[:80]
