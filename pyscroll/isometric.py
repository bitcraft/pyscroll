import math

import pygame
import pygame.gfxdraw

from pyscroll.orthographic import BufferedRenderer


def vector3_to_iso(vector3):
    offset = 0, 0
    return ((vector3[0] - vector3[1]) + offset[0],
            ((vector3[0] + vector3[1]) >> 1) - vector3[2] + offset[1])


def vector2_to_iso(vector2):
    offset = 0, 0
    return ((vector2[0] - vector2[1]) + offset[0],
            ((vector2[0] + vector2[1]) >> 1) + offset[1])


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
        mw, mh = self.data.map_size
        buffer_tile_width = int(math.ceil(size[0] / tw) + 2) * 2
        buffer_tile_height = int(math.ceil(size[1] / th) + 2) * 2
        buffer_pixel_size = buffer_tile_width * tw, buffer_tile_height * th

        self.map_rect = pygame.Rect(0, 0, mw * tw, mh * th)
        self._view_rect.size = size
        self._tile_view = pygame.Rect(0, 0, buffer_tile_width, buffer_tile_height)
        self._redraw_cutoff = min(buffer_tile_width, buffer_tile_height)
        self._create_buffers(size, buffer_pixel_size)
        self._half_width = size[0] // 2
        self._half_height = size[1] // 2
        self._x_offset = 0
        self._y_offset = 0

        self.redraw_tiles()

    def _draw_surfaces(self, surface, rect, surfaces):
        if surfaces is not None:
            [(surface.blit(i[0], i[1]), i[2]) for i in surfaces]

    def _flush_tile_queue(self):
        """ Blits (x, y, layer) tuples to buffer from iterator
        """
        iterator = self._tile_queue
        surface_blit = self._buffer.blit

        bw, bh = self._buffer.get_size()
        bw /= 2

        tw, th = self.data.tile_size
        twh = tw // 2
        thh = th // 2

        for x, y, l, tile, gid in iterator:
            x -= self._tile_view.left
            y -= self._tile_view.top

            # iso => cart
            iso_x = ((x - y) * twh) + bw
            iso_y = ((x + y) * thh)
            surface_blit(tile, (iso_x, iso_y))

    def center(self, coords):
        """ center the map on a "map pixel"
        """
        x, y = [round(i, 0) for i in coords]
        self._view_rect.center = x, y

        # if self.clamp_camera:
        #     self._view_rect.clamp_ip(self.map_rect)
        #     x, y = self._view_rect.center

        tw, th = self.data.tile_size
        xx, yy = vector2_to_iso(coords)

        self._x_offset = 500
        self._y_offset = 100

        left, _ = divmod(x, tw)
        top, _ = divmod(y, th)

        # adjust the view if the view has changed without a redraw
        dx = int(left - self._tile_view.left)
        dy = int(top - self._tile_view.top)

        self._tile_view.move_ip((dx, dy))
        # self._queue_edge_tiles(dx, dy)
        # self._flush_tile_queue()
        self.redraw_tiles()

