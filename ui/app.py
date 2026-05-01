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
MAP_H = 980
DEFAULT_SCREEN_W = 1450
DEFAULT_SCREEN_H = 980
MIN_SCREEN_W = 980
MIN_SCREEN_H = 640
PANEL_X = 1120
PANEL_W = 330
UI_MARGIN = 16
UI_GAP = 12
TOP_BAR_H = 60
BOTTOM_BAR_H = 48
LEFT_RAIL_W = 210
RIGHT_RAIL_W = 300
CARD_PAD = 14
DIP_LIST_W = 170
DIP_SIDE_W = 230

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
        self.screen_w, self.screen_h = self._initial_window_size()
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h), pygame.RESIZABLE)
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
        self.sidebar_rect = pygame.Rect(PANEL_X, 0, PANEL_W, self.screen_h)
        self.submit_rect = pygame.Rect(0, 0, 0, 0)
        self.process_rect = pygame.Rect(0, 0, 0, 0)
        self.send_rect = pygame.Rect(0, 0, 0, 0)
        self.order_option_rects = []
        self.recipient_rects = []
        self.setup_chip_rects = []
        self.setup_start_rect = pygame.Rect(1210, 830, 140, 44)
        self.chat_input_rect = pygame.Rect(0, 0, 0, 0)
        self.drawer_toggle_rect = pygame.Rect(0, 0, 0, 0)
        self.diplomacy_drawer_rect = pygame.Rect(0, 0, 0, 0)
        self.chat_button_rect = pygame.Rect(0, 0, 0, 0)
        self.input_active = False
        self.chat_input = ""
        self.ai_busy = False
        self.ai_error = None
        self.ai_thread = None
        self.chat_busy = False
        self.chat_error = None
        self.chat_thread = None
        self.chat_result = None
        self.conversation_scroll = 0
        self.conversation_max_scroll = 0
        self.mode = "SETUP" if start_in_setup else "GAME"
        self.setup_human_powers = {"FRANCE"} if start_in_setup else set(POWERS)
        self.human_powers = set(POWERS)
        self.ai_powers = set()
        self.chat_recipient = "ENGLAND"
        self.screen_mode = "MAP"
        self.layout = {}
        self.apply_controller_selection(self.setup_human_powers if start_in_setup else set(POWERS))
        self.layout = self._compute_main_layout()

    def _initial_window_size(self):
        info = pygame.display.Info()
        width = min(DEFAULT_SCREEN_W, max(MIN_SCREEN_W, info.current_w - 80))
        height = min(DEFAULT_SCREEN_H, max(MIN_SCREEN_H, info.current_h - 100))
        return width, height

    def _resize_window(self, width: int, height: int):
        self.screen_w = max(MIN_SCREEN_W, int(width))
        self.screen_h = max(MIN_SCREEN_H, int(height))
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h), pygame.RESIZABLE)
        self.sidebar_rect = pygame.Rect(PANEL_X, 0, PANEL_W, self.screen_h)
        self.layout = self._compute_layout()
        self._sync_interactive_rects()

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
            return pygame.transform.smoothscale(img, (MAP_W, MAP_H))
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
        self.screen_mode = "MAP"
        self.layout = self._compute_layout()
        self._sync_interactive_rects()

    def run(self):
        running = True
        while running:
            self._poll_ai_worker()
            self._poll_chat_worker()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self._resize_window(event.w, event.h)
                elif event.type == pygame.KEYDOWN:
                    if self._handle_keydown(event):
                        continue
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_mousewheel(event)
            self._render()
            self.clock.tick(30)
        pygame.quit()

    def _handle_keydown(self, event) -> bool:
        if (self.ai_busy or self.chat_busy) and self.mode == "GAME":
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

        if self.chat_button_rect.collidepoint(pos) and self.ai_powers:
            self.screen_mode = "DIPLOMACY" if self.screen_mode == "MAP" else "MAP"
            if self.screen_mode == "MAP":
                self.input_active = False
            return

        if self.screen_mode == "DIPLOMACY":
            if self.send_rect.collidepoint(pos):
                self._send_current_chat()
                return
            for rect, recipient in self.recipient_rects:
                if rect.collidepoint(pos):
                    self.chat_recipient = recipient
                    self.conversation_scroll = 0
                    self.message_log = [f"Chat target set to {recipient}"]
                    return
            if self.chat_input_rect.collidepoint(pos):
                self.input_active = True
                return
            self.input_active = False
            return

        if self.ai_busy or self.chat_busy:
            self.message_log = ["AI is busy. Please wait..."]
            return

        if self.submit_rect.collidepoint(pos):
            self._submit_current_power()
            return
        if self.process_rect.collidepoint(pos):
            self._process_phase()
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
            center = self._location_center(loc)
            if center is None:
                continue
            dx = pos[0] - center[0]
            dy = pos[1] - center[1]
            if dx * dx + dy * dy <= self._unit_click_radius() ** 2:
                self.selected_location = loc
                self.message_log = [f"Selected {loc}"]
                return
        for loc, unit in self.game.state.units.items():
            center = self._location_center(loc)
            if center is None:
                continue
            dx = pos[0] - center[0]
            dy = pos[1] - center[1]
            if dx * dx + dy * dy <= self._unit_click_radius() ** 2:
                if unit.power == self.current_power:
                    self.selected_location = loc
                    self.message_log = [f"Selected {loc}"]
                else:
                    self.message_log = [f"{loc} belongs to {unit.power}"]
                return

    def _handle_mousewheel(self, event):
        if self.mode != "GAME" or self.screen_mode != "DIPLOMACY":
            return
        if not self.diplomacy_drawer_rect.collidepoint(pygame.mouse.get_pos()):
            return
        self.conversation_scroll += event.y * 48
        self.conversation_scroll = max(0, min(self.conversation_scroll, self.conversation_max_scroll))

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
        if self.chat_busy:
            self.message_log = ["A diplomatic reply is already in progress."]
            return
        if self.current_power not in self.human_powers:
            self.message_log = ["Only the current human-controlled power can send messages."]
            return
        if not self.chat_recipient:
            self.message_log = ["There is no AI power to talk to."]
            return

        sender = self.current_power
        recipient = self.chat_recipient
        content = self.chat_input.strip()
        self.chat_input = ""
        self.input_active = False
        self.conversation_scroll = 0
        self.chat_busy = True
        self.chat_error = None
        self.chat_result = None
        self.message_log = [f"Waiting for {recipient} to reply..."]
        self.chat_thread = threading.Thread(
            target=self._run_chat_worker,
            args=(sender, recipient, content),
            daemon=True,
        )
        self.chat_thread.start()

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
            pending_powers = []
            seen = set()
            scan_power = self.current_power
            while (
                scan_power in self.ai_powers
                and scan_power not in self.game.state.submitted_orders
                and scan_power not in seen
            ):
                pending_powers.append(scan_power)
                seen.add(scan_power)
                relevant = self._relevant_powers()
                if scan_power not in relevant:
                    break
                position = relevant.index(scan_power)
                if position >= len(relevant) - 1:
                    break
                scan_power = relevant[position + 1]

            if not pending_powers:
                break

            results = self.ai_director.choose_orders_for_powers(self.game, pending_powers)
            for power in pending_powers:
                result = results[power]
                self.power_drafts[power] = list(result.orders)
                self.game.set_orders(power, result.orders)
                self.message_log = [f"{power} AI: {result.reasoning}"]
                safety += 1
                if safety >= 16:
                    break

            if self.game.all_orders_submitted():
                self.diplomacy_feed = self.ai_director.memory.recent_public_lines()
                return

            previous_power = self.current_power
            self._advance_to_next_relevant_power()
            if self.current_power == previous_power:
                break

    def _start_ai_turns_async(self):
        if self.mode != "GAME" or self.ai_busy or self.chat_busy:
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

    def _run_chat_worker(self, sender: str, recipient: str, content: str):
        try:
            reply = self.ai_director.receive_message(
                self.game,
                sender,
                recipient,
                content,
            )
            self.chat_result = (recipient, reply)
        except Exception as exc:  # pragma: no cover - background UI safety
            self.chat_error = str(exc)
        finally:
            self.chat_busy = False

    def _poll_chat_worker(self):
        if self.chat_thread is not None and not self.chat_thread.is_alive():
            self.chat_thread = None
            if self.chat_error:
                self.message_log = [f"Chat error: {self.chat_error[:120]}"]
                self.chat_error = None
                return
            if self.chat_result is not None:
                recipient, reply = self.chat_result
                self.diplomacy_feed = self.ai_director.memory.recent_public_lines()
                self.conversation_scroll = 0
                self.message_log = [f"{recipient} replied: {reply[:64]}"]
                self.chat_result = None

    def _render(self):
        self.layout = self._compute_layout()
        self._sync_interactive_rects()
        self.screen.fill(MAP_EDGE)
        if self.mode == "SETUP":
            self._render_setup_overlay()
            pygame.display.flip()
            return

        if self.screen_mode == "MAP":
            if self.map_image is not None:
                map_rect = self.layout["map_view"]
                scaled = pygame.transform.smoothscale(self.map_image, map_rect.size)
                self.screen.blit(scaled, map_rect.topleft)
                self._render_map_finish()
            else:
                pygame.draw.rect(self.screen, (40, 34, 28), self.layout["map_view"], border_radius=18)
            self._render_order_overlay()
            self._render_units()
            self._render_special_markers()
            self._render_header_bar()
            self._render_left_rail()
            self._render_right_rail()
            self._render_bottom_strip()
        else:
            self._render_diplomacy_view()
        pygame.display.flip()

    def _render_map_finish(self):
        map_rect = self.layout["map_view"]
        overlay = pygame.Surface((map_rect.w, map_rect.h), pygame.SRCALPHA)
        overlay.fill((72, 46, 24, 20))
        pygame.draw.rect(overlay, (10, 10, 10, 65), pygame.Rect(0, 0, map_rect.w, map_rect.h), 18)
        pygame.draw.rect(overlay, (250, 230, 174, 28), pygame.Rect(10, 10, map_rect.w - 20, map_rect.h - 20), 3)
        self.screen.blit(overlay, map_rect.topleft)
        pygame.draw.rect(self.screen, (18, 20, 24), map_rect, 4, border_radius=18)

    def _compute_layout(self):
        if self.screen_mode == "DIPLOMACY":
            return self._compute_diplomacy_layout()
        return self._compute_main_layout()

    def _compute_main_layout(self):
        header_rect = pygame.Rect(UI_MARGIN, UI_MARGIN, self.screen_w - UI_MARGIN * 2, TOP_BAR_H)
        bottom_rect = pygame.Rect(
            UI_MARGIN,
            self.screen_h - UI_MARGIN - BOTTOM_BAR_H,
            self.screen_w - UI_MARGIN * 2,
            BOTTOM_BAR_H,
        )
        left_rail_rect = pygame.Rect(
            UI_MARGIN,
            header_rect.bottom + UI_GAP,
            LEFT_RAIL_W,
            bottom_rect.y - header_rect.bottom - UI_GAP * 2,
        )
        right_rail_rect = pygame.Rect(
            self.screen_w - UI_MARGIN - RIGHT_RAIL_W,
            header_rect.bottom + UI_GAP,
            RIGHT_RAIL_W,
            left_rail_rect.h,
        )
        map_area_rect = pygame.Rect(
            left_rail_rect.right + UI_GAP,
            left_rail_rect.y,
            right_rail_rect.x - left_rail_rect.right - UI_GAP * 2,
            left_rail_rect.h,
        )
        map_view_rect = self._fit_map_rect(map_area_rect, MAP_W, MAP_H)

        left_inner_x = left_rail_rect.x
        left_inner_y = left_rail_rect.y
        selection_rect = pygame.Rect(left_inner_x, left_inner_y, left_rail_rect.w, 216)
        help_rect = pygame.Rect(
            left_inner_x,
            selection_rect.bottom + UI_GAP,
            left_rail_rect.w,
            left_rail_rect.bottom - selection_rect.bottom - UI_GAP,
        )

        right_inner_x = right_rail_rect.x
        right_inner_y = right_rail_rect.y
        right_inner_w = right_rail_rect.w
        controls_rect = pygame.Rect(
            right_inner_x,
            right_rail_rect.bottom - 112,
            right_inner_w,
            112,
        )
        draft_rect = pygame.Rect(
            right_inner_x,
            controls_rect.y - UI_GAP - 118,
            right_inner_w,
            118,
        )
        orders_rect = pygame.Rect(
            right_inner_x,
            right_inner_y,
            right_inner_w,
            draft_rect.y - right_inner_y - UI_GAP,
        )
        chat_button_rect = pygame.Rect(header_rect.right - 108, header_rect.y + 12, 94, 36)

        return {
            "header": header_rect,
            "bottom": bottom_rect,
            "left_rail": left_rail_rect,
            "right_rail": right_rail_rect,
            "map_area": map_area_rect,
            "map_view": map_view_rect,
            "selection": selection_rect,
            "help": help_rect,
            "orders": orders_rect,
            "draft": draft_rect,
            "controls": controls_rect,
            "chat_button": chat_button_rect,
        }

    def _compute_diplomacy_layout(self):
        header_rect = pygame.Rect(UI_MARGIN, UI_MARGIN, self.screen_w - UI_MARGIN * 2, TOP_BAR_H)
        composer_rect = pygame.Rect(
            UI_MARGIN,
            self.screen_h - UI_MARGIN - 76,
            self.screen_w - UI_MARGIN * 2,
            76,
        )
        content_top = header_rect.bottom + UI_GAP
        content_bottom = composer_rect.y - UI_GAP
        power_list_rect = pygame.Rect(UI_MARGIN, content_top, DIP_LIST_W, content_bottom - content_top)
        side_rect = pygame.Rect(self.screen_w - UI_MARGIN - DIP_SIDE_W, content_top, DIP_SIDE_W, content_bottom - content_top)
        history_rect = pygame.Rect(
            power_list_rect.right + UI_GAP,
            content_top,
            side_rect.x - power_list_rect.right - UI_GAP * 2,
            content_bottom - content_top,
        )
        chat_button_rect = pygame.Rect(header_rect.x + 14, header_rect.y + 12, 126, 36)
        return {
            "header": header_rect,
            "composer": composer_rect,
            "power_list": power_list_rect,
            "history": history_rect,
            "side": side_rect,
            "chat_button": chat_button_rect,
        }

    def _sync_interactive_rects(self):
        self.chat_button_rect = self.layout.get("chat_button", pygame.Rect(0, 0, 0, 0))
        self.drawer_toggle_rect = self.chat_button_rect
        if self.screen_mode == "MAP":
            controls_rect = self.layout.get("controls", pygame.Rect(0, 0, 0, 0))
            self.submit_rect = pygame.Rect(controls_rect.x + 14, controls_rect.bottom - 50, 118, 38)
            self.process_rect = pygame.Rect(controls_rect.right - 132, controls_rect.bottom - 50, 118, 38)
            self.diplomacy_drawer_rect = pygame.Rect(0, 0, 0, 0)
            self.recipient_rects = []
            self.chat_input_rect = pygame.Rect(0, 0, 0, 0)
            self.send_rect = pygame.Rect(0, 0, 0, 0)
            return

        composer = self.layout.get("composer", pygame.Rect(0, 0, 0, 0))
        self.submit_rect = pygame.Rect(0, 0, 0, 0)
        self.process_rect = pygame.Rect(0, 0, 0, 0)
        self.diplomacy_drawer_rect = self.layout.get("history", pygame.Rect(0, 0, 0, 0))
        self.chat_input_rect = pygame.Rect(composer.x + 14, composer.bottom - 48, composer.w - 118, 34)
        self.send_rect = pygame.Rect(self.chat_input_rect.right + 10, composer.bottom - 48, 80, 34)
        if not self.ai_powers:
            self.chat_input_rect = pygame.Rect(0, 0, 0, 0)
            self.send_rect = pygame.Rect(0, 0, 0, 0)

    def _fit_map_rect(self, container, source_w, source_h):
        scale = min(container.w / source_w, container.h / source_h)
        width = max(1, int(source_w * scale))
        height = max(1, int(source_h * scale))
        x = container.x + (container.w - width) // 2
        y = container.y + (container.h - height) // 2
        return pygame.Rect(x, y, width, height)

    def _fit_text(self, text, font, width):
        if font.size(text)[0] <= width:
            return text
        trimmed = text
        while trimmed and font.size(trimmed + "...")[0] > width:
            trimmed = trimmed[:-1]
        return trimmed + "..." if trimmed else "..."

    def _wrap_text(self, text, font, width, max_lines=None):
        if width is None or width <= 0:
            return [text]

        paragraphs = str(text).splitlines() or [""]
        lines = []

        for paragraph in paragraphs:
            if not paragraph:
                lines.append("")
                continue

            tokens = paragraph.split(" ")
            current = ""
            for token in tokens:
                candidate = token if not current else f"{current} {token}"
                if font.size(candidate)[0] <= width:
                    current = candidate
                    continue

                if current:
                    lines.append(current)
                    current = ""

                if font.size(token)[0] <= width:
                    current = token
                    continue

                chunk = ""
                for char in token:
                    candidate = chunk + char
                    if chunk and font.size(candidate)[0] > width:
                        lines.append(chunk)
                        chunk = char
                    else:
                        chunk = candidate
                current = chunk

            if current or not lines:
                lines.append(current)

        if max_lines is not None and len(lines) > max_lines:
            visible = lines[:max_lines]
            visible[-1] = self._fit_text(visible[-1], font, width)
            return visible
        return lines

    def _draw_text(self, text, font, color, pos, max_width=None, max_lines=1, line_height=None):
        lines = (
            self._wrap_text(text, font, max_width, max_lines=max_lines)
            if max_width is not None or max_lines != 1
            else [text]
        )
        spacing = line_height or font.get_linesize()
        for index, line in enumerate(lines):
            self.screen.blit(font.render(line, True, color), (pos[0], pos[1] + index * spacing))
        return len(lines) * spacing

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

    def _draw_inner_panel(self, rect, fill=(24, 31, 39), border=CARD_BORDER, radius=10):
        pygame.draw.rect(self.screen, fill, rect, border_radius=radius)
        pygame.draw.rect(self.screen, border, rect, 1, border_radius=radius)

    def _draw_chip(self, rect, label, fill, active=False, text_color=WHITE):
        pygame.draw.rect(self.screen, fill, rect, border_radius=9)
        pygame.draw.rect(self.screen, GOLD if active else (20, 24, 28), rect, 2 if active else 1, border_radius=9)
        text = self.tiny.render(label, True, text_color)
        self.screen.blit(text, text.get_rect(center=rect.center))

    def _set_clip(self, rect):
        previous = self.screen.get_clip()
        self.screen.set_clip(rect)
        return previous

    def _restore_clip(self, previous):
        self.screen.set_clip(previous)

    def _power_color(self, power):
        return POWER_COLORS.get(power, (90, 90, 90))

    def _location_center(self, location):
        map_rect = self.layout.get("map_view")
        if not map_rect:
            return None
        point = self.unit_positions.get(base_location(location))
        if not point:
            return None
        x = map_rect.x + int(point["x"] * map_rect.w / MAP_W)
        y = map_rect.y + int(point["y"] * map_rect.h / MAP_H)
        return (x, y)

    def _map_scale(self):
        map_rect = self.layout.get("map_view")
        if not map_rect:
            return 1.0
        return min(map_rect.w / MAP_W, map_rect.h / MAP_H)

    def _unit_click_radius(self):
        return max(14, int(17 * self._map_scale()))

    def _ordered_possible_orders(self, location, power):
        def order_priority(order_text):
            parsed = parse_order(order_text)
            if isinstance(parsed, MoveOrder):
                return (0, order_text)
            if isinstance(parsed, ConvoyOrder):
                return (1, order_text)
            if isinstance(parsed, SupportMoveOrder):
                return (2, order_text)
            if isinstance(parsed, SupportHoldOrder):
                return (3, order_text)
            if isinstance(parsed, HoldOrder):
                return (4, order_text)
            return (5, order_text)

        return sorted(self.game.get_possible_orders(location, power), key=order_priority)

    def _chat_history_lines(self, limit: int = 6):
        if self.current_power not in POWERS:
            return ["Diplomatic channels are quiet."]
        messages = self.ai_director.memory.recent_messages_for(self.current_power, limit=limit)
        if not messages:
            if self.diplomacy_feed:
                return self.diplomacy_feed[-min(limit, len(self.diplomacy_feed)) :]
            return ["Diplomatic channels are quiet."]

        lines = []
        for message in messages[-limit:]:
            sender = "YOU" if message.sender == self.current_power else message.sender[:3]
            recipient = "YOU" if message.recipient == self.current_power else message.recipient[:3]
            lines.append(f"{sender} -> {recipient}: {message.content}")
        return lines

    def _conversation_lines(self, limit: int | None = 18):
        if self.current_power not in POWERS or not self.chat_recipient:
            return ["Select an AI power to review diplomacy history."]
        messages = self.ai_director.memory.recent_messages_for(self.current_power, limit=500)
        lines = []
        for message in messages:
            participants = {message.sender, message.recipient}
            if self.current_power not in participants or self.chat_recipient not in participants:
                continue
            sender = "YOU" if message.sender == self.current_power else message.sender
            recipient = "YOU" if message.recipient == self.current_power else message.recipient
            lines.append(f"{message.phase} | {sender} -> {recipient}: {message.content}")
        if limit is not None:
            lines = lines[-limit:]
        return lines or ["No direct conversation with this power yet."]

    def _relationship_notes(self, limit: int = 6):
        notes = []
        if self.chat_recipient:
            notes.extend(
                f"Promise: {commitment.sender} -> {commitment.recipient} at {commitment.location}"
                for commitment in self.ai_director.memory.commitments
                if not commitment.resolved
                and {commitment.sender, commitment.recipient} == {self.current_power, self.chat_recipient}
            )
            notes.extend(
                betrayal
                for betrayal in self.ai_director.memory.betrayals
                if self.current_power in betrayal or self.chat_recipient in betrayal
            )
        return notes[:limit] or ["No promises or betrayals recorded yet."]

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
        surface = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
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
        scale = self._map_scale()
        outer = max(12, int(20 * scale))
        inner = max(9, int(15 * scale))
        shadow = (center[0] + max(2, int(3 * scale)), center[1] + max(2, int(4 * scale)))
        pygame.draw.circle(self.screen, (14, 16, 18), shadow, outer + 1)
        pygame.draw.circle(self.screen, (237, 219, 171), center, outer)
        pygame.draw.circle(self.screen, GOLD_DARK, center, outer, max(1, int(2 * scale)))
        pygame.draw.circle(self.screen, color, center, inner)
        pygame.draw.circle(self.screen, (255, 244, 220), (center[0] - max(2, int(4 * scale)), center[1] - max(2, int(5 * scale))), max(3, int(5 * scale)))
        badge_size = max(12, int(16 * scale))
        badge = pygame.Rect(center[0] - badge_size // 2, center[1] - badge_size // 2, badge_size, badge_size)
        pygame.draw.rect(self.screen, (246, 236, 213), badge, border_radius=4)
        pygame.draw.rect(self.screen, (99, 81, 49), badge, 1, border_radius=4)
        text = self.small.render("A", True, BLACK)
        self.screen.blit(text, text.get_rect(center=(center[0], center[1] + 1)))
        if selected:
            pygame.draw.circle(self.screen, (255, 223, 125), center, outer + max(5, int(6 * scale)), max(2, int(4 * scale)))
            pygame.draw.circle(self.screen, (255, 245, 196), center, outer + max(9, int(11 * scale)), 1)

    def _draw_fleet_piece(self, center, color, selected):
        scale = self._map_scale()
        x16 = max(10, int(16 * scale))
        x20 = max(12, int(20 * scale))
        x12 = max(8, int(12 * scale))
        x15 = max(10, int(15 * scale))
        x7 = max(5, int(7 * scale))
        shadow_points = [
            (center[0] - x16 - 1, center[1] + max(5, int(8 * scale))),
            (center[0] + x16 + 1, center[1] + max(5, int(8 * scale))),
            (center[0] + x20 + 1, center[1] - max(3, int(4 * scale))),
            (center[0], center[1] - max(12, int(18 * scale))),
            (center[0] - x20 - 1, center[1] - max(3, int(4 * scale))),
        ]
        pygame.draw.polygon(self.screen, (14, 16, 18), [(x + max(2, int(3 * scale)), y + max(2, int(4 * scale))) for x, y in shadow_points])
        ring = [
            (center[0] - x16, center[1] + max(5, int(7 * scale))),
            (center[0] + x16, center[1] + max(5, int(7 * scale))),
            (center[0] + x20, center[1] - max(3, int(4 * scale))),
            (center[0], center[1] - max(11, int(17 * scale))),
            (center[0] - x20, center[1] - max(3, int(4 * scale))),
        ]
        pygame.draw.polygon(self.screen, (237, 219, 171), ring)
        pygame.draw.polygon(self.screen, GOLD_DARK, ring, max(1, int(2 * scale)))
        inner = [
            (center[0] - x12, center[1] + max(3, int(5 * scale))),
            (center[0] + x12, center[1] + max(3, int(5 * scale))),
            (center[0] + x15, center[1] - max(2, int(3 * scale))),
            (center[0], center[1] - max(9, int(13 * scale))),
            (center[0] - x15, center[1] - max(2, int(3 * scale))),
        ]
        pygame.draw.polygon(self.screen, color, inner)
        pygame.draw.circle(self.screen, (246, 236, 213), center, x7)
        pygame.draw.circle(self.screen, (99, 81, 49), center, x7, 1)
        text = self.small.render("F", True, BLACK)
        self.screen.blit(text, text.get_rect(center=(center[0], center[1] + 1)))
        if selected:
            ring_outer = max(17, int(26 * scale))
            pygame.draw.circle(self.screen, (255, 223, 125), center, ring_outer, max(2, int(4 * scale)))
            pygame.draw.circle(self.screen, (255, 245, 196), center, ring_outer + max(4, int(5 * scale)), 1)

    def _render_units(self):
        for loc, unit in self.game.state.units.items():
            center = self._location_center(loc)
            if center is None:
                continue
            color = self._power_color(unit.power)
            if unit.unit_type == "A":
                self._draw_army_piece(center, color, loc == self.selected_location)
            else:
                self._draw_fleet_piece(center, color, loc == self.selected_location)
            label = base_location(loc)
            text = self.tiny.render(label, True, BLACK)
            scale = self._map_scale()
            pill = pygame.Rect(center[0] + max(12, int(19 * scale)), center[1] - max(7, int(10 * scale)), text.get_width() + 10, 19)
            pygame.draw.rect(self.screen, (244, 232, 198), pill, border_radius=8)
            pygame.draw.rect(self.screen, (89, 73, 46), pill, 1, border_radius=8)
            self.screen.blit(text, (pill.x + 5, pill.y + 3))

    def _render_special_markers(self):
        if self.game.state.phase == "RETREATS":
            for loc in self.game.get_orderable_locations(self.current_power):
                center = self._location_center(loc)
                if center is None:
                    continue
                radius = max(12, int(20 * self._map_scale()))
                arm = max(7, int(12 * self._map_scale()))
                pygame.draw.circle(self.screen, RED, center, radius, max(2, int(3 * self._map_scale())))
                pygame.draw.line(self.screen, RED, (center[0] - arm, center[1] - arm), (center[0] + arm, center[1] + arm), max(2, int(3 * self._map_scale())))
                pygame.draw.line(self.screen, RED, (center[0] - arm, center[1] + arm), (center[0] + arm, center[1] - arm), max(2, int(3 * self._map_scale())))

        if self.game.state.phase == "ADJUSTMENTS" and self.game.get_adjustment_requirement(self.current_power) > 0:
            for loc in self.game.get_orderable_locations(self.current_power):
                center = self._location_center(loc)
                if center is None:
                    continue
                pygame.draw.circle(self.screen, GREEN, center, max(10, int(18 * self._map_scale())), max(2, int(3 * self._map_scale())))
                pygame.draw.circle(self.screen, BLUE, center, max(4, int(6 * self._map_scale())))

    def _render_setup_overlay(self):
        shade = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        shade.fill((10, 10, 14, 170))
        self.screen.blit(shade, (0, 0))

        card_w = min(970, self.screen_w - UI_MARGIN * 2)
        card_h = min(760, self.screen_h - UI_MARGIN * 2)
        card = pygame.Rect(
            (self.screen_w - card_w) // 2,
            (self.screen_h - card_h) // 2,
            card_w,
            card_h,
        )
        self._draw_card(card, "Campaign Setup")
        self._draw_text("Choose 0-6 human powers", self.title, INK, (card.x + 24, card.y + 42))
        self._draw_text(
            "Unselected powers will use DeepSeek-backed diplomacy AI.",
            self.small,
            INK_MUTED,
            (card.x + 26, card.y + 86),
            520,
            max_lines=2,
        )

        self.setup_chip_rects = []
        x = card.x + 30
        y = card.y + 138
        chip_w = max(120, min(184, (card.w - 100) // 3))
        chip_h = 66 if card.h < 720 else 78
        chip_gap = max(12, (card.w - 60 - chip_w * 3) // 2)
        row_gap = 82 if card.h < 720 else 104
        for idx, power in enumerate(POWERS):
            rect = pygame.Rect(x, y, chip_w, chip_h)
            active = power in self.setup_human_powers
            fill = self._power_color(power)
            if not active:
                fill = tuple(max(45, component // 2) for component in fill)
            pygame.draw.rect(self.screen, fill, rect, border_radius=14)
            pygame.draw.rect(self.screen, GOLD if active else CARD_BORDER, rect, 3 if active else 1, border_radius=14)
            self._draw_text(power, self.big, BLACK if power in ("RUSSIA", "TURKEY", "FRANCE") else WHITE, (rect.x + 12, rect.y + 14), rect.w - 24)
            self._draw_text("Human" if active else "AI", self.small, BLACK if active else INK_MUTED, (rect.x + 14, rect.bottom - 28), rect.w - 28)
            self.setup_chip_rects.append((rect, power))
            x += chip_w + chip_gap
            if idx in (2, 5):
                x = card.x + 30
                y += row_gap

        guide_y = min(card.y + 470, y + chip_h + 28)
        self._draw_text(f"Human powers: {len(self.setup_human_powers)}", self.big, INK, (card.x + 30, guide_y), 260)
        summary = ", ".join(sorted(self.setup_human_powers)) or "None"
        self._draw_text(summary, self.small, INK_MUTED, (card.x + 30, guide_y + 34), card.w - 60, max_lines=2)

        tip_lines = [
            "Players can chat with AI during the orders phase.",
            "AI powers also negotiate privately and track trust, fear, and betrayals.",
            "Promises about supply centers can affect future moves.",
        ]
        tip_y = guide_y + 90
        for line in tip_lines:
            used = self._draw_text(line, self.small, INK, (card.x + 30, tip_y), card.w - 60, max_lines=2)
            tip_y += used + 2

        can_start = len(self.setup_human_powers) <= 6
        self.setup_start_rect = pygame.Rect(card.right - 170, card.bottom - 58, 140, 44)
        self._draw_button(self.setup_start_rect, "Start Match", (208, 179, 104), can_start)
        self._draw_text(
            "Click a country to toggle Human / AI.",
            self.small,
            INK_MUTED,
            (card.x + 30, self.setup_start_rect.y + 12),
            max(220, self.setup_start_rect.x - card.x - 46),
            max_lines=2,
        )

    def _render_header_bar(self):
        rect = self.layout["header"]
        self._draw_card(rect)

        left = rect.x + 18
        self._draw_text("DIPLOMACY", self.big, INK, (left, rect.y + 9), 210)
        self._draw_text("Map-first command view", self.tiny, INK_MUTED, (left + 2, rect.y + 36), 180, max_lines=1)

        phase_rect = pygame.Rect(rect.x + 228, rect.y + 12, 282, 36)
        self._draw_inner_panel(phase_rect, fill=(22, 28, 35), border=GOLD_DARK)
        self._draw_text(self.game.get_current_phase(), self.font, GOLD, (phase_rect.x + 12, phase_rect.y + 8), phase_rect.w - 24)

        power_rect = pygame.Rect(phase_rect.right + 12, rect.y + 12, 236, 36)
        self._draw_inner_panel(power_rect, fill=(22, 28, 35), border=self._power_color(self.current_power))
        control_label = "AI" if self.current_power in self.ai_powers else "HUMAN"
        self._draw_text(f"{self.current_power} ({control_label})", self.small, INK, (power_rect.x + 12, power_rect.y + 9), power_rect.w - 24)

        chip_x = power_rect.right + 18
        chip_y = rect.y + 12
        for power in POWERS:
            chip = pygame.Rect(chip_x, chip_y, 40, 22)
            active = power == self.current_power
            text_color = BLACK if power in ("RUSSIA", "TURKEY") else WHITE
            self._draw_chip(chip, power[:2], self._power_color(power), active=active, text_color=text_color)
            if power in self.game.state.submitted_orders:
                pygame.draw.circle(self.screen, SUCCESS, (chip.right - 5, chip.y + 5), 4)
            chip_x += 46

        status_text = f"H {len(self.human_powers)} | AI {len(self.ai_powers)}"
        if self.ai_busy:
            status_text += " | Thinking"
        if self.chat_busy:
            status_text += " | Replying"
        self._draw_text(status_text, self.tiny, INK_MUTED, (self.chat_button_rect.x - 140, rect.y + 23), 126, max_lines=1)

        if self.ai_powers:
            self._draw_button(self.chat_button_rect, "Diplomacy", (118, 158, 181), True)

    def _render_left_rail(self):
        self._render_selection_card(self.layout["selection"])
        self._render_help_card(self.layout["help"])

    def _render_right_rail(self):
        self._render_orders_card(self.layout["orders"])
        self._render_draft_card(self.layout["draft"])
        self._render_controls_card(self.layout["controls"])

    def _render_bottom_strip(self):
        rect = self.layout["bottom"]
        self._draw_inner_panel(rect, fill=(19, 25, 32), border=(74, 84, 95), radius=10)
        status_line = self.message_log[0] if self.message_log else "Ready."
        self._draw_text(status_line, self.small, INK, (rect.x + 12, rect.y + 13), rect.w - 24, max_lines=1)

    def _render_diplomacy_view(self):
        self._render_diplomacy_header()
        self._render_diplomacy_power_list(self.layout["power_list"])
        self._render_diplomacy_history(self.layout["history"])
        self._render_diplomacy_side(self.layout["side"])
        self._render_diplomacy_composer(self.layout["composer"])

    def _render_diplomacy_header(self):
        rect = self.layout["header"]
        self._draw_card(rect)
        self._draw_button(self.chat_button_rect, "Back To Map", (118, 158, 181), True)
        self._draw_text("Diplomacy", self.big, INK, (self.chat_button_rect.right + 20, rect.y + 9), 220)
        self._draw_text(self.game.get_current_phase(), self.small, GOLD, (self.chat_button_rect.right + 22, rect.y + 35), 260, max_lines=1)

        power_rect = pygame.Rect(rect.centerx - 140, rect.y + 12, 280, 36)
        self._draw_inner_panel(power_rect, fill=(22, 28, 35), border=self._power_color(self.current_power))
        self._draw_text(f"{self.current_power} diplomacy desk", self.small, INK, (power_rect.x + 12, power_rect.y + 9), power_rect.w - 24, max_lines=1)

        target_text = f"Talking to {self.chat_recipient}" if self.chat_recipient else "No recipient selected"
        self._draw_text(target_text, self.small, INK_MUTED, (rect.right - 260, rect.y + 21), 230, max_lines=1)

    def _render_diplomacy_power_list(self, rect):
        self._draw_card(rect, "Powers")
        x = rect.x + 14
        y = rect.y + 34
        inner_w = rect.w - 28
        self.recipient_rects = []
        previous_clip = self._set_clip(rect.inflate(-8, -8))
        recipients = sorted(self.ai_powers - {self.current_power})
        if not recipients:
            self._draw_text("No AI powers available.", self.small, INK_MUTED, (x, y), inner_w, max_lines=3)
            self._restore_clip(previous_clip)
            return
        if self.chat_recipient not in recipients:
            self.chat_recipient = recipients[0]
            self.conversation_scroll = 0
        for recipient in recipients:
            chip = pygame.Rect(x, y, inner_w, 34)
            active = recipient == self.chat_recipient
            fill = self._power_color(recipient)
            self._draw_chip(chip, recipient, fill, active=active, text_color=BLACK if recipient in ("RUSSIA", "TURKEY") else WHITE)
            self.recipient_rects.append((chip, recipient))
            y += 42
        self._restore_clip(previous_clip)

    def _render_diplomacy_history(self, rect):
        self._draw_card(rect, "Conversation")
        x = rect.x + 14
        y = rect.y + 34
        inner_w = rect.w - 28
        previous_clip = self._set_clip(rect.inflate(-8, -8))
        history_box = pygame.Rect(x, y, inner_w, rect.h - 48)
        self._draw_inner_panel(history_box, fill=(20, 26, 33), border=(74, 84, 95), radius=10)
        lines = self._conversation_lines(limit=None)
        text_width = history_box.w - 28
        line_height = 16
        gap = 8
        wrapped_blocks = [
            self._wrap_text(line, self.small, text_width, max_lines=None)
            for line in lines
        ]
        content_height = sum(len(block) * line_height + gap for block in wrapped_blocks)
        visible_height = history_box.h - 20
        self.conversation_max_scroll = max(0, content_height - visible_height)
        self.conversation_scroll = max(0, min(self.conversation_scroll, self.conversation_max_scroll))

        if self.conversation_max_scroll == 0:
            line_y = history_box.y + 10
        else:
            line_y = history_box.bottom - 10 - content_height + self.conversation_scroll
        for block in wrapped_blocks:
            block_height = len(block) * line_height
            if line_y + block_height >= history_box.y + 8 and line_y <= history_box.bottom - 8:
                for index, text in enumerate(block):
                    draw_y = line_y + index * line_height
                    if history_box.y + 6 <= draw_y <= history_box.bottom - line_height:
                        self.screen.blit(
                            self.small.render(text, True, INK),
                            (history_box.x + 10, draw_y),
                        )
            line_y += block_height + gap

        if self.conversation_max_scroll > 0:
            track = pygame.Rect(history_box.right - 9, history_box.y + 8, 3, history_box.h - 16)
            pygame.draw.rect(self.screen, (68, 78, 88), track, border_radius=2)
            thumb_h = max(24, int(track.h * visible_height / max(content_height, 1)))
            thumb_range = max(1, track.h - thumb_h)
            thumb_y = track.bottom - thumb_h - int(
                thumb_range * (self.conversation_scroll / self.conversation_max_scroll)
            )
            pygame.draw.rect(self.screen, GOLD, pygame.Rect(track.x - 1, thumb_y, 5, thumb_h), border_radius=3)
        self._restore_clip(previous_clip)

    def _render_diplomacy_side(self, rect):
        self._draw_card(rect, "Relations")
        x = rect.x + 14
        y = rect.y + 34
        inner_w = rect.w - 28
        previous_clip = self._set_clip(rect.inflate(-8, -8))
        snapshot = {row["power"]: row for row in self.ai_director.memory.relationship_snapshot(self.current_power)}
        row = snapshot.get(self.chat_recipient or "", {})
        if row:
            self._draw_text(f"Trust: {row['trust']:+.2f}", self.small, INK, (x, y), inner_w, max_lines=1)
            y += 20
            self._draw_text(f"Fear: {row['fear']:+.2f}", self.small, INK, (x, y), inner_w, max_lines=1)
            y += 28
        else:
            self._draw_text("No active diplomatic data yet.", self.small, INK_MUTED, (x, y), inner_w, max_lines=3)
            y += 44

        self._draw_text("Notes", self.tiny, GOLD, (x, y), inner_w, max_lines=1)
        y += 18
        notes = self._relationship_notes(limit=6)
        for note in notes:
            if y > rect.bottom - 24:
                break
            used = self._draw_text(note, self.tiny, INK_MUTED, (x, y), inner_w, max_lines=2, line_height=14)
            y += used + 4
        self._restore_clip(previous_clip)

    def _render_diplomacy_composer(self, rect):
        self._draw_card(rect, "Message")
        x = rect.x + 14
        inner_w = rect.w - 28
        self._draw_text(
            f"Send as {self.current_power} to {self.chat_recipient or 'nobody'}",
            self.tiny,
            INK_MUTED,
            (x, rect.y + 12),
            inner_w,
            max_lines=1,
        )
        self._draw_inner_panel(self.chat_input_rect, fill=(24, 31, 39), border=GOLD if self.input_active else CARD_BORDER, radius=8)
        placeholder = self.chat_input if self.chat_input else "Type a diplomatic message..."
        self._draw_text(placeholder, self.small, INK if self.chat_input else INK_MUTED, (self.chat_input_rect.x + 10, self.chat_input_rect.y + 8), self.chat_input_rect.w - 20, max_lines=1)
        send_enabled = (
            bool(self.chat_recipient)
            and self.current_power in self.human_powers
            and not self.ai_busy
            and not self.chat_busy
        )
        self._draw_button(self.send_rect, "Send", (118, 158, 181), send_enabled)

    def _render_help_card(self, rect):
        self._draw_card(rect, "Phase Guide")
        x = rect.x + 14
        y = rect.y + 34
        inner_w = rect.w - 28
        previous_clip = self._set_clip(rect.inflate(-8, -8))
        if self.game.state.phase == "RETREATS":
            hint = "Retreats: choose one dislodged unit, then select a legal retreat or disband."
        elif self.game.state.phase == "ADJUSTMENTS":
            req = self.game.get_adjustment_requirement(self.current_power)
            if req > 0:
                hint = "Adjustments: select a home center to build a new unit."
            else:
                hint = "Adjustments: select one of your units to disband."
        else:
            hint = "Orders: select one of your units on the map to see only legal commands."
        used = self._draw_text(hint, self.small, INK, (x, y), inner_w, max_lines=5)
        y += used + 10
        self._draw_text("Legend", self.tiny, GOLD, (x, y), inner_w)
        y += 18
        for line in ("Arrow = move", "Double ring = hold", "Dashed line = convoy", "Red X = retreat target"):
            if y > rect.bottom - 22:
                break
            self._draw_text(line, self.tiny, INK_MUTED, (x, y), inner_w, max_lines=1)
            y += 16
        self._restore_clip(previous_clip)

    def _render_selection_card(self, rect):
        self._draw_card(rect, "Selection")
        x = rect.x + 14
        y = rect.y + 34
        inner_w = rect.w - 28
        previous_clip = self._set_clip(rect.inflate(-8, -8))

        unit = None
        if self.selected_location:
            unit = self.game.state.units.get(self.selected_location) or self.game.state.dislodged_units.get(self.selected_location)

        if unit:
            unit_label = "Army" if unit.unit_type == "A" else "Fleet"
            self._draw_text(base_location(unit.location), self.big, INK, (x, y), inner_w)
            y += 30
            self._draw_text(f"{unit_label} of {unit.power}", self.small, INK_MUTED, (x, y), inner_w, max_lines=2)
            y += 34
            if self.selected_location in self.game.get_orderable_locations(self.current_power):
                self._draw_text("This unit is ready for orders.", self.small, SUCCESS, (x, y), inner_w, max_lines=2)
            else:
                self._draw_text("This unit is not orderable this step.", self.small, WARNING, (x, y), inner_w, max_lines=2)
        else:
            prompt = "Select one of your units on the map."
            if self.game.state.phase == "RETREATS":
                prompt = "Select a dislodged unit to retreat or disband."
            elif self.game.state.phase == "ADJUSTMENTS":
                if self.game.get_adjustment_requirement(self.current_power) > 0:
                    prompt = "Select a home center to build."
                elif self.game.get_adjustment_requirement(self.current_power) < 0:
                    prompt = "Select one of your units to disband."
            self._draw_text(prompt, self.small, INK_MUTED, (x, y), inner_w, max_lines=6)
        self._restore_clip(previous_clip)

    def _render_orders_card(self, rect):
        self._draw_card(rect, "Possible Orders")
        self.order_option_rects = []
        x = rect.x + 14
        y = rect.y + 34
        inner_w = rect.w - 28
        previous_clip = self._set_clip(rect.inflate(-8, -8))

        if self.current_power in self.ai_powers:
            self._draw_text(
                "AI powers negotiate and submit automatically when their turn comes up.",
                self.small,
                INK_MUTED,
                (x, y),
                inner_w,
                max_lines=4,
            )
            self._restore_clip(previous_clip)
            return

        if not self.selected_location or self.selected_location not in self.game.get_orderable_locations(self.current_power):
            prompt = "Choose a unit first. The command deck will list only legal orders for the current phase."
            self._draw_text(prompt, self.small, INK_MUTED, (x, y), inner_w, max_lines=4)
            self._restore_clip(previous_clip)
            return

        orders = self._ordered_possible_orders(self.selected_location, self.current_power)
        row_pitch = 20
        row_height = 17
        rows_per_column = max(1, (rect.h - 42) // row_pitch)
        if inner_w >= 600 and len(orders) > rows_per_column * 2:
            column_count = 3
        elif inner_w >= 420:
            column_count = 2
        else:
            column_count = 1
        visible_limit = rows_per_column * column_count
        column_gap = 10
        column_width = (inner_w - column_gap * (column_count - 1)) // column_count
        visible_orders = list(orders[:visible_limit])
        if len(orders) > visible_limit and visible_orders:
            hold_order = next((order for order in orders if isinstance(parse_order(order), HoldOrder)), None)
            if hold_order and hold_order not in visible_orders:
                visible_orders[-1] = hold_order

        for index, order in enumerate(visible_orders):
            col = index // rows_per_column
            row = index % rows_per_column
            row_rect = pygame.Rect(
                x + col * (column_width + column_gap),
                y + row * row_pitch,
                column_width,
                row_height,
            )
            hover = row_rect.collidepoint(pygame.mouse.get_pos())
            fill = (72, 88, 103) if hover else (56, 69, 82)
            self._draw_inner_panel(row_rect, fill=fill, border=GOLD_DARK, radius=7)
            self._draw_text(order, self.tiny, INK, (row_rect.x + 8, row_rect.y + 4), row_rect.w - 16, max_lines=1)
            self.order_option_rects.append((row_rect, order))

        hidden_count = len(orders) - len(visible_orders)
        if hidden_count > 0:
            footer_y = rect.bottom - 24
            self._draw_text(f"+ {hidden_count} more legal orders for this unit", self.tiny, INK_MUTED, (x, footer_y), inner_w, max_lines=1)
        self._restore_clip(previous_clip)

    def _render_draft_card(self, rect):
        self._draw_card(rect, "Draft Orders")
        x = rect.x + 14
        y = rect.y + 30
        inner_w = rect.w - 28
        drafts = self.power_drafts[self.current_power]
        previous_clip = self._set_clip(rect.inflate(-8, -8))

        if not drafts:
            self._draw_text("No draft orders yet.", self.small, INK_MUTED, (x, y), inner_w, max_lines=2)
            self._restore_clip(previous_clip)
            return

        max_rows = max(1, (rect.h - 48) // 19)
        for order in drafts[:max_rows]:
            self._draw_text(order, self.small, INK, (x, y), inner_w, max_lines=1)
            y += 19
        hidden_count = len(drafts) - max_rows
        if hidden_count > 0 and y <= rect.bottom - 22:
            self._draw_text(f"+ {hidden_count} more draft orders", self.tiny, INK_MUTED, (x, y), inner_w, max_lines=1)
        self._restore_clip(previous_clip)

    def _render_controls_card(self, rect):
        self._draw_card(rect, "Actions")
        x = rect.x + 14
        y = rect.y + 34
        inner_w = rect.w - 28
        previous_clip = self._set_clip(rect.inflate(-8, -8))

        submitted = len(self.game.state.submitted_orders)
        if self.game.state.phase == "ADJUSTMENTS":
            summary = f"Sub {submitted}/{len(POWERS)}  |  Adj {self.game.get_adjustment_requirement(self.current_power):+d}"
        else:
            summary = f"Sub {submitted}/{len(POWERS)}  |  Ord {len(self.game.get_orderable_locations(self.current_power))}"
        self._draw_text(summary, self.tiny, INK_MUTED, (x, y), inner_w, max_lines=1)

        button_y = rect.bottom - 46
        self.submit_rect = pygame.Rect(rect.x + 14, button_y, 118, 38)
        self.process_rect = pygame.Rect(rect.right - 132, button_y, 118, 38)
        submit_enabled = self.current_power in self.human_powers and not self.ai_busy and not self.chat_busy
        process_enabled = self.game.all_orders_submitted() and not self.ai_busy and not self.chat_busy
        self._draw_button(self.submit_rect, "Submit", (208, 179, 104), submit_enabled)
        self._draw_button(self.process_rect, "Process", (118, 158, 181), process_enabled)
        self._restore_clip(previous_clip)
