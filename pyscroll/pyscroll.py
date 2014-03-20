from itertools import product, chain
from . import quadtree
import pygame


# this image will be used when a tile cannot be loaded
def generate_default_image(size):
    i = pygame.Surface(size)
    i.fill((0, 0, 0))
    i.set_alpha(128)
    return i


class TiledMapData:
    def __init__(self, tmx):
        self.tmx = tmx
        self.default_image = generate_default_image((tmx.tilewidth, tmx.tileheight))

    @property
    def tilewidth(self):
        return self.tmx.tilewidth

    @property
    def tileheight(self):
        return self.tmx.tileheight

    @property
    def width(self):
        return self.tmx.width

    @property
    def height(self):
        return self.tmx.height

    @property
    def visible_layers(self):
        return list(self.tmx.visible_layers)

    def get_tile_image(self, position):
        """
        Return a surface for this position.  Returns a blank tile if cannot be loaded.
        position is x, y, layer tuple
        """

        x, y, l = map(int, position)
        try:
            t = self.tmx.get_tile_image(x, y, l)
            if t:
                return t
            else:
                return self.default_image
        except ValueError:
            return self.default_image

    def convert(self, surface=None, depth=None, flags=0):
        """
        The display may have changed since the map was loaded.
        Calling this on will convert() all the surfaces to the same format as the surface passed.

        Using this function ensures all tiles are the same pixel format for fast blitting,
        """

        if (surface==depth==None) and (flags==0):
            print("Need to pass a surface, depth, for flags")
            raise ValueError

        if surface:
            for i, t in enumerate(self.tmx.images):
                if t: self.tmx.images[i] = t.convert(surface)

        elif depth or flags:
            for i, t in enumerate(self.tmx.images):
                if t:
                    self.tmx.images[i] = t.convert(depth, flags)


