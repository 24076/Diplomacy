from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from engine.map_data import POWERS, get_all_named_locations, base_location
from engine.order_parser import parse_order
from engine.orders import MoveOrder


POSITIVE_KEYWORDS = (
    "ally",
    "alliance",
    "support",
    "peace",
    "dmz",
    "demilitarized",
    "trust",
    "cooperate",
    "合作",
    "支持",
    "和平",
    "结盟",
    "互不侵犯",
)

NEGATIVE_KEYWORDS = (
    "attack",
    "threat",
    "warning",
    "betray",
    "hostile",
    "背刺",
    "进攻",
    "威胁",
    "敌对",
)

NAMED_LOCATIONS = tuple(sorted(get_all_named_locations(), key=len, reverse=True))

NON_AGGRESSION_PATTERNS = (
    "will not move to",
    "won't move to",
    "stay out of",
    "do not enter",
    "不去",
    "不进",
    "不会进",
    "不进入",
)


@dataclass
class DiplomaticMessage:
    sender: str
    recipient: str
    content: str
    phase: str
    visibility: str = "private"


@dataclass
class Commitment:
    sender: str
    recipient: str
    phase: str
    kind: str
    location: str
    content: str
    resolved: bool = False


@dataclass
class DiplomacyMemory:
    messages: List[DiplomaticMessage] = field(default_factory=list)
    public_summaries: List[str] = field(default_factory=list)
    trust: Dict[str, Dict[str, float]] = field(default_factory=dict)
    fear: Dict[str, Dict[str, float]] = field(default_factory=dict)
    commitments: List[Commitment] = field(default_factory=list)
    betrayals: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.trust:
            self.trust = {
                power: {other: 0.0 for other in POWERS if other != power}
                for power in POWERS
            }
        if not self.fear:
            self.fear = {
                power: {other: 0.0 for other in POWERS if other != power}
                for power in POWERS
            }

    def record_message(
        self,
        sender: str,
        recipient: str,
        content: str,
        phase: str,
        visibility: str = "private",
    ) -> DiplomaticMessage:
        message = DiplomaticMessage(
            sender=sender,
            recipient=recipient,
            content=content.strip(),
            phase=phase,
            visibility=visibility,
        )
        self.messages.append(message)
        self._update_relationships_from_message(message)
        self._extract_commitments(message)
        if visibility == "public":
            self.public_summaries.append(f"{sender} -> {recipient}: {content.strip()}")
        return message

    def recent_messages_for(self, power: str, limit: int = 8) -> List[DiplomaticMessage]:
        visible = [
            message
            for message in self.messages
            if message.sender == power
            or message.recipient == power
            or message.visibility == "public"
        ]
        return visible[-limit:]

    def ai_summary_for(self, power: str, limit: int = 8) -> str:
        lines = []
        for message in self.recent_messages_for(power, limit=limit):
            lines.append(
                f"{message.phase} | {message.sender} -> {message.recipient}: {message.content}"
            )
        if not lines:
            return "No meaningful diplomacy yet."
        return "\n".join(lines)

    def relationship_snapshot(self, power: str) -> List[dict]:
        rows = []
        for other in POWERS:
            if other == power:
                continue
            rows.append(
                {
                    "power": other,
                    "trust": round(self.trust[power][other], 2),
                    "fear": round(self.fear[power][other], 2),
                }
            )
        return rows

    def register_order_outcomes(
        self,
        phase: str,
        submitted_orders: dict[str, list],
    ):
        for commitment in self.commitments:
            if commitment.resolved or commitment.phase != phase:
                continue
            power_orders = submitted_orders.get(commitment.sender, [])
            if commitment.kind == "avoid_location":
                violated = False
                for order in power_orders:
                    if isinstance(order, MoveOrder) and base_location(order.target) == commitment.location:
                        violated = True
                        break
                if violated:
                    self.trust[commitment.recipient][commitment.sender] = max(
                        -1.0,
                        self.trust[commitment.recipient][commitment.sender] - 0.35,
                    )
                    self.fear[commitment.recipient][commitment.sender] = min(
                        1.0,
                        self.fear[commitment.recipient][commitment.sender] + 0.25,
                    )
                    self.betrayals.append(
                        f"{phase}: {commitment.sender} broke promise to {commitment.recipient} about {commitment.location}"
                    )
                commitment.resolved = True

    def recent_public_lines(self, limit: int = 6) -> List[str]:
        lines = list(self.public_summaries)
        lines.extend(self.betrayals[-2:])
        return lines[-limit:]

    def _update_relationships_from_message(self, message: DiplomaticMessage):
        lowered = message.content.lower()
        if any(keyword in lowered for keyword in POSITIVE_KEYWORDS):
            self.trust[message.recipient][message.sender] = min(
                1.0,
                self.trust[message.recipient][message.sender] + 0.12,
            )
        if any(keyword in lowered for keyword in NEGATIVE_KEYWORDS):
            self.fear[message.recipient][message.sender] = min(
                1.0,
                self.fear[message.recipient][message.sender] + 0.18,
            )

        mentioned_locations = [location for location in NAMED_LOCATIONS if location.lower() in lowered]
        if mentioned_locations:
            self.public_summaries.append(
                f"{message.sender} discussed {', '.join(mentioned_locations[:2])} with {message.recipient}"
            )

    def _extract_commitments(self, message: DiplomaticMessage):
        lowered = message.content.lower()
        location = None
        for named_location in NAMED_LOCATIONS:
            if named_location.lower() in lowered:
                location = named_location
                break
        if location is None:
            return
        if any(pattern in lowered for pattern in NON_AGGRESSION_PATTERNS):
            self.commitments.append(
                Commitment(
                    sender=message.sender,
                    recipient=message.recipient,
                    phase=message.phase,
                    kind="avoid_location",
                    location=location,
                    content=message.content,
                )
            )

    @staticmethod
    def parse_orders(order_texts: list[str]) -> list:
        orders = []
        for text in order_texts:
            try:
                orders.append(parse_order(text))
            except ValueError:
                continue
        return orders
