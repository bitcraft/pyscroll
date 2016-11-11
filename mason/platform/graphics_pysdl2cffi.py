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
    """ Renderer for use with pysdl2_cffi
    """
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
        """ Copy the buffer to the screen

        :return:
        """
        sdl.renderCopy(self.ctx.renderer, self._buffer, None, self._buffer_rect)

    def clear_buffer(self):
        """ Clear the buffer

        :return:
        """
        renderer = self.ctx.renderer
        with render_target_context(renderer, self._buffer):
            sdl.renderClear(renderer)

    def clear_screen(self):
        """ Clear the screen

        :return:
        """
        sdl.renderClear(self.ctx.renderer)

    def new_buffer(self, desired_size):
        """ New buffer for use as render target

        :param desired_size:
        :return:
        """
        fmt = sdl.PIXELFORMAT_RGBA8888
        flags = sdl.TEXTUREACCESS_TARGET
        w, h = desired_size
        return sdl.createTexture(self.ctx.renderer, fmt, flags, w, h)

    def create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        print(view_size, buffer_size)
        self._buffer = self.new_buffer(buffer_size)
        size = sdl.queryTexture(self._buffer)[3:]
        self._buffer_rect.w, self._buffer_rect.h = 1632, 1248
        print(view_size, buffer_size, size)

    def flush_sprite_queue(self, sprite_queue):
        """ Copy a list of sprites to the screen

        :param sprite_queue:
        :return:
        """
        renderer = self.ctx.renderer
        dst_rect = sdl.Rect()
        rcx = sdl.renderCopyEx

        for sprite, rect in sprite_queue:
            texture, src_rect, angle, flip = sprite
            dst_rect.x, dst_rect.y, dst_rect.w, dst_rect.h = [int(i) for i in rect]
            rcx(renderer, texture, src_rect, dst_rect, angle, None, flip)

    def flush_tile_queue(self, tile_queue):
        """ Copy a list of tiles to the buffer

        tex_info: (texture, src, angle, flip)
        tiles_queue: [(z, x, y, tex_info, gid), ...]

        """
        with render_target_context(self.ctx.renderer, self._buffer):
            self.flush_sprite_queue(tile_queue)
