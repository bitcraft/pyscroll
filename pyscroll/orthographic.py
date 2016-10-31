from __future__ import division
from __future__ import print_function

import logging
import time
from heapq import heappop, heappush
from itertools import groupby
from operator import gt, itemgetter

import pygame

from pyscroll import surface_clipping_context
from pyscroll.base import RendererBase

logger = logging.getLogger('orthographic')


class BufferedRenderer(RendererBase):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in pyscroll.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """
    _alpha_clear_color = 0, 0, 0, 0

    def __init__(self, data, size, clamp_camera=True, colorkey=None, alpha=False,
                 time_source=time.time, scaling_function=pygame.transform.scale):

        self.scaling_function = scaling_function  # what function to use when scaling the zoom buffer
        super(BufferedRenderer, self).__init__(data, size, clamp_camera, colorkey, alpha, time_source)

    def change_view(self, dx, dy):
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
            self._render_map(surface, rect, surfaces)
        else:
            self._render_map(self._zoom_buffer, self._zoom_buffer.get_rect(), surfaces)
            self.scaling_function(self._zoom_buffer, rect.size, surface)

    def clear_buffer(self, target, color):
        target.fill(color)

    def _render_map(self, surface, rect, surfaces):
        """ Render the map and optional surfaces to destination surface

        :param surface: pygame surface to draw to
        :param rect: area to draw to
        :param surfaces: optional sequence of surfaces to interlace between tiles
        """
        if self._animation_queue:
            self._process_animation_queue()

        if not self.anchored_view:
            surface.fill(0)

        offset = -self._x_offset + rect.left, -self._y_offset + rect.top

        with surface_clipping_context(surface, rect):
            surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                self._draw_surfaces(surface, surfaces_offset, surfaces)

    def _draw_surfaces(self, surface, offset, surfaces):
        """ Draw surfaces onto buffer, then redraw tiles that cover them

        :param surface: destination
        :param offset: offset to compensate for buffer alignment
        :param surfaces: sequence of surfaces to blit
        """
        surface_blit = surface.blit
        ox, oy = offset
        left, top = self._tile_view.topleft
        hit = self._layer_quadtree.hit
        get_tile = self.data.get_tile_image
        tile_layers = tuple(self.data.visible_tile_layers)
        dirty = list()
        dirty_append = dirty.append

        # TODO: check to avoid sorting overhead
        layer_getter = itemgetter(2)
        surfaces.sort(key=layer_getter)

        for layer, group in groupby(surfaces, layer_getter):
            del dirty[:]

            for i in group:
                try:
                    flags = i[3]
                except IndexError:
                    dirty_append(surface_blit(i[0], i[1]))
                else:
                    dirty_append(surface_blit(i[0], i[1], None, flags))

            # TODO: make set of covered tiles, in the case where a cluster
            # of sprite surfaces causes excessive over tile overdrawing
            for dirty_rect in dirty:
                for r in hit(dirty_rect.move(ox, oy)):
                    x, y, tw, th = r
                    for l in [i for i in tile_layers if gt(i, layer)]:
                        tile = get_tile((x // tw + left, y // th + top, l))
                        if tile:
                            surface_blit(tile, (x - ox, y - oy))

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
    def new_buffer(size, **flags):
        if flags.get('alpha'):
            return pygame.Surface(size, flags=pygame.SRCALPHA)
        elif flags.get('colorkey'):
            surface = pygame.Surface(size, flags=pygame.RLEACCEL)
            surface.set_colorkey(flags['colorkey'])
            return surface
        else:
            return pygame.Surface(size)

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        requires_zoom_buffer = not view_size == buffer_size
        self._zoom_buffer = None

        if self._clear_color == self._alpha_clear_color:
            if requires_zoom_buffer:
                self._zoom_buffer = self.new_buffer(view_size, alpha=True)
            self._buffer = self.new_buffer(buffer_size, alpha=True)
            self.data.convert_surfaces(self._buffer, True)

        elif self._clear_color:
            if requires_zoom_buffer:
                self._zoom_buffer = self.new_buffer(colorkey=self._clear_color)
            self._buffer = self.new_buffer(buffer_size, colorkey=self._clear_color)
            self._buffer.fill(self._clear_color)

        else:
            if requires_zoom_buffer:
                self._zoom_buffer = self.new_buffer(view_size)
            self._buffer = self.new_buffer(buffer_size)

    def _flush_tile_queue(self, surface):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        surface_blit = surface.blit

        for x, y, l, tile, gid in self._tile_queue:
            self._animation_tiles[gid].add((x, y, l))
            surface_blit(tile, (x * tw - ltw, y * th - tth))
