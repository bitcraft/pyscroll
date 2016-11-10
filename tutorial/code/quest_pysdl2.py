# -*- coding: utf-8 -*-
""" Quest - An epic journey.

Simple demo that demonstrates PyTMX and mason.

requires pysdl2_cffi and pytmx.  runs on pypy!

https://github.com/bitcraft/pytmx

pip install pytmx
"""
import os.path

import sdl
from pytmx.util_pysdl2_cffi import load_pysdl2_cffi

import mason
import mason.data
from mason.compat import Rect

# define configuration variables here
RESOURCES_DIR = 'data'

HERO_MOVE_SPEED = 200  # pixels per second
MAP_FILENAME = 'grasslands.tmx'


# make loading maps a little easier
def get_map(filename):
    return os.path.join(RESOURCES_DIR, filename)


# make loading images a little easier
def load_image(renderer, filename):
    path = os.path.join(RESOURCES_DIR, filename)
    return sdl.image.loadTexture(renderer, path)


class Hero(object):
    """ Our Hero

    The Hero has three collision rects, one for the whole sprite "rect" and
    "old_rect", and another to check collisions with walls, called "feet".

    The position list is used because Rects are inaccurate for
    positioning sprites; because the values they get are 'rounded down'
    as integers, the sprite would move faster moving left or up.

    Feet is 1/2 as wide as the normal rect, and 8 pixels tall.  This size size
    allows the top of the sprite to overlap walls.  The feet rect is used for
    collisions, while the 'rect' rect is used for drawing.

    There is also an old_rect that is used to reposition the sprite if it
    collides with level walls.
    """

    def __init__(self):
        self.velocity = [0, 0]
        self._position = [0, 0]
        self._old_position = self.position
        self.rect = Rect(0, 0, 32, 48)  # TODO: no hardcode
        self.feet = Rect(0, 0, self.rect.width * .5, 8)

    def load_textures(self, renderer):
        self.image = load_image(renderer, 'hero.png')

    @property
    def position(self):
        return list(self._position)

    @position.setter
    def position(self, value):
        self._position = list(value)

    def update(self, dt):
        self._old_position = self._position[:]
        self._position[0] += self.velocity[0] * dt
        self._position[1] += self.velocity[1] * dt
        self.rect.topleft = self._position
        self.feet.midbottom = self.rect.midbottom

        self.velocity[0] *= .91
        self.velocity[1] *= .91

    def move_back(self, dt):
        """ If called after an update, the sprite can move back
        """
        self._position = self._old_position
        self.rect.topleft = self._position
        self.feet.midbottom = self.rect.midbottom


class QuestGame(object):
    """ This class is a basic game.

    This class will load data, create a mason group, a hero object.
    It also reads input and moves the Hero around the map.
    Finally, it uses a mason group to render the map and Hero.
    """
    filename = get_map(MAP_FILENAME)

    def __init__(self, ctx):
        self.ctx = ctx
        self.event = sdl.Event()
        self.running = False

        # load data from pytmx
        tmx_data = load_pysdl2_cffi(ctx, self.filename)

        # setup level geometry with simple pygame rects, loaded from pytmx
        self.walls = list()
        for obj in tmx_data.objects:
            self.walls.append(Rect(obj.x, obj.y, obj.width, obj.height))

        # create new data source for mason
        map_data = mason.data.TiledMapData(tmx_data)

        # create new renderer (camera)
        screen_size = ctx.window.getWindowSize()
        self.map_layer = mason.GraphicsPysdl2cffi(ctx, map_data, screen_size)

        self.hero = Hero()
        self.hero.load_textures(self.ctx.renderer)
        self.hero.position = self.map_layer.map_rect.center

    def update(self, dt):
        self.hero.update(dt)

    def draw(self):
        renderer = self.ctx.renderer

        self.map_layer.center(self.hero.rect.center)

        tex_info = self.hero.image, None, 0, 0

        ox, oy = self.map_layer.get_center_offset()
        x, y = self.hero.rect.topleft
        rect = Rect(x + ox, y + oy, 48, 48)

        self.map_layer.draw([(tex_info, rect, 2)])
        sdl.renderPresent(renderer)

    def handle_input(self):
        """ Handle pygame input events
        """
        event = self.event

        while sdl.pollEvent(event) != 0:
            if is_quit_event(event):
                quit_sdl(self.ctx)
                self.running = False
                break

            elif event.type == sdl.KEYDOWN:
                sym = event.key.keysym.sym
                if sym == sdl.K_UP:
                    self.hero.velocity[1] = -HERO_MOVE_SPEED
                elif sym == sdl.K_DOWN:
                    self.hero.velocity[1] = HERO_MOVE_SPEED
                elif sym == sdl.K_LEFT:
                    self.hero.velocity[0] = -HERO_MOVE_SPEED
                elif sym == sdl.K_RIGHT:
                    self.hero.velocity[0] = HERO_MOVE_SPEED

                    # elif event.type == sdl.KEYUP:
                    #     sym = event.key.keysym.sym
                    #     if sym == sdl.K_UP or sym == sdl.K_DOWN:
                    #         self.hero.velocity[1] = 0
                    #     elif sym == sdl.K_LEFT or sym == sdl.K_RIGHT:
                    #         self.hero.velocity[0] = 0

    def run(self):
        """ Run the game loop
        """
        self.running = True
        import time

        target_time = 1 / 60.

        try:
            while self.running:
                start = time.time()

                self.handle_input()
                if self.running:
                    self.update(target_time)
                    self.draw()

                elapsed = time.time() - start
                while elapsed < target_time:
                    time.sleep(.001)
                    elapsed = time.time() - start

        except KeyboardInterrupt:
            self.running = False


class SDLContext(object):
    def __init__(self):
        self.window = None
        self.renderer = None
        self.display_info = None


def is_quit_event(event):
    return event.type == sdl.QUIT or \
           (event.type == sdl.KEYDOWN and event.key.keysym.sym == sdl.K_ESCAPE)


def quit_sdl(sdl_context):
    if sdl_context.renderer is not None:
        sdl.destroyRenderer(sdl_context.renderer)
    if sdl_context.window is not None:
        sdl.destroyWindow(sdl_context.window)
    sdl.quit()


if __name__ == "__main__":
    sdl.init(sdl.INIT_VIDEO)

    ctx = SDLContext()
    ctx.display_info = sdl.DisplayMode()
    sdl.getDesktopDisplayMode(0, ctx.display_info)

    ctx.window = sdl.createWindow(
        "reeeeeeeee",
        0, 0,
        ctx.display_info.w, ctx.display_info.h,
        sdl.WINDOW_SHOWN)

    sdl.setWindowFullscreen(ctx.window, sdl.WINDOW_FULLSCREEN)

    ctx.renderer = sdl.createRenderer(
        ctx.window,
        -1,  # What's this do? ¯\_(ツ)_/¯
        sdl.RENDERER_ACCELERATED |
        sdl.RENDERER_PRESENTVSYNC)

    sdl.ttf.init()

    try:
        game = QuestGame(ctx)
        game.run()
    except:
        raise