class BufferedRenderer:
    """
    Base class to render a map onto a buffer that is suitable for blitting onto
    the screen as one surface, rather than a collection of tiles.

    The class supports differed rendering and multiple layers

    This class works well for maps that operate on a small display and where
    the map is much larger than the display.

    Combine with a data class to get a useful map renderer
    """

    time_update = True

    def __init__(self, data, size, **kwargs):
        self.set_data(data)
        self.set_size(size)

    def set_data(self, data):
        self.data = data

    def set_size(self, size):
        """
        Set the size of the map in pixels

        This isn't a very quick operation, so try to avoid doing it often
        """

        self.view = pygame.Rect(0, 0, (size[0] / self.data.tilewidth),
                                      (size[1] / self.data.tileheight))

        buffer_width = size[0] + self.data.tilewidth * 2
        buffer_height = size[1] + self.data.tileheight * 2
        self.buffer = pygame.Surface((buffer_width, buffer_height))

        # this is the pixel size of the entire map
        self.width = self.data.width * self.data.tilewidth
        self.height = self.data.height * self.data.tileheight

        self.half_width  = size[0] / 2
        self.half_height = size[1] / 2

        # how many tiles are blitted to the buffer during an update
        self.blits_per_update = self.view.width * 2

        # quadtree is used to correctly draw tiles that cover 'sprites'
        def make_rect(x, y):
            return pygame.Rect((x*self.data.tilewidth,y*self.data.tileheight),
                               (self.data.tilewidth, self.data.tileheight))

        rects = [ make_rect(x, y) for x, y in product(range(self.view.width+2), range(self.view.height+2)) ]

        self.layer_quadtree = quadtree.FastQuadTree(rects, 4)

        self.size = size
        self.idle = False
        self.blank = True
        self.queue = None
        self.xoffset = 0
        self.yoffset = 0
        self.old_x = 0
        self.old_y = 0

    def scroll(self, vector):
        """
        scroll the background in pixels
        """

        x, y = map(int, vector)
        self.center((x + self.old_x, y + self.old_y))

    def center(self, coords):
        """
        center the map on a pixel
        pixel coordinates have the origin on the upper-left corner
        """

        x, y = map(int, coords)

        if self.old_x == x and self.old_y == y:
            self.idle = True
            return

        self.idle = False

        # calc the new postion in tiles and offset
        left, self.xoffset = divmod(x-self.half_width,  self.data.tilewidth)
        top,  self.yoffset = divmod(y-self.half_height, self.data.tileheight)

        # determine if tiles should be redrawn
        dx = left - self.view.left
        dy = top - self.view.top

        # determine which direction the map is moving, then
        # adjust the offsets to compensate for it:
        #    make sure the leading "edge" always has extra row/column of tiles

        if self.old_x > x:
            if self.xoffset < self.data.tilewidth:
                self.xoffset += self.data.tilewidth
                dx -= 1

        if self.old_y > y:
            if self.yoffset < self.data.tileheight:
                self.yoffset += self.data.tileheight
                dy -= 1

        # adjust the view of the view has changed
        if not (dx, dy) == (0, 0):
            dx = int(dx)
            dy = int(dy)

            self.flush()
            self.view = self.view.move((dx, dy))

            # scroll the image (much faster than reblitting the tiles!)
            self.buffer.scroll(-dx * self.data.tilewidth, -dy * self.data.tileheight)
            self.queue_edge_tiles((dx, dy))

            # prevent edges on the screen if moving too fast or camera is shaking
            if (abs(dx) > 1) or (abs(dy) > 1):
                self.flush()

        self.old_x, self.old_y = x, y

    def convert(self, surface=None, depth=None, flags=0):
        """
        The display may have changed since the map was loaded.
        Calling this on will convert() all the surfaces to the same format as the surface passed.

        Using this function ensures all tiles are the same pixel format for fast blitting,
        """

        if (surface == depth is None) and (flags == 0):
            print("Need to pass a surface, depth, for flags")
            raise ValueError

        self.data.convert(surface, depth, flags)

        if surface:
            self.buffer = self.buffer.convert(surface)
        elif depth or flags:
            self.buffer = self.buffer.convert(depth, flags)

    def queue_edge_tiles(self, tiles):
        """
        add the tiles on the edge that need to be redrawn to the queue.
        for internal use
        """

        x, y = map(int, tiles)

        if self.queue is None:
            self.queue = iter([])

        # right
        if x > 0:
            p = product(range(self.view.right+1, self.view.right-x,-1),
                        range(self.view.top, self.view.bottom + 2),
                        range(len(self.data.visible_layers)))
            self.queue = chain(p, self.queue)

        # left
        elif x < 0:
            p = product(range(self.view.left, self.view.left - x),
                        range(self.view.top, self.view.bottom + 2),
                        range(len(self.data.visible_layers)))
            self.queue = chain(p, self.queue)

        # bottom
        if y > 0:
            p = product(range(self.view.left, self.view.right + 2),
                        range(self.view.bottom+1, self.view.bottom-y, -1),
                        range(len(self.data.visible_layers)))
            self.queue = chain(p, self.queue)

        # top
        elif y < 0:
            p = product(range(self.view.left, self.view.right + 2),
                        range(self.view.top, self.view.top - y),
                        range(len(self.data.visible_layers)))
            self.queue = chain(p, self.queue)

    def update(self, time=None):
        """
        the drawing operations and management of the buffer is handled here.
        if you notice that the tiles are being drawn while the screen
        is scrolling, you will need to adjust the number of tiles that are
        bilt per update or increase update frequency.
        """

        if self.queue:
            bufblit = self.buffer.blit
            get_tile = self.data.get_tile_image
            ltw = self.data.tilewidth * self.view.left
            tth = self.data.tileheight * self.view.top
            tw = self.data.tilewidth
            th = self.data.tileheight

            for i in range(self.blits_per_update):
                try:
                    x,y,l = next(self.queue)
                except StopIteration:
                    self.queue = None
                    break

                image = get_tile((x, y, l))
                if image:
                    bufblit(image, (x * tw - ltw, y * th - tth))

    def draw(self, surface, rect, surfaces=[]):
        """
        draw the map onto a surface.

        pass a rect that defines the draw area for:
            dirty screen update support
            drawing to an area smaller that the whole window/screen

        surfaces may optionally be passed that will be blited onto the surface.
        this must be a list of tuples containing a layer number, image, and
        rect in screen coordinates.  surfaces will be drawn in order passed,
        and will be correctly drawn with tiles from a higher layer overlap
        the surface.
        """

        if self.blank:
            self.redraw()
            self.blank = False

        surblit = surface.blit
        left, top = self.view.topleft
        ox, oy = self.xoffset, self.yoffset
        get_tile = self.data.get_tile_image

        # need to set clipping otherwise the map will draw outside its defined area
        original_clip = surface.get_clip()
        surface.set_clip(rect)
        ox -= rect.left
        oy -= rect.top

        if self.queue:
            self.flush()

        # draw the entire map to the surface, taking in account the scrolling offset
        surblit(self.buffer, (-ox, -oy))

        # TODO: new sorting method for surfaces
        # TODO: make sure to filter out surfaces outside the screen
        dirty = [ (surblit(a[0], a[1]), a[2]) for a in surfaces ]

        # redraw tiles that overlap surfaces that were passed in
        for dirtyRect, layer in dirty:
            dirtyRect = dirtyRect.move(ox, oy)
            for r in self.layer_quadtree.hit(dirtyRect):
                x, y, tw, th = r
                layers = range(layer+1, len(self.data.visible_layers))
                for l in layers:
                    tile = get_tile((x/tw + left, y/th + top, l))
                    if tile:
                        surblit(tile, (x-ox, y-oy))

        surface.set_clip(original_clip)

        if self.idle:
            return [ i[0] for i in dirty ]
        else:
            return [ rect ]

    def flush(self):
        """
        draw all tiles that are sitting in the queue
        """

        if self.queue:
            tw = self.data.tilewidth
            th = self.data.tileheight
            blit = self.buffer.blit
            ltw = self.view.left * tw
            tth = self.view.top * th
            get_tile = self.data.get_tile_image
            images = filter(lambda x: x[1], ((i, get_tile(i)) for i in self.queue))
            [ blit(image, (x*tw-ltw, y*th-tth)) for ((x,y,l), image) in images ]
            self.queue = None

    def redraw(self):
        """
        redraw the visible portion of the buffer -- it is slow.

        should be called right after the map is created to initialize the the buffer.
        will be slow, you've been warned.
        """

        self.queue = product(range(self.view.left, self.view.right + 2),
                             range(self.view.top, self.view.bottom + 2),
                             range(len(self.data.visible_layers)))
        self.flush()
