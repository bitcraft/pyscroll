from __future__ import division, print_function

import logging
import math
import time
from functools import partial
from itertools import chain, groupby, product
from operator import gt, itemgetter

import pygame
from pygame import Rect, Surface

from pyscroll import quadtree, surface_clipping_context

logger = logging.getLogger('orthographic')


class BufferedRenderer(object):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in pyscroll.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    
    NOTE: colorkey and alpha transparency is quite slow
    """
    _alpha_clear_color = 0, 0, 0, 0
    _rgb_clear_color = 0, 0, 0

    def __init__(self, data, size, clamp_camera=True, colorkey=None, alpha=False,
                 time_source=time.time, scaling_function=pygame.transform.scale,
                 tall_sprites=0, **kwargs):

        # default options
        self.data = data                           # reference to data source
        self.clamp_camera = clamp_camera           # if true, cannot scroll past map edge
        self.anchored_view = True                  # if true, map will be fixed to upper left corner
        self.map_rect = None                       # pygame rect of entire map
        self.time_source = time_source             # determines how tile animations are processed
        self.scaling_function = scaling_function   # what function to use when scaling the zoom buffer
        self.tall_sprites = tall_sprites           # correctly render tall sprites

        # Tall Sprites
        # this value, if greater than 0, is the number of pixels from the bottom of
        # tall sprites which is compared against the bottom of a tile on the same
        # lays of the sprite.  In other words, if set, it prevents tiles from being
        # drawn over sprites which are taller than the tile height.  The value that
        # is how far apart the sprites have to be before drawing the tile over.
        # Reasonable values are about 10% of the tile height
        # This feature only works for the first layer over the tall sprite, all
        # other layers will be drawn over the tall sprite.

        # internal private defaults
        if colorkey and alpha:
            print('cannot select both colorkey and alpha.  choose one.')
            raise ValueError
        elif colorkey:
            self._clear_color = colorkey
        elif alpha:
            self._clear_color = self._alpha_clear_color
        else:
            self._clear_color = self._rgb_clear_color

        # private attributes
        self._previous_blit = None    # rect of the previous map blit when map edges are visible
        self._size = None             # size that the camera/viewport is on screen, kinda
        self._redraw_cutoff = None    # size of dirty tile edge that will trigger full redraw
        self._x_offset = None         # offsets are used to scroll map in sub-tile increments
        self._y_offset = None
        self._buffer = None           # complete rendering of tilemap
        self._tile_view = None        # this rect represents each tile on the buffer
        self._half_width = None       # 'half x' attributes are used to reduce division ops.
        self._half_height = None
        self._tile_queue = None       # tiles queued to be draw onto buffer
        self._animation_queue = None  # heap queue of animation token;  schedules tile changes
        self._layer_quadtree = None   # used to draw tiles that overlap optional surfaces
        self._zoom_buffer = None      # used to speed up zoom operations
        self._zoom_level = 1.0        # negative numbers make map smaller, positive: bigger

        # this represents the viewable pixels, aka 'camera'
        self.view_rect = Rect(0, 0, 0, 0)

        self.set_size(size)

    def scroll(self, vector):
        """ scroll the background in pixels

        :param vector: (int, int)
        """
        self.center((vector[0] + self.view_rect.centerx,
                     vector[1] + self.view_rect.centery))

    def center(self, coords):
        """ center the map on a pixel

        float numbers will be rounded.

        :param coords: (number, number)
        """
        x, y = [round(i, 0) for i in coords]
        self.view_rect.center = x, y

        mw, mh = self.data.map_size
        tw, th = self.data.tile_size
        vw, vh = self._tile_view.size

        # TODO: remove check from here; cache it
        # small_map = (self._tile_view.width >= mw) or (self._tile_view.height >= mh)

        # prevent camera from exposing edges of the map
        if self.clamp_camera:
            self.anchored_view = True
            self.view_rect.clamp_ip(self.map_rect)
            x, y = self.view_rect.center

        # calc the new position in tiles and pixel offset
        left, self._x_offset = divmod(x - self._half_width, tw)
        top, self._y_offset = divmod(y - self._half_height, th)

        # test if camera will expose edges of the map
        if not self.clamp_camera:
            # not anchored, so the rendered map is being offset by values larger
            # than the tile size.  this occurs when the edges of the map are inside
            # the screen.  a situation like is shows a background under the map.
            self.anchored_view = True

            if left > mw - vw:
                left = mw - vw
                self._x_offset = x - self._half_width - (mw - vw) * tw
                self.anchored_view = False

            elif left < 0:
                left = 0
                self._x_offset = x - self._half_width
                self.anchored_view = False

            if top > mh - vh:
                top = mh - vh
                self._y_offset = y - self._half_height - (mh - vh) * th
                self.anchored_view = False

            elif top < 0:
                top = 0
                self._y_offset = y - self._half_height
                self.anchored_view = False

        # adjust the view if the view has changed without a redraw
        dx = int(left - self._tile_view.left)
        dy = int(top - self._tile_view.top)
        view_change = max(abs(dx), abs(dy))

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
        self._size = size
        self._initialize_buffers(buffer_size)

    def redraw_tiles(self, surface):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        # TODO/BUG: Redraw animated tiles correctly.  They are getting reset here
        logger.warning('pyscroll buffer redraw')
        if self._clear_color is not None:
            surface.fill(self._clear_color)

        self._tile_queue = self.data.get_tile_images_by_rect(self._tile_view)
        self._flush_tile_queue(surface)

    def get_center_offset(self):
        """ Return x, y pair that will change world coords to screen coords
        :return: int, int
        """
        return (-self.view_rect.centerx + self._half_width,
                -self.view_rect.centery + self._half_height)

    def _render_map(self, surface, rect, surfaces):
        """ Render the map and optional surfaces to destination surface

        :param surface: pygame surface to draw to
        :param rect: area to draw to
        :param surfaces: optional sequence of surfaces to interlace between tiles
        """
        self._tile_queue = self.data.process_animation_queue(self._tile_view)
        if self._tile_queue:
            self._flush_tile_queue(self._buffer)

        # TODO: could maybe optimize to remove just the edges
        # if not self.anchored_view:
        #     surface.fill(self._clear_color, self._previous_blit)
        if not self.anchored_view:
            surface.fill(self._clear_color)

        offset = -self._x_offset + rect.left, -self._y_offset + rect.top

        with surface_clipping_context(surface, rect):
            self._previous_blit = surface.blit(self._buffer, offset)
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
        # sort layers, then the y value
        def sprite_sort(i):
            return i[2], i[1][1] + i[0].get_height()

        surfaces.sort(key=sprite_sort)

        layer_getter = itemgetter(2)
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

                        if self.tall_sprites and l == layer + 1:
                            if y - oy + th <= dirty_rect.bottom - self.tall_sprites:
                                continue

                        tile = get_tile(x // tw + left, y // th + top, l)
                        if tile:
                            surface_blit(tile, (x - ox, y - oy))

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
            if self._clear_color is not None:
                fill(((rect[0] - v.left) * tw,
                      (rect[1] - v.top) * th,
                      rect[2] * tw, rect[3] * th))

        if dx > 0:    # right side
            append((v.right - 1, v.top, dx, v.height))

        elif dx < 0:  # left side
            append((v.left, v.top, -dx, v.height))

        if dy > 0:    # bottom side
            append((v.left, v.bottom - 1, v.width, dy))

        elif dy < 0:  # top side
            append((v.left, v.top, v.width, -dy))

    @staticmethod
    def _calculate_zoom_buffer_size(size, value):
        if value <= 0:
            print('zoom level cannot be zero or less')
            raise ValueError
        value = 1.0 / value
        return [int(round(i * value)) for i in size]

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        requires_zoom_buffer = not view_size == buffer_size
        self._zoom_buffer = None

        if self._clear_color == self._alpha_clear_color:
            if requires_zoom_buffer:
                self._zoom_buffer = Surface(view_size, flags=pygame.SRCALPHA)
            self._buffer = Surface(buffer_size, flags=pygame.SRCALPHA)
            self.data.convert_surfaces(self._buffer, True)
        elif self._clear_color is not self._rgb_clear_color:
            if requires_zoom_buffer:
                self._zoom_buffer = Surface(view_size, flags=pygame.RLEACCEL)
                self._zoom_buffer.set_colorkey(self._clear_color)
            self._buffer = Surface(buffer_size, flags=pygame.RLEACCEL)
            self._buffer.set_colorkey(self._clear_color)
            self._buffer.fill(self._clear_color)
        else:
            if requires_zoom_buffer:
                self._zoom_buffer = Surface(view_size)
            self._buffer = Surface(buffer_size)

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
        self._previous_blit = Rect(self.view_rect)
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
        self._layer_quadtree = quadtree.FastQuadTree(rects, 4)

        self.redraw_tiles(self._buffer)

    def _flush_tile_queue(self, surface):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        surface_blit = surface.blit

        for x, y, l, image in self._tile_queue:
            surface_blit(image, (x * tw - ltw, y * th - tth))
