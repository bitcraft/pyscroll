import unittest
from unittest.mock import MagicMock

import pygame
from pygame.rect import Rect
from pygame.sprite import Sprite
from pygame.surface import Surface

from pyscroll.group import PyscrollGroup, SpriteMeta
from pyscroll.orthographic import BufferedRenderer


class TestSpriteMeta(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_initialization_with_blendmode(self):
        surface = Surface((32, 32))
        rect = Rect(10, 10, 32, 32)
        meta = SpriteMeta(
            surface=surface, rect=rect, layer=1, blendmode=pygame.BLEND_ADD
        )

        self.assertEqual(meta.surface.get_size(), (32, 32))
        self.assertEqual(meta.rect, rect)
        self.assertEqual(meta.layer, 1)
        self.assertEqual(meta.blendmode, pygame.BLEND_ADD)

    def test_default_blendmode_is_none(self):
        surface = Surface((32, 32))
        rect = Rect(0, 0, 32, 32)
        meta = SpriteMeta(surface=surface, rect=rect, layer=0)

        self.assertIsNone(meta.blendmode)


class TestPyscrollGroup(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.surface = Surface((640, 480))
        self.map_layer = MagicMock(spec=BufferedRenderer)
        self.group = PyscrollGroup(self.map_layer)

    def test_init(self):
        self.assertIsInstance(self.group, PyscrollGroup)
        self.assertEqual(self.group._map_layer, self.map_layer)

    def test_center(self):
        self.group.center((100, 100))
        self.map_layer.center.assert_called_once_with((100, 100))

    def test_view(self):
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        view = self.group.view
        self.assertEqual(view, Rect(0, 0, 640, 480))
        self.assertIsNot(view, self.map_layer.view_rect)

    def test_draw(self):
        sprite1 = MagicMock(spec=Sprite)
        sprite1.image = Surface((32, 32))
        sprite1.rect = Rect(10, 10, 32, 32)
        sprite1.layer = 0

        sprite2 = MagicMock(spec=Sprite)
        sprite2.image = Surface((32, 32))
        sprite2.rect = Rect(600, 400, 32, 32)
        sprite2.layer = 0

        self.group.add(sprite1, sprite2)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect, sprite2.rect]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect, sprite2.rect])

    def test_draw_with_offset(self):
        sprite1 = MagicMock(spec=Sprite)
        sprite1.image = Surface((32, 32))
        sprite1.rect = Rect(10, 10, 32, 32)
        self.group.add(sprite1)

        self.map_layer.get_center_offset.return_value = (50, 50)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect.move(50, 50)]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect.move(50, 50)])

    def test_draw_with_blendmode(self):
        sprite1 = MagicMock(spec=Sprite)
        sprite1.image = Surface((32, 32))
        sprite1.rect = Rect(10, 10, 32, 32)
        sprite1.blendmode = pygame.BLEND_ADD
        self.group.add(sprite1)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect])

    def test_draw_without_blendmode(self):
        sprite1 = MagicMock(spec=Sprite)
        sprite1.image = Surface((32, 32))
        sprite1.rect = Rect(10, 10, 32, 32)
        self.group.add(sprite1)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite1.rect]

        drawn_rects = self.group.draw(self.surface)

        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn_rects, [sprite1.rect])

    def test_lostsprites_reset(self):
        sprite = MagicMock(spec=Sprite)
        sprite.image = Surface((32, 32))
        sprite.rect = Rect(10, 10, 32, 32)
        self.group.add(sprite)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite.rect]

        self.group.lostsprites = [sprite]  # manually set
        self.group.draw(self.surface)
        self.assertEqual(self.group.lostsprites, [])

    def test_sprite_layer_in_draw(self):
        sprite = MagicMock(spec=Sprite)
        sprite.image = Surface((32, 32))
        sprite.rect = Rect(10, 10, 32, 32)
        self.group.add(sprite, layer=2)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite.rect]

        self.group.draw(self.surface)
        layer = self.group.get_layer_of_sprite(sprite)
        self.assertEqual(layer, 2)

    def test_sprite_outside_view_is_skipped(self):
        sprite = MagicMock(spec=Sprite)
        sprite.image = Surface((32, 32))
        sprite.rect = Rect(1000, 1000, 32, 32)  # way outside
        self.group.add(sprite)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = []

        drawn = self.group.draw(self.surface)
        self.assertEqual(drawn, [])

    def test_sprite_partially_visible(self):
        sprite = MagicMock(spec=Sprite)
        sprite.image = Surface((32, 32))
        sprite.rect = Rect(630, 470, 32, 32)  # just inside bottom-right
        self.group.add(sprite)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite.rect]

        drawn = self.group.draw(self.surface)
        self.assertEqual(drawn, [sprite.rect])

    def test_draw_no_sprites(self):
        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = []

        drawn = self.group.draw(self.surface)
        self.map_layer.draw.assert_called_once()
        self.assertEqual(drawn, [])

    def test_draw_sprite_without_blendmode_attribute(self):
        sprite = MagicMock(spec=Sprite)
        sprite.image = Surface((32, 32))
        sprite.rect = Rect(10, 10, 32, 32)
        del sprite.blendmode  # simulate absence
        self.group.add(sprite)

        self.map_layer.get_center_offset.return_value = (0, 0)
        self.map_layer.view_rect = Rect(0, 0, 640, 480)
        self.map_layer.draw.return_value = [sprite.rect]

        drawn = self.group.draw(self.surface)
        self.assertEqual(drawn, [sprite.rect])
