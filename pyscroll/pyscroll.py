import pygame
import pygame.gfxdraw
import math
import threading
from itertools import islice, product, chain
from six.moves import queue, range
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
    def __init__(self, data, size, colorkey=None, padding=4,
                 clamp_camera=False):

        # default options
        self.colorkey = colorkey
        self.padding = padding
        self.clamp_camera = clamp_camera
        self.clipping = True
        self.flush_on_draw = True
        self.update_rate = 25
        self.default_shape_texture_gid = 1
        self.default_shape_color = (0, 255, 0)

        # internal defaults
        self.idle = False
        self.blank = False
        self.data = None
        self.size = None
        self.xoffset = None
        self.yoffset = None
        self.old_x = None
        self.old_y = None
        self.default_image = None
        self.buffer = None
        self.rect = None
        self.view = None
        self.half_width = None
        self.half_height = None

        self.lock = threading.Lock()
        self.set_data(data)
        self.set_size(size)
        self.queue = iter([])

    def set_data(self, data):
        self.data = data
        self.generate_default_image()

    def set_size(self, size):
        """ Set the size of the map in pixels
        """
        tw = self.data.tilewidth
        th = self.data.tileheight

        buffer_width = size[0] + tw * self.padding
        buffer_height = size[1] + th * self.padding
        self.buffer = pygame.Surface((buffer_width, buffer_height))

        self.view = pygame.Rect(0, 0,
                                math.ceil(buffer_width / tw),
                                math.ceil(buffer_height / th))

        if self.colorkey:
            self.buffer.set_colorkey(self.colorkey)
            self.buffer.fill(self.colorkey)

        # this is the pixel size of the entire map
        self.rect = pygame.Rect(0, 0,
                                self.data.width * tw,
                                self.data.height * th)

        self.half_width = size[0] / 2
        self.half_height = size[1] / 2

        # quadtree is used to correctly draw tiles that cover 'sprites'
        def make_rect(x, y):
            return pygame.Rect((x * tw, y * th), (tw, th))

        rects = [make_rect(x, y)
                 for x, y in product(range(self.view.width),
                                     range(self.view.height))]

        # TODO: figure out what depth -actually- does
        self.layer_quadtree = quadtree.FastQuadTree(rects, 1)

        self.size = size
        self.idle = False
        self.blank = True
        self.xoffset = 0
        self.yoffset = 0
        self.old_x = 0
        self.old_y = 0

    def generate_default_image(self):
        self.default_image = pygame.Surface((self.data.tilewidth,
                                             self.data.tileheight))
        self.default_image.fill((0, 0, 0))

    def get_tile_image(self, position):
        try:
            return self.data.get_tile_image(position)
        except ValueError:
            return self.default_image

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
            elif x + self.half_width > self.rect.width:
                x = self.rect.width - self.half_width
            if y < self.half_height:
                y = self.half_height
            elif y + self.half_height > self.rect.height:
                y = self.rect.height - self.half_height

        if self.old_x == x and self.old_y == y:
            self.idle = True
            return

        hpad = int(self.padding / 2)
        tw = self.data.tilewidth
        th = self.data.tileheight
        self.idle = False

        # calc the new postion in tiles and offset
        left, self.xoffset = divmod(x - self.half_width, tw)
        top, self.yoffset = divmod(y - self.half_height, th)

        # determine if tiles should be redrawn
        dx = int(left - hpad - self.view.left)
        dy = int(top - hpad - self.view.top)

        # adjust the offsets of the buffer is placed correctly
        self.xoffset += hpad * tw
        self.yoffset += hpad * th

        # adjust the view if the view has changed
        if (abs(dx) >= 1) or (abs(dy) >= 1):
            self.flush()
            self.view = self.view.move((dx, dy))

            # scroll the image (much faster than redrawing the tiles!)
            self.buffer.scroll(-dx * tw, -dy * th)
            self.update_queue(self.get_edge_tiles((dx, dy)))

        self.old_x, self.old_y = x, y

    def update_queue(self, iterator):
        """ Add some tiles to the queue
        """
        self.queue = chain(self.queue, iterator)

    def get_edge_tiles(self, offset):
        """ Get the tile coordinates that need to be redrawn
        """
        x, y = map(int, offset)
        layers = list(self.data.visible_tile_layers)
        view = self.view
        queue = None

        # NOTE: i'm not sure why the the -1 in right and bottom are required
        #       for python 3.  it may have some performance implications, but
        #       i'll benchmark it later.

        # right
        if x > 0:
            queue = product(range(view.right - x - 1, view.right),
                            range(view.top, view.bottom), layers)

        # left
        elif x < 0:
            queue = product(range(view.left, view.left - x),
                            range(view.top, view.bottom), layers)

        # bottom
        if y > 0:
            p = product(range(view.left, view.right),
                        range(view.bottom - y - 1, view.bottom), layers)
            if queue is None:
                queue = p
            else:
                queue = chain(p, queue)

        # top
        elif y < 0:
            p = product(range(view.left, view.right),
                        range(view.top, view.top - y), layers)
            if queue is None:
                queue = p
            else:
                queue = chain(p, queue)

        return queue

    def update(self, dt=None):
        """ Draw tiles in the background

        the drawing operations and management of the buffer is handled here.
        if you are updating more than drawing, then updating here will draw
        off screen tiles.  this will limit expensive tile blits during screen
        draws.  if your draw and update happens every game loop, then you will
        not benefit from updates, but it won't hurt either.
        """
        self.blit_tiles(islice(self.queue, self.update_rate))

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
        if self.blank:
            self.blank = False
            self.redraw()

        surblit = surface.blit
        left, top = self.view.topleft
        ox, oy = self.xoffset, self.yoffset
        ox -= rect.left
        oy -= rect.top

        if self.flush_on_draw:
            self.flush()

        # need to set clipping otherwise the map will draw outside its area
        original_clip = None
        if self.clipping:
            original_clip = surface.get_clip()
            surface.set_clip(rect)

        # draw the entire map to the surface,
        # taking in account the scrolling offset
        surblit(self.buffer, (-ox, -oy))

        if surfaces is None:
            dirty = list()

        else:
            def above(x, y):
                return x > y

            hit = self.layer_quadtree.hit
            get_tile = self.get_tile_image
            tile_layers = tuple(self.data.visible_tile_layers)
            dirty = [(surblit(i[0], i[1]), i[2]) for i in surfaces]

            for dirty_rect, layer in dirty:
                for r in hit(dirty_rect.move(ox, oy)):
                    x, y, tw, th = r
                    for l in [i for i in tile_layers if above(i, layer)]:
                        tile = get_tile((int(x / tw + left),
                                         int(y / th + top), int(l)))
                        if tile:
                            surblit(tile, (x - ox, y - oy))

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
        self.draw_objects()

    def draw_objects(self):
        """ Totally unoptimized drawing of objects to the map
        """
        tw = self.data.tilewidth
        th = self.data.tileheight
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
        """ Bilts (x, y, layer) tuples to buffer from iterator
        """
        tw = self.data.tilewidth
        th = self.data.tileheight
        blit = self.buffer.blit
        ltw = self.view.left * tw
        tth = self.view.top * th
        get_tile = self.get_tile_image

        if self.colorkey:
            fill = self.buffer.fill
            old_tiles = set()
            for x, y, l in iterator:
                tile = get_tile((x, y, l))
                if tile:
                    if l == 0:
                        fill(self.colorkey,
                             (x * tw - ltw, y * th - tth, tw, th))
                    old_tiles.add((x, y))
                    blit(tile, (x * tw - ltw, y * th - tth))
                else:
                    if l > 0:
                        if (x, y) not in old_tiles:
                            fill(self.colorkey,
                                 (x * tw - ltw, y * th - tth, tw, th))
        else:
            for x, y, l in iterator:
                tile = get_tile((x, y, l))
                if tile:
                    blit(tile, (x * tw - ltw, y * th - tth))

    def redraw(self):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        queue = product(range(self.view.left, self.view.right),
                        range(self.view.top, self.view.bottom),
                        self.data.visible_tile_layers)

        self.update_queue(queue)
        self.flush()


