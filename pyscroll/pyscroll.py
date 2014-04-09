from itertools import islice, product, chain
import pygame
import math
import threading
from six.moves import filter, queue, range
from . import quadtree


class BufferedRenderer(object):
    """ Renderer that can be updated incrementally

    Base class to render a map onto a buffer that is suitable for blitting onto
    the screen as one surface, rather than a collection of tiles.

    The class supports differed rendering and multiple layers

    This class works well for maps that operate on a small display and where
    the map is much larger than the display.

    Combine with a data class to get a useful map renderer
    """
    def __init__(self, data, size, colorkey=None, padding=4):
        # defaults
        self.clipping = True
        self.flush_on_draw = True
        self.update_rate = 25

        self.colorkey = colorkey
        self.padding = padding
        self.lock = threading.Lock()
        self.set_data(data)
        self.set_size(size)
        self.queue = iter([])

    def close(self):
        pass

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

        self.layer_quadtree = quadtree.FastQuadTree(rects, 4)

        self.size = size
        self.idle = False
        self.blank = True
        self.xoffset = 0
        self.yoffset = 0
        self.old_x = 0
        self.old_y = 0

    def generate_default_image(self):
        self.default_image = pygame.Surface((self.data.tilewidth, self.data.tileheight))
        self.default_image.fill((0, 0, 0))

    def get_tile_image(self, position):
        try:
            return self.data.get_tile_image(position)
        except ValueError:
            return self.default_image

    def scroll(self, vector):
        """ scroll the background in pixels
        """
        self.center((int(vector[0] + self.old_x), int(vector[1] + self.old_y)))

    def center(self, coords):
        """ center the map on a pixel
        """
        x, y = [round(i, 0) for i in coords]

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
        #self.xoffset += (hpad / 2 - 1) * tw
        #self.yoffset += (hpad / 2 - 1) * th
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
        queue = None
        layers = len(self.data.visible_layers)

        # NOTE: i'm not sure why the the -1 in right and bottom are required
        #       for python 3.  it may have some performance implications, but
        #       i'll benchmark it later.

        # right
        if x > 0:
            queue = product(range(self.view.right - x - 1, self.view.right),
                            range(self.view.top, self.view.bottom),
                            range(layers))

        # left
        elif x < 0:
            queue = product(range(self.view.left, self.view.left - x),
                            range(self.view.top, self.view.bottom),
                            range(layers))

        # bottom
        if y > 0:
            p = product(range(self.view.left, self.view.right),
                        range(self.view.bottom - y - 1, self.view.bottom),
                        range(layers))
            if queue is None:
                queue = p
            else:
                queue = chain(p, queue)

        # top
        elif y < 0:
            p = product(range(self.view.left, self.view.right),
                        range(self.view.top, self.view.top - y),
                        range(layers))
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

    def draw(self, surface, rect, surfaces=[]):
        """ Draw the map onto a surface

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
            self.blank = False
            self.redraw()

        get_tile = self.get_tile_image
        surblit = surface.blit
        left, top = self.view.topleft
        ox, oy = self.xoffset, self.yoffset
        ox -= rect.left
        oy -= rect.top

        if self.flush_on_draw:
            self.flush()

        with self.lock:
            # need to set clipping otherwise the map will draw
            # outside its defined area
            if self.clipping:
                original_clip = surface.get_clip()
                surface.set_clip(rect)

            # draw the entire map to the surface,
            # taking in account the scrolling offset
            surblit(self.buffer, (-ox, -oy))

            # TODO: new sorting method for surfaces
            # TODO: make sure to filter out surfaces outside the screen
            dirty = [(surblit(a[0], a[1]), a[2]) for a in surfaces]

            # redraw tiles that overlap surfaces that were passed in
            for dirty_rect, layer in dirty:
                dirty_rect = dirty_rect.move(ox, oy)
                for r in self.layer_quadtree.hit(dirty_rect):
                    x, y, tw, th = r
                    layers = range(layer + 1, len(self.data.visible_layers))
                    for l in layers:
                        tile = get_tile((x / tw + left, y / th + top, l))
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
        if self.queue:
            self.blit_tiles(self.queue)

    def blit_tiles(self, iterator):
        """ Bilts (x, y, layer) tuples to buffer from iterator
        """
        tw = self.data.tilewidth
        th = self.data.tileheight
        blit = self.buffer.blit
        ltw = self.view.left * tw
        tth = self.view.top * th
        get_tile = self.get_tile_image

        with self.lock:
            if self.colorkey:
                fill = self.buffer.fill
                old_tiles = set()
                for x, y, l in iterator:
                    tile = get_tile((x, y, l))
                    if tile:
                        if l == 0:
                            fill(self.colorkey, (x*tw-ltw, y*th-tth, tw, th))
                        old_tiles.add((x, y, l))
                        blit(tile, (x*tw-ltw, y*th-tth))
                    else:
                        if (x, y, l-1) not in old_tiles:
                            fill(self.colorkey, (x*tw-ltw, y*th-tth, tw, th))
            else:
                images = filter(lambda x: x[1], ((i, get_tile(i)) for i in iterator))
                [blit(image, (x*tw-ltw, y*th-tth)) for ((x,y,l), image) in images]

    def redraw(self):
        """ redraw the visible portion of the buffer -- it is slow.
        """
        queue = product(range(self.view.left, self.view.right),
                        range(self.view.top, self.view.bottom),
                        range(len(self.data.visible_layers)))

        self.update_queue(queue)
        self.flush()


class ThreadedRenderer(BufferedRenderer):
    """ Off-screen tiling is handled in a thread

    This class MUST be closed before the program terminates, or the thread will
    never close and you will have a bad time.
    """
    def __init__(self, *args, **kwargs):
        BufferedRenderer.__init__(self, *args, **kwargs)
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=tile_thread, args=(self,))
        self.thread.start()

    def update(self, dt=None):
        pass

    def flush(self):
        self.queue.join()

    def update_queue(self, iterator):
        [self.queue.put(i) for i in iterator]

    def close(self):
        """ Stop the thread that is running in the background
        """
        self.thread.running = False


def tile_thread(renderer):
    """ poll the tile queue for new tiles and draw them to the buffer
    """
    tw = renderer.data.tilewidth
    th = renderer.data.tileheight
    get_tile = renderer.get_tile_image
    blit = renderer.buffer.blit
    colorkey = renderer.colorkey
    fill = renderer.buffer.fill
    queue = renderer.queue
    lock = renderer.lock

    running = 1

    while running:
        x, y, l = queue.get()

        ltw = renderer.view.left * tw
        tth = renderer.view.top * th
        old_tiles = set()

        if renderer.colorkey:
            tile = get_tile((x, y, l))
            if tile:
                with lock:
                    if l == 0:
                        fill(colorkey, (x*tw-ltw, y*th-tth, tw, th))
                    old_tiles.add((x, y, l))
                    blit(tile, (x*tw-ltw, y*th-tth))
            else:
                if (x, y, l-1) not in old_tiles:
                    with lock:
                        fill(colorkey, (x*tw-ltw, y*th-tth, tw, th))
        else:
            tile = get_tile((x, y, l))
            if tile:
                with lock:
                    blit(tile, (x*tw-ltw, y*th-tth))

        queue.task_done()
