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

import sdl

from mason.bond.orthographic import OrthographicTiler

logger = logging.getLogger(__file__)


@contextmanager
def render_target_context(renderer, target):
    original = sdl.getRenderTarget(renderer)
    sdl.setRenderTarget(renderer, target)
    yield
    sdl.setRenderTarget(renderer, original)


class GraphicsPysdl2cffi(OrthographicTiler):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in mason.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """
    _always_clear = True

    def __init__(self, ctx, data, size, clamp_camera=False, time_source=time.time):
        # private attributes
        self.ctx = ctx
        self._animation_map = dict()
        self._buffer_rect = sdl.Rect()

        super(GraphicsPysdl2cffi, self).__init__(data, size, clamp_camera, time_source)

    def _change_view(self, dx, dy):
        self._tile_view.move_ip(dx, dy)
        self.redraw_tiles()

    def _copy_buffer(self):
        sdl.renderCopy(self.ctx.renderer, self._buffer, None, self._buffer_rect)

    def _clear_buffer(self, target, color=None):
        renderer = self.ctx.renderer
        with render_target_context(renderer, target):
            sdl.renderClear(renderer)

    def _copy_sprite(self, destination, sprite, rect):
        texture, src_rect, angle, flip = sprite

        dst_rect = sdl.Rect()
        dst_rect.x, dst_rect.y, dst_rect.w, dst_rect.h = [int(i) for i in rect]

        sdl.renderCopy(self.ctx.renderer, texture, src_rect, dst_rect)

    def _new_buffer(self, desired_size):
        fmt = sdl.PIXELFORMAT_RGBA8888
        flags = sdl.TEXTUREACCESS_TARGET
        w, h = desired_size
        return sdl.createTexture(self.ctx.renderer, fmt, flags, w, h)

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        self._buffer = self._new_buffer(buffer_size)
        size = sdl.queryTexture(self._buffer)[3:]
        self._buffer_rect.w, self._buffer_rect.h = size

    def _flush_tile_queue(self, destination=None):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        renderer = self.ctx.renderer
        map_get = self._animation_map.get
        rcx = sdl.renderCopyEx

        dst_rect = sdl.Rect()
        dst_rect.w = tw
        dst_rect.h = th

        with render_target_context(self.ctx.renderer, self._buffer):
            for z, x, y, tile, gid in self._tile_queue:
                texture, src_rect, angle, flip = map_get(gid, tile)
                dst_rect.x = x * tw - ltw
                dst_rect.y = y * th - tth
                rcx(renderer, texture, src_rect, dst_rect, angle, None, flip)
