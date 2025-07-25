"""

Rendering demo showing 9 TMX maps rendered at once


Very basic!  No animations.

"""

from __future__ import annotations

from pathlib import Path

import pygame
from pygame.locals import (
    K_DOWN,
    K_EQUALS,
    K_ESCAPE,
    K_LEFT,
    K_MINUS,
    K_RIGHT,
    K_UP,
    KEYDOWN,
    QUIT,
    VIDEORESIZE,
    K_r,
)
from pygame.math import Vector2
from pygame.rect import Rect
from pygame.sprite import Sprite
from pygame.surface import Surface
from pytmx.util_pygame import load_pygame  # type: ignore

import pyscroll
from pyscroll.data import MapAggregator, TiledMapData
from pyscroll.group import PyscrollGroup

# define configuration variables here
CURRENT_DIR = Path(__file__).parent
RESOURCES_DIR = CURRENT_DIR
WINDOW_SIZE = (800, 600)
HERO_MOVE_SPEED = 200  # pixels per second
ZOOM_STEP = 0.25
INITIAL_ZOOM = 2.0


def init_screen(width: int, height: int) -> Surface:
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


def load_image(filename: str) -> Surface:
    path = RESOURCES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return pygame.image.load(str(path)).convert_alpha()


class Hero(Sprite):
    def __init__(self) -> None:
        super().__init__()
        self.image = load_image("hero.png")
        self.velocity = Vector2(0, 0)
        self.position = Vector2(400.0, 400.0)
        self.old_position = self.position.copy()
        self.rect = self.image.get_rect(topleft=self.position)
        self.feet = Rect(0, 0, self.rect.width * 0.5, 8)
        self.update_feet()

    def update_feet(self) -> None:
        self.feet.midbottom = self.rect.midbottom

    @property
    def position(self) -> list[float]:
        return list(self._position)

    @position.setter
    def position(self, value: list[float]) -> None:
        self._position = list(value)

    def update(self, dt: float) -> None:
        self.old_position = self.position.copy()
        self.position += self.velocity * dt
        self.rect.topleft = self.position
        self.update_feet()

    def move_back(self, dt: float) -> None:
        self.position = self.old_position.copy()
        self.rect.topleft = self.position
        self.update_feet()


class QuestGame:
    def __init__(self, screen: Surface) -> None:
        self.screen = screen
        self.running = False

        # Load and stitch maps
        world_data = MapAggregator((16, 16))
        stitched_maps = [
            ("stitched0.tmx", (-20, -20)),
            ("stitched1.tmx", (0, -20)),
            ("stitched2.tmx", (20, -20)),
            ("stitched3.tmx", (-20, 0)),
            ("stitched4.tmx", (0, 0)),
            ("stitched5.tmx", (20, 0)),
            ("stitched6.tmx", (-20, 20)),
            ("stitched7.tmx", (0, 20)),
            ("stitched8.tmx", (20, 20)),
        ]

        for filename, offset in stitched_maps:
            path = RESOURCES_DIR / filename
            if not path.exists():
                raise FileNotFoundError(f"TMX map not found: {path}")
            tmx_data = load_pygame(str(path))
            world_data.add_map(TiledMapData(tmx_data), offset)

        self.map_layer = pyscroll.orthographic.BufferedRenderer(
            data=world_data,
            size=screen.get_size(),
            clamp_camera=True,
        )
        self.map_layer.zoom = INITIAL_ZOOM
        self.group = PyscrollGroup(map_layer=self.map_layer, default_layer=0)

        # Hero setup
        self.hero = Hero()
        self.hero.layer = 0
        self.group.add(self.hero)

    def draw(self) -> None:
        self.group.center(self.hero.rect.center)
        self.group.draw(self.screen)

    def handle_input(self) -> None:
        """
        Handle pygame input events
        """
        for event in pygame.event.get():
            if event.type == QUIT or (event.type == KEYDOWN and event.key == K_ESCAPE):
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_r:
                    self.map_layer.reload()
                elif event.key == K_EQUALS:
                    self.map_layer.zoom += ZOOM_STEP
                elif event.key == K_MINUS:
                    new_zoom = self.map_layer.zoom - ZOOM_STEP
                    if new_zoom > 0:
                        self.map_layer.zoom = new_zoom
            elif event.type == VIDEORESIZE:
                self.screen = init_screen(event.w, event.h)
                self.map_layer.set_size((event.w, event.h))

        pressed = pygame.key.get_pressed()
        self.hero.velocity.x = 0
        self.hero.velocity.y = 0

        if pressed[K_UP]:
            self.hero.velocity.y = -HERO_MOVE_SPEED
        elif pressed[K_DOWN]:
            self.hero.velocity.y = HERO_MOVE_SPEED

        if pressed[K_LEFT]:
            self.hero.velocity.x = -HERO_MOVE_SPEED
        elif pressed[K_RIGHT]:
            self.hero.velocity.x = HERO_MOVE_SPEED

    def update(self, dt: float) -> None:
        self.group.update(dt)

    def run(self) -> None:
        clock = pygame.time.Clock()
        self.running = True

        while self.running:
            dt = clock.tick(60) / 1000.0
            self.handle_input()
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main() -> None:
    pygame.init()
    pygame.font.init()
    screen = init_screen(*WINDOW_SIZE)
    pygame.display.set_caption("Quest - An Epic Journey")

    try:
        game = QuestGame(screen)
        game.run()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