class ThreadedRenderer(BufferedRenderer):
    """ Off-screen tiling is handled in a thread
    """

    def __init__(self, *args, **kwargs):
        BufferedRenderer.__init__(self, *args, **kwargs)
        self.flush_on_draw = False
        self.queue = queue.Queue()

        self.thread = TileThread(renderer=self)
        self.thread.start()

    def update(self, dt=None):
        pass

    def flush(self):
        self.queue.join()

    def update_queue(self, iterator):
        for i in iterator:
            self.queue.put(i)


class TileThread(threading.Thread):
    """ poll the tile queue for new tiles and draw them to the buffer
    """

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self)
        self.renderer = kwargs.get('renderer')
        self.daemon = True

    def run(self):
        r = self.renderer

        tw = r.data.tilewidth
        th = r.data.tileheight
        get_tile = r.get_tile_image
        colorkey = r.colorkey
        tile_queue = r.queue
        lock = r.lock
        old_tiles = set()
        old_view = None

        running = 1

        while running:
            x, y, l = tile_queue.get()

            # pyscroll may change these references to another object
            # so, while we are defrencing them, we need to create new
            # references if they change.
            if old_view is not r.view:
                fill = r.buffer.fill
                blit = r.buffer.blit
                ltw = r.view.left * tw
                tth = r.view.top * th
                old_tiles = set()

            if colorkey:
                tile = get_tile((x, y, l))
                if tile:
                    with lock:
                        if l == 0:
                            fill(colorkey, (x * tw - ltw, y * th - tth, tw, th))
                        old_tiles.add((x, y, l))
                        blit(tile, (x * tw - ltw, y * th - tth))
                else:
                    if (x, y, l - 1) not in old_tiles:
                        with lock:
                            fill(colorkey, (x * tw - ltw, y * th - tth, tw, th))
            else:
                tile = get_tile((x, y, l))
                if tile:
                    with lock:
                        blit(tile, (x * tw - ltw, y * th - tth))

            tile_queue.task_done()
