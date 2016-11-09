# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2016

This file is part of mason.

mason is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

mason is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with mason.  If not, see <http://www.gnu.org/licenses/>.
"""
from itertools import product

import pytmx

from mason import rect_to_bb

__all__ = ('PyscrollDataAdapter', 'TiledMapData')


class PyscrollDataAdapter(object):
    """ Use this as a template for data adapters
    """
    # the following can be class/instance attributes
    # or properties.  they are listed here as class
    # instances, but use as properties is fine, too.
    tile_size = None  # (int, int): size of each tile in pixels
    map_size = None  # (int, int): size of map in tiles
    visible_tile_layers = None  # list of visible layer integers

    def convert_surfaces(self, parent, alpha=False):
        """ Convert all images in the data to match the parent

        :param parent: pygame.Surface
        :return: None
        """
        raise NotImplementedError

    def get_animations(self):
        """ Get tile animation data

        This method is subject to change in the future.

        Must yield tuples that in the following format:
          ( GID, Frames )

          Where Frames is:
          [ (GID, Duration), ... ]

        :returns: sequence
        """
        raise NotImplementedError

    def get_tile_image(self, position):
        """ Return an image for the given position.

        Return None if no tile for position.

        :param position: (x, y, layer) sequence
        :returns: pygame Surface or None
        """
        raise NotImplementedError

    def get_tile_images_by_rect(self, rect):
        """ Given a 2d area, return generator of tile images inside

        Given the coordinates, yield the following tuple for each tile:
          X, Y, Layer Number, pygame Surface, GID

        This method also defines render order by re arranging the
        positions of each tile as it is yielded to the renderer.

        This is an optimization that you can make for your data.
        If you can provide access to tile information in a batch,
        then mason can access data faster and render quicker.

        To implement an optimization, override this method.

        Not like python 'Range': should include the end index!

        GID's are required for animated tiles only.  This value, if not
        used by your game engine, can be 0 or None.

        < The GID requirement will change in the future >

        :param rect: a rect-like object that defines tiles to draw
        :return:
        """
        x1, y1, x2, y2 = rect_to_bb(rect)
        for layer in self.visible_tile_layers:
            for y, x in product(range(y1, y2 + 1),
                                range(x1, x2 + 1)):
                tile = self.get_tile_image((x, y, layer))
                if tile:
                    yield x, y, layer, tile, 0


class TiledMapData(PyscrollDataAdapter):
    """ For data loaded from pytmx

    Use of this class requires a recent version of pytmx.
    """

    def __init__(self, tmx):
        self.tmx = tmx

    def convert_surfaces(self, parent, alpha=False):
        """ Convert all images in the data to match the parent

        :param parent: pygame.Surface
        :param alpha: preserve alpha channel or not
        :return: None
        """
        import operator

        if alpha:
            getter = operator.attrgetter('convert_alpha')
        else:
            getter = operator.attrgetter('convert')

        images = list()
        for i in self.tmx.images:
            if i:
                images.append(getter(i)(parent))
            else:  # this will be None sometimes
                images.append(i)
        self.tmx.images = images

    @property
    def tile_size(self):
        """ This is the pixel size of tiles to be rendered
        :return: (int, int)
        """
        return self.tmx.tilewidth, self.tmx.tileheight

    @property
    def map_size(self):
        """ This is the size of the map in tiles
        :return: (int, int)
        """
        return self.tmx.width, self.tmx.height

    @property
    def pixel_size(self):
        """ This is the size of the map if completely rendered
        :return: (int, int)
        """
        return [a * b for a, b in zip(self.tile_size, self.map_size)]

    @property
    def visible_tile_layers(self):
        """ This must return layer numbers, not objects
        :return: [int, int, ...]
        """
        return (int(i) for i in self.tmx.visible_tile_layers)

    @property
    def visible_object_layers(self):
        """ This must return layer objects

        This is not required for custom data formats.

        :return: Sequence of pytmx object layers/groups
        """
        return (layer for layer in self.tmx.visible_layers
                if isinstance(layer, pytmx.TiledObjectGroup))

    def get_animations(self):
        for gid, d in self.tmx.tile_properties.items():
            try:
                frames = d['frames']
            except KeyError:
                continue
            if frames:
                yield gid, frames

    def get_tile_image(self, position):
        try:
            return self.tmx.get_tile_image(*position)
        except ValueError:
            return None

    def set_tile_image_by_gid(self, position, gid):
        """ Set a tile's image by changing the gid (experimental)
        """
        x, y, layer = position
        self.tmx.layers[layer][y][x] = gid

    def get_tile_image_by_gid(self, gid):
        """ Return surface for a gid (experimental)
        """
        return self.tmx.get_tile_image_by_gid(gid)

    def get_tile_images_by_rect(self, rect):
        """ Speed up data access

        More efficient because data is accessed and cached locally
        """

        def rev(seq, start, stop):
            if start < 0:
                start = 0
            return enumerate(seq[start:stop + 1], start)

        x1, y1, x2, y2 = rect_to_bb(rect)
        images = self.tmx.images
        layers = self.tmx.layers
        for layer in self.tmx.visible_tile_layers:
            for y, row in rev(layers[layer].data, y1, y2):
                for x, gid in [i for i in rev(row, x1, x2) if i[1]]:
                    yield x, y, layer, images[gid], gid