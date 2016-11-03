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
import math
import time
from collections import defaultdict
from functools import partial
from heapq import heappop, heappush
from itertools import chain, product

from pyscroll.animation import AnimationFrame, AnimationToken
from pyscroll.compat import Rect
from pyscroll.quadtree import FastQuadTree

logger = logging.getLogger('orthographic')


class RendererAB(object):
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
        raise NotImplementedError

    def redraw(self):
        """ Clear all buffers and redraw all the tiles.  Slow!

        :return:
        """
        raise NotImplementedError

    def _change_offset(self, d, y):
        raise NotImplementedError

    def _change_view(self, dx, dy):
        raise NotImplementedError

    @staticmethod
    def _new_buffer(size, **flags):
        raise NotImplementedError

    def _clear_buffer(self, target, color):
        raise NotImplementedError

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        raise NotImplementedError

    def _flush_tile_queue(self, surface):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        raise NotImplementedError

    def _render_map(self, surface, rect, surfaces):
        """ Render the map and optional surfaces to destination surface

        :param surface: pygame surface to draw to
        :param rect: area to draw to
        :param surfaces: optional sequence of surfaces to interlace between tiles
        """
        raise NotImplementedError


class RendererBase(RendererAB):
    """ Base for buffered tile renderers.
    """

    alpha_clear_color = 0, 0, 0, 0

    def __init__(self, data, size, clamp_camera=True, time_source=time.time):

        # default options
        self.data = data  # reference to data source
        self.clamp_camera = clamp_camera  # if true, cannot scroll past map edge
        self.anchored_view = True  # if true, map will be fixed to upper left corner
        self.map_rect = None  # rect of entire map
        self.time_source = time_source  # determines how tile animations are processed

        # private attributes
        self._size = None  # size that the camera/viewport is on screen, kinda
        self._redraw_cutoff = None  # size of dirty tile edge that will trigger full redraw
        self._x_offset = None  # offsets are used to scroll map in sub-tile increments
        self._y_offset = None
        self._buffer = None  # complete rendering of tilemap
        self._buffer_size = None
        self._tile_view = None  # this rect represents each tile on the buffer
        self._half_width = None  # 'half x' attributes are used to reduce division ops.
        self._half_height = None
        self._tile_queue = None  # tiles queued to be draw onto buffer
        self._animation_queue = None  # heap queue of animation token;  schedules tile changes
        self._last_time = None  # used for scheduling animations
        self._layer_quadtree = None  # used to draw tiles that overlap optional surfaces
        self._zoom_level = 1.0  # negative numbers make map smaller, positive: bigger

        # used to speed up animated tile redraws by keeping track of animated tiles
        # so they can be updated individually
        self._animation_tiles = defaultdict(set)

        # this represents the viewable pixels, aka 'camera'
        self.view_rect = Rect(0, 0, 0, 0)

        self.reload_animations()
        self.set_size(size)

    def redraw_tiles(self, destination=None):
        logger.warn('pyscroll buffer redraw')
        if self._clear_color:
            self._clear_buffer(self._buffer, self._clear_color)

        self._tile_queue = self.data.get_tile_images_by_rect(self._tile_view)
        self._flush_tile_queue(destination)

    def scroll(self, v):
        """ scroll the background in pixels

        :param v: (int, int)
        """
        self.center((v[0] + self.view_rect.centerx, v[1] + self.view_rect.centery))

    def center(self, coords):
        """ center the map on a pixel

        float numbers will be rounded.

        :param coords: (number, number)
        """
        x, y = [round(i, 0) for i in coords]
        self.view_rect.center = x, y

        mw, mh = self.data.map_size
        tw, th = self.data.tile_size

        self.anchored_view = ((self._tile_view.width < mw) or
                              (self._tile_view.height < mh))

        if self.anchored_view and self.clamp_camera:
            self.view_rect.clamp_ip(self.map_rect)

        x, y = self.view_rect.center

        if not self.anchored_view:
            # calculate offset and do not scroll the map layer
            # this is used to handle maps smaller than screen
            self._change_offset(x - self._half_width, y - self._half_height)

        else:
            # calc the new position in tiles and offset
            left, ox = divmod(x - self._half_width, tw)
            top, oy = divmod(y - self._half_height, th)
            self._change_offset(ox, oy)

            # get the difference on each axis by tile
            dx = int(left - self._tile_view.left)
            dy = int(top - self._tile_view.top)

            # adjust the view if the view has changed without a redraw
            if dx or dy:
                self._change_view(dx, dy)

    @property
    def zoom(self):
        """ Zoom the map in or out.

        Increase this number to make map appear to come closer to camera.
        Decrease this number to make map appear to move away from camera.

        Default value is 1.0
        This value cannot be negative or 0.0

        :return: float
        """
        return self._zoom_level

    @zoom.setter
    def zoom(self, value):
        buffer_size = self._calculate_zoom_buffer_size(self._size, value)
        self._zoom_level = value
        self._initialize_buffers(buffer_size)

    def set_size(self, size):
        """ Set the size of the map in pixels

        This is an expensive operation, do only when absolutely needed.

        :param size: (width, height) pixel size of camera/view of the group
        """
        buffer_size = self._calculate_zoom_buffer_size(size, self._zoom_level)
        self._size = [int(i) for i in size]
        self._initialize_buffers(buffer_size)

    def get_center_offset(self):
        """ Return x, y pair that will change world coords to screen coords
        :return: int, int
        """
        return (-self.view_rect.centerx + self._half_width,
                -self.view_rect.centery + self._half_height)

    def _queue_edge_tiles(self, dx, dy):
        """ Queue edge tiles and clear edge areas on buffer if needed

        :param dx: Edge along X axis to enqueue
        :param dy: Edge along Y axis to enqueue
        :return: None
        """
        v = self._tile_view
        fill = partial(self._buffer.fill, self._clear_color)
        tw, th = self.data.tile_size
        self._tile_queue = iter([])

        def append(rect):
            self._tile_queue = chain(self._tile_queue, self.data.get_tile_images_by_rect(rect))
            if self._clear_color:
                fill(((rect[0] - v.left) * tw,
                      (rect[1] - v.top) * th,
                      rect[2] * tw, rect[3] * th))

        if dx > 0:  # right side
            append((v.right - 1, v.top, dx, v.height))

        elif dx < 0:  # left side
            append((v.left, v.top, -dx, v.height))

        if dy > 0:  # bottom side
            append((v.left, v.bottom - 1, v.width, dy))

        elif dy < 0:  # top side
            append((v.left, v.top, v.width, -dy))

    def _update_time(self):
        self._last_time = time.time() * 1000

    def reload_animations(self):
        """ Reload animation information
        """
        self._update_time()
        self._animation_queue = list()

        for gid, frame_data in self.data.get_animations():
            frames = list()
            for frame_gid, frame_duration in frame_data:
                image = self.data.get_tile_image_by_gid(frame_gid)
                frames.append(AnimationFrame(image, frame_duration))

            ani = AnimationToken(gid, frames)
            ani.next += self._last_time
            heappush(self._animation_queue, ani)

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

    @staticmethod
    def _calculate_zoom_buffer_size(size, value):
        if value <= 0:
            print('zoom level cannot be zero or less')
            raise ValueError
        value = 1.0 / value
        return [int(round(i * value)) for i in size]

    def _initialize_buffers(self, view_size):
        """ Create the buffers to cache tile drawing

        :param view_size: (int, int): size of the draw area
        :return: None
        """
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size
        buffer_tile_width = int(math.ceil(view_size[0] / tw) + 1)
        buffer_tile_height = int(math.ceil(view_size[1] / th) + 1)
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        self.map_rect = Rect(0, 0, mw * tw, mh * th)
        self.view_rect.size = view_size
        self._tile_view = Rect(0, 0, buffer_tile_width, buffer_tile_height)
        self._redraw_cutoff = 1  # TODO: optimize this value
        self._create_buffers(view_size, buffer_pixel_size)
        self._half_width = view_size[0] // 2
        self._half_height = view_size[1] // 2
        self._x_offset = 0
        self._y_offset = 0

        def make_rect(x, y):
            return Rect((x * tw, y * th), (tw, th))

        rects = [make_rect(*i) for i in product(range(buffer_tile_width),
                                                range(buffer_tile_height))]

        # TODO: figure out what depth -actually- does
        # values <= 8 tend to reduce performance
        self._layer_quadtree = FastQuadTree(rects, 4)

        self.redraw_tiles(self._buffer)
