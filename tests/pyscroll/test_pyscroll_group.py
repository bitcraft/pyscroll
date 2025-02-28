import unittest
from unittest.mock import MagicMock

import pygame

from pyscroll.group import PyscrollGroup
from pyscroll.orthographic import BufferedRenderer


class TestPyscrollGroup(unittest.TestCase):

    def setUp(self):
        pygame.init()
        self.surface = pygame.Surface((640, 480))
        self.map_layer = MagicMock(spec=BufferedRenderer)
        self.group = PyscrollGroup(self.map_layer)

    def tearDown(self):
        pygame.quit()

    def test_init(self):
        self.assertIsInstance(self.group, PyscrollGroup)
        self.assertEqual(self.group._map_layer, self.map_layer)

    def test_center(self):
        self.group.center((100, 100))
        self.map_layer.center.assert_called_once_with((100, 100))

    def test_view(self):
        self.map_layer.view_rect = pygame.Rect(0, 0, 640, 480)
        view = self.group.view
        self.assertEqual(view, pygame.Rect(0, 0, 640, 480))
        self.assertIsNot(view, self.map_layer.view_rect)

    def test_draw(self):
        sprite1 = MagicMock(spec=pygame.sprite.Sprite)
        sprite1.image = pygame.Surface((32, 32))
        sprite1.rect = pygame.Rect(10, 10, 32, 32)
        sprite1.layer = 0

        sprite2 = MagicMock(spec=pygame.sprite.Sprite)
        sprite2.image = pygame.Surface((32, 32))
        sprite2.rect = pygame.Rect(600, 400, 32, 32)
        sprite2.layer = 0

        self.group.add(sprite1, sprite2)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = pygame.Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect, sprite2.rect]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect, sprite2.rect])

    def test_draw_with_offset(self):
        sprite1 = MagicMock(spec=pygame.sprite.Sprite)
        sprite1.image = pygame.Surface((32, 32))
        sprite1.rect = pygame.Rect(10, 10, 32, 32)
        self.group.add(sprite1)

        self.map_layer.get_center_offset.return_value = (50, 50)
        self.map_layer.view_rect = pygame.Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect.move(50,50)]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect.move(50,50)])

    def test_draw_with_blendmode(self):
        sprite1 = MagicMock(spec=pygame.sprite.Sprite)
        sprite1.image = pygame.Surface((32, 32))
        sprite1.rect = pygame.Rect(10, 10, 32, 32)
        sprite1.blendmode = pygame.BLEND_ADD
        self.group.add(sprite1)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = pygame.Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect])

    def test_draw_without_blendmode(self):
        sprite1 = MagicMock(spec=pygame.sprite.Sprite)
        sprite1.image = pygame.Surface((32, 32))
        sprite1.rect = pygame.Rect(10, 10, 32, 32)
        self.group.add(sprite1)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = pygame.Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect])
