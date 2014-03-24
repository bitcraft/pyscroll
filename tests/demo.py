"""
This is tested on pygame 1.9 and python 3.3.
bitcraft (leif dot theden at gmail.com)

Simple rendering demo for the pyscroll.
"""
import pytmx
import pygame
import pyscroll
import collections
from pygame.locals import *


# simple wrapper to keep the screen resizeable
def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class ScrollTest:
    def __init__(self, filename):
        tmx_data = pytmx.load_pygame("desert.tmx")
        map_data = pyscroll.TiledMapData(tmx_data)
        self.map_layer = pyscroll.BufferedRenderer(map_data, screen.get_size())

        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        t = ["scroll demo. press escape to quit",
             "arrow keys move"]

        self.text_overlay = [f.render(i, 1, (180, 180, 0)) for i in t]
        self.center = [self.map_layer.width/2,self.map_layer.height/2]
        self.camera_vector = [0, 0, 0]
        self.running = False

    def draw(self, surface):
        self.map_layer.draw(surface, surface.get_rect())
        self.draw_text(surface)

    def draw_text(self, surface):
        y = 0
        for text in self.text_overlay:
            surface.blit(text, (0, y))
            y += text.get_height()

    def handle_input(self):
        event = pygame.event.poll()
        while event:
            if event.type == QUIT:
                self.running = False
                break

            elif event.type == KEYDOWN:
                if event.key == K_UP:
                    self.camera_vector[1] -= 100
                elif event.key == K_DOWN:
                    self.camera_vector[1] += 100
                elif event.key == K_LEFT:
                    self.camera_vector[0] -= 100
                elif event.key == K_RIGHT:
                    self.camera_vector[0] += 100
                elif event.key == K_ESCAPE:
                    self.running = False
                    break

            elif event.type == VIDEORESIZE:
                init_screen(event.w, event.h)
                self.map_layer.set_size((event.w, event.h))

            event = pygame.event.poll()

    def update(self, td):

        # map can be updated to lazily blit the off-screen tiles to the buffer
        self.map_layer.update()

        # update the camera vector
        self.center[0] += self.camera_vector[0] * td
        self.center[1] += self.camera_vector[1] * td

        # make sure the movement vector stops when scrolling off the screen
        if self.center[0] < 0: self.camera_vector[0] = 0
        if self.center[0] >= self.map_layer.width: self.camera_vector[0] = 0

        if self.center[1] < 0: self.camera_vector[1] = 0
        if self.center[1] >= self.map_layer.height: self.camera_vector[1] = 0

        self.map_layer.center(self.center)

    def run(self):
        clock = pygame.time.Clock()
        self.running = True
        fps = 60.
        fps_log = collections.deque(maxlen=20)

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

if __name__ == "__main__":
    import sys

    pygame.init()
    pygame.font.init()
    screen = init_screen(900, 700)
    pygame.display.set_caption('pyscroll Test')

    try:
        filename = sys.argv[1]
    except IndexError:
        print("no TMX map specified, using default")
        filename = "desert.tmx"

    try:
        test = ScrollTest(filename)
        test.run()
    except:
        pygame.quit()
        raise
