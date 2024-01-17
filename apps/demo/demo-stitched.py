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
from pytmx.util_pygame import load_pygame

import pyscroll
from pyscroll.data import MapAggregator, TiledMapData
from pyscroll.group import PyscrollGroup

# define configuration variables here
CURRENT_DIR = Path(__file__).parent
RESOURCES_DIR = CURRENT_DIR
HERO_MOVE_SPEED = 200  # pixels per second


def init_screen(width: int, height: int) -> pygame.Surface:
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    return screen


def load_image(filename: str) -> pygame.Surface:
    return pygame.image.load(str(RESOURCES_DIR / filename))


class Hero(pygame.sprite.Sprite):
    def __init__(self) -> None:
        super().__init__()
        self.image = load_image("hero.png").convert_alpha()
        self.velocity = [0, 0]
        self._position = [0.0, 0.0]
        self._old_position = self.position
        self.rect = self.image.get_rect()
        self.feet = pygame.Rect(0, 0, self.rect.width * 0.5, 8)

    @property
    def position(self) -> list[float]:
        return list(self._position)

    @position.setter
    def position(self, value: list[float]) -> None:
        self._position = list(value)

    def update(self, dt: float) -> None:
        self._old_position = self._position[:]
        self._position[0] += self.velocity[0] * dt
        self._position[1] += self.velocity[1] * dt
        self.rect.topleft = self._position
        self.feet.midbottom = self.rect.midbottom

    def move_back(self, dt: float) -> None:
        self._position = self._old_position
        self.rect.topleft = self._position
        self.feet.midbottom = self.rect.midbottom


class QuestGame:
    map_path = RESOURCES_DIR / "grasslands.tmx"

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.running = False

        world_data = MapAggregator((16, 16))
        for filename, offset in [
            ("stitched0.tmx", (-20, -20)),
            ("stitched1.tmx", (0, -20)),
            ("stitched2.tmx", (20, -20)),
            ("stitched3.tmx", (-20, 0)),
            ("stitched4.tmx", (0, 0)),
            ("stitched5.tmx", (20, 0)),
            ("stitched6.tmx", (-20, 20)),
            ("stitched7.tmx", (0, 20)),
            ("stitched8.tmx", (20, 20)),
        ]:
            tmx_data = load_pygame(RESOURCES_DIR / filename)
            pyscroll_data = TiledMapData(tmx_data)
            world_data.add_map(pyscroll_data, offset)

        self.map_layer = pyscroll.BufferedRenderer(
            data=world_data,
            size=screen.get_size(),
            clamp_camera=True,
        )
        self.map_layer.zoom = 2
        self.group = PyscrollGroup(map_layer=self.map_layer, default_layer=0)

        # put the hero in the center of the map
        self.hero = Hero()
        self.hero.layer = 0
        self.hero.position = (400, 400)

        # add our hero to the group
        self.group.add(self.hero)

    def draw(self) -> None:
        self.group.center(self.hero.rect.center)
        self.group.draw(self.screen)

    def handle_input(self) -> None:
        """
        Handle pygame input events

        """
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
                break

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                    break

                elif event.key == K_r:
                    self.map_layer.reload()

                elif event.key == K_EQUALS:
                    self.map_layer.zoom += 0.25

                elif event.key == K_MINUS:
                    value = self.map_layer.zoom - 0.25
                    if value > 0:
                        self.map_layer.zoom = value

            # this will be handled if the window is resized
            elif event.type == VIDEORESIZE:
                self.screen = init_screen(event.w, event.h)
                self.map_layer.set_size((event.w, event.h))

        # use `get_pressed` for an easy way to detect held keys
        pressed = pygame.key.get_pressed()
        if pressed[K_UP]:
            self.hero.velocity[1] = -HERO_MOVE_SPEED
        elif pressed[K_DOWN]:
            self.hero.velocity[1] = HERO_MOVE_SPEED
        else:
            self.hero.velocity[1] = 0

        if pressed[K_LEFT]:
            self.hero.velocity[0] = -HERO_MOVE_SPEED
        elif pressed[K_RIGHT]:
            self.hero.velocity[0] = HERO_MOVE_SPEED
        else:
            self.hero.velocity[0] = 0

    def update(self, dt: float) -> None:
        """
        Tasks that occur over time should be handled here

        """
        self.group.update(dt)

    def run(self) -> None:
        clock = pygame.time.Clock()
        self.running = True

        try:
            while self.running:
                dt = clock.tick() / 1000.0
                self.handle_input()
                self.update(dt)
                self.draw()
                pygame.display.flip()

        except KeyboardInterrupt:
            self.running = False


def main() -> None:
    pygame.init()
    pygame.font.init()
    screen = init_screen(800, 600)
    pygame.display.set_caption("Quest - An epic journey.")

    try:
        game = QuestGame(screen)
        game.run()
    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
