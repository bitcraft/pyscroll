"""
This file containsata class for pytmx

If you are developing your own map format, please use this
as a template.  Just fill in values that work for your game.
"""
import pytmx

__all__ = ['TiledMapData']


class TiledMapData(object):
    """ For PyTMX 3.x
    """

    def __init__(self, tmx):
        self.tmx = tmx

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
    def visible_layers(self):
        """ This must return layer numbers, not objects
        :return:
        """
        return (int(i) for i in self.tmx.visible_layers)

    @property
    def visible_tile_layers(self):
        """ This must return layer numbers, not objects
        :return:
        """
        return (int(i) for i in self.tmx.visible_tile_layers)

    @property
    def visible_object_layers(self):
        """ This must return layer objects

        This is not required for custom data formats.

        :return:
        """
        return (layer for layer in self.tmx.visible_layers
                if isinstance(layer, pytmx.TiledObjectGroup))

    def get_animations(self):
        """ Get tile animation data

        Must yield tuples that in the following format:
          ( GID, Frames )

          Where Frames is:
          [ (GID, Duration) ... ]

        """
        for gid, d in self.tmx.tile_properties.items():
            frames = d['frames']
            if not frames:
                continue

            yield gid, frames

    def get_tile_image(self, position):
        """ Must return a surface for this position.

        position is (x, y, layer) tuple.
        """
        try:
            return self.tmx.get_tile_image(*position)
        except ValueError:
            return None

    def get_tile_image_by_gid(self, gid):
        """ Return surface for a gid (experimental)
        """
        return self.tmx.get_tile_image_by_gid(gid)

    def get_tile_images_by_rect(self, x1, x2, y1, y2, layers):
        """ Not like python 'Range': will include the end index!

        Given the coordinates, yield the following tuple for each tile:
          X, Y, Layer Number, pygame Surface, GID

        GID's are required for animated tiles only.  This value, if not
        used by your game engine, can be 0 or None.

        :param x1: Start x (column) index
        :param x2: Stop x (column) index
        :param y1: Start of y (row) index
        :param y2: Stop of y (row) index
        :param layers:
        :return:
        """

        def do_rev(seq, start, stop):
            if start < stop:
                return enumerate(seq[start:stop], start)
            else:
                return enumerate(seq[stop:start], stop)

        images = self.tmx.images
        for layer_no in layers:
            data = self.tmx.layers[layer_no].data
            for y, row in do_rev(data, y1, y2):
                for x, gid in do_rev(row, x1, x2):
                    if gid:
                        yield x, y, layer_no, images[gid], gid
