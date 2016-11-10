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

import sdl

from mason.platform.graphics import RendererAB

logger = logging.getLogger(__file__)


@contextmanager
def render_target_context(renderer, target):
    original = sdl.getRenderTarget(renderer)
    sdl.setRenderTarget(renderer, target)
    yield
    sdl.setRenderTarget(renderer, original)


class GraphicsPysdl2cffi(RendererAB):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in mason.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """
    _always_redraw_all_tiles = True

    def __init__(self, ctx):
        # private attributes
        self.ctx = ctx
        self._buffer = None
        self._animation_map = dict()
        self._buffer_rect = sdl.Rect()
        self._sprite_offset = 0, 0

    def change_offset(self, x, y):
        x, y = int(x), int(y)
        self._buffer_rect.x = -x
        self._buffer_rect.y = -y
        self._sprite_offset = x, y

    def change_view(self, dx, dy):
        pass

    def copy_buffer(self):
        sdl.renderCopy(self.ctx.renderer, self._buffer, None, self._buffer_rect)

    def clear_buffer(self):
        renderer = self.ctx.renderer
        with render_target_context(renderer, self._buffer):
            sdl.renderClear(renderer)

    def clear_screen(self):
        sdl.renderClear(self.ctx.renderer)

    def copy_sprite(self, destination, sprite, rect):
        texture, src_rect, angle, flip = sprite

        dst_rect = sdl.Rect()
        dst_rect.x, dst_rect.y, dst_rect.w, dst_rect.h = [int(i) for i in rect]

        sdl.renderCopy(self.ctx.renderer, texture, src_rect, dst_rect)

    def new_buffer(self, desired_size):
        fmt = sdl.PIXELFORMAT_RGBA8888
        flags = sdl.TEXTUREACCESS_TARGET
        w, h = desired_size
        return sdl.createTexture(self.ctx.renderer, fmt, flags, w, h)

    def create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        self._buffer = self.new_buffer(buffer_size)
        size = sdl.queryTexture(self._buffer)[3:]
        self._buffer_rect.w, self._buffer_rect.h = size

    def flush_tile_queue(self, tile_queue):
        """ Blit the queued tiles and block until the tile queue is empty

        tex_info: (texture, src, angle, flip)
        tiles_queue: [(z, x, y, tex_info, gid), ...]

        """
        renderer = self.ctx.renderer
        rcx = sdl.renderCopyEx

        dst_rect = sdl.Rect()
        dst_rect.w = 32
        dst_rect.h = 32

        with render_target_context(renderer, self._buffer):
            for z, x, y, tile, gid in tile_queue:
                dst_rect.x = x
                dst_rect.y = y
                texture, src_rect, angle, flip = tile
                rcx(renderer, texture, src_rect, dst_rect, angle, None, flip)
