from pathlib import Path
import json
import pygame
from engine.game import Game, POWERS

WHITE=(250,250,250); BLACK=(20,20,20); GRAY=(235,235,235); DARK=(70,70,70); RED=(180,30,30)

class DiplomacyApp:
    def __init__(self):
        pygame.init()
        self.root = Path(__file__).resolve().parent.parent
        self.screen = pygame.display.set_mode((1450, 980))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 18)
        self.small = pygame.font.SysFont("arial", 15)
        self.big = pygame.font.SysFont("arial", 24)
        self.game = Game()
        self.current_power_index = 0
        self.selected_location = None
        self.power_drafts = {power: [] for power in POWERS}
        self.message_log = ["Loaded user map background", "Press R to reload points"]
        self.last_results = []
        self.map_image = self._load_map()
        self.unit_positions = self._load_layout().get("unit_positions", {})
        self.sidebar_rect = pygame.Rect(1120, 0, 330, 980)
        self.submit_rect = pygame.Rect(1140, 930, 140, 36)
        self.process_rect = pygame.Rect(1295, 930, 140, 36)
        self.order_option_rects = []

    @property
    def current_power(self):
        return POWERS[self.current_power_index]

    def _load_map(self):
        p = self.root / "map" / "assets" / "diplomacy_map.jpg"
        if p.exists():
            img = pygame.image.load(str(p)).convert()
            return pygame.transform.smoothscale(img, (1120, 980))
        return None

    def _load_layout(self):
        p = self.root / "map" / "ui_layout.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        return {"unit_positions": {}}

    def reload_points(self):
        self.unit_positions = self._load_layout().get("unit_positions", {})
        self.message_log = ["Reloaded map/ui_layout.json"]

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    self.reload_points()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
            self._render()
            self.clock.tick(30)
        pygame.quit()

    def _handle_click(self, pos):
        if self.submit_rect.collidepoint(pos):
            self.game.set_orders(self.current_power, self.power_drafts[self.current_power])
            self.message_log = [f"Submitted {self.current_power}"]
            if self.current_power_index < len(POWERS)-1:
                self.current_power_index += 1
            else:
                self.message_log = ["All powers submitted. Click Process Phase."]
            return
        if self.process_rect.collidepoint(pos):
            if self.game.all_orders_submitted():
                self.last_results = self.game.process()
                self.message_log = [f"{src}: {result}" for src, result in self.last_results[-8:]]
                self.power_drafts = {power: [] for power in POWERS}
                self.current_power_index = 0
                self.selected_location = None
            else:
                self.message_log = ["Not all powers submitted."]
            return
        for rect, order in self.order_option_rects:
            if rect.collidepoint(pos):
                drafts = self.power_drafts[self.current_power]
                src = order.split()[1]
                drafts = [d for d in drafts if d.split()[1] != src]
                drafts.append(order)
                self.power_drafts[self.current_power] = drafts
                self.message_log = [f"Selected: {order}"]
                return
        for loc, unit in self.game.state.units.items():
            p = self.unit_positions.get(loc)
            if not p:
                continue
            dx = pos[0]-p["x"]
            dy = pos[1]-p["y"]
            if dx*dx + dy*dy <= 17*17:
                if unit.power == self.current_power:
                    self.selected_location = loc
                    self.message_log = [f"Selected {loc}"]
                else:
                    self.message_log = [f"{loc} belongs to {unit.power}"]
                return

    def _render(self):
        self.screen.fill(WHITE)
        if self.map_image is not None:
            self.screen.blit(self.map_image, (0,0))
        self._render_units()
        self._render_sidebar()
        pygame.display.flip()

    def _render_units(self):
        colors = {"AUSTRIA":(192,57,43),"ENGLAND":(31,58,147),"FRANCE":(93,173,226),"GERMANY":(40,40,40),"ITALY":(35,155,86),"RUSSIA":(220,220,220),"TURKEY":(244,208,63)}
        for loc, unit in self.game.state.units.items():
            p = self.unit_positions.get(loc)
            if not p:
                continue
            color = colors.get(unit.power, (90,90,90))
            center = (p["x"], p["y"])
            if unit.unit_type == "A":
                pygame.draw.circle(self.screen, color, center, 14)
            else:
                pygame.draw.rect(self.screen, color, pygame.Rect(center[0]-16, center[1]-10, 32, 20))
            pygame.draw.circle(self.screen, BLACK, center, 16, 2)
            if loc == self.selected_location:
                pygame.draw.circle(self.screen, RED, center, 20, 3)
            txt = self.small.render(loc, True, BLACK)
            self.screen.blit(txt, (center[0]+18, center[1]-8))

    def _render_sidebar(self):
        pygame.draw.rect(self.screen, GRAY, self.sidebar_rect)
        pygame.draw.line(self.screen, DARK, (1120,0), (1120,980), 2)
        y=12
        self.screen.blit(self.big.render("Local Hotseat", True, BLACK), (1140,y)); y+=34
        self.screen.blit(self.font.render(self.game.get_current_phase(), True, BLACK), (1140,y)); y+=28
        self.screen.blit(self.font.render(f"Current Power: {self.current_power}", True, RED), (1140,y)); y+=36
        self.screen.blit(self.font.render("Draft Orders", True, BLACK), (1140,y)); y+=24
        for order in self.power_drafts[self.current_power][:10]:
            self.screen.blit(self.small.render(order, True, BLACK), (1145,y)); y+=20
        y+=10
        self.screen.blit(self.font.render("Possible Orders", True, BLACK), (1140,y)); y+=24
        self.order_option_rects=[]
        if self.selected_location and self.selected_location in self.game.get_orderable_locations(self.current_power):
            for order in self.game.get_possible_orders(self.selected_location)[:12]:
                rect = pygame.Rect(1140,y,285,22)
                pygame.draw.rect(self.screen, WHITE, rect)
                pygame.draw.rect(self.screen, DARK, rect, 1)
                self.screen.blit(self.small.render(order, True, BLACK), (1144,y+3))
                self.order_option_rects.append((rect, order))
                y+=26
        else:
            self.screen.blit(self.small.render("Select one of your units on the map.", True, BLACK), (1145,y)); y+=24
        y+=10
        self.screen.blit(self.font.render("Status", True, BLACK), (1140,y)); y+=24
        for line in self.message_log[:8]:
            self.screen.blit(self.small.render(line, True, BLACK), (1145,y)); y+=20
        self.submit_rect = pygame.Rect(1140,930,140,36)
        self.process_rect = pygame.Rect(1295,930,140,36)
        pygame.draw.rect(self.screen, (220,240,220), self.submit_rect)
        pygame.draw.rect(self.screen, DARK, self.submit_rect, 2)
        self.screen.blit(self.font.render("Submit Power", True, BLACK), (1148,938))
        pygame.draw.rect(self.screen, (220,230,245), self.process_rect)
        pygame.draw.rect(self.screen, DARK, self.process_rect, 2)
        self.screen.blit(self.font.render("Process Phase", True, BLACK), (1302,938))
