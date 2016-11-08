"""
Copyright (C) 2012-2016

This file is part of pyscroll.

pyscroll is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyscroll is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pyscroll.  If not, see <http://www.gnu.org/licenses/>.
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

    def __init__(self, ctx, data, size, clamp_camera=False, time_source=time.time):
        # private attributes
        self.ctx = ctx
        self._animation_map = dict()
        self._buffer_rect = sdl.Rect()
        self._always_clear = True

        super(GraphicsPysdl2cffi, self).__init__(data, size, clamp_camera, time_source)

    def _change_offset(self, x, y):
        self._buffer_rect.x = -int(x)
        self._buffer_rect.y = -int(y)

    def _change_view(self, dx, dy):
        self._tile_view.move_ip(dx, dy)
        self.redraw_tiles()

    def _copy_buffer(self):
        sdl.renderCopy(self.ctx.renderer, self._buffer, None, self._buffer_rect)

    def _clear_buffer(self, target, color=None):
        renderer = self.ctx.renderer
        orig = sdl.getRenderTarget(renderer)
        sdl.setRenderTarget(renderer, target)
        sdl.renderClear(renderer)
        sdl.setRenderTarget(renderer, orig)

    def _process_animation_queue(self):
        self._update_time()
        needs_redraw = False

        # test if the next scheduled tile change is ready
        while self._animation_queue[0].next <= self._last_time:
            needs_redraw = True
            token = heappop(self._animation_queue)

            # advance the animation frame index, looping by default
            if token.index == len(token.frames) - 1:
                token.index = 0
            else:
                token.index += 1

            next_frame = token.frames[token.index]
            token.next = next_frame.duration + self._last_time
            self._animation_map[token.gid] = next_frame.image
            heappush(self._animation_queue, token)

        # TODO: don't redraw
        if needs_redraw:
            self.redraw_tiles()

    def _new_buffer(self, size):
        w, h = size
        fmt = sdl.PIXELFORMAT_RGBA8888
        texture = sdl.createTexture(self.ctx.renderer, fmt, sdl.TEXTUREACCESS_TARGET, w, h)
        return texture

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        self._buffer = self._new_buffer(buffer_size)
        size = sdl.queryTexture(self._buffer)[3:]
        self._buffer_rect.w = size[0]
        self._buffer_rect.h = size[1]

    def _flush_tile_queue(self, destination=None):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        renderer = self.ctx.renderer
        rcx = sdl.renderCopyEx

        map_get = self._animation_map.get

        dst_rect = sdl.Rect()
        dst_rect.w = tw
        dst_rect.h = th

        self._clear_buffer(self._buffer)  # DEBUG

        with render_target_context(self.ctx.renderer, self._buffer):
            for x, y, l, tile, gid in self._tile_queue:
                texture, src_rect, angle, flip = map_get(gid, tile)
                dst_rect.x = x * tw - ltw
                dst_rect.y = y * th - tth
                rcx(renderer, texture, src_rect, dst_rect, angle, None, flip)
