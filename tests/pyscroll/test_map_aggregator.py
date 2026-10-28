import itertools
import unittest

import pygame

from pyscroll.data import MapAggregator, PyscrollDataAdapter


class SolidMap(PyscrollDataAdapter):
    tile_size = (2, 2)
    visible_tile_layers = [0]

    def __init__(self, size, color):
        super().__init__()
        self.map_size = size
        self.image = pygame.Surface(self.tile_size)
        self.image.fill(color)

    def _get_tile_image(self, x, y, layer):
        if 0 <= x < self.map_size[0] and 0 <= y < self.map_size[1]:
            return self.image


class TestMapAggregator(unittest.TestCase):
    def check_layout(self, entries):
        aggregator = MapAggregator(SolidMap.tile_size)
        added = []
        for size, offset, color in entries:
            data = SolidMap(size, color)
            added.append((data, offset))
            aggregator.add_map(data, offset)
            min_x = min(0, *(position[0] for _, position in added))
            min_y = min(0, *(position[1] for _, position in added))
            expected_size = (
                max(position[0] + source.map_size[0] for source, position in added)
                - min_x,
                max(position[1] + source.map_size[1] for source, position in added)
                - min_y,
            )
            self.assertEqual(aggregator.map_size, expected_size)
            for (source, rect), (original, position) in zip(aggregator.maps, added):
                self.assertIs(source, original)
                self.assertEqual(
                    rect.topleft, (position[0] - min_x, position[1] - min_y)
                )
                self.assertEqual(rect.size, source.map_size)
        return aggregator

    def test_smaller_map_does_not_shrink_world(self):
        self.check_layout([((10, 8), (0, 0), "red"), ((1, 1), (2, 3), "green")])

    def test_new_minimum_moves_only_that_axis(self):
        for offset in [(-3, 5), (5, -3), (-3, -5)]:
            with self.subTest(offset=offset):
                self.check_layout([((2, 2), (0, 0), "red"), ((2, 2), offset, "green")])

    def test_map_order_and_repeated_origin_changes(self):
        entries = [
            ((2, 3), (-4, 2), "red"),
            ((3, 2), (3, -5), "green"),
            ((1, 1), (0, 0), "blue"),
        ]
        for order in itertools.permutations(entries):
            with self.subTest(offsets=[entry[1] for entry in order]):
                self.check_layout(order)

    def test_tile_queries_use_normalized_map_positions(self):
        entries = [
            ((2, 2), (0, 0), "red"),
            ((2, 2), (-3, 4), "green"),
            ((1, 1), (5, -2), "blue"),
        ]
        aggregator = MapAggregator(SolidMap.tile_size)
        for size, offset, color in entries:
            aggregator.add_map(SolidMap(size, color), offset)
        min_x, min_y = -3, -2
        expected = {}
        for (width, height), (ox, oy), color in entries:
            for x, y in itertools.product(range(width), range(height)):
                expected[x + ox - min_x, y + oy - min_y] = pygame.Color(color)
        for view in [pygame.Rect(0, 0, 9, 8), pygame.Rect(0, 5, 3, 3)]:
            with self.subTest(view=view):
                actual = {
                    (x, y): image.get_at((0, 0))
                    for x, y, layer, image in aggregator.get_tile_images_by_rect(view)
                }
                self.assertEqual(
                    actual,
                    {
                        position: color
                        for position, color in expected.items()
                        if view.collidepoint(position)
                    },
                )
