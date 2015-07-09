import math
from itertools import product, chain
from functools import partial

import pygame
import pygame.gfxdraw

from . import quadtree


class BufferedRenderer(object):
    """ Renderer that can be updated incrementally

    Base class to render a map onto a buffer that is suitable for blitting onto
    the screen as one surface, rather than a collection of tiles.

    The class supports differed rendering, multiple layers, shapes and layering
    surfaces (usually from sprites) in the map, creating an illusion of depth.

    This class works well for maps that operate on a small display and where
    the map is much larger than the display, but you will get poor performance
    if the map is smaller than the display.

    The buffered renderer must be used with a data class to get tile and shape
    information.  See the data class api in pyscroll.data, or use the built in
    pytmx support.
    """

    def __init__(self, data, size, clamp_camera=False, colorkey=None, alpha=False):

        # default options
        self.clamp_camera = clamp_camera
        self.alpha = False
        self.clipping = True
        self.default_shape_texture_gid = 1
        self.default_shape_color = 0, 255, 0

        if colorkey and alpha:
            raise ValueError
        elif colorkey:
            self.clear_color = colorkey
        elif alpha:
            self.clear_color = 0, 0, 0, 0
        else:
            self.clear_color = None

        # internal defaults
        self.redraw_cutoff = 0
        self.idle = False
        self.data = None
        self.size = None
        self.x_offset = None
        self.y_offset = None
        self.old_x = None
        self.old_y = None
        self.default_image = None
        self.buffer = None
        self.map_rect = None
        self.view = None
        self.half_width = None
        self.half_height = None

        self.data = data
        self.set_size(size)
        self.queue = iter([])

    def set_size(self, size):
        """ Set the size of the map in pixels
        """
        tw, th = self.data.tile_size

        buffer_tile_width = math.ceil(size[0] / tw) + 2
        buffer_tile_height = math.ceil(size[1] / th) + 2
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        # this rect represents each tile on the buffer
        self.view = pygame.Rect(0, 0, buffer_tile_width, buffer_tile_height)
        self.redraw_cutoff = min(buffer_tile_width, buffer_tile_height)

        if self.clear_color:
            self.buffer = pygame.Surface(buffer_pixel_size, flags=pygame.RLEACCEL)
            self.buffer.set_colorkey(self.clear_color)
            self.buffer.fill(self.clear_color)
        elif self.alpha:
            self.buffer = pygame.Surface(buffer_pixel_size, flags=pygame.SRCALPHA)
        else:
            self.buffer = pygame.Surface(buffer_pixel_size)

        self.half_width = size[0] / 2
        self.half_height = size[1] / 2

        # this is the pixel size of the entire map
        self.map_rect = pygame.Rect(0, 0,
                                    self.data.map_width * tw,
                                    self.data.map_height * th)

        # quadtree is used to correctly draw tiles that cover 'sprites'
        def make_rect(x, y):
            return pygame.Rect((x * tw, y * th), (tw, th))

        rects = [make_rect(x, y)
                 for x, y in product(range(self.view.width),
                                     range(self.view.height))]

        # TODO: figure out what depth -actually- does
        self.layer_quadtree = quadtree.FastQuadTree(rects, 4)

        self.size = size
        self.idle = False
        self.blank = True
        self.x_offset = 0
        self.y_offset = 0
        self.old_x = 0
        self.old_y = 0

        self.redraw()

    def scroll(self, vector):
        """ scroll the background in pixels
        """
        self.center((vector[0] + self.old_x, vector[1] + self.old_y))

    def center(self, coords):
        """ center the map on a pixel
        """
        x, y = [round(i, 0) for i in coords]

        if self.clamp_camera:
            if x < self.half_width:
                x = self.half_width
            elif x + self.half_width > self.map_rect.width:
                x = self.map_rect.width - self.half_width
            if y < self.half_height:
                y = self.half_height
            elif y + self.half_height > self.map_rect.height:
                y = self.map_rect.height - self.half_height

        if self.old_x == x and self.old_y == y:
            self.idle = True
            return

        tw, th = self.data.tile_size
        self.idle = False

        # calc the new postion in tiles and offset
        left, self.x_offset = divmod(x - self.half_width, tw)
        top, self.y_offset = divmod(y - self.half_height, th)

        # self.x_offset += 4
        # self.y_offset += 4

        # determine if tiles should be redrawn
        dx = int(left - self.view.left)
        dy = int(top - self.view.top)

        # adjust the view if the view has changed without a redraw
        view_change = max(abs(dx), abs(dy))
        if view_change <= self.redraw_cutoff:
            # scroll the image (much faster than redrawing the tiles!)
            self.buffer.scroll(-dx * tw, -dy * th)
            self.view.move_ip((dx, dy))
            self.draw_edge_tiles((dx, dy))

        elif view_change > self.redraw_cutoff:
            self.view.move_ip((dx, dy))
            self.redraw()

        self.old_x, self.old_y = x, y

    def draw_edge_tiles(self, offset):
        """ Get the tile coordinates that need to be redrawn
        """
        x, y = map(int, offset)
        layers = list(self.data.visible_tile_layers)
        v = self.view
        self.queue = iter([])
        fill = partial(self.buffer.fill, self.clear_color)
        bw, bh = self.buffer.get_size()
        tw, th = self.data.tile_size

        def append(*args):
            self.queue = chain(self.queue, self.data.get_tile_images_by_rect(*args))

        if x > 0:    # right side
            append(v.right - x, v.right, v.top, v.bottom, layers)
            if self.clear_color:
                d = x * tw
                fill((bw - d, 0, d, bh))

        elif x < 0:  # left side
            append(v.left - x, v.left, v.top, v.bottom, layers)
            if self.clear_color:
                fill((0, 0, -x * tw, bh))

        if y > 0:    # bottom side
            append(v.left, v.right, v.bottom - y, v.bottom, layers)
            if self.clear_color:
                d = y * th
                fill((0, bh - d, bw, d))

        elif y < 0:  # top side
            append(v.left, v.right, v.top, v.top - y, layers)
            if self.clear_color:
                fill((0, 0, bw, -y * th))

        self.flush()

    def draw(self, surface, rect, surfaces=None):
        """ Draw the map onto a surface

        pass a rect that defines the draw area for:
            dirty screen update support
            drawing to an area smaller that the whole window/screen

        surfaces may optionally be passed that will be blited onto the surface.
        this must be a list of tuples containing a layer number, image, and
        rect in screen coordinates.  surfaces will be drawn in order passed,
        and will be correctly drawn with tiles from a higher layer overlapping
        the surface.
        """
        surface_blit = surface.blit
        left, top = self.view.topleft
        ox, oy = self.x_offset, self.y_offset
        ox -= rect.left
        oy -= rect.top

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
                        tile = get_tile((int(x / tw + left),
                                         int(y / th + top), int(l)))
                        if tile:
                            surface_blit(tile, (x - ox, y - oy))

        if self.clipping:
            surface.set_clip(original_clip)

        if self.idle:
            return [i[0] for i in dirty]
        else:
            return [rect]

    def flush(self):
        """ Blit the tiles and block until the tile queue is empty
        """
        self.blit_tiles(self.queue)
        if len(list(self.data.visible_object_layers)):
            self.draw_objects()

    def draw_objects(self):
        """ Totally unoptimized drawing of objects to the map
        """
        tw = self.data.tile_width
        th = self.data.tile_height
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

    def blit_tiles(self, iterator):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self.view.left * tw
        tth = self.view.top * th
        blit = self.buffer.blit

        return [blit(tile, (x * tw - ltw, y * th - tth))
                for x, y, l, tile in self.queue]

    def redraw(self):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        # self.buffer.fill(self.clear_color)
        self.queue = self.data.get_tile_images_by_rect(
            self.view.left, self.view.right,
            self.view.top, self.view.bottom,
            self.data.visible_tile_layers)
        self.flush()

    def get_center_offset(self):
        """ Return x, y pair that will change world coords to screen coords
        :return: x, y
        """
        return -self.old_x + self.half_width, -self.old_y + self.half_height
