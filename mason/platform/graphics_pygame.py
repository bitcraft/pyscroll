# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2016

This file is part of mason.

mason is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

mason is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with mason.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import division

import logging
from contextlib import contextmanager

import pygame

from mason.platform.graphics import RendererAB

logger = logging.getLogger(__file__)


@contextmanager
def surface_clipping_context(surface, clip):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


class PygameGraphics(RendererAB):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in mason.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """
    alpha_clear_color = 0, 0, 0, 0

    def __init__(self, colorkey=None, alpha=False, scaling_function=pygame.transform.scale):

        # default_options
        self.scaling_function = scaling_function  # what function to use when scaling the zoom buffer

        # internal private defaults
        self._zoom_buffer = None  # used to speed up zoom operations
        self._buffer = None
        self._buffer_rect = pygame.Rect(0, 0, 100, 100)
        self._sprite_offset = 0, 0

        # handle colorkey/alpha
        if colorkey and alpha:
            print('cannot select both colorkey and alpha.  choose one.')
            raise ValueError
        elif colorkey:
            self._clear_color = colorkey
            self._colorkey = True
        elif alpha:
            self._clear_color = self.alpha_clear_color
            self._alpha = True
        else:
            self._clear_color = None
            self._alpha = False
            self._colorkey = False

    def change_offset(self, x, y):
        x, y = int(x), int(y)
        self._buffer_rect.x = -x
        self._buffer_rect.y = -y
        self._sprite_offset = x, y

    def change_view(self, dx, dy):
        view_change = max(abs(dx), abs(dy))

        redraw_cutoff = 1

        if view_change and view_change <= redraw_cutoff:
            tw, th = 32, 32
            self._buffer.scroll(-dx * tw, -dy * th)
            # self._queue_edge_tiles(dx, dy)
            # self.flush_tile_queue()

        elif view_change > redraw_cutoff:
            logger.info('scrolling too quickly.  redraw forced')

    def clear_screen(self):
        surface = pygame.display.get_surface()
        surface.fill(0)

    def copy_buffer(self):
        destination = pygame.display.get_surface()
        destination.blit(self._buffer, self._buffer_rect)

    def clear_buffer(self):
        self._buffer.fill(self._clear_color)

    def new_buffer(self, size):
        if self._alpha:
            return pygame.Surface(size, flags=pygame.SRCALPHA)
        elif self._colorkey:
            surface = pygame.Surface(size, flags=pygame.RLEACCEL)
            surface.set_colorkey(self._clear_color)
            return surface
        else:
            return pygame.Surface(size)

    def create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        logger.warn('creating pygame buffers')
        requires_zoom_buffer = not view_size == buffer_size

        if requires_zoom_buffer:
            self._zoom_buffer = self.new_buffer(view_size)
        else:
            self._zoom_buffer = None

        self._buffer = self.new_buffer(buffer_size)
        self._buffer_rect.size = buffer_size
        # self.data.convert_surfaces(self._buffer, True)

    def flush_sprite_queue(self, sprite_queue):
        destination = pygame.display.get_surface()
        blit = destination.blit

        for sprite, rect in sprite_queue:
            blit(sprite, rect)

    def flush_tile_queue(self, tile_queue):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        blit = self._buffer.blit

        for sprite, rect in tile_queue:
            blit(sprite, rect)
