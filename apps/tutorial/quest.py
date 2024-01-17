""" Quest - An epic journey.

Simple demo that demonstrates PyTMX and pyscroll.

requires pygame and pytmx.

https://github.com/bitcraft/pytmx

pip install pytmx
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
import pyscroll.data
from pyscroll.group import PyscrollGroup

# define configuration variables here
CURRENT_DIR = Path(__file__).parent
RESOURCES_DIR = CURRENT_DIR / "data"
HERO_MOVE_SPEED = 200  # pixels per second


# simple wrapper to keep the screen resizeable
def init_screen(width: int, height: int) -> pygame.Surface:
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    return screen


# make loading images a little easier
def load_image(filename: str) -> pygame.Surface:
    return pygame.image.load(str(RESOURCES_DIR / filename))


class Hero(pygame.sprite.Sprite):
    """
    Our Hero

    The Hero has three collision rects, one for the whole sprite "rect"
    and "old_rect", and another to check collisions with walls, called
    "feet".

    The position list is used because pygame rects are inaccurate for
    positioning sprites; because the values they get are 'rounded down'
    as integers, the sprite would move faster moving left or up.

    Feet is 1/2 as wide as the normal rect, and 8 pixels tall.  This
    size allows the top of the sprite to overlap walls.  The feet rect
    is used for collisions, while the 'rect' rect is used for drawing.

    There is also an old_rect that is used to reposition the sprite if
    it collides with level walls.

    """

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
        """
        If called after an update, the sprite can move back

        """
        self._position = self._old_position
        self.rect.topleft = self._position
        self.feet.midbottom = self.rect.midbottom


class QuestGame:
    """
    This class is a basic game.

    This class will load data, create a pyscroll group, a hero object.
    It also reads input and moves the Hero around the map.
    Finally, it uses a pyscroll group to render the map and Hero.

    """

    map_path = RESOURCES_DIR / "grasslands.tmx"

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen

        # true while running
        self.running = False

        # load data from pytmx
        tmx_data = load_pygame(self.map_path)

        # setup level geometry with simple pygame rects, loaded from pytmx
        self.walls = []
        for obj in tmx_data.objects:
            self.walls.append(pygame.Rect(obj.x, obj.y, obj.width, obj.height))

        # create new renderer (camera)
        self.map_layer = pyscroll.BufferedRenderer(
            data=pyscroll.data.TiledMapData(tmx_data),
            size=screen.get_size(),
            clamp_camera=False,
        )
        self.map_layer.zoom = 2

        # pyscroll supports layered rendering.  our map has 3 'under'
        # layers.  layers begin with 0.  the layers are 0, 1, and 2.
        # sprites are always drawn over the tiles of the layer they are
        # on.  since we want the sprite to be on top of layer 2, we set
        # the default layer for sprites as 2.
        self.group = PyscrollGroup(map_layer=self.map_layer, default_layer=2)

        # put the hero in the center of the map
        self.hero = Hero()
        self.hero.position = self.map_layer.map_rect.center

        # add our hero to the group
        self.group.add(self.hero)

    def draw(self) -> None:

        # center the map/screen on our Hero
        self.group.center(self.hero.rect.center)

        # draw the map and all sprites
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

        # check if the sprite's feet are colliding with wall
        # sprite must have a rect called feet, and move_back method,
        # otherwise this will fail
        for sprite in self.group.sprites():
            if sprite.feet.collidelist(self.walls) > -1:
                sprite.move_back(dt)

    def run(self) -> None:
        """
        Run the game loop

        """
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
