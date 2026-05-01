from pathlib import Path
import json
import threading
import pygame

from engine.ai import AIDiplomacyDirector
from engine.game import Game, POWERS
from engine.map_data import base_location
from engine.order_parser import parse_order
from engine.order_formatter import disband, hold
from engine.orders import ConvoyOrder, HoldOrder, MoveOrder, RetreatOrder, SupportHoldOrder, SupportMoveOrder

WHITE = (250, 250, 250)
BLACK = (20, 20, 20)
GRAY = (235, 235, 235)
DARK = (70, 70, 70)
RED = (180, 30, 30)
GREEN = (40, 150, 70)
BLUE = (45, 110, 190)

MAP_W = 1120
SCREEN_W = 1450
SCREEN_H = 980
PANEL_X = 1120
PANEL_W = 330

INK = (236, 229, 213)
INK_MUTED = (180, 171, 151)
PANEL_BG = (29, 38, 48)
PANEL_BG_2 = (38, 51, 64)
CARD_BG = (48, 61, 75)
CARD_BORDER = (104, 91, 61)
GOLD = (213, 168, 82)
GOLD_DARK = (145, 101, 45)
SUCCESS = (96, 169, 111)
WARNING = (213, 111, 87)
MAP_EDGE = (32, 28, 24)
POWER_COLORS = {
    "AUSTRIA": (192, 57, 43),
    "ENGLAND": (31, 58, 147),
    "FRANCE": (93, 173, 226),
    "GERMANY": (42, 42, 42),
    "ITALY": (35, 155, 86),
    "RUSSIA": (232, 232, 224),
    "TURKEY": (244, 208, 63),
}

CJK_SANS_CANDIDATES = [
    "Microsoft YaHei",
    "SimHei",
    "SimSun",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "Arial Unicode MS",
    "Segoe UI",
]

CJK_SERIF_CANDIDATES = [
    "Microsoft YaHei",
    "SimSun",
    "SimHei",
    "Georgia",
]


