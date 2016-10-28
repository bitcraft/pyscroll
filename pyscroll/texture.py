from __future__ import division
from __future__ import print_function

import logging
import time
from operator import gt

import sdl

from pyscroll.base import RendererBase

logger = logging.getLogger('orthographic')


class TextureRenderer(RendererBase):
    """ Renderer that support scrolling, zooming, layers, and animated tiles

    The buffered renderer must be used with a data class to get tile, shape,
    and animation information.  See the data class api in pyscroll.data, or
    use the built-in pytmx support for loading maps created with Tiled.
    """
    def __init__(self, ctx, data, size, clamp_camera=False, time_source=time.time):

        # private attributes
        self.ctx = ctx
        self._sdl_buffer_src = sdl.Rect()  # rect for use when doing a RenderCopy
        self._sdl_buffer_dst = sdl.Rect()  # rect for use when doing a RenderCopy

        super(TextureRenderer, self).__init__(
            data, size, clamp_camera, time_source=time_source, alpha=True)

    def center(self, coords):
        """ center the map on a map pixel

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

                # DEBUG
                self.clear_buffer(self._buffer)
                self._tile_view.move_ip(dx, dy)
                self.redraw_tiles()

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
            self.clear_buffer()

        self.clear_buffer()

        # set the drawing offset
        self._sdl_buffer_dst.x = -int(self._x_offset) + 128
        self._sdl_buffer_dst.y = -int(self._y_offset) + 128
        self._sdl_buffer_dst.w = self._size[0]
        self._sdl_buffer_dst.h = self._size[1]

        print(self._size)

        sdl.renderCopy(renderer, self._buffer, None, self._sdl_buffer_dst)

    def clear_buffer(self, target=None, color=None):
        renderer = self.ctx.renderer
        if target is None:
            sdl.renderClear(renderer)
        else:
            orig = sdl.getRenderTarget(renderer)
            sdl.setRenderTarget(renderer, target)
            sdl.renderClear(renderer)
            sdl.setRenderTarget(renderer, orig)

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

    def _process_animation_queue(self):
        return

    def new_buffer(self, size, **flags):
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
        self._size = sdl.queryTexture(self._buffer)[3:]

    def _flush_tile_queue(self, destination=None):
        """ Blit the queued tiles and block until the tile queue is empty
        """
        tw, th = self.data.tile_size
        ltw = self._tile_view.left * tw
        tth = self._tile_view.top * th
        renderer = self.ctx.renderer
        rcx = sdl.renderCopyEx

        dst_rect = sdl.Rect()
        dst_rect.w = tw
        dst_rect.h = th

        orig = sdl.getRenderTarget(self.ctx.renderer)
        sdl.setRenderTarget(self.ctx.renderer, self._buffer)

        for x, y, l, tile, gid in self._tile_queue:
            texture, src_rect, angle, flip = tile
            dst_rect.x = x * tw - ltw
            dst_rect.y = y * th - tth
            rcx(renderer, texture, src_rect, dst_rect, angle, None, flip)

        sdl.setRenderTarget(self.ctx.renderer, orig)
