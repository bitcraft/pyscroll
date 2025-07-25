"""
This is tested on pygame 1.9 and python 3.3 & 2.7.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the pyscroll.

Use the arrow keys to smoothly scroll the map.
Window is resizable.

See the "Quest" tutorial for a more simple use with
pygame sprites and groups.
"""

import logging
from collections import deque
from pathlib import Path
from typing import Deque

import pygame
from pygame.font import Font
from pygame.locals import (
    K_DOWN,
    K_ESCAPE,
    K_LEFT,
    K_RIGHT,
    K_UP,
    KEYDOWN,
    QUIT,
    VIDEORESIZE,
    K_a,
    K_d,
    K_s,
    K_w,
)
from pygame.math import Vector2
from pygame.surface import Surface
from pytmx.util_pygame import load_pygame  # type: ignore

import pyscroll
import pyscroll.data
import pyscroll.orthographic

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

SCROLL_SPEED = 5000
FONT_SIZE = 20
TEXT_COLOR = (180, 180, 0)
FRICTION_BASE = 0.0001
WINDOW_SIZE = (800, 600)


# simple wrapper to keep the screen resizeable
def init_screen(width: int, height: int) -> Surface:
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class ScrollTest:
    """Test and demo of pyscroll

    For normal use, please see the quest demo, not this.

    """

    def __init__(self, filename: Path, screen: Surface) -> None:
        self.screen = screen

        # Load TMX map
        tmx_data = load_pygame(filename.as_posix())
        map_data = pyscroll.data.TiledMapData(tmx_data)
        self.map_layer = pyscroll.orthographic.BufferedRenderer(
            map_data, screen.get_size()
        )

        # Text overlay
        font = Font(pygame.font.get_default_font(), FONT_SIZE)
        messages = ["Scroll demo. Press ESC to quit", "Arrow keys or WASD to move"]
        self.text_overlay = [font.render(msg, True, TEXT_COLOR) for msg in messages]
        self.font = font

        # Camera setup
        self.center = Vector2(
            self.map_layer.map_rect.width / 2, self.map_layer.map_rect.height / 2
        )
        self.camera_acc = Vector2(0, 0)
        self.camera_vel = Vector2(0, 0)
        self.last_update_time = 0.0

        self.running = False

    def draw(self) -> None:
        self.map_layer.draw(self.screen, self.screen.get_rect())
        self.draw_text()

    def draw_text(self) -> None:
        y = 0
        for text in self.text_overlay:
            self.screen.blit(text, (0, y))
            y += text.get_height()

        fps_text = self.font.render(f"FPS: {int(self.fps)}", True, TEXT_COLOR)
        self.screen.blit(fps_text, (self.screen.get_width() - 100, 0))

    def handle_input(self) -> None:
        """Simply handle pygame input events"""
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                self.running = False
            elif event.type == VIDEORESIZE:
                self.screen = init_screen(event.w, event.h)
                self.map_layer.set_size((event.w, event.h))

        pressed = pygame.key.get_pressed()
        self.camera_acc = Vector2(0, 0)

        if pressed[K_UP] or pressed[K_w]:
            self.camera_acc.y = -SCROLL_SPEED * self.last_update_time
        elif pressed[K_DOWN] or pressed[K_s]:
            self.camera_acc.y = SCROLL_SPEED * self.last_update_time

        if pressed[K_LEFT] or pressed[K_a]:
            self.camera_acc.x = -SCROLL_SPEED * self.last_update_time
        elif pressed[K_RIGHT] or pressed[K_d]:
            self.camera_acc.x = SCROLL_SPEED * self.last_update_time

    def update(self, dt: float) -> None:
        self.last_update_time = dt
        friction = FRICTION_BASE**dt

        self.camera_vel += self.camera_acc * dt
        self.camera_vel *= friction
        self.center += self.camera_vel

        # Clamp to map bounds
        self.center.x = max(0, min(self.center.x, self.map_layer.map_rect.width))
        self.center.y = max(0, min(self.center.y, self.map_layer.map_rect.height))

        self.map_layer.center(self.center)

    def run(self) -> None:
        clock = pygame.time.Clock()
        self.running = True
        fps_log: Deque[float] = deque(maxlen=20)

        while self.running:
            clock.tick(120)
            try:
                fps_log.append(clock.get_fps())
                self.fps = sum(fps_log) / len(fps_log)
                dt = 1 / self.fps if self.fps > 0 else 0.016
            except ZeroDivisionError:
                continue

            self.handle_input()
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main() -> None:
    pygame.init()
    pygame.font.init()
    screen = init_screen(*WINDOW_SIZE)
    pygame.display.set_caption("pyscroll Test")

    script_dir = Path(__file__).parent.resolve()
    filename = script_dir / "desert.tmx"

    if not filename.exists():
        logger.error(f"TMX file not found: {filename}")
        sys.exit(1)

    try:
        ScrollTest(filename, screen).run()
    except Exception as e:
        logger.exception("An error occurred during execution.")
        pygame.quit()
        raise e


if __name__ == "__main__":
    import sys

    main()
