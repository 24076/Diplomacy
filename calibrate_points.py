from pathlib import Path
import json
import pygame

WHITE = (250, 250, 250)
BLACK = (20, 20, 20)
GRAY = (235, 235, 235)
RED = (180, 30, 30)
GREEN = (40, 150, 70)
TRACK = (210, 210, 210)
THUMB = (120, 120, 120)


class PointCalibrator:
    def __init__(self):
        pygame.init()
        self.root = Path(__file__).resolve().parent.parent
        self.screen = pygame.display.set_mode((1450, 980))
        pygame.display.set_caption("Diplomacy Map Point Calibrator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 18)
        self.small = pygame.font.SysFont("arial", 15)
        self.big = pygame.font.SysFont("arial", 22)

        self.layout_path = self.root / "map" / "ui_layout.json"
        self.layout = self._load_layout()
        self.unit_positions = self.layout.get("unit_positions", {})
        self.locations = self.layout.get("editable_locations", [])
        self.index = 0
        self.message = "Click map to place point (auto-save on)"
        self.map_image = self._load_map()
        self.list_rects = []

        self.map_rect = pygame.Rect(0, 0, 1120, 980)
        self.sidebar_rect = pygame.Rect(1120, 0, 330, 980)

        self.row_height = 26
        self.items_per_row = 2
        self.visible_top = 140
        self.visible_bottom = 940
        self.scroll_offset = 0

    def _load_map(self):
        p = self.root / "map" / "assets" / "diplomacy_map.jpg"
        if p.exists():
            img = pygame.image.load(str(p)).convert()
            return pygame.transform.smoothscale(img, (1120, 980))
        return None

    def _load_layout(self):
        if self.layout_path.exists():
            return json.loads(self.layout_path.read_text(encoding="utf-8"))
        return {
            "image_size": {"width": 1366, "height": 1024},
            "editable_locations": [],
            "unit_positions": {},
        }

    @property
    def current_location(self):
        return self.locations[self.index] if self.locations else None

    def save(self):
        self.layout["unit_positions"] = self.unit_positions
        self.layout["editable_locations"] = self.locations
        self.layout_path.write_text(
            json.dumps(self.layout, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.message = f"Saved to {self.layout_path}"

    def _total_rows(self):
        return (len(self.locations) + self.items_per_row - 1) // self.items_per_row

    def _visible_rows(self):
        return max(1, (self.visible_bottom - self.visible_top) // self.row_height)

    def _handle_scroll(self, wheel_y):
        total_rows = self._total_rows()
        visible_rows = self._visible_rows()
        max_scroll = max(0, total_rows - visible_rows)

        self.scroll_offset -= wheel_y
        if self.scroll_offset < 0:
            self.scroll_offset = 0
        if self.scroll_offset > max_scroll:
            self.scroll_offset = max_scroll

    def _ensure_selected_visible(self):
        if not self.locations:
            return

        selected_row = self.index // self.items_per_row
        visible_rows = self._visible_rows()

        if selected_row < self.scroll_offset:
            self.scroll_offset = selected_row
        elif selected_row >= self.scroll_offset + visible_rows:
            self.scroll_offset = selected_row - visible_rows + 1

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_s:
                        self.save()
                    elif event.key == pygame.K_r:
                        self.layout = self._load_layout()
                        self.unit_positions = self.layout.get("unit_positions", {})
                        self.locations = self.layout.get(
                            "editable_locations", self.locations
                        )
                        if self.locations:
                            self.index = min(self.index, len(self.locations) - 1)
                        self._ensure_selected_visible()
                        self.message = f"Reloaded {self.layout_path}"
                    elif event.key == pygame.K_n and self.locations:
                        self.index = min(len(self.locations) - 1, self.index + 1)
                        self._ensure_selected_visible()
                        self.message = f"Selected {self.current_location}"
                    elif event.key == pygame.K_p and self.locations:
                        self.index = max(0, self.index - 1)
                        self._ensure_selected_visible()
                        self.message = f"Selected {self.current_location}"
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_scroll(event.y)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)

            self._render()
            self.clock.tick(30)

        pygame.quit()

    def _handle_click(self, pos):
        for i, rect in self.list_rects:
            if rect.collidepoint(pos):
                self.index = i
                self._ensure_selected_visible()
                self.message = f"Selected {self.current_location}"
                return

        if self.map_rect.collidepoint(pos) and self.current_location is not None:
            self.unit_positions[self.current_location] = {"x": pos[0], "y": pos[1]}
            self.save()
            self.message = f"Placed {self.current_location} at {pos} and auto-saved"

    def _render(self):
        self.screen.fill(WHITE)

        if self.map_image is not None:
            self.screen.blit(self.map_image, (0, 0))

        for loc, point in self.unit_positions.items():
            color = RED if loc == self.current_location else BLACK
            pygame.draw.circle(self.screen, color, (point["x"], point["y"]), 8, 2)
            self.screen.blit(
                self.small.render(loc, True, color),
                (point["x"] + 10, point["y"] - 8),
            )

        pygame.draw.rect(self.screen, GRAY, self.sidebar_rect)

        y = 12
        self.screen.blit(self.big.render("Point Calibrator", True, BLACK), (1140, y))
        y += 30
        self.screen.blit(
            self.small.render("Left click map = set point", True, BLACK), (1140, y)
        )
        y += 18
        self.screen.blit(
            self.small.render(
                "Wheel scroll | S save | R reload | ESC quit", True, BLACK
            ),
            (1140, y),
        )
        y += 24

        if self.current_location:
            self.screen.blit(
                self.font.render(f"Current: {self.current_location}", True, GREEN),
                (1140, y),
            )
            y += 28

        self.screen.blit(self.small.render(self.message[:42], True, BLACK), (1140, y))

        self.list_rects = []

        row_y = self.visible_top
        start_row = self.scroll_offset
        visible_rows = self._visible_rows()
        start_index = start_row * self.items_per_row
        end_index = min(
            len(self.locations), start_index + visible_rows * self.items_per_row
        )

        for i in range(start_index, end_index):
            loc = self.locations[i]
            local_index = i - start_index
            x = 1140 if local_index % 2 == 0 else 1280
            if local_index % 2 == 0 and local_index > 0:
                row_y += self.row_height

            rect = pygame.Rect(x, row_y, 120, 22)
            pygame.draw.rect(self.screen, WHITE, rect)
            pygame.draw.rect(self.screen, RED if i == self.index else BLACK, rect, 1)
            self.screen.blit(self.small.render(loc, True, BLACK), (x + 4, row_y + 3))
            self.list_rects.append((i, rect))

        total_rows = self._total_rows()
        visible_rows = self._visible_rows()

        track_x = 1420
        track_y = self.visible_top
        track_h = self.visible_bottom - self.visible_top
        track_rect = pygame.Rect(track_x, track_y, 12, track_h)
        pygame.draw.rect(self.screen, TRACK, track_rect)
        pygame.draw.rect(self.screen, BLACK, track_rect, 1)

        if total_rows > visible_rows:
            thumb_h = max(30, int(track_h * (visible_rows / total_rows)))
            max_scroll = total_rows - visible_rows
            thumb_y = track_y + int(
                (track_h - thumb_h) * (self.scroll_offset / max_scroll)
            )
        else:
            thumb_h = track_h
            thumb_y = track_y

        thumb_rect = pygame.Rect(track_x + 1, thumb_y, 10, thumb_h)
        pygame.draw.rect(self.screen, THUMB, thumb_rect)

        pygame.display.flip()


if __name__ == "__main__":
    PointCalibrator().run()
