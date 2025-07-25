"""
Test for pyscroll map_layer translate methods.

Draws translated rectangles and points for dummy sprites.
"""

import pygame
from pygame.locals import QUIT
from pygame.math import Vector2
from pygame.rect import Rect
from pygame.sprite import Group, Sprite
from pygame.surface import Surface


class DummySprite(Sprite):
    def __init__(self, x: int, y: int, w: int = 32, h: int = 32) -> None:
        super().__init__()
        self.rect = Rect(x, y, w, h)


class DummyMapLayer:
    """Mock map layer with translate methods for testing."""

    def __init__(self, offset: Vector2 = Vector2(100, 100)) -> None:
        self.offset = offset

    def translate_rect(self, rect: Rect) -> Rect:
        return rect.move(-self.offset.x, -self.offset.y)

    def translate_point(self, point: tuple[int, int]) -> tuple[int, int]:
        return (point[0] - int(self.offset.x), point[1] - int(self.offset.y))

    def translate_rects(self, rects: list[Rect]) -> list[Rect]:
        return [self.translate_rect(r) for r in rects]

    def translate_points(self, points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return [self.translate_point(p) for p in points]


class Dummy:
    def __init__(self, screen: Surface) -> None:
        self.screen = screen
        self._map_layer = DummyMapLayer()
        self._sprites = Group(
            DummySprite(150, 150),
            DummySprite(200, 180),
            DummySprite(250, 220),
        )

    def sprites(self) -> list[DummySprite]:
        return list(self._sprites)

    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False

            self.screen.fill((30, 30, 30))

            # Draw translated rects
            for spr in self.sprites():
                r = self._map_layer.translate_rect(spr.rect)
                pygame.draw.rect(self.screen, (20, 200, 20), r, 2)

            # Draw translated points
            for spr in self.sprites():
                p = self._map_layer.translate_point(spr.rect.topleft)
                pygame.draw.circle(self.screen, (20, 20, 200), p, 4)

            # Batch rects
            rects = [spr.rect for spr in self.sprites()]
            for r in self._map_layer.translate_rects(rects):
                pygame.draw.rect(self.screen, (200, 10, 10), r, 1)

            # Batch points
            points = [r.topleft for r in rects]
            for p in self._map_layer.translate_points(points):
                pygame.draw.circle(self.screen, (200, 10, 10), p, 3)

            pygame.display.flip()
            clock.tick(60)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("Translate Test")
    Dummy(screen).run()
    pygame.quit()


if __name__ == "__main__":
    main()
