"""
This is tested on pygame 1.9 and python 3.3.
bitcraft (leif dot theden at gmail.com)

Simple rendering demo for the pyscroll.
"""
import pytmx
import pygame
import pyscroll
import collections
import logging
from pygame.locals import *


# pyscroll is a python 2.7/3.3 project
# using the logging module simplifies "print" statements and has nice output.
# the following sets the logger up for this app.
# NOTE: it is not necessary for your app to do this, but it is a good practice.
logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
logger.setLevel(logging.INFO)

SCROLL_SPEED = 5000


# simple wrapper to keep the screen resizeable
def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class ScrollTest:
    """ Test and demo of pyscroll

    Using this class as a guide, you can adopt pyscroll into your new or
    existing game or app.  I'm using PyTMX as that data provider, but you are
    free to use and data source that conforms the the pyscroll data api.
    """
    def __init__(self, filename):

        # load data from pytmx
        tmx_data = pytmx.load_pygame(filename)

        # create new data source
        map_data = pyscroll.TiledMapData(tmx_data)

        # create new renderer
        # pyscroll only has two renderers: BufferedRenderer
        #                                  ThreadedRenderer
        # the threaded renderer is an experimental feature

        #self.map_layer = pyscroll.ThreadedRenderer(map_data, screen.get_size())
        self.map_layer = pyscroll.BufferedRenderer(map_data, screen.get_size())

        # create a font and pre-render some text to be displayed over the map
        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        t = ["scroll demo. press escape to quit",
             "arrow keys move"]

        # save the rendered text
        self.text_overlay = [f.render(i, 1, (180, 180, 0)) for i in t]

        # set our initial viewpoint in the center of the map
        self.center = [self.map_layer.rect.width / 2,
                       self.map_layer.rect.height / 2]

        # the camera vector is used to handle camera movement
        self.camera_acc = [0, 0, 0]
        self.camera_vel = [0, 0, 0]
        self.last_update_time = 0

        # true when running
        self.running = False

    def draw(self, surface):

        # tell the map_layer (BufferedRenderer) to draw to the surface
        # the draw function requires a rect to draw to.
        self.map_layer.draw(surface, surface.get_rect())

        # blit our text over the map
        self.draw_text(surface)

    def draw_text(self, surface):
        y = 0
        for text in self.text_overlay:
            surface.blit(text, (0, y))
            y += text.get_height()

    def handle_input(self):
        """ Simply handle pygame input events
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

        # these keys will change the camera vector
        # the camera vector changes the center of the viewport,
        # which causes the map to scroll

        # using get_pressed is slightly less accurate than testing for events
        # but is much easier to use.
        pressed = pygame.key.get_pressed()
        if pressed[K_UP]:
            self.camera_acc[1] = -SCROLL_SPEED * self.last_update_time
        elif pressed[K_DOWN]:
            self.camera_acc[1] = SCROLL_SPEED * self.last_update_time
        else:
            self.camera_acc[1] = 0

        if pressed[K_LEFT]:
            self.camera_acc[0] = -SCROLL_SPEED * self.last_update_time
        elif pressed[K_RIGHT]:
            self.camera_acc[0] = SCROLL_SPEED * self.last_update_time
        else:
            self.camera_acc[0] = 0

    def update(self, td):

        # map can be updated to lazily blit the off-screen tiles to the buffer
        self.map_layer.update()

        self.last_update_time = td

        friction = pow(.0001, self.last_update_time)

        # update the camera vector
        self.camera_vel[0] += self.camera_acc[0] * td
        self.camera_vel[1] += self.camera_acc[1] * td

        self.camera_vel[0] *= friction
        self.camera_vel[1] *= friction

        # make sure the movement vector stops when scrolling off the screen
        if self.center[0] < 0:
            self.center[0] -= self.camera_vel[0]
            self.camera_acc[0] = 0
            self.camera_vel[0] = 0
        if self.center[0] >= self.map_layer.rect.width :
            self.center[0] -= self.camera_vel[0]
            self.camera_acc[0] = 0
            self.camera_vel[0] = 0

        if self.center[1] < 0:
            self.center[1] -= self.camera_vel[1]
            self.camera_acc[1] = 0
            self.camera_vel[1] = 0
        if self.center[1] >= self.map_layer.rect.height:
            self.center[1] -= self.camera_vel[1]
            self.camera_acc[1] = 0
            self.camera_vel[1] = 0

        self.center[0] += self.camera_vel[0]
        self.center[1] += self.camera_vel[1]

        # set the center somewhere else
        # in a game, you would set center to a playable character
        self.map_layer.center(self.center)

    def run(self):
        clock = pygame.time.Clock()
        self.running = True
        fps = 60.
        fps_log = collections.deque(maxlen=30)

        try:
            while self.running:

                # somewhat smoother way to get fps
                clock.tick(fps*2)
                try:
                    fps_log.append(clock.get_fps())
                    fps = sum(fps_log)/len(fps_log)
                    dt = 1/fps
                except ZeroDivisionError:
                    dt = 1/60.

                self.handle_input()
                self.update(dt)
                self.draw(screen)
                pygame.display.flip()

        except KeyboardInterrupt:
            self.running = False

        self.map_layer.close()

if __name__ == "__main__":
    import sys

    pygame.init()
    pygame.font.init()
    screen = init_screen(800, 600)
    pygame.display.set_caption('pyscroll Test')

    try:
        filename = sys.argv[1]
    except IndexError:
        logger.info("no TMX map specified, using default")
        filename = "desert.tmx"

    try:
        test = ScrollTest(filename)
        test.run()
    except:
        pygame.quit()
        raise
