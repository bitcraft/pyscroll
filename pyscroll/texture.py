from __future__ import division
from __future__ import print_function

import logging
import math
import time
from functools import partial
from heapq import heappush, heappop
from itertools import product, chain
from operator import gt

import sdl

from pyscroll import surface_clipping_context, quadtree
from pyscroll.animation import AnimationFrame, AnimationToken
from .rect import Rect

logger = logging.getLogger('orthographic')


class TextureRenderer(object):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in pyscroll.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """

    def __init__(self, ctx, data, size, clamp_camera=False, time_source=time.time):

        # default options
        self.ctx = ctx
        self.data = data  # reference to data source
        self.clamp_camera = clamp_camera  # if true, cannot scroll past map edge
        self.anchored_view = True  # if true, map will be fixed to upper left corner
        self.map_rect = None  # pygame rect of entire map
        self.time_source = time_source  # determines how tile animations are processed
        self.default_shape_texture_gid = 1  # [experimental] texture to draw shapes with
        self.default_shape_color = 0, 255, 0  # [experimental] color to fill polygons with

        self._clear_color = (0, 0, 0, 0)

        # private attributes
        self._sdl_buffer_src = sdl.Rect()  # rect for use when doing a RenderCopy
        self._sdl_buffer_dst = sdl.Rect()  # rect for use when doing a RenderCopy
        self._size = None  # size that the camera/viewport is on screen, kinda
        self._redraw_cutoff = None  # size of dirty tile edge that will trigger full redraw
        self._x_offset = None  # offsets are used to scroll map in sub-tile increments
        self._y_offset = None
        self._buffer = None  # complete rendering of tilemap
        self._tile_view = None  # this rect represents each tile on the buffer
        self._half_width = None  # 'half x' attributes are used to reduce division ops.
        self._half_height = None
        self._tile_queue = None  # tiles queued to be draw onto buffer
        self._animation_queue = None  # heap queue of animation token.  schedules tile changes
        self._animation_map = None  # map of GID to other GIDs in an animation
        self._last_time = None  # used for scheduling animations
        self._layer_quadtree = None  # used to draw tiles that overlap optional surfaces
        self._zoom_buffer = None  # used to speed up zoom operations
        self._zoom_level = 1.0  # negative numbers make map smaller, positive: bigger

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

            if view_change:
                # self._buffer.scroll(-dx * tw, -dy * th)
                # not sure how to implement texture scrolling, so just retile it
                # pretty sure it is not worth the effort, idk
                # https://bitbucket.org/pygame/pygame/src/010a750596cf0e60c6b6268ca345c7807b913e22/src/surface.c?at=default&fileviewer=file-view-default#surface.c-1596
                # maybe "change pixel pitch" idk.
                print(dx, dy)
                ox, oy = self._tile_view.topleft
                self._tile_view.move_ip(-dx, -dy)
                self.redraw_tiles()
                self._tile_view.topleft = ox + dx, oy + dy

        print(self._x_offset, self._y_offset)

    def draw(self, renderer, surfaces=None):
        """ Draw the map onto a surface

        pass a rect that defines the draw area for:
            drawing to an area smaller that the whole window/screen

        surfaces may optionally be passed that will be blitted onto the surface.
        this must be a sequence of tuples containing a layer number, image, and
        rect in screen coordinates.  surfaces will be drawn in order passed,
        and will be correctly drawn with tiles from a higher layer overlapping
        the surface.

        surfaces list should be in the following format:
        [ (layer, texture, rect), ... ]

        :param renderer: ya know, the thing
        :param surfaces: optional sequence of surfaces to interlace between tiles
        """

        if self._animation_queue:
            self._process_animation_queue()

        if not self.anchored_view:
            sdl.renderClear()

        # set the drawing offset
        self._sdl_buffer_dst.x = -int(self._x_offset)
        self._sdl_buffer_dst.y = -int(self._y_offset)
        self._sdl_buffer_dst.w = self._size[0]
        self._sdl_buffer_dst.h = self._size[1]

        sdl.renderCopy(renderer, self._buffer, None, self._sdl_buffer_dst)

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
        self._zoom_level = value
        buffer_size = self._calculate_zoom_buffer_size(value)
        self._initialize_buffers(buffer_size)

    def set_size(self, size):
        """ Set the size of the map in pixels

        This is an expensive operation, do only when absolutely needed.

        :param size: (width, height) pixel size of camera/view of the group
        """
        self._size = [int(i) for i in size]
        buffer_size = self._calculate_zoom_buffer_size(self._zoom_level)
        self._initialize_buffers(buffer_size)

    def redraw_tiles(self):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        renderer = self.ctx.renderer

        # clear the buffer
        orig = sdl.getRenderTarget(renderer)
        sdl.setRenderTarget(renderer, self._buffer)
        sdl.renderClear(renderer)
        sdl.setRenderTarget(renderer, orig)

        self._tile_queue = self.data.get_tile_images_by_rect(self._tile_view)
        self._flush_tile_queue()

    def get_center_offset(self):
        """ Return x, y pair that will change world coords to screen coords
        :return: int, int
        """
        return (-self.view_rect.centerx + self._half_width,
                -self.view_rect.centery + self._half_height)

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
        for i in surfaces:
            try:
                flags = i[3]
            except IndexError:
                dirty_append((surface_blit(i[0], i[1]), i[2]))
            else:
                dirty_append((surface_blit(i[0], i[1], None, flags), i[2]))

        for dirty_rect, layer in dirty:
            for r in hit(dirty_rect.move(ox, oy)):
                x, y, tw, th = r
                for l in [i for i in tile_layers if gt(i, layer)]:
                    tile = get_tile((x // tw + left, y // th + top, l))
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
        requires_redraw = False

        # test if the next scheduled tile change is ready
        while self._animation_queue[0].next <= self._last_time:
            requires_redraw = True
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

        if requires_redraw:
            # TODO: record the tiles that changed and update only affected tiles
            self.redraw_tiles()

    def _calculate_zoom_buffer_size(self, value):
        if value <= 0:
            print('zoom level cannot be zero or less')
            raise ValueError
        value = 1.0 / value
        return [int(round(i * value)) for i in self._size]

    def new_buffer(self, size):
        w, h = size
        fmt = sdl.PIXELFORMAT_RGBA8888
        texture = sdl.createTexture(self.ctx.renderer, fmt, sdl.TEXTUREACCESS_TARGET, w, h)
        return texture

    def _create_buffers(self, view_size, buffer_size):
        """ Create the buffers, taking in account pixel alpha or colorkey

        :param view_size: pixel size of the view
        :param buffer_size: pixel size of the buffer
        """
        self._buffer = self.new_buffer(buffer_size)

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
        self._layer_quadtree = quadtree.FastQuadTree(rects, 4)
        self.redraw_tiles()

    def _flush_tile_queue(self):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        map_get = self._animation_map.get
        rcx = sdl.renderCopyEx
        renderer = self.ctx.renderer

        dst_rect = sdl.Rect()
        dst_rect.x = 0
        dst_rect.y = 0
        dst_rect.w = tw
        dst_rect.h = th

        orig = sdl.getRenderTarget(self.ctx.renderer)
        sdl.setRenderTarget(self.ctx.renderer, self._buffer)

        for x, y, l, tile, gid in self._tile_queue:
            texture, src_rect, angle, flip = map_get(gid, tile)
            dst_rect.x = x * tw - ltw
            dst_rect.y = y * th - tth
            rcx(renderer, texture, src_rect, dst_rect, angle, None, flip)

        sdl.setRenderTarget(self.ctx.renderer, orig)
