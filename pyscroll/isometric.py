import math

import pygame
import pygame.gfxdraw

from pyscroll.orthographic import BufferedRenderer


class IsometricBufferedRenderer(BufferedRenderer):
    """ TEST ISOMETRIC

    here be dragons.  lots of odd, untested, and unoptimised stuff.

    - coalescing of surfaces is not supported
    - drawing may have depth sorting issues
    - will be slower than orthographic maps for window of same size
    """

    def __init__(self, *args, **kwargs):
        self.iso_double_height = True
        super(IsometricBufferedRenderer, self).__init__(*args, **kwargs)

    def _initialize_buffers(self, size):
        """ Set the size of the map in pixels
        """
        tw = self.data.tile_size[0]
        th = self.data.tile_size[1] // 2

        buffer_tile_width = int(math.ceil(size[0] / tw) + 2)
        buffer_tile_height = int(math.ceil(size[1] / th) + 2)
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th
        self._redraw_cutoff = min(buffer_tile_width, buffer_tile_height)

        # this is the pixel size of the entire map
        mw, mh = self.data.map_size
        self.map_rect = pygame.Rect(0, 0, mw * tw, mh * th)

        self._view = pygame.Rect(0, 0, buffer_tile_width, buffer_tile_height)

        self._make_buffers(size, buffer_pixel_size)

        self._half_width = size[0] / 2
        self._half_height = size[1] / 2

        self._x_offset = 0
        self._y_offset = 0
        self._old_x = 0
        self._old_y = 0

        self.redraw_tiles()

    def _draw_surfaces(self, surface, rect, surfaces):
        if surfaces is not None:
            [(surface.blit(i[0], i[1]), i[2]) for i in surfaces]

    def _flush_tile_queue(self):
        """ Bilts (x, y, layer) tuples to buffer from iterator
        """
        iterator = self._tile_queue
        surface_blit = self._buffer.blit
        get_tile = self.data.get_tile_image

        bw, bh = self._buffer.get_size()
        bw /= 2

        tw, th = self.data.tile_size
        twh = tw // 2
        thh = th // 2

        for x, y, l, tile, gid in iterator:
            x -= self._view.left
            y -= self._view.top

            # iso => cart
            iso_x = ((x - y) * twh) + bw
            iso_y = ((x + y) * thh)
            surface_blit(tile, (iso_x, iso_y))

    def center(self, coords):
        """ center the map on a "map pixel"
        """
        x, y = [round(i, 0) for i in coords]

        tw, th = self.data.tile_size
        twh = tw // 2
        thh = th // 2

        # iso => screen
        xx = x - y
        yy = (y + x) / 2

        # calc the new offset
        left, self._x_offset = divmod(x - self._half_width, tw)
        top, self._y_offset = divmod(y - self._half_height, th)

        ox = (x % tw)
        oy = (y % th)
        self._x_offset = xx
        self._y_offset = yy

        # calc new view
        # left = int(x / tw)
        # top = int(y / th)

        # determine if tiles should be redrawn
        dx = int(left - self._view.left)
        dy = int(top - self._view.top)

        self._view.move_ip((dx, dy))
        self.redraw_tiles()

        self._old_x, self._old_y = x, y
