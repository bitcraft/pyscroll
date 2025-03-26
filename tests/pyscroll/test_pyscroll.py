import unittest
from unittest import mock

import pygame

from pyscroll.common import Vector2DInt
from pyscroll.data import PyscrollDataAdapter
from pyscroll.orthographic import BufferedRenderer


class DummyDataAdapter(PyscrollDataAdapter):
    tile_size = (32, 32)
    map_size = (32, 32)
    visible_tile_layers = [1]

    def get_animations(self):
        return []

    def get_tile_image(self, *position):
        return position[0] * position[1]


class DummyBufferer:
    _tile_view = pygame.Rect(2, 2, 2, 2)
    _clear_color = None
    _buffer = mock.Mock()
    _clear_surface = mock.Mock()
    data = DummyDataAdapter()


class TestTileQueue(unittest.TestCase):
    def setUp(self) -> None:
        self.mock = DummyBufferer()
        self.queue = BufferedRenderer._queue_edge_tiles

    def verify_queue(self, expected: set[Vector2DInt]) -> None:
        queue = {i[:2] for i in self.mock._tile_queue}
        self.assertEqual(queue, set(expected))

    def test_queue_left(self) -> None:
        self.queue(self.mock, -1, 0)
        self.verify_queue({(2, 3), (2, 2)})

    def test_queue_top(self) -> None:
        self.queue(self.mock, 0, -1)
        self.verify_queue({(2, 2), (3, 2)})

    def test_queue_right(self) -> None:
        self.queue(self.mock, 1, 0)
        self.verify_queue({(3, 3), (3, 2)})

    def test_queue_bottom(self) -> None:
        self.queue(self.mock, 0, 1)
        self.verify_queue({(2, 3), (3, 3)})
