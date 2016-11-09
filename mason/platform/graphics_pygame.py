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
from math import ceil

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
        self._x_offset = None  # offsets are used to scroll map in sub-tile increments
        self._y_offset = None
        self._zoom_buffer = None  # used to speed up zoom operations

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

    def _change_offset(self, x, y):
        self._x_offset = x
        self._y_offset = y

    def _change_view(self, dx, dy):
        view_change = max(abs(dx), abs(dy))
        tw, th = self.data.tile_size

        if view_change and (view_change <= self._redraw_cutoff):
            self._buffer.scroll(-dx * tw, -dy * th)
            self._tile_view.move_ip(dx, dy)
            self._queue_edge_tiles(dx, dy)
            self._flush_tile_queue(self._buffer)

        elif view_change > self._redraw_cutoff:
            logger.info('scrolling too quickly.  redraw forced')
            self._tile_view.move_ip(dx, dy)
            self.redraw_tiles(self._buffer)

    def draw(self, surface, rect, surfaces=None):
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
        :param surfaces: optional sequence of surfaces to interlace between tiles
        """
        if self._zoom_level == 1.0:
            self._draw_map(surface, rect, surfaces)
        else:
            self._draw_map(self._zoom_buffer, self._zoom_buffer.get_rect(), surfaces)
            self.scaling_function(self._zoom_buffer, rect.size, surface)

    def _clear_buffer(self, target, color):
        target.fill(color)

    def _draw_map(self, surface, rect, surfaces):
        """ Render the map and optional surfaces to destination surface

        :param surface: pygame surface to draw to
        :param rect: area to draw to
        :param surfaces: optional sequence of surfaces to interlace between tiles
        """
        if not self.anchored_view:
            surface.fill(0)

        offset = -self._x_offset + rect.left, -self._y_offset + rect.top

        with surface_clipping_context(surface, rect):
            surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                self._draw_surfaces(surface, surfaces_offset, surfaces)

    def _draw_surfaces(self, destination, offset, surfaces):
        """ Draw surfaces onto buffer, then redraw tiles that cover them

        :param destination: destination
        :param offset: offset to compensate for buffer alignment
        :param surfaces: sequence of surfaces to blit
        """
        destination_blit = destination.blit
        ox, oy = offset
        left, top = self._tile_view.topleft
        get_tiles = self.data.get_tile_images_by_rect
        tw, th = self.data.tile_size
        dirty = list()
        dirty_append = dirty.append

        out_rect = None

        for sprite in surfaces:
            # tokenize the sprite to blit
            sprite_surface, sprite_rect, sprite_layer = sprite
            token = sprite_layer, sprite_rect.topleft, sprite_surface, 0
            dirty_append(token)

            # create rect that contains all the dirty tiles
            damage = sprite_rect.move(ox, oy)

            # convert screen coords to tile coords
            # truncate/round down the left/top edge
            _left = damage.left // tw
            _top = damage.top // th

            # round up the right/bottom edges

            _right = ceil(damage.right / float(tw))
            _bottom = ceil(damage.bottom / float(th))

            _width = _right - _left
            _height = _bottom - _top

            damage = pygame.Rect(_left, _top, _width, _height)
            out_rect = pygame.Rect(*[i * 32 for i in damage]).move(-ox, -oy)

            # adjust for the view
            damage.left += left
            damage.top += top

            # get all the covered tiles, in render order
            # tokenize each covered tile
            for tile in get_tiles(damage):
                x, y, tile_layer, surface, gid = tile

                if sprite_layer < tile_layer:

                    # adjust for view
                    x -= left
                    y -= top

                    # convert tile coords to screen coords
                    token = tile_layer, (x * tw - ox, y * th - oy), surface, gid
                    dirty_append(token)

        # sort tiles and surfaces for best rendering
        dirty.sort()

        debug_draws = list()
        for layer, position, surface, gid in dirty:
            dirty_rect = destination_blit(surface, position)
            debug_draws.append(dirty_rect)

        debug = 1
        if debug:
            for dirty_rect in debug_draws:
                pygame.draw.rect(destination, (255, 0, 255), dirty_rect, 2)

            pygame.draw.rect(destination, (255, 255, 0), out_rect, 2)

    def _process_animation_queue(self):
        self._update_time()
        self._tile_queue = list()
        tile_layers = tuple(self.data.visible_tile_layers)

        # test if the next scheduled tile change is ready
        while self._animation_queue[0].next <= self._last_time:
            token = heappop(self._animation_queue)

            # advance the animation frame index, looping by default
            if token.index == len(token.frames) - 1:
                token.index = 0
            else:
                token.index += 1

            next_frame = token.frames[token.index]
            token.next = next_frame.duration + self._last_time
            heappush(self._animation_queue, token)

            # go through the animated tile map:
            #   * queue tiles that need to be changed
            #   * remove map entries that do not collide with screen

            needs_clear = False
            for x, y, l in self._animation_tiles[token.gid]:

                # if this tile is on the buffer (checked by using the tile view)
                if self._tile_view.collidepoint(x, y):

                    # redraw the entire column of tiles
                    for layer in tile_layers:
                        if layer == l:
                            self._tile_queue.append((x, y, layer, next_frame.image, token.gid))
                        else:
                            image = self.data.get_tile_image((x, y, layer))
                            if image:
                                self._tile_queue.append((x, y, layer, image, None))
                else:
                    needs_clear = True

            # this will delete the set of tile locations that are checked for
            # animated tiles.  when the tile queue is flushed, any tiles in the
            # queue will be added again.  i choose to remove the set, rather
            # than removing the item in the set to reclaim memory over time...
            # though i could implement it by removing entries.  idk  -lt
            if needs_clear:
                del self._animation_tiles[token.gid]

        if self._tile_queue:
            self._flush_tile_queue(self._buffer)

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
        self.data.convert_surfaces(self._buffer, True)

    def _flush_tile_queue(self, surface):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        surface_blit = surface.blit
        ani_tiles = self._animation_tiles

        for x, y, l, tile, gid in self._tile_queue:
            ani_tiles[gid].add((x, y, l))
            surface_blit(tile, (x * tw - ltw, y * th - tth))
