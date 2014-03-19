"""
This is tested on pygame 1.9 and python 3.3.
bitcraft (leif dot theden at gmail.com)

Rendering demo (pixelated) for the pyscroll.
"""
import pytmx
import pyscroll
import pygame
from pygame.locals import *


# simple wrapper to keep the screen resizeable
def init_screen(width, height):
    return pygame.display.set_mode((width, height), pygame.RESIZABLE)


class ScrollTest:
    def __init__(self, filename):
        self.init_buffer([screen.get_width() / 2, screen.get_height() / 2])

        tmx_data = pytmx.load_pygame("desert.tmx")
        map_data = pyscroll.TiledMapData(tmx_data)
        self.map_layer = pyscroll.BufferedRenderer(map_data, self.buffer_size)

        f = pygame.font.Font(pygame.font.get_default_font(), 20)
        t = ["scroll demo. press escape to quit",
             "arrow keys move"]

        self.text_overlay = [f.render(i, 1, (180, 180, 0)) for i in t]
        self.center = [self.map_layer.width/2,self.map_layer.height/2]
        self.camera_vector = [0, 0, 0]
        self.running = False

    def init_buffer(self, size):
        self.map_buffer = pygame.Surface(size)
        self.buffer_size = self.map_buffer.get_size()

    def draw(self, surface):
        self.map_layer.draw(self.map_buffer, surface.get_rect())
        pygame.transform.scale(self.map_buffer, surface.get_size(), surface)
        self.draw_text(surface)

    def draw_text(self, surface):
        y = 0
        for text in self.text_overlay:
            surface.blit(text, (0, y))
            y += text.get_height()

    def handle_input(self):
        for event in pygame.event.get():
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
                self.init_buffer([screen.get_width() / 2, screen.get_height() / 2])
                self.map_layer.set_size(self.buffer_size)

    def update(self, td):

        # map can be updated to lazily blit the off-screen tiles to the buffer
        self.map_layer.update()

        # update the camera vector
        self.center[0] += self.camera_vector[0] * td
        self.center[1] += self.camera_vector[1] * td

        # make sure the movement vector stops when scrolling off the screen
        # not perfect, though.
        if self.center[0] < 0: self.camera_vector[0] = 0
        if self.center[0] >= self.map_layer.width: self.camera_vector[0] = 0

        if self.center[1] < 0: self.camera_vector[1] = 0
        if self.center[1] >= self.map_layer.height: self.camera_vector[1] = 0

        self.map_layer.center(self.center)

    def run(self):
        clock = pygame.time.Clock()
        self.running = True

        try:
            while self.running:
                td = clock.tick(60) / 1000.0
                self.handle_input()
                self.update(td)
                self.draw(screen)
                pygame.display.flip()

        except KeyboardInterrupt:
            self.running = False

if __name__ == "__main__":
    import sys
    sys.path.append('..')

    pygame.init()
    pygame.font.init()
    screen = init_screen(700, 700)
    pygame.display.set_caption('pyscroll Test')

    try:
        filename = sys.argv[1]
    except IndexError:
        print("no TMX map specified, using default")
        filename = "desert.tmx"

    test = ScrollTest(filename)
    test.run()

    pygame.quit()
