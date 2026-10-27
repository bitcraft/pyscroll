import unittest

import pygame

from pyscroll.data import PyscrollDataAdapter
from pyscroll.orthographic import BufferedRenderer


class ColorTiles(PyscrollDataAdapter):
    tile_size = (4, 4)
    map_size = (20, 20)
    visible_tile_layers = [0]

    def get_animations(self):
        return []

    def get_tile_image(self, x, y, layer):
        tile = pygame.Surface(self.tile_size, pygame.SRCALPHA)
        tile.fill((40 + x * 5, 60 + y * 5, 180, 255))
        tile.fill((0, 0, 0, 0), (0, 0, 2, 2))
        return tile

    def convert_surfaces(self, parent, alpha=False):
        pass


class TestZoomDrawArea(unittest.TestCase):
    def check_draw(self, zoom, rect, clip=None, **options):
        renderer = BufferedRenderer(ColorTiles(), (8, 8), zoom=zoom, **options)
        destination = pygame.Surface((16, 16), pygame.SRCALPHA)
        destination.fill((20, 30, 40, 255))
        if clip is not None:
            destination.set_clip(clip)
        expected = destination.copy()
        expected.set_clip(destination.get_clip())

        # Render the same camera without zoom, then scale and place it normally.
        reference = BufferedRenderer(ColorTiles(), renderer.view_rect.size, **options)
        image = pygame.Surface(reference.view_rect.size, pygame.SRCALPHA)
        reference.draw(image, image.get_rect())
        scaled = pygame.transform.scale(image, rect.size)
        expected_area = expected.blit(scaled, rect)

        result = renderer.draw(destination, rect)
        self.assertEqual(result, expected_area)
        self.assertEqual(destination.get_clip(), expected.get_clip())
        self.assertEqual(
            pygame.image.tobytes(destination, "RGBA"),
            pygame.image.tobytes(expected, "RGBA"),
        )

    def test_zoomed_subrectangle(self):
        for zoom in (0.5, 2.0):
            with self.subTest(zoom=zoom):
                self.check_draw(zoom, pygame.Rect(3, 4, 8, 8))

    def test_zoomed_rectangle_clipped_by_surface(self):
        self.check_draw(2.0, pygame.Rect(-2, 12, 8, 8))

    def test_zoomed_rectangle_respects_existing_clip(self):
        self.check_draw(2.0, pygame.Rect(0, 0, 16, 16), (4, 5, 6, 7))

    def test_zoomed_alpha_subrectangle(self):
        self.check_draw(2.0, pygame.Rect(3, 4, 8, 8), alpha=True)

    def test_subrectangle_keeps_three_argument_scaler(self):
        calls = []

        def scale(source, size, target):
            calls.append(target.get_size())
            return pygame.transform.scale(source, size, target)

        self.check_draw(2.0, pygame.Rect(3, 4, 8, 8), scaling_function=scale)
        self.assertEqual(calls, [(8, 8)])

    def test_full_surface_keeps_three_argument_scaler(self):
        calls = []

        def scale(source, size, target):
            calls.append(target)
            return pygame.transform.scale(source, size, target)

        renderer = BufferedRenderer(
            ColorTiles(), (8, 8), zoom=2.0, scaling_function=scale
        )
        destination = pygame.Surface((8, 8))
        result = renderer.draw(destination, destination.get_rect())
        self.assertEqual(calls, [destination])
        self.assertEqual(result, destination.get_rect())
