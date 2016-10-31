# coding=utf-8
""" Quest - An epic journey.

Simple demo that demonstrates PyTMX and pyscroll.

requires pysdl2_cffi and pytmx.  runs on pypy!

https://github.com/bitcraft/pytmx

pip install pytmx
"""
import os.path

import sdl
from pytmx.util_pysdl2_cffi import load_pysdl2_cffi

import pyscroll
import pyscroll.data
from pyscroll.rect import Rect

# define configuration variables here
RESOURCES_DIR = 'data'

HERO_MOVE_SPEED = 200  # pixels per second
MAP_FILENAME = 'grasslands.tmx'


# make loading maps a little easier
def get_map(filename):
    return os.path.join(RESOURCES_DIR, filename)


class QuestGame(object):
    """ This class is a basic game.

    This class will load data, create a pyscroll group, a hero object.
    It also reads input and moves the Hero around the map.
    Finally, it uses a pyscroll group to render the map and Hero.
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

        # create new data source for pyscroll
        map_data = pyscroll.data.TiledMapData(tmx_data)

        # create new renderer (camera)
        screen_size = ctx.window.getWindowSize()
        self.map_layer = pyscroll.TextureRenderer(ctx, map_data, screen_size)
        self.center = [i // self.map_layer.zoom for i in map_data.pixel_size]

    def draw(self):
        renderer = self.ctx.renderer

        self.map_layer.center(self.center)
        self.map_layer.draw(renderer)
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
                    self.center[1] -= 4
                elif sym == sdl.K_DOWN:
                    self.center[1] += 4
                elif sym == sdl.K_LEFT:
                    self.center[0] -= 4
                elif sym == sdl.K_RIGHT:
                    self.center[0] += 4

    def run(self):
        """ Run the game loop
        """
        self.running = True
        import time

        target_time = 1/61.

        try:
            while self.running:
                start = time.time()

                self.handle_input()
                if self.running:
                    self.draw()

                elapsed = time.time() - start
                while elapsed < target_time:
                    time.sleep(0)
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