class DiplomacyApp:
    def __init__(self, start_in_setup: bool = False):
        pygame.init()
        self.root = Path(__file__).resolve().parent.parent
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Diplomacy Local Hotseat")
        self.clock = pygame.time.Clock()
        self.font = self._load_font(CJK_SANS_CANDIDATES, 18)
        self.small = self._load_font(CJK_SANS_CANDIDATES, 15)
        self.tiny = self._load_font(CJK_SANS_CANDIDATES, 12)
        self.big = self._load_font(CJK_SERIF_CANDIDATES, 25, bold=True)
        self.title = self._load_font(CJK_SERIF_CANDIDATES, 34, bold=True)
        self.button_font = self._load_font(CJK_SANS_CANDIDATES, 16, bold=True)

        self.game = Game()
        self.ai_director = AIDiplomacyDirector()
        self.current_power_index = 0
        self.selected_location = None
        self.power_drafts = {power: [] for power in POWERS}
        self.message_log = ["Loaded user map background", "Press R to reload points"]
        self.diplomacy_feed = ["Diplomatic channels are quiet."]
        self.last_results = []
        self.map_image = self._load_map()
        self.unit_positions = self._load_layout().get("unit_positions", {})
        self.sidebar_rect = pygame.Rect(PANEL_X, 0, PANEL_W, SCREEN_H)
        self.submit_rect = pygame.Rect(1140, 930, 140, 36)
        self.process_rect = pygame.Rect(1295, 930, 140, 36)
        self.send_rect = pygame.Rect(1345, 884, 82, 30)
        self.order_option_rects = []
        self.recipient_rects = []
        self.setup_chip_rects = []
        self.setup_start_rect = pygame.Rect(1210, 830, 140, 44)
        self.chat_input_rect = pygame.Rect(1144, 844, 192, 30)
        self.input_active = False
        self.chat_input = ""
        self.ai_busy = False
        self.ai_error = None
        self.ai_thread = None
        self.mode = "SETUP" if start_in_setup else "GAME"
        self.setup_human_powers = {"FRANCE"} if start_in_setup else set(POWERS)
        self.human_powers = set(POWERS)
        self.ai_powers = set()
        self.chat_recipient = "ENGLAND"
        self.apply_controller_selection(self.setup_human_powers if start_in_setup else set(POWERS))

    def _load_font(self, candidates, size, bold=False):
        for name in candidates:
            path = pygame.font.match_font(name)
            if path:
                font = pygame.font.Font(path, size)
                font.set_bold(bold)
                return font
        return pygame.font.SysFont(None, size, bold=bold)

    @property
    def current_power(self):
        return POWERS[self.current_power_index]

    def _relevant_powers(self):
        if self.game.state.phase == "RETREATS":
            return [
                power
                for power in POWERS
                if self.game.get_orderable_locations(power)
            ]
        if self.game.state.phase == "ADJUSTMENTS":
            return [
                power
                for power in POWERS
                if self.game.get_adjustment_requirement(power) != 0
            ]
        return POWERS

    def _first_relevant_power_index(self):
        relevant = self._relevant_powers()
        if not relevant:
            return 0
        return POWERS.index(relevant[0])

    def _advance_to_next_relevant_power(self):
        relevant = self._relevant_powers()
        if not relevant:
            self.current_power_index = 0
            return
        current = self.current_power
        if current not in relevant:
            self.current_power_index = POWERS.index(relevant[0])
            return
        position = relevant.index(current)
        if position < len(relevant) - 1:
            self.current_power_index = POWERS.index(relevant[position + 1])

    def _load_map(self):
        p = self.root / "map" / "assets" / "diplomacy_map.jpg"
        if p.exists():
            img = pygame.image.load(str(p)).convert()
            return pygame.transform.smoothscale(img, (MAP_W, SCREEN_H))
        return None

    def _load_layout(self):
        p = self.root / "map" / "ui_layout.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"unit_positions": {}}

    def reload_points(self):
        self.unit_positions = self._load_layout().get("unit_positions", {})
        self.message_log = ["Reloaded map/ui_layout.json"]

    def apply_controller_selection(self, human_powers: set[str]):
        self.human_powers = set(human_powers)
        self.ai_powers = set(POWERS) - self.human_powers
        if self.current_power in self.ai_powers and not self.game.all_orders_submitted():
            self.current_power_index = self._first_relevant_power_index()
        recipients = sorted(self.ai_powers)
        self.chat_recipient = recipients[0] if recipients else None

    def run(self):
        running = True
        while running:
            self._poll_ai_worker()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if self._handle_keydown(event):
                        continue
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
            self._render()
            self.clock.tick(30)
        pygame.quit()

    def _handle_keydown(self, event) -> bool:
        if self.ai_busy and self.mode == "GAME":
            if event.key == pygame.K_r:
                self.reload_points()
                return True
            return False

        if self.mode == "GAME" and self.input_active:
            if event.key == pygame.K_RETURN:
                self._send_current_chat()
                return True
            if event.key == pygame.K_BACKSPACE:
                self.chat_input = self.chat_input[:-1]
                return True
            if event.key == pygame.K_ESCAPE:
                self.input_active = False
                return True
            if event.unicode and event.unicode.isprintable():
                self.chat_input += event.unicode
                self.chat_input = self.chat_input[-160:]
                return True

        if event.key == pygame.K_r:
            self.reload_points()
            return True
        return False

    def _handle_click(self, pos):
        if self.mode == "SETUP":
            self._handle_setup_click(pos)
            return

        if self.ai_busy:
            self.message_log = ["AI is thinking. Please wait..."]
            return

        if self.submit_rect.collidepoint(pos):
            self._submit_current_power()
            return
        if self.process_rect.collidepoint(pos):
            self._process_phase()
            return
        if self.send_rect.collidepoint(pos):
            self._send_current_chat()
            return
        for rect, recipient in self.recipient_rects:
            if rect.collidepoint(pos):
                self.chat_recipient = recipient
                self.message_log = [f"Chat target set to {recipient}"]
                return

        if self.chat_input_rect.collidepoint(pos):
            self.input_active = True
            return
        self.input_active = False
        for rect, order in self.order_option_rects:
            if rect.collidepoint(pos):
                drafts = self.power_drafts[self.current_power]
                parsed = parse_order(order)
                src = parsed.location
                drafts = [d for d in drafts if parse_order(d).location != src]
                drafts.append(order)
                self.power_drafts[self.current_power] = drafts
                self.message_log = [f"Selected: {order}"]
                return
        for loc in self.game.get_orderable_locations(self.current_power):
            p = self.unit_positions.get(base_location(loc))
            if not p:
                continue
            dx = pos[0] - p["x"]
            dy = pos[1] - p["y"]
            if dx * dx + dy * dy <= 17 * 17:
                self.selected_location = loc
                self.message_log = [f"Selected {loc}"]
                return
        for loc, unit in self.game.state.units.items():
            p = self.unit_positions.get(base_location(loc))
            if not p:
                continue
            dx = pos[0] - p["x"]
            dy = pos[1] - p["y"]
            if dx * dx + dy * dy <= 17 * 17:
                if unit.power == self.current_power:
                    self.selected_location = loc
                    self.message_log = [f"Selected {loc}"]
                else:
                    self.message_log = [f"{loc} belongs to {unit.power}"]
                return

    def _handle_setup_click(self, pos):
        for rect, power in self.setup_chip_rects:
            if rect.collidepoint(pos):
                if power in self.setup_human_powers:
                    self.setup_human_powers.remove(power)
                elif len(self.setup_human_powers) < 6:
                    self.setup_human_powers.add(power)
                else:
                    self.message_log = ["You can choose at most 6 human powers."]
                return

        if self.setup_start_rect.collidepoint(pos):
            if len(self.setup_human_powers) > 6:
                self.message_log = ["At most 6 human powers are allowed."]
                return
            self.apply_controller_selection(self.setup_human_powers)
            self.mode = "GAME"
            self.message_log = [f"Humans: {', '.join(sorted(self.human_powers)) or 'None'}"]
            self._start_ai_turns_async()

    def _submit_current_power(self):
        if self.current_power in self.ai_powers:
            self.message_log = [f"{self.current_power} is AI-controlled."]
            return
        self.game.set_orders(self.current_power, self.power_drafts[self.current_power])
        self.message_log = [f"Submitted {self.current_power}"]
        if self.game.all_orders_submitted():
            self.message_log = ["All powers submitted. Click Process Phase."]
        else:
            previous_power = self.current_power
            self._advance_to_next_relevant_power()
            if self.current_power == previous_power:
                for power in self._relevant_powers():
                    if power not in self.game.state.submitted_orders:
                        self.current_power_index = POWERS.index(power)
                        break
            self._start_ai_turns_async()

    def _process_phase(self):
        if not self.game.all_orders_submitted():
            self.message_log = ["Not all powers submitted."]
            return
        self.ai_director.register_submitted_orders(self.game)
        self.last_results = self.game.process()
        self.message_log = [f"{src}: {result}" for src, result in self.last_results[-8:]]
        if self.game.state.winner is not None:
            self.message_log = [f"Winner: {self.game.state.winner}"]
        self.power_drafts = {power: [] for power in POWERS}
        self.current_power_index = self._first_relevant_power_index()
        self.selected_location = None
        feed = self.ai_director.memory.recent_public_lines()
        if feed:
            self.diplomacy_feed = feed
        self._start_ai_turns_async()

    def _send_current_chat(self):
        if self.mode != "GAME":
            return
        if not self.chat_input.strip():
            return
        if self.current_power not in self.human_powers:
            self.message_log = ["Only the current human-controlled power can send messages."]
            return
        if not self.chat_recipient:
            self.message_log = ["There is no AI power to talk to."]
            return
        reply = self.ai_director.receive_message(
            self.game,
            self.current_power,
            self.chat_recipient,
            self.chat_input.strip(),
        )
        self.diplomacy_feed = self.ai_director.memory.recent_public_lines()
        self.message_log = [f"{self.chat_recipient} replied: {reply[:64]}"]
        self.chat_input = ""
        self.input_active = False

    def _auto_handle_ai_turns(self):
        if self.mode != "GAME":
            return
        if self.ai_powers:
            summaries = self.ai_director.ensure_phase_negotiation(self.game, self.ai_powers)
            if summaries:
                self.diplomacy_feed = self.ai_director.memory.recent_public_lines()
        safety = 0
        while (
            not self.game.all_orders_submitted()
            and self.current_power in self.ai_powers
            and safety < 16
        ):
            result = self.ai_director.choose_orders(self.game, self.current_power)
            self.power_drafts[self.current_power] = list(result.orders)
            self.game.set_orders(self.current_power, result.orders)
            self.message_log = [f"{self.current_power} AI: {result.reasoning}"]
            previous_power = self.current_power
            if self.game.all_orders_submitted():
                self.diplomacy_feed = self.ai_director.memory.recent_public_lines()
                return
            self._advance_to_next_relevant_power()
            if self.current_power == previous_power:
                break
            safety += 1

    def _start_ai_turns_async(self):
        if self.mode != "GAME" or self.ai_busy:
            return
        needs_ai = bool(self.ai_powers) and (
            self.current_power in self.ai_powers or not self.game.all_orders_submitted()
        )
        if not needs_ai:
            return
        self.ai_busy = True
        self.ai_error = None
        self.message_log = ["AI is thinking..."]
        self.ai_thread = threading.Thread(target=self._run_ai_turns_worker, daemon=True)
        self.ai_thread.start()

    def _run_ai_turns_worker(self):
        try:
            self._auto_handle_ai_turns()
        except Exception as exc:  # pragma: no cover - background UI safety
            self.ai_error = str(exc)
        finally:
            self.ai_busy = False

    def _poll_ai_worker(self):
        if self.ai_thread is not None and not self.ai_thread.is_alive():
            self.ai_thread = None
            if self.ai_error:
                self.message_log = [f"AI error: {self.ai_error[:120]}"]
                self.ai_error = None

    def _render(self):
        self.screen.fill(MAP_EDGE)
        if self.map_image is not None:
            self.screen.blit(self.map_image, (0, 0))
            self._render_map_finish()
        if self.mode == "SETUP":
            self._render_setup_overlay()
            pygame.display.flip()
            return
        self._render_order_overlay()
        self._render_units()
        self._render_special_markers()
        self._render_sidebar()
        pygame.display.flip()

    def _render_map_finish(self):
        overlay = pygame.Surface((MAP_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((72, 46, 24, 20))
        pygame.draw.rect(overlay, (10, 10, 10, 65), pygame.Rect(0, 0, MAP_W, SCREEN_H), 18)
        pygame.draw.rect(overlay, (250, 230, 174, 28), pygame.Rect(10, 10, MAP_W - 20, SCREEN_H - 20), 3)
        self.screen.blit(overlay, (0, 0))
        pygame.draw.line(self.screen, (18, 20, 24), (MAP_W - 1, 0), (MAP_W - 1, SCREEN_H), 5)

    def _fit_text(self, text, font, width):
        if font.size(text)[0] <= width:
            return text
        trimmed = text
        while trimmed and font.size(trimmed + "...")[0] > width:
            trimmed = trimmed[:-1]
        return trimmed + "..." if trimmed else "..."

    def _draw_text(self, text, font, color, pos, max_width=None):
        if max_width is not None:
            text = self._fit_text(text, font, max_width)
        self.screen.blit(font.render(text, True, color), pos)

    def _draw_card(self, rect, title=None):
        shadow = rect.move(0, 3)
        pygame.draw.rect(self.screen, (12, 16, 20), shadow, border_radius=12)
        pygame.draw.rect(self.screen, CARD_BG, rect, border_radius=12)
        pygame.draw.rect(self.screen, CARD_BORDER, rect, 1, border_radius=12)
        if title:
            self._draw_text(title.upper(), self.tiny, GOLD, (rect.x + 12, rect.y + 9), rect.w - 24)

    def _draw_button(self, rect, label, base, enabled=True):
        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos) and enabled
        fill = tuple(min(255, c + 18) for c in base) if hover else base
        if not enabled:
            fill = (76, 82, 86)
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, GOLD if enabled else (112, 112, 112), rect, 1, border_radius=8)
        color = BLACK if enabled else (180, 180, 180)
        text = self.button_font.render(label, True, color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _power_color(self, power):
        return POWER_COLORS.get(power, (90, 90, 90))

    def _location_center(self, location):
        point = self.unit_positions.get(base_location(location))
        if not point:
            return None
        return (point["x"], point["y"])

    def _draw_dashed_line(self, color, start, end, dash_length=9, width=2):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = max(1.0, (dx * dx + dy * dy) ** 0.5)
        vx = dx / distance
        vy = dy / distance
        gap = dash_length * 0.6
        step = dash_length + gap
        progress = 0.0
        while progress < distance:
            seg_start = (
                int(start[0] + vx * progress),
                int(start[1] + vy * progress),
            )
            seg_end_progress = min(distance, progress + dash_length)
            seg_end = (
                int(start[0] + vx * seg_end_progress),
                int(start[1] + vy * seg_end_progress),
            )
            pygame.draw.line(self.screen, color, seg_start, seg_end, width)
            progress += step

    def _draw_arrow(self, color, start, end, width=3, alpha=190):
        if start == end:
            return
        surface = pygame.Surface((MAP_W, SCREEN_H), pygame.SRCALPHA)
        pygame.draw.line(surface, (*color, alpha), start, end, width)
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = max(1.0, (dx * dx + dy * dy) ** 0.5)
        ux = dx / length
        uy = dy / length
        head = 12
        left = (
            int(end[0] - ux * head - uy * 6),
            int(end[1] - uy * head + ux * 6),
        )
        right = (
            int(end[0] - ux * head + uy * 6),
            int(end[1] - uy * head - ux * 6),
        )
        pygame.draw.polygon(surface, (*color, alpha), [end, left, right])
        self.screen.blit(surface, (0, 0))

    def _preview_orders(self):
        if not self.game.all_orders_submitted():
            return []

        preview = []
        if self.game.state.phase == "RETREATS":
            for power in POWERS:
                power_orders = list(self.game.state.submitted_orders.get(power, []))
                issued_locs = {order.location for order in power_orders}
                for loc in self.game.get_orderable_locations(power):
                    if loc not in issued_locs:
                        unit = self.game.state.dislodged_units[loc]
                        power_orders.append(parse_order(disband(unit.unit_type, loc)))
                preview.extend((power, order) for order in power_orders)
            return preview

        if self.game.state.phase == "ADJUSTMENTS":
            for power in POWERS:
                for order in self.game.state.submitted_orders.get(power, []):
                    preview.append((power, order))
            return preview

        for power in POWERS:
            power_orders = list(self.game.state.submitted_orders.get(power, []))
            issued_locs = {order.location for order in power_orders}
            for loc in self.game.get_orderable_locations(power):
                if loc not in issued_locs:
                    unit = self.game.state.units[loc]
                    power_orders.append(parse_order(hold(unit.unit_type, loc)))
            preview.extend((power, order) for order in power_orders)
        return preview

    def _render_order_overlay(self):
        preview_orders = self._preview_orders()
        if not preview_orders:
            return

        for power, order in preview_orders:
            color = self._power_color(power)
            start = self._location_center(order.location)
            if start is None:
                continue

            if isinstance(order, (MoveOrder, RetreatOrder)):
                end = self._location_center(order.target)
                if end is not None:
                    self._draw_arrow(color, start, end, width=4 if isinstance(order, RetreatOrder) else 3, alpha=210)
                continue

            if isinstance(order, SupportMoveOrder):
                mid = self._location_center(order.supported_location)
                end = self._location_center(order.target)
                if mid is not None:
                    pygame.draw.line(self.screen, color, start, mid, 2)
                    pygame.draw.circle(self.screen, color, mid, 5, 2)
                if end is not None:
                    self._draw_arrow(color, start if mid is None else mid, end, width=2, alpha=135)
                continue

            if isinstance(order, SupportHoldOrder):
                end = self._location_center(order.supported_location)
                if end is not None:
                    pygame.draw.line(self.screen, color, start, end, 2)
                    pygame.draw.circle(self.screen, color, end, 8, 2)
                continue

            if isinstance(order, ConvoyOrder):
                army = self._location_center(order.convoyed_location)
                target = self._location_center(order.target)
                if army is not None:
                    self._draw_dashed_line(color, start, army, dash_length=8, width=2)
                if target is not None:
                    self._draw_dashed_line(color, start, target, dash_length=8, width=2)
                    pygame.draw.circle(self.screen, color, start, 10, 2)
                continue

            if isinstance(order, HoldOrder):
                pygame.draw.circle(self.screen, color, start, 23, 2)
                pygame.draw.circle(self.screen, color, start, 27, 1)
                continue

            pygame.draw.circle(self.screen, color, start, 14, 2)

    def _draw_army_piece(self, center, color, selected):
        shadow = (center[0] + 3, center[1] + 4)
        pygame.draw.circle(self.screen, (14, 16, 18), shadow, 21)
        pygame.draw.circle(self.screen, (237, 219, 171), center, 20)
        pygame.draw.circle(self.screen, GOLD_DARK, center, 20, 2)
        pygame.draw.circle(self.screen, color, center, 15)
        pygame.draw.circle(self.screen, (255, 244, 220), (center[0] - 4, center[1] - 5), 5)
        badge = pygame.Rect(center[0] - 8, center[1] - 8, 16, 16)
        pygame.draw.rect(self.screen, (246, 236, 213), badge, border_radius=4)
        pygame.draw.rect(self.screen, (99, 81, 49), badge, 1, border_radius=4)
        text = self.small.render("A", True, BLACK)
        self.screen.blit(text, text.get_rect(center=(center[0], center[1] + 1)))
        if selected:
            pygame.draw.circle(self.screen, (255, 223, 125), center, 26, 4)
            pygame.draw.circle(self.screen, (255, 245, 196), center, 31, 1)

    def _draw_fleet_piece(self, center, color, selected):
        shadow_points = [
            (center[0] - 17, center[1] + 8),
            (center[0] + 17, center[1] + 8),
            (center[0] + 21, center[1] - 4),
            (center[0], center[1] - 18),
            (center[0] - 21, center[1] - 4),
        ]
        pygame.draw.polygon(self.screen, (14, 16, 18), [(x + 3, y + 4) for x, y in shadow_points])
        ring = [
            (center[0] - 16, center[1] + 7),
            (center[0] + 16, center[1] + 7),
            (center[0] + 20, center[1] - 4),
            (center[0], center[1] - 17),
            (center[0] - 20, center[1] - 4),
        ]
        pygame.draw.polygon(self.screen, (237, 219, 171), ring)
        pygame.draw.polygon(self.screen, GOLD_DARK, ring, 2)
        inner = [
            (center[0] - 12, center[1] + 5),
            (center[0] + 12, center[1] + 5),
            (center[0] + 15, center[1] - 3),
            (center[0], center[1] - 13),
            (center[0] - 15, center[1] - 3),
        ]
        pygame.draw.polygon(self.screen, color, inner)
        pygame.draw.circle(self.screen, (246, 236, 213), center, 7)
        pygame.draw.circle(self.screen, (99, 81, 49), center, 7, 1)
        text = self.small.render("F", True, BLACK)
        self.screen.blit(text, text.get_rect(center=(center[0], center[1] + 1)))
        if selected:
            pygame.draw.circle(self.screen, (255, 223, 125), center, 26, 4)
            pygame.draw.circle(self.screen, (255, 245, 196), center, 31, 1)

    def _render_units(self):
        for loc, unit in self.game.state.units.items():
            p = self.unit_positions.get(base_location(loc))
            if not p:
                continue
            color = self._power_color(unit.power)
            center = (p["x"], p["y"])
            if unit.unit_type == "A":
                self._draw_army_piece(center, color, loc == self.selected_location)
            else:
                self._draw_fleet_piece(center, color, loc == self.selected_location)
            label = base_location(loc)
            text = self.tiny.render(label, True, BLACK)
            pill = pygame.Rect(center[0] + 19, center[1] - 10, text.get_width() + 10, 19)
            pygame.draw.rect(self.screen, (244, 232, 198), pill, border_radius=8)
            pygame.draw.rect(self.screen, (89, 73, 46), pill, 1, border_radius=8)
            self.screen.blit(text, (pill.x + 5, pill.y + 3))

    def _render_special_markers(self):
        if self.game.state.phase == "RETREATS":
            for loc in self.game.get_orderable_locations(self.current_power):
                p = self.unit_positions.get(base_location(loc))
                if not p:
                    continue
                pygame.draw.circle(self.screen, RED, (p["x"], p["y"]), 20, 3)
                pygame.draw.line(self.screen, RED, (p["x"] - 12, p["y"] - 12), (p["x"] + 12, p["y"] + 12), 3)
                pygame.draw.line(self.screen, RED, (p["x"] - 12, p["y"] + 12), (p["x"] + 12, p["y"] - 12), 3)

        if self.game.state.phase == "ADJUSTMENTS" and self.game.get_adjustment_requirement(self.current_power) > 0:
            for loc in self.game.get_orderable_locations(self.current_power):
                p = self.unit_positions.get(base_location(loc))
                if not p:
                    continue
                pygame.draw.circle(self.screen, GREEN, (p["x"], p["y"]), 18, 3)
                pygame.draw.circle(self.screen, BLUE, (p["x"], p["y"]), 6)

    def _render_setup_overlay(self):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((10, 10, 14, 170))
        self.screen.blit(shade, (0, 0))

        card = pygame.Rect(240, 110, 970, 760)
        self._draw_card(card, "Campaign Setup")
        self._draw_text("Choose 0-6 human powers", self.title, INK, (card.x + 24, card.y + 42))
        self._draw_text("Unselected powers will use DeepSeek-backed diplomacy AI.", self.small, INK_MUTED, (card.x + 26, card.y + 86), 520)

        self.setup_chip_rects = []
        x = card.x + 30
        y = card.y + 138
        for idx, power in enumerate(POWERS):
            rect = pygame.Rect(x, y, 184, 78)
            active = power in self.setup_human_powers
            fill = self._power_color(power)
            if not active:
                fill = tuple(max(45, component // 2) for component in fill)
            pygame.draw.rect(self.screen, fill, rect, border_radius=14)
            pygame.draw.rect(self.screen, GOLD if active else CARD_BORDER, rect, 3 if active else 1, border_radius=14)
            self._draw_text(power, self.big, BLACK if power in ("RUSSIA", "TURKEY", "FRANCE") else WHITE, (rect.x + 14, rect.y + 18), 150)
            self._draw_text("Human" if active else "AI", self.small, BLACK if active else INK_MUTED, (rect.x + 16, rect.y + 50), 120)
            self.setup_chip_rects.append((rect, power))
            x += 204
            if idx in (2, 5):
                x = card.x + 30
                y += 104

        guide_y = card.y + 470
        self._draw_text(f"Human powers: {len(self.setup_human_powers)}", self.big, INK, (card.x + 30, guide_y), 260)
        summary = ", ".join(sorted(self.setup_human_powers)) or "None"
        self._draw_text(summary, self.small, INK_MUTED, (card.x + 30, guide_y + 34), 760)

        tip_lines = [
            "Players can chat with AI during the orders phase.",
            "AI powers also negotiate privately and track trust, fear, and betrayals.",
            "Promises about supply centers can affect future moves.",
        ]
        tip_y = guide_y + 90
        for line in tip_lines:
            self._draw_text(line, self.small, INK, (card.x + 30, tip_y), 780)
            tip_y += 22

        can_start = len(self.setup_human_powers) <= 6
        self._draw_button(self.setup_start_rect, "Start Match", (208, 179, 104), can_start)
        self._draw_text("Click a country to toggle Human / AI.", self.small, INK_MUTED, (self.setup_start_rect.x - 120, self.setup_start_rect.y + 56), 380)

    def _render_sidebar(self):
        panel_left = 1132
        panel_inner_left = 1148
        panel_width = 302
        panel_inner_width = 268
        bottom_buttons_y = 930
        buttons_height = 36
        gap = 10

        pygame.draw.rect(self.screen, PANEL_BG, self.sidebar_rect)
        for i in range(0, SCREEN_H, 22):
            shade = PANEL_BG_2 if (i // 22) % 2 == 0 else PANEL_BG
            pygame.draw.rect(self.screen, shade, pygame.Rect(PANEL_X, i, PANEL_W, 22))
        pygame.draw.line(self.screen, (11, 14, 18), (PANEL_X, 0), (PANEL_X, SCREEN_H), 4)
        pygame.draw.line(self.screen, GOLD_DARK, (PANEL_X + 4, 0), (PANEL_X + 4, SCREEN_H), 1)

        y = 18
        self._draw_text("DIPLOMACY", self.title, INK, (1140, y))
        y += 38
        subtitle = "AI Diplomacy Mode" if self.ai_powers else "Local Hotseat Command"
        self._draw_text(subtitle, self.small, INK_MUTED, (1142, y))
        y += 32
        if self.ai_busy:
            self._draw_text("AI is thinking...", self.small, WARNING, (1142, y), 220)
            y += 22

        phase_rect = pygame.Rect(1140, y, 285, 42)
        pygame.draw.rect(self.screen, (22, 28, 35), phase_rect, border_radius=10)
        pygame.draw.rect(self.screen, GOLD_DARK, phase_rect, 1, border_radius=10)
        self._draw_text(self.game.get_current_phase(), self.font, GOLD, (1154, y + 11), 255)
        y += 56

        power_color = self._power_color(self.current_power)
        pygame.draw.rect(self.screen, power_color, pygame.Rect(1140, y, 8, 36), border_radius=4)
        self._draw_text("CURRENT POWER", self.tiny, INK_MUTED, (1158, y + 1), 240)
        control_label = "AI" if self.current_power in self.ai_powers else "HUMAN"
        self._draw_text(f"{self.current_power} ({control_label})", self.big, INK, (1158, y + 14), 240)
        y += 50

        chip_x = 1140
        chip_y = y
        for power in POWERS:
            chip = pygame.Rect(chip_x, chip_y, 34, 20)
            submitted = power in self.game.state.submitted_orders
            active = power == self.current_power
            pygame.draw.rect(self.screen, self._power_color(power), chip, border_radius=8)
            pygame.draw.rect(self.screen, GOLD if active else (18, 22, 26), chip, 2 if active else 1, border_radius=8)
            if submitted:
                pygame.draw.circle(self.screen, SUCCESS, (chip.right - 4, chip.y + 4), 4)
            self._draw_text(power[:2], self.tiny, BLACK if power in ("RUSSIA", "TURKEY") else WHITE, (chip.x + 6, chip.y + 3), 24)
            chip_x += 40
        y += 34

        self._draw_text(f"Humans: {len(self.human_powers)} | AI: {len(self.ai_powers)}", self.small, INK_MUTED, (1140, y), 260)
        y += 24

        if self.game.state.phase == "ADJUSTMENTS":
            req = self.game.get_adjustment_requirement(self.current_power)
            self._draw_text(f"Adjustment: {req:+d}", self.small, INK, (1140, y))
            y += 24

        draft_rect = pygame.Rect(panel_left, y, panel_width, 68)
        self._draw_card(draft_rect, "Draft Orders")
        y = draft_rect.y + 32
        for order in self.power_drafts[self.current_power][:4]:
            self._draw_text(order, self.small, INK, (panel_inner_left, y), panel_inner_width)
            y += 18
        if not self.power_drafts[self.current_power]:
            self._draw_text("No draft orders yet.", self.small, INK_MUTED, (panel_inner_left, y), panel_inner_width)

        content_top = draft_rect.bottom + gap
        has_diplomacy_controls = bool(self.ai_powers)
        status_height = 44
        dip_height = 116 if has_diplomacy_controls else 52
        status_rect = pygame.Rect(panel_left, bottom_buttons_y - status_height - gap, panel_width, status_height)
        dip_rect = pygame.Rect(panel_left, status_rect.y - dip_height - gap, panel_width, dip_height)
        orders_rect = pygame.Rect(panel_left, content_top, panel_width, dip_rect.y - content_top - gap)

        self._draw_card(orders_rect, "Possible Orders")
        y = orders_rect.y + 32
        self.order_option_rects = []
        if self.current_power in self.ai_powers:
            self._draw_text("AI powers auto-submit after diplomacy.", self.small, INK_MUTED, (panel_inner_left, y), panel_inner_width)
            y += 20
            if self.power_drafts[self.current_power]:
                for order in self.power_drafts[self.current_power][:10]:
                    if y > orders_rect.bottom - 20:
                        break
                    self._draw_text(order, self.tiny, INK, (panel_inner_left, y), panel_inner_width)
                    y += 17
        elif self.selected_location and self.selected_location in self.game.get_orderable_locations(self.current_power):
            for order in self.game.get_possible_orders(self.selected_location, self.current_power):
                if y > orders_rect.bottom - 30:
                    break
                rect = pygame.Rect(panel_inner_left, y, 270, 16)
                hover = rect.collidepoint(pygame.mouse.get_pos())
                fill = (68, 83, 98) if hover else (58, 70, 84)
                pygame.draw.rect(self.screen, fill, rect, border_radius=5)
                pygame.draw.rect(self.screen, GOLD_DARK, rect, 1, border_radius=5)
                self._draw_text(order, self.tiny, INK, (1156, y + 1), 252)
                self.order_option_rects.append((rect, order))
                y += 17
        else:
            prompt = "Select one of your units on the map."
            if self.game.state.phase == "RETREATS":
                prompt = "Select a dislodged unit to retreat or disband."
            elif self.game.state.phase == "ADJUSTMENTS":
                if self.game.get_adjustment_requirement(self.current_power) > 0:
                    prompt = "Select a home center to build."
                elif self.game.get_adjustment_requirement(self.current_power) < 0:
                    prompt = "Select one of your units to disband."
            self._draw_text(prompt, self.small, INK_MUTED, (panel_inner_left, y), panel_inner_width)
            y += 24

        self._draw_card(dip_rect, "Diplomacy")
        self.chat_input_rect = pygame.Rect(panel_inner_left, dip_rect.bottom - 40, 192, 30)
        self.send_rect = pygame.Rect(1345, dip_rect.bottom - 40, 82, 30)
        self.recipient_rects = []
        chip_x = panel_inner_left
        chip_y = dip_rect.y + 24
        recipients = sorted(self.ai_powers - {self.current_power})
        if not has_diplomacy_controls:
            self._draw_text("Enable at least one AI power to use diplomacy chat.", self.small, INK_MUTED, (panel_inner_left, chip_y), panel_inner_width)
        elif not recipients:
            self._draw_text("No AI recipients available.", self.small, INK_MUTED, (panel_inner_left, chip_y), panel_inner_width)
        else:
            for recipient in recipients:
                rect = pygame.Rect(chip_x, chip_y, 62, 20)
                active = recipient == self.chat_recipient
                pygame.draw.rect(self.screen, self._power_color(recipient), rect, border_radius=8)
                pygame.draw.rect(self.screen, GOLD if active else (24, 26, 30), rect, 2 if active else 1, border_radius=8)
                self._draw_text(recipient[:3], self.tiny, BLACK if recipient in ("RUSSIA", "TURKEY") else WHITE, (rect.x + 9, rect.y + 3), 46)
                self.recipient_rects.append((rect, recipient))
                chip_x += 68
                if chip_x > 1360:
                    chip_x = panel_inner_left
                    chip_y += 24

        if has_diplomacy_controls:
            feed_y = chip_y + 28
            for line in self.diplomacy_feed[-2:]:
                if feed_y > self.chat_input_rect.y - 18:
                    break
                self._draw_text(line, self.tiny, INK_MUTED, (panel_inner_left, feed_y), panel_inner_width)
                feed_y += 16

            pygame.draw.rect(self.screen, (24, 31, 39), self.chat_input_rect, border_radius=7)
            pygame.draw.rect(self.screen, GOLD if self.input_active else CARD_BORDER, self.chat_input_rect, 1, border_radius=7)
            placeholder = self.chat_input if self.chat_input else "Type a diplomatic message..."
            self._draw_text(placeholder, self.tiny, INK if self.chat_input else INK_MUTED, (self.chat_input_rect.x + 8, self.chat_input_rect.y + 7), 176)
            send_enabled = bool(self.chat_recipient) and self.current_power in self.human_powers
            if self.ai_busy:
                send_enabled = False
            self._draw_button(self.send_rect, "Send", (118, 158, 181), send_enabled)

        self._draw_card(status_rect, "Status")
        y = status_rect.y + 32
        for line in self.message_log[:1]:
            self._draw_text(line, self.small, INK, (panel_inner_left, y), panel_inner_width)
            y += 18
        self.submit_rect = pygame.Rect(1140, bottom_buttons_y, 140, buttons_height)
        self.process_rect = pygame.Rect(1295, bottom_buttons_y, 140, buttons_height)
        submit_enabled = self.current_power in self.human_powers and not self.ai_busy
        self._draw_button(self.submit_rect, "Submit", (208, 179, 104), submit_enabled)
        self._draw_button(self.process_rect, "Process", (118, 158, 181), self.game.all_orders_submitted() and not self.ai_busy)
