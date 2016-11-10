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
from __future__ import print_function

import logging
import time
from contextlib import contextmanager
from heapq import heappop, heappush

import pygame

from mason.bond.orthographic import OrthographicTiler

logger = logging.getLogger(__file__)


@contextmanager
def surface_clipping_context(surface, clip):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


class PygameGraphics(OrthographicTiler):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in mason.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """
    alpha_clear_color = 0, 0, 0, 0

    def __init__(self, data, size, clamp_camera=True, colorkey=None, alpha=False,
                 time_source=time.time, scaling_function=pygame.transform.scale):

        # default_options
        self.scaling_function = scaling_function  # what function to use when scaling the zoom buffer

        # internal private defaults
        self._zoom_buffer = None  # used to speed up zoom operations
        self._buffer_rect = pygame.Rect(0, 0, 100, 100)

        # handle colorkey/alpha
        if colorkey and alpha:
            print('cannot select both colorkey and alpha.  choose one.')
            raise ValueError
        elif colorkey:
            self._clear_color = colorkey
            self._colorkey = True
        elif alpha:
            self._alpha = True
        else:
            self._clear_color = None
            self._alpha = False
            self._colorkey = False

        super(PygameGraphics, self).__init__(data, size, clamp_camera, time_source)

    def _change_view(self, dx, dy):
        view_change = max(abs(dx), abs(dy))

        if view_change and (view_change <= self._redraw_cutoff):
            tw, th = self.data.tile_size
            self._buffer.scroll(-dx * tw, -dy * th)
            self._tile_view.move_ip(dx, dy)
            self._queue_edge_tiles(dx, dy)
            self._flush_tile_queue(self._buffer)

        elif view_change > self._redraw_cutoff:
            logger.info('scrolling too quickly.  redraw forced')
            self._tile_view.move_ip(dx, dy)
            self.redraw_tiles(self._buffer)

    def _copy_sprite(self, destination, sprite, rect):
        return destination.blit(sprite, rect)

    def draw(self, sprites, surface=None, rect=None):
        """ Draw the map onto a surface

        pass a rect that defines the draw area for:
            drawing to an area smaller that the whole window/screen

        surfaces may optionally be passed that will be blitted onto the surface.
        this must be a sequence of tuples containing a layer number, image, and
        rect in screen coordinates.  surfaces will be drawn in order passed,
        and will be correctly drawn with tiles from a higher layer overlapping
        the surface.

        surfaces list should be in the following format:
        [ (layer, surface, rect), ... ]

        or this:
        [ (layer, surface, rect, blendmode_flags), ... ]

        :param surface: pygame surface to draw to
        :param rect: area to draw to
        :param sprites: optional sequence of surfaces to interlace between tiles
        """
        if self._animation_queue:
            self._process_animation_queue()

        if not self.anchored_view:
            self._clear_screen()

        with surface_clipping_context(surface, rect):
            if self._zoom_level == 1.0:
                self._copy_buffer(surface)
            else:
                self._copy_buffer(surface)
                # self._draw_map(self._zoom_buffer, self._zoom_buffer.get_rect(), sprites)
                # self.scaling_function(self._zoom_buffer, rect.size, surface)

            if sprites:
                self._draw_surfaces(surface, sprites)

    def _copy_buffer(self, destination):
        destination.blit(self._buffer, self._buffer_rect)

    def _clear_buffer(self, target, color):
        target.fill(color)

    def _new_buffer(self, size):
        if self._alpha:
            return pygame.Surface(size, flags=pygame.SRCALPHA)
        elif self._colorkey:
            surface = pygame.Surface(size, flags=pygame.RLEACCEL)
            surface.set_colorkey(self._clear_color)
            return surface
        else:
            return pygame.Surface(size)

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        logger.warn('creating pygame buffers')
        requires_zoom_buffer = not view_size == buffer_size

        if requires_zoom_buffer:
            self._zoom_buffer = self._new_buffer(view_size)
        else:
            self._zoom_buffer = None

        self._buffer = self._new_buffer(buffer_size)
        self._buffer_rect.size = buffer_size
        self.data.convert_surfaces(self._buffer, True)

    def _flush_tile_queue(self, surface):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        surface_blit = surface.blit
        ani_tiles = self._animation_tiles

        for z, x, y, tile, gid in self._tile_queue:
            ani_tiles[gid].add((x, y))
            surface_blit(tile, (x * tw - ltw, y * th - tth))
