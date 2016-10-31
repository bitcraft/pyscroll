"""
This is tested on pygame 1.9 and python 3.3 & 2.7.
bitcraft (leif dot theden at gmail.com)

Rendering demo for the pyscroll.

Use the arrow keys to smoothly scroll the map.
Window is resizable.

See the "Quest" tutorial for a more simple use with
pygame sprites and groups.
"""
from pytmx.util_pysdl2_cffi import load_pysdl2_cffi
import pyscroll
import pyscroll.data
import collections
import sdl
import logging

logger = logging.getLogger(__name__)

SCROLL_SPEED = 5000


class ScrollTest:
    """ Test and demo of pyscroll

    For normal use, please see the quest demo, not this.

    """
    def __init__(self, ctx, filename):
        self.ctx = ctx
        self.event = sdl.Event()
        self.running = False
        self.pressed = collections.defaultdict(bool)

        # load data from pytmx
        tmx_data = load_pysdl2_cffi(ctx, filename)

        # create new data source
        map_data = pyscroll.data.TiledMapData(tmx_data)

        # create new renderer
        screen_size = ctx.window.getWindowSize()
        self.map_layer = pyscroll.TextureRenderer(ctx, map_data, screen_size)
        self.center = [(i // self.map_layer.zoom) // 2 for i in map_data.pixel_size]

        # create a font and pre-render some text to be displayed over the map
        # f = pygame.font.Font(pygame.font.get_default_font(), 20)
        # t = ["scroll demo. press escape to quit",
        #      "arrow keys move"]

        # save the rendered text
        # self.text_overlay = [f.render(i, 1, (180, 180, 0)) for i in t]

        # set our initial viewpoint in the center of the map

        # the camera vector is used to handle camera movement
        self.camera_acc = [0, 0, 0]
        self.camera_vel = [0, 0, 0]
        self.last_update_time = 0

    def draw(self):
        renderer = self.ctx.renderer

        # tell the map_layer (BufferedRenderer) to draw to the surface
        # the draw function requires a rect to draw to.
        self.map_layer.center(self.center)
        self.map_layer.draw(renderer)
        sdl.renderPresent(renderer)

        # blit our text over the map
        # self.draw_text(surface)

    def draw_text(self, surface):
        y = 0
        for text in self.text_overlay:
            surface.blit(text, (0, y))
            y += text.get_height()

    def handle_input(self):
        """ Simply handle pygame input events
        """
        event = self.event
        pressed = self.pressed
        keys = {sdl.K_UP, sdl.K_DOWN, sdl.K_LEFT, sdl.K_RIGHT}

        while sdl.pollEvent(event) != 0:
            if is_quit_event(event):
                quit_sdl(self.ctx)
                self.running = False
                break

            elif event.type == sdl.KEYDOWN:
                sym = event.key.keysym.sym
                if sym in keys:
                    pressed[sym] = True

            elif event.type == sdl.KEYUP:
                sym = event.key.keysym.sym
                if sym in keys:
                    pressed[sym] = False

        # these keys will change the camera vector
        # the camera vector changes the center of the viewport,
        # which causes the map to scroll
        if pressed[sdl.K_UP]:
            self.camera_acc[1] = -SCROLL_SPEED * self.last_update_time
        elif pressed[sdl.K_DOWN]:
            self.camera_acc[1] = SCROLL_SPEED * self.last_update_time
        else:
            self.camera_acc[1] = 0

        if pressed[sdl.K_LEFT]:
            self.camera_acc[0] = -SCROLL_SPEED * self.last_update_time
        elif pressed[sdl.K_RIGHT]:
            self.camera_acc[0] = SCROLL_SPEED * self.last_update_time
        else:
            self.camera_acc[0] = 0

    def update(self, td):
        self.last_update_time = td

        friction = pow(.0001, self.last_update_time)

        # update the camera vector
        self.camera_vel[0] += self.camera_acc[0] * td
        self.camera_vel[1] += self.camera_acc[1] * td

        self.camera_vel[0] *= friction
        self.camera_vel[1] *= friction

        # make sure the movement vector stops when scrolling off the screen
        # if self.center[0] < 0:
        #     self.center[0] -= self.camera_vel[0]
        #     self.camera_acc[0] = 0
        #     self.camera_vel[0] = 0
        # if self.center[0] >= self.map_layer.map_rect.width:
        #     self.center[0] -= self.camera_vel[0]
        #     self.camera_acc[0] = 0
        #     self.camera_vel[0] = 0
        #
        # if self.center[1] < 0:
        #     self.center[1] -= self.camera_vel[1]
        #     self.camera_acc[1] = 0
        #     self.camera_vel[1] = 0
        # if self.center[1] >= self.map_layer.map_rect.height:
        #     self.center[1] -= self.camera_vel[1]
        #     self.camera_acc[1] = 0
        #     self.camera_vel[1] = 0

        self.center[0] += self.camera_vel[0]
        self.center[1] += self.camera_vel[1]

        # set the center somewhere else
        # in a game, you would set center to a playable character
        self.map_layer.center(self.center)

    def run(self):
        self.running = True

        import time
        time_func = time.time

        target_time = 1/60.
        # fps_log = collections.deque(maxlen=20)

        try:
            dt = 0
            while self.running:
                start = time.time()
                self.last_update_time = dt

                self.handle_input()
                if self.running:
                    self.update(target_time)
                    self.draw()

                dt = time_func() - start
                while dt < target_time:
                    dt = time_func() - start

                self.last_update_time = dt

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
    import sys

    sdl.init(sdl.INIT_VIDEO)

    ctx = SDLContext()
    ctx.display_info = sdl.DisplayMode()
    sdl.getDesktopDisplayMode(0, ctx.display_info)

    ctx.window = sdl.createWindow(
        "reeeeeeeee",
        0, 0, 800, 600,
        sdl.WINDOW_SHOWN)

    # sdl.setWindowFullscreen(ctx.window, sdl.WINDOW_FULLSCREEN)

    ctx.renderer = sdl.createRenderer(
        ctx.window,
        -1,  # What's this do? ¯\_(ツ)_/¯
        sdl.RENDERER_ACCELERATED |
        sdl.RENDERER_PRESENTVSYNC)

    try:
        filename = sys.argv[1]
    except IndexError:
        logger.info("no TMX map specified, using default")
        filename = "desert.tmx"

    try:
        test = ScrollTest(ctx, filename)
        test.run()
    except:
        raise
