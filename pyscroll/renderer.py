import math
import logging
import time
from heapq import heappush, heappop
from collections import namedtuple
from itertools import product, chain
from functools import partial

import pygame
import pygame.gfxdraw

from . import quadtree


logger = logging.getLogger('renderer')


AnimationFrame = namedtuple("AnimationFrame", "image duration")


class AnimationToken(object):
    __slots__ = ['next', 'gid', 'frames', 'index']

    def __init__(self, gid, frames):
        frames = tuple(AnimationFrame(*i) for i in frames)
        self.next = frames[0].duration
        self.gid = gid
        self.frames = frames
        self.index = 0

    def __lt__(self, other):
        try:
            return self.next < other.next
        except AttributeError:
            return self.next < other


class BufferedRenderer(object):
    """ Renderer that support layers and animated tiles

    Base class to render a map onto a buffer that is suitable for blitting onto
    the screen as one surface, rather than a collection of tiles.

    The class supports animated tiled, multiple layers, shapes and layering
    surfaces (usually from sprites) in the map, creating an illusion of depth.

    The buffered renderer must be used with a data class to get tile and shape
    information.  See the data class api in pyscroll.data, or use the built in
    pytmx support for loading maps created with Tiled.
    """
    def __init__(self, data, size, clamp_camera=True, colorkey=None, alpha=False,
                 time_source=None, scaling_function=pygame.transform.scale):

        # default options
        self.data = data
        self.clamp_camera = clamp_camera
        self.alpha = False
        self.clipping = True
        self.default_shape_texture_gid = 1
        self.default_shape_color = 0, 255, 0
        self.scaling_function=scaling_function

        if time_source is None:
            self.time_source = time.time

        if colorkey and alpha:
            print('cannot select both colorkey and alpha.  choose one.')
            raise ValueError
        elif colorkey:
            self.clear_color = colorkey
        elif alpha:
            self.clear_color = 0, 0, 0, 0
        else:
            self.clear_color = None

        # internal defaults
        self.redraw_cutoff = None
        self.idle = False
        self.size = None
        self.x_offset = None
        self.y_offset = None
        self.buffer = None
        self.map_rect = None
        self.view = None
        self.half_width = None
        self.half_height = None
        self.tile_queue = None
        self.animation_queue = None
        self.animation_map = None
        self.last_time = None
        self._zoom_level = 1.0
        self._zoom_buffer = None
        self._unscaled_size = None

        self.reload_animations()
        self.set_size(size)

    def update_time(self):
        self.last_time = time.time() * 1000

    def reload_animations(self):
        self.update_time()
        self.animation_map = dict()
        self.animation_queue = list()

        for gid, frame_data in self.data.get_animations():
            frames = list()
            for frame_gid, frame_duration in frame_data:
                image = self.data.get_tile_image_by_gid(frame_gid)
                frames.append(AnimationFrame(image, frame_duration))

            ani = AnimationToken(gid, frames)
            ani.next += self.last_time

            self.animation_map[ani.gid] = ani.frames[ani.index].image
            heappush(self.animation_queue, ani)

    @property
    def zoom(self):
        return self._zoom_level

    @zoom.setter
    def zoom(self, value):
        self._zoom_level = value
        buffer_size = self._calculate_zoom_buffer_size(value)
        self._initialize_buffers(buffer_size)

    def _calculate_zoom_buffer_size(self, value):
        if value == 0:
            print('zoom level cannot be zero')
            raise ValueError
        value = 1.0 / value
        return [int(round(i * value)) for i in self._unscaled_size]

    def set_size(self, size):
        """ Set the size of the map in pixels

        This is an expensive operation, do only when absolutely needed.

        :param size: (width, height) pizel size of camera/view of the group
        """
        self._unscaled_size = size
        buffer_size = self._calculate_zoom_buffer_size(self._zoom_level)
        self._initialize_buffers(buffer_size)

    def _initialize_buffers(self, size):
        tw, th = self.data.tile_size
        buffer_tile_width = int(math.ceil(size[0] / tw) + 2)
        buffer_tile_height = int(math.ceil(size[1] / th) + 2)
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th
        self.redraw_cutoff = min(buffer_tile_width, buffer_tile_height)

        # this is the pixel size of the entire map
        mw, mh = self.data.map_size
        self.map_rect = pygame.Rect(0, 0, mw * tw, mh * th)

        # this rect represents each tile on the buffer
        self.view = pygame.Rect(0, 0, buffer_tile_width, buffer_tile_height)

        requires_zoom_buffer = not self._zoom_level == 1.0

        # create the buffer to use, taking in account pixel alpha or colorkey
        if self.clear_color:
            if requires_zoom_buffer:
                self._zoom_buffer = pygame.Surface(size, flags=pygame.RLEACCEL)
                self._zoom_buffer.set_colorkey(self.clear_color)
            self.buffer = pygame.Surface(buffer_pixel_size, flags=pygame.RLEACCEL)
            self.buffer.set_colorkey(self.clear_color)
            self.buffer.fill(self.clear_color)
        elif self.alpha:
            if requires_zoom_buffer:
                self._zoom_buffer = pygame.Surface(size, flags=pygame.SRCALPHA)
            self.buffer = pygame.Surface(buffer_pixel_size, flags=pygame.SRCALPHA)
        else:
            if requires_zoom_buffer:
                self._zoom_buffer = pygame.Surface(size)
            self.buffer = pygame.Surface(buffer_pixel_size)

        self.half_width = size[0] / 2
        self.half_height = size[1] / 2

        # quadtree is used to correctly draw tiles that cover 'sprites'
        def make_rect(x, y):
            return pygame.Rect((x * tw, y * th), (tw, th))

        rects = [make_rect(x, y)
                 for x, y in product(range(buffer_tile_width),
                                     range(buffer_tile_height))]

        # TODO: figure out what depth -actually- does
        self.layer_quadtree = quadtree.FastQuadTree(rects, 4)

        self.idle = False
        self.x_offset = 0
        self.y_offset = 0

        self.old_x = 0
        self.old_y = 0

        self.redraw_tiles()

    def scroll(self, vector):
        """ scroll the background in pixels
        """
        self.center((vector[0] + self.old_x, vector[1] + self.old_y))

    def center(self, coords):
        """ center the map on a pixel
        """
        x, y = [round(i, 0) for i in coords]

        mw, mh = self.map_rect.size
        if self.clamp_camera:
            if x < self.half_width:
                x = self.half_width
            elif x + self.half_width > mw:
                x = mw - self.half_width
            if y < self.half_height:
                y = self.half_height
            elif y + self.half_height > mh:
                y = mh - self.half_height

        tw, th = self.data.tile_size

        # calc the new position in tiles and offset
        left, self.x_offset = divmod(x - self.half_width, tw)
        top, self.y_offset = divmod(y - self.half_height, th)

        # determine if tiles should be redrawn
        # int is req'd b/c of Surface.scroll(...)
        dx = int(left - self.view.left)
        dy = int(top - self.view.top)

        # adjust the view if the view has changed without a redraw
        view_change = max(abs(dx), abs(dy))
        if view_change <= self.redraw_cutoff:
            # scroll the image (much faster than redrawing the tiles!)
            self.buffer.scroll(-dx * tw, -dy * th)
            self.view.move_ip((dx, dy))
            self.queue_edge_tiles(dx, dy)

        elif view_change > self.redraw_cutoff:
            logger.info('scrolling too quickly.  redraw forced')
            self.view.move_ip((dx, dy))
            self.redraw_tiles()

        self.old_x, self.old_y = x, y

    def queue_edge_tiles(self, dx, dy):
        """ Queue edge tiles and clear edge areas on buffer if needed

        :param dx: Edge along X axis to queue
        :param dy: Edge along Y axis to queue
        :return: None
        """
        layers = list(self.data.visible_tile_layers)
        v = self.view
        self.tile_queue = iter([])
        fill = partial(self.buffer.fill, self.clear_color)
        bw, bh = self.buffer.get_size()
        tw, th = self.data.tile_size

        def append(*args):
            self.tile_queue = chain(self.tile_queue, self.data.get_tile_images_by_rect(*args))

        if dx > 0:    # right side
            append(v.right - dx, v.right, v.top, v.bottom, layers)
            if self.clear_color:
                d = dx * tw
                fill((bw - d, 0, d, bh))

        elif dx < 0:  # left side
            append(v.left - dx, v.left, v.top, v.bottom, layers)
            if self.clear_color:
                fill((0, 0, -dx * tw, bh))

        if dy > 0:    # bottom side
            append(v.left, v.right, v.bottom - dy, v.bottom, layers)
            if self.clear_color:
                d = dy * th
                fill((0, bh - d, bw, d))

        elif dy < 0:  # top side
            append(v.left, v.right, v.top, v.top - dy, layers)
            if self.clear_color:
                fill((0, 0, bw, -dy * th))

        self.flush_tile_queue()

    def process_animation_queue(self):
        self.update_time()

        # return if the next scheduled change isn't ready
        if self.animation_queue[0].next > self.last_time:
            return

        # get token from the queue
        token = heappop(self.animation_queue)

        # advance the animation index
        if token.index == len(token.frames) - 1:
            token.index = 0
        else:
            token.index += 1
        next_frame = token.frames[token.index]

        # set the next time to change
        token.next = next_frame.duration + self.last_time

        # update the animation map
        self.animation_map[token.gid] = next_frame.image

        # place back into the queue
        heappush(self.animation_queue, token)

        # todo: something better!
        self.redraw_tiles()

    def draw(self, surface, rect, surfaces=None):
        """ Draw the map onto a surface

        pass a rect that defines the draw area for:
            dirty screen update support
            drawing to an area smaller that the whole window/screen

        surfaces may optionally be passed that will be blitted onto the surface.
        this must be a list of tuples containing a layer number, image, and
        rect in screen coordinates.  surfaces will be drawn in order passed,
        and will be correctly drawn with tiles from a higher layer overlapping
        the surface.
        """
        if self._zoom_level == 1.0:
            self._render_map(surface, rect, surfaces)
        else:
            self._render_map(self._zoom_buffer, self._zoom_buffer.get_rect(), surfaces)
            self.scaling_function(self._zoom_buffer, rect.size, surface)

    def _render_map(self, surface, rect, surfaces):
        surface_blit = surface.blit
        left, top = self.view.topleft
        ox, oy = self.x_offset, self.y_offset
        ox -= rect.left
        oy -= rect.top

        # if map has animated tiles, then handle it now
        if self.animation_queue:
            self.process_animation_queue()

        # need to set clipping otherwise the map will draw outside its area
        original_clip = None
        if self.clipping:
            original_clip = surface.get_clip()
            surface.set_clip(rect)

        # draw the entire map to the surface,
        # taking in account the scrolling offset
        surface_blit(self.buffer, (-ox, -oy))

        if surfaces is None:
            dirty = list()

        else:
            def above(x, y):
                return x > y

            hit = self.layer_quadtree.hit
            get_tile = self.data.get_tile_image
            tile_layers = tuple(self.data.visible_tile_layers)
            dirty = [(surface_blit(i[0], i[1]), i[2]) for i in surfaces]

            for dirty_rect, layer in dirty:
                for r in hit(dirty_rect.move(ox, oy)):
                    x, y, tw, th = r
                    for l in [i for i in tile_layers if above(i, layer)]:
                        tile = get_tile((x // tw + left, y // th + top, l))
                        if tile:
                            surface_blit(tile, (x - ox, y - oy))

        if self.clipping:
            surface.set_clip(original_clip)

        if self.idle:
            return [i[0] for i in dirty]
        else:
            return [rect]

    def draw_objects(self):
        """ Totally unoptimized drawing of objects to the map
        """
        tw, th = self.data.tile_size
        buff = self.buffer
        blit = buff.blit
        map_gid = self.data.tmx.map_gid
        default_color = self.default_shape_color
        get_image_by_gid = self.data.get_tile_image_by_gid
        _draw_textured_poly = pygame.gfxdraw.textured_polygon
        _draw_poly = pygame.draw.polygon
        _draw_lines = pygame.draw.lines

        ox = self.view.left * tw
        oy = self.view.top * th

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

    def flush_tile_queue(self):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self.view.left * tw
        tth = self.view.top * th
        blit = self.buffer.blit

        for x, y, l, tile, gid in self.tile_queue:
            blit(self.animation_map.get(gid, tile),
                 (x * tw - ltw, y * th - tth))

    def redraw_tiles(self):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        if self.clear_color:
            self.buffer.fill(self.clear_color)

        self.tile_queue = self.data.get_tile_images_by_rect(
            self.view.left, self.view.right,
            self.view.top, self.view.bottom,
            self.data.visible_tile_layers)

        self.flush_tile_queue()

    def get_center_offset(self):
        """ Return x, y pair that will change world coords to screen coords
        :return: x, y
        """
        return -self.old_x + self.half_width, -self.old_y + self.half_height
