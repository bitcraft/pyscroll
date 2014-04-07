""" Quest - An epic journey.

Simple game that demonstrates PyTMX and pyscroll.
"""

import os.path
import pytmx
import pygame
import pyscroll
from pyscroll.util import PyscrollGroup
from pygame.locals import *


# define configuration variables here
RESOURCES_DIR = 'data'

HERO_MOVE_SPEED = 300
MAP_FILENAME = 'desert.tmx'


# simple wrapper to keep the screen resizeable
def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


# make loading maps a little easier
def get_map(filename):
    return os.path.join(RESOURCES_DIR, filename)


# make loading images a little easier
def load_image(filename):
    return pygame.image.load(os.path.join(RESOURCES_DIR, filename))


# this is a pretty standard pygame sprite object
# nothing interesting here
class Hero(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = load_image('hero.png').convert_alpha()
        self.rect = self.image.get_rect()
        self.velocity = [0, 0]

    def update(self, dt):
        self.rect.x += self.velocity[0] * dt
        self.rect.y += self.velocity[1] * dt


class QuestGame:
    """ Where you play
    """
    filename = get_map('desert.tmx')

    def __init__(self):
        self.running = False  # true when running

        # load data from pytmx
        tmx_data = pytmx.load_pygame(self.filename)

        # create new data source for pyscroll
        map_data = pyscroll.TiledMapData(tmx_data)

        # create new renderer
        # currently, pyscroll only has one renderer, the BufferedRenderer
        self.map_layer = pyscroll.BufferedRenderer(map_data, screen.get_size())

        # use the pyscroll Group for easy rendering
        self.group = PyscrollGroup(map_layer=self.map_layer)
        self.hero = Hero()

        # put the hero in the center of the map
        self.hero.rect.center = self.map_layer.rect.center

        # add our hero to the group
        self.group.add(self.hero)

    def draw(self, surface):
        self.group.center(self.hero.rect.center)
        self.group.draw(surface)

    def handle_input(self):
        """ Handle pygame input events
        """
        event = pygame.event.poll()
        while event:
            if event.type == QUIT:
                self.running = False
                break

            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                    break

            # this will be handled if the window is resized
            elif event.type == VIDEORESIZE:
                init_screen(event.w, event.h)
                self.map_layer.set_size((event.w, event.h))

            event = pygame.event.poll()

        # using get_pressed is slightly less accurate than testing for events
        # but is much easier to use.
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

    def update(self, dt):
        """ Tasks that occur over time should be handled here
        """
        self.map_layer.center(self.hero.rect.center)
        self.group.update(dt)

    def run(self):
        """ Run the game loop
        """
        clock = pygame.time.Clock()
        fps = 60
        self.running = True

        try:
            while self.running:
                dt = clock.tick(fps) / 1000.

                self.handle_input()
                self.update(dt)
                self.draw(screen)
                pygame.display.flip()

        except KeyboardInterrupt:
            self.running = False


if __name__ == "__main__":
    pygame.init()
    pygame.font.init()
    screen = init_screen(900, 700)
    pygame.display.set_caption('Quest - An epic journey.')

    try:
        game = QuestGame()
        game.run()
    except:
        pygame.quit()
        raise