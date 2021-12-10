from __future__ import annotations

import logging
import math
import time
from itertools import chain, product
from typing import List, TYPE_CHECKING, Callable

import pygame
from pygame import Rect, Surface

from .common import (
    surface_clipping_context,
    RectLike,
    Vector2D,
    Vector2DInt,
)
from .quadtree import FastQuadTree

if TYPE_CHECKING:
    from .data import PyscrollDataAdapter

log = logging.getLogger(__file__)


class BufferedRenderer:
    """
    Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile,
    shape, and animation information.  See the data class api in
    pyscroll.data, or use the built-in pytmx support for loading maps
    created with Tiled.

    """
    _rgba_clear_color = 0, 0, 0, 0
    _rgb_clear_color = 0, 0, 0

    def __init__(
        self,
        data: PyscrollDataAdapter,
        size: Vector2DInt,
        clamp_camera: bool=True,
        colorkey=None,
        alpha: bool=False,
        time_source: Callable=time.time,
        scaling_function: Callable=pygame.transform.scale,
        tall_sprites: int=0,
        sprite_damage_height: int=0,
        zoom: float=1.0,
    ):
        """
        Constructor

        NOTE: `colorkey` and `alpha` are special purpose and not related
              to the transparency values for tiles. In 99.99% of cases,
              you do not need to set them

        Args:
            data: reference to data source
            size: if true, cannot scroll past map edge
            clamp_camera: determines how tile animations are processed
            colorkey: used for enabling transparent layers.  not needed usually
            alpha: used for enabling transparent layers.  not needed usually
            time_source: used to get time when cycling tile animations
            scaling_function: what function to use when scaling the zoom buffer
            tall_sprites: deprecated.  will be removed in future
            sprite_damage_height: modify when sprites are drawn over tiles on another layer
            zoom: negative numbers make map smaller, positive numbers zoom in
        """

        # default options
        self.data = data
        self.clamp_camera = clamp_camera
        self.time_source = time_source
        self.scaling_function = scaling_function
        self.tall_sprites = tall_sprites
        self.sprite_damage_height = sprite_damage_height
        self.map_rect = None

        # internal private defaults
        if colorkey and alpha:
            log.error('cannot select both colorkey and alpha')
            raise ValueError
        elif colorkey:
            self._clear_color = colorkey
        elif alpha:
            self._clear_color = self._rgba_clear_color
        else:
            self._clear_color = None

        # private attributes
        self._anchored_view = True    # if true, map is fixed to upper left corner
        self._previous_blit = None    # rect of the previous map blit when map edges are visible
        self._size = None             # actual pixel size of the view, as it occupies the screen
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
        self._zoom_level = zoom
        self._real_ratio_x = 1.0      # zooming slightly changes aspect ratio; this compensates
        self._real_ratio_y = 1.0      # zooming slightly changes aspect ratio; this compensates
        self.view_rect = Rect(0, 0, 0, 0)  # this represents the viewable map pixels

        self.set_size(size)

        if self.tall_sprites != 0:
            log.warning('using tall_sprites feature is not supported')

    def reload(self):
        """
        Reload tiles and animations for the data source.

        """
        self.data.reload_data()
        self.data.reload_animations()
        self.redraw_tiles(self._buffer)

    def scroll(self, vector: Vector2DInt):
        """
        Scroll the background in pixels.

        Args:
            vector: x, y

        """
        self.center((vector[0] + self.view_rect.centerx,
                     vector[1] + self.view_rect.centery))

    def center(self, coords: Vector2D):
        """
        Center the map on a pixel.

        Float numbers will be rounded.

        Args:
            coords: x, y

        """
        x, y = round(coords[0]), round(coords[1])
        self.view_rect.center = x, y

        mw, mh = self.data.map_size
        tw, th = self.data.tile_size
        vw, vh = self._tile_view.size

        # prevent camera from exposing edges of the map
        if self.clamp_camera:
            self._anchored_view = True
            self.view_rect.clamp_ip(self.map_rect)
            x, y = self.view_rect.center

        # calc the new position in tiles and pixel offset
        left, self._x_offset = divmod(x - self._half_width, tw)
        top, self._y_offset = divmod(y - self._half_height, th)
        right = left + vw
        bottom = top + vh

        if not self.clamp_camera:
            # not anchored, so the rendered map is being offset by
            # values larger than the tile size.  this occurs when the
            # edges of the map are inside the screen.  a situation like
            # is shows a background under the map.
            self._anchored_view = True
            dx = int(left - self._tile_view.left)
            dy = int(top - self._tile_view.top)

            if mw < vw or left < 0:
                left = 0
                self._x_offset = x - self._half_width
                self._anchored_view = False

            elif right > mw:
                left = mw - vw
                self._x_offset += dx * tw
                self._anchored_view = False

            if mh < vh or top < 0:
                top = 0
                self._y_offset = y - self._half_height
                self._anchored_view = False

            elif bottom > mh:
                top = mh - vh
                self._y_offset += dy * th
                self._anchored_view = False

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
            log.debug('scrolling too quickly.  redraw forced')
            self._tile_view.move_ip(dx, dy)
            self.redraw_tiles(self._buffer)

    def draw(
        self,
        surface: Surface,
        rect: RectLike,
        surfaces:
        List[Surface]=None
    ):
        """
        Draw the map onto a surface.

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

        Args:
            surface: surface to draw to
            rect: area to draw to
            surfaces: optional sequence of surfaces to interlace between tiles
            rect: area that was drawn over

        """
        if self._zoom_level == 1.0:
            self._render_map(surface, rect, surfaces)
        else:
            self._render_map(
                self._zoom_buffer,
                self._zoom_buffer.get_rect(),
                surfaces
            )
            self.scaling_function(self._zoom_buffer, rect.size, surface)
        return self._previous_blit.copy()

    @property
    def zoom(self) -> float:
        """
        Zoom the map in or out.

        Increase this number to make map appear to come closer to camera.
        Decrease this number to make map appear to move away from camera.

        Default value is 1.0
        This value cannot be negative or 0.0

        """
        return self._zoom_level

    @zoom.setter
    def zoom(self, value: float):
        zoom_buffer_size = self._calculate_zoom_buffer_size(self._size, value)
        self._zoom_level = value
        self._initialize_buffers(zoom_buffer_size)

        zoom_buffer_size = self._zoom_buffer.get_size()
        self._real_ratio_x = float(self._size[0]) / zoom_buffer_size[0]
        self._real_ratio_y = float(self._size[1]) / zoom_buffer_size[1]

    def set_size(self, size: Vector2DInt):
        """
        Set the size of the map in pixels.

        This is an expensive operation, do only when absolutely needed.

        Args:
            size: pixel size of camera/view of the group

        """
        buffer_size = self._calculate_zoom_buffer_size(size, self._zoom_level)
        self._size = size
        self._initialize_buffers(buffer_size)

    def redraw_tiles(self, surface: Surface):
        """
        Redraw the visible portion of the buffer -- it is slow.

        Args:
            surface: where to draw

        """
        # TODO/BUG: Animated tiles are getting reset here
        log.debug('pyscroll buffer redraw')
        self._clear_surface(self._buffer)
        self._tile_queue = self.data.get_tile_images_by_rect(self._tile_view)
        self._flush_tile_queue(surface)

    def get_center_offset(self) -> Vector2DInt:
        """
        Return x, y pair that will change world coords to screen coords.

        """
        return (-self.view_rect.centerx + self._half_width,
                -self.view_rect.centery + self._half_height)

    def translate_point(self, point: Vector2D) -> Vector2DInt:
        """
        Translate world coordinates and return screen coordinates.

        Args:
            point: point to translate

        """
        mx, my = self.get_center_offset()
        if self._zoom_level == 1.0:
            return int(point[0] + mx), int(point[1] + my)
        else:
            return (
                int(round((point[0] + mx)) * self._real_ratio_x),
                int(round((point[1] + my) * self._real_ratio_y))
            )

    def translate_rect(self, rect: RectLike) -> Rect:
        """
        Translate rect position and size to screen coordinates.

        Args:
            rect: rect to translate

        """
        mx, my = self.get_center_offset()
        rx = self._real_ratio_x
        ry = self._real_ratio_y
        x, y, w, h = rect
        if self._zoom_level == 1.0:
            return Rect(x + mx, y + my, w, h)
        else:
            return Rect(round((x + mx) * rx), round((y + my) * ry), round(w * rx), round(h * ry))

    def translate_points(self, points: List[Vector2D]) -> List[Vector2DInt]:
        """
        Translate coordinates and return screen coordinates.

        Args:
            points: points to translate

        """
        retval = list()
        append = retval.append
        sx, sy = self.get_center_offset()
        if self._zoom_level == 1.0:
            for c in points:
                append((c[0] + sx, c[1] + sy))
        else:
            rx = self._real_ratio_x
            ry = self._real_ratio_y
            for c in points:
                append((int(round((c[0] + sx) * rx)), int(round((c[1] + sy) * ry))))
        return retval

    def translate_rects(self, rects: List[Rect]) -> List[Rect]:
        """
        Translate rect position and size to screen coordinates.

        Args:
            rects: rects to translate

        """
        retval = list()
        append = retval.append
        sx, sy = self.get_center_offset()
        if self._zoom_level == 1.0:
            for r in rects:
                x, y, w, h = r
                append(Rect(x + sx, y + sy, w, h))
        else:
            rx = self._real_ratio_x
            ry = self._real_ratio_y
            for r in rects:
                x, y, w, h = r
                append(
                    Rect(
                        round((x + sx) * rx),
                        round((y + sy) * ry),
                        round(w * rx),
                        round(h * ry)
                    )
                )
        return retval

    def _render_map(
        self,
        surface: Surface,
        rect: RectLike,
        surfaces: List[Surface]
    ):
        """
        Render the map and optional surfaces to destination surface.

        Args:
            surface: pygame surface to draw to
            rect: area to draw to
            surfaces: optional sequence of surfaces to interlace between tiles

        """
        self._tile_queue = self.data.process_animation_queue(self._tile_view)
        self._tile_queue and self._flush_tile_queue(self._buffer)

        # TODO: could maybe optimize to remove just the edges, ideally by drawing lines
        if not self._anchored_view:
            self._clear_surface(surface, self._previous_blit)

        offset = -self._x_offset + rect.left, -self._y_offset + rect.top

        with surface_clipping_context(surface, rect):
            self._previous_blit = surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                self._draw_surfaces(surface, surfaces_offset, surfaces)

    def _clear_surface(self, surface: Surface, area: RectLike = None):
        """
        Clear the surface using the right clear color.

        Args:
            surface: surface to clear
            area: area to clear

        """
        clear_color = self._rgb_clear_color if self._clear_color is None else self._clear_color
        surface.fill(clear_color, area)

    def _draw_surfaces(self, surface: Surface, offset: Vector2DInt, surfaces):
        """
        Draw surfaces while correcting overlapping tile layers.

        Args:
            surface: destination
            offset: offset to compensate for buffer alignment
            surfaces: sequence of surfaces to blit

        """
        ox, oy = offset
        left, top = self._tile_view.topleft
        hit = self._layer_quadtree.hit
        get_tile = self.data.get_tile_image
        tile_layers = tuple(sorted(self.data.visible_tile_layers))
        top_layer = tile_layers[-1]
        blit_list = list()
        sprite_damage = set()
        order = 0

        # get tile that sprites overlap
        for i in surfaces:
            s, r, l = i[:3]

            # sprite must not be over the top layer for damage to matter
            if l <= top_layer:
                damage_rect = Rect(i[1])
                damage_rect.move_ip(ox, oy)
                # tall sprites only damage a portion of the bottom of their sprite
                if self.tall_sprites:
                    damage_rect = Rect(
                        damage_rect.x,
                        damage_rect.y + (damage_rect.height - self.tall_sprites),
                        damage_rect.width,
                        self.tall_sprites
                    )
                for hit_rect in hit(damage_rect):
                    sprite_damage.add((l, hit_rect))

            # add surface to draw list
            try:
                blend = i[3]
            except IndexError:
                blend = None
            x, y, w, h = r
            blit_op = l, 1, x, y, order, s, blend
            blit_list.append(blit_op)
            order += 1

        # TODO: heightmap to avoid checking tiles in each cell
        # from bottom to top, clear screen and add tiles into the draw
        # list.  while getting tiles for the damage, compare the damaged
        # layer to the highest tile.  if the highest tile is greater or
        # equal to the damaged layer, then add the entire column of
        # tiles to the blit_list.  if not, then discard the column and
        # do not update the screen when the damage was done.
        column = list()
        is_over = False
        for dl, damage_rect in sprite_damage:
            x, y, w, h = damage_rect
            tx = x // w + left
            ty = y // h + top
            # TODO: heightmap
            for l in tile_layers:
                tile = get_tile(tx, ty, l)
                if tile:
                    sx = x - ox
                    sy = y - oy
                    if dl <= l:
                        is_over = True
                    blit_op = l, 0, sx, sy, order, tile, None
                    column.append(blit_op)
                    order += 1
            if is_over:
                blit_list.extend(column)
            column.clear()
            is_over = False

        # finally sort and do the thing
        blit_list.sort()
        draw_list2 = list()
        for l, priority, x, y, order, s, blend in blit_list:
            if blend is not None:
                blit_op = s, (x, y), None, blend
            else:
                blit_op = s, (x, y)
            draw_list2.append(blit_op)
        surface.blits(draw_list2, doreturn=False)

    def _queue_edge_tiles(self, dx: int, dy: int):
        """
        Queue edge tiles and clear edge areas on buffer if needed.

        Args:
            dx: Edge along X axis to enqueue
            dy: Edge along Y axis to enqueue

        """
        v = self._tile_view
        tw, th = self.data.tile_size
        self._tile_queue = iter([])

        def append(rect):
            self._tile_queue = chain(self._tile_queue, self.data.get_tile_images_by_rect(rect))
            # TODO: optimize so fill is only used when map is smaller than buffer
            self._clear_surface(self._buffer, ((rect[0] - v.left) * tw, (rect[1] - v.top) * th,
                                               rect[2] * tw, rect[3] * th))

        if dx > 0:  # right side
            append((v.right - 1, v.top, dx, v.height))

        elif dx < 0:  # left side
            append((v.left, v.top, -dx, v.height))

        if dy > 0:  # bottom side
            append((v.left, v.bottom - 1, v.width, dy))

        elif dy < 0:  # top side
            append((v.left, v.top, v.width, -dy))

    @staticmethod
    def _calculate_zoom_buffer_size(size: Vector2DInt, value: float):
        if value <= 0:
            log.error('zoom level cannot be zero or less')
            raise ValueError
        value = 1.0 / value
        return int(size[0] * value), int(size[1] * value)

    def _create_buffers(
        self,
        view_size: Vector2DInt,
        buffer_size: Vector2DInt
    ):
        """
        Create the buffers, taking in account pixel alpha or colorkey.

        Args:
            view_size: pixel size of the view
            buffer_size: pixel size of the buffer

        """
        requires_zoom_buffer = not view_size == buffer_size
        self._zoom_buffer = None

        if self._clear_color is None:
            if requires_zoom_buffer:
                self._zoom_buffer = Surface(view_size)
            self._buffer = Surface(buffer_size)
        elif self._clear_color == self._rgba_clear_color:
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

    def _initialize_buffers(self, view_size: Vector2DInt):
        """
        Create the buffers to cache tile drawing.

        Args:
            view_size: size of the draw area

        """

        def make_rect(x, y):
            return Rect((x * tw, y * th), (tw, th))

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

        rects = [make_rect(*i) for i in product(range(buffer_tile_width),
                                                range(buffer_tile_height))]

        # TODO: figure out what depth -actually- does
        # values <= 8 tend to reduce performance
        self._layer_quadtree = FastQuadTree(rects, 4)

        self.redraw_tiles(self._buffer)

    def _flush_tile_queue(self, surface: Surface):
        """
        Blit the queued tiles and block until the tile queue is empty.

        Args:
            surface: surface to draw onto

        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th

        self.data.prepare_tiles(self._tile_view)

        blit_list = [(image, (x * tw - ltw, y * th - tth)) for x, y, l, image in self._tile_queue]
        surface.blits(blit_list, doreturn=False)
