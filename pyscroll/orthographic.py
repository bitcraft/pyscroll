from __future__ import division
from __future__ import print_function

import logging
import math
import time
from functools import partial
from heapq import heappush, heappop
from itertools import product, chain
from collections import defaultdict
import pygame
from pygame import Surface, Rect
from pyscroll import surface_clipping_context, quadtree
from pyscroll.animation import AnimationFrame, AnimationToken

logger = logging.getLogger('orthographic')


class BufferedRenderer(object):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in pyscroll.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """
    _alpha_clear_color = 0, 0, 0, 0

    def __init__(self, data, size, clamp_camera=True, colorkey=None, alpha=False,
                 time_source=time.time, scaling_function=pygame.transform.scale):

        # default options
        self.data = data                           # reference to data source
        self.clamp_camera = clamp_camera           # if true, cannot scroll past map edge
        self.anchored_view = True                  # if true, map will be fixed to upper left corner
        self.map_rect = None                       # pygame rect of entire map
        self.time_source = time_source             # determines how tile animations are processed
        self.scaling_function = scaling_function   # what function to use when scaling the zoom buffer
        self.default_shape_texture_gid = 1         # [experimental] texture to draw shapes with
        self.default_shape_color = 0, 255, 0       # [experimental] color to fill polygons with

        # internal private defaults
        if colorkey and alpha:
            print('cannot select both colorkey and alpha.  choose one.')
            raise ValueError
        elif colorkey:
            self._clear_color = colorkey
        elif alpha:
            self._clear_color = self._alpha_clear_color
        else:
            self._clear_color = None

        # private attributes
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
        self._animation_map = None    # map of GID to other GIDs in an animation
        self._last_time = None        # used for scheduling animations
        self._layer_quadtree = None   # used to draw tiles that overlap optional surfaces
        self._zoom_buffer = None      # used to speed up zoom operations
        self._zoom_level = 1.0        # negative numbers make map smaller, positive: bigger

        self._scroll = None
        self._redraw = None

        # used to speed up animated tile redraws by keeping track of animated tiles
        # so they can be updated individually
        self._animation_tiles = defaultdict(set)

        # this represents the viewable pixels, aka 'camera'
        self.view_rect = Rect(0, 0, 0, 0)

        self.reload_animations()
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
        ox, oy = self.view_rect.center
        x, y = [round(i, 0) for i in coords]
        self.view_rect.center = x, y

        mw, mh = self.data.map_size
        tw, th = self.data.tile_size

        self.anchored_view = ((self._tile_view.width < mw) or
                              (self._tile_view.height < mh))

        if self.anchored_view and self.clamp_camera:
            self.view_rect.clamp_ip(self.map_rect)

        x, y = self.view_rect.center

        dpx = ox - x
        dpy = oy - y

        if not self.anchored_view:
            # calculate offset and do not scroll the map layer
            # this is used to handle maps smaller than screen
            self._x_offset = x - self._half_width
            self._y_offset = y - self._half_height

        else:
            # calc the new position in tiles and offset
            left, self._x_offset = divmod(x - self._half_width, tw)
            top, self._y_offset = divmod(y - self._half_height, th)

            # adjust the view if the view has changed without a redraw
            dx = int(left - self._tile_view.left)
            dy = int(top - self._tile_view.top)
            view_change = max(abs(dx), abs(dy))

            if view_change and (view_change <= self._redraw_cutoff):
                self._redraw = True
                # self._buffer.scroll(-dx * tw, -dy * th)
                self._tile_view.move_ip(dx, dy)
                # self._queue_edge_tiles(dx, dy)
                # self._flush_tile_queue()

            # elif view_change > self._redraw_cutoff:
            #     print("redraw")
            #     logger.info('scrolling too quickly.  redraw forced')
            #     self._tile_view.move_ip(dx, dy)
            #     self.redraw_tiles()

            elif dpx or dpy:
                print(dpx, dpy)
                self._scroll = int(dpx), int(dpy)

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

    def redraw_tiles(self):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        if self._clear_color:
            self._buffer.fill(self._clear_color)

        self._tile_queue = self.data.get_tile_images_by_rect(self._tile_view)
        self._flush_tile_queue()

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
        if self._animation_queue:
            self._process_animation_queue()

        if not self.anchored_view:
            surface.fill(0)

        offset = -self._x_offset + rect.left, -self._y_offset + rect.top

        if self._redraw:
            surface.blit(self._buffer, (0, 0))
            self._redraw = None

        if self._scroll:
            surface.scroll(*self._scroll)
            # self._queue_edge_tiles(1, 0)
            # self._flush_tile_queue()
            self._scroll = None

        with surface_clipping_context(surface, rect):
            # surface.blit(self._buffer, offset)
            if surfaces:
                surfaces_offset = -offset[0], -offset[1]
                dirty = self._draw_surfaces(surface, surfaces)
                # self._repair_damage(surface, dirty, surfaces_offset)

    def _draw_surfaces(self, surface, surfaces):
        """ Draw surfaces onto the screen, yield dirty areas

        :type surface: pygame.Surface
        :type surfaces: list
        :rtype: generator
        """
        surface_blit = surface.blit
        for i in surfaces:
            try:
                flags = i[3]
            except IndexError:
                yield surface_blit(i[0], i[1]), i[2] + 1
            else:
                yield surface_blit(i[0], i[1], None, flags), i[2] + 1

    def _repair_damage(self, surface, dirty, offset):
        """ Redraw tiles that cover dirty areas

        :type surface: pygame.Surface
        :type dirty: list
        :param offset: offset to compensate for buffer alignment
        """
        # offset the dirty areas to compensate for the scroll-blit offset
        self._redraw_cells(surface, dirty, offset)

    def _repair_damage_limit_overdraw(self, dirty, offset):
        """ Collapse cells to just the lowest layer.  Useful to limit overdraw.

        This method does more book keeping to limit overdraw.  May be
        quicker in some situations.  Seems slower in general use, however.

        :type dirty: list
        """
        ox, oy = offset
        hit = self._layer_quadtree.hit

        # populate the dict with unique cells, each with lowest layer to redraw from
        cover_dict = dict()
        for rect, layer in dirty:
            for r in hit(rect.move(ox, oy)):
                cell = tuple(r)
                try:
                    lowest = cover_dict[cell]
                except KeyError:
                    cover_dict[cell] = layer
                else:
                    if layer < lowest:
                        cover_dict[cell] = layer

        return cover_dict.items()

    def _redraw_cells(self, surface, dirty, offset):
        """ Given redraw areas.  Used for repairing damage to buffer/screen.

        :return:
        """
        ox, oy = offset
        left, top = self._tile_view.topleft
        surface_blit = surface.blit
        get_tile = self.data.get_tile_image
        hit = self._layer_quadtree.hit
        tile_layers = len(list(self.data.visible_tile_layers))

        for rect, layer in dirty:
            for cell in hit(rect.move(ox, oy)):
                x, y, tw, th = cell
                tx, ty = x // tw + left, y // th + top
                for l in range(layer, tile_layers):
                    tile = get_tile((tx, ty, l))
                    if tile:
                        surface_blit(tile, (x - ox, y - oy))

    def _draw_objects(self):
        """ Totally unoptimized drawing of objects to the map [probably broken]
        """
        tw, th = self.data.tile_size
        buff = self._buffer
        blit = buff.blit
        map_gid = self.data.tmx.map_gid
        default_color = self.default_shape_color
        get_image_by_gid = self.data.get_tile_image_by_gid
        _draw_textured_poly = pygame.gfxdraw.textured_polygon
        _draw_poly = pygame.draw.polygon
        _draw_lines = pygame.draw.lines

        ox = self._tile_view.left * tw
        oy = self._tile_view.top * th

        def draw_textured_poly(texture, points):
            try:
                _draw_textured_poly(buff, points, texture, tw, th)
            except pygame.error:
                pass

        def draw_poly(color, points, width=0):
            _draw_poly(buff, color, points, width)

        def draw_lines(color, points, width=2):
            _draw_lines(buff, color, False, points, width)

        def to_buffer(pt):
            return pt[0] - ox, pt[1] - oy

        for layer in self.data.visible_object_layers:
            for o in (o for o in layer if o.visible):
                texture_gid = getattr(o, "texture", None)
                color = getattr(o, "color", default_color)

                # BUG: this is not going to be completely accurate, because it
                # does not take into account times where texture is flipped.
                if texture_gid:
                    texture_gid = map_gid(texture_gid)[0][0]
                    texture = get_image_by_gid(int(texture_gid))

                if hasattr(o, 'points'):
                    points = [to_buffer(i) for i in o.points]
                    if o.closed:
                        if texture_gid:
                            draw_textured_poly(texture, points)
                        else:
                            draw_poly(color, points)
                    else:
                        draw_lines(color, points)

                elif o.gid:
                    tile = get_image_by_gid(o.gid)
                    if tile:
                        pt = to_buffer((o.x, o.y))
                        blit(tile, pt)

                else:
                    x, y = to_buffer((o.x, o.y))
                    points = ((x, y), (x + o.width, y),
                              (x + o.width, y + o.height), (x, y + o.height))
                    if texture_gid:
                        draw_textured_poly(texture, points)
                    else:
                        draw_poly(color, points)

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

        if dx > 0:    # right side
            append((v.right - 1, v.top, dx, v.height))

        elif dx < 0:  # left side
            append((v.left, v.top, -dx, v.height))

        if dy > 0:    # bottom side
            append((v.left, v.bottom - 1, v.width, dy))

        elif dy < 0:  # top side
            append((v.left, v.top, v.width, -dy))

    def _update_time(self):
        self._last_time = time.time() * 1000

    def reload_animations(self):
        """ Reload animation information
        """
        self._update_time()
        self._animation_map = dict()
        self._animation_queue = list()

        for gid, frame_data in self.data.get_animations():
            frames = list()
            for frame_gid, frame_duration in frame_data:
                image = self.data.get_tile_image_by_gid(frame_gid)
                frames.append(AnimationFrame(image, frame_duration))

            ani = AnimationToken(gid, frames)
            ani.next += self._last_time
            self._animation_map[ani.gid] = ani.frames[ani.index].image
            heappush(self._animation_queue, ani)

    def _process_animation_queue(self):
        self._update_time()
        self._tile_queue = list()

        # test if the next scheduled tile change is ready
        while self._animation_queue[0].next <= self._last_time:
            token = heappop(self._animation_queue)

            # advance the animation index, looping by default
            if token.index == len(token.frames) - 1:
                token.index = 0
            else:
                token.index += 1

            next_frame = token.frames[token.index]
            token.next = next_frame.duration + self._last_time
            self._animation_map[token.gid] = next_frame.image
            heappush(self._animation_queue, token)

            # go through the animated tile map:
            #   * queue tiles that need to be changed
            #   * remove map entries that do not collide with screen
            needs_clear = False
            for x, y, l in self._animation_tiles[token.gid]:

                # if this tile is on the buffer (checked by using the tile view)
                if self._tile_view.collidepoint(x, y):
                    self._tile_queue.append((x, y, l, next_frame.image, token.gid))
                    # for i in range(0, l):
                    #     self._tile_queue.append((x, y, i, None, token.gid))
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
            self._flush_tile_queue()

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
        requires_zoom_buffer = not self._zoom_level == 1.0

        if self._clear_color == self._alpha_clear_color:
            if requires_zoom_buffer:
                self._zoom_buffer = Surface(view_size, flags=pygame.SRCALPHA)
            self._buffer = Surface(buffer_size, flags=pygame.SRCALPHA)
            self.data.convert_surfaces(self._buffer, True)
        elif self._clear_color:
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

        self._redraw = True

    def _initialize_buffers(self, view_size):
        """ Create the buffers to cache tile drawing

        :param view_size: (int, int): size of the draw area
        :return: None
        """
        tw, th = self.data.tile_size
        mw, mh = self.data.map_size
        buffer_tile_width = int(math.ceil(view_size[0] / tw) + 2)
        buffer_tile_height = int(math.ceil(view_size[1] / th) + 2)
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
        self._layer_quadtree = quadtree.FastQuadTree(rects, 4)
        self.redraw_tiles()

    def _flush_tile_queue(self):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        blit = self._buffer.blit

        for x, y, l, tile, gid in self._tile_queue:
            self._animation_tiles[gid].add((x, y, l))
            blit(tile, (x * tw - ltw, y * th - tth))
