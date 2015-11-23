"""
This file contains two data classes for use with pytmx.
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
        return self.tmx.tilewidth, self.tmx.tileheight

    @property
    def map_size(self):
        return self.tmx.width, self.tmx.height

    @property
    def visible_layers(self):
        return (int(i) for i in self.tmx.visible_layers)

    @property
    def visible_tile_layers(self):
        return (int(i) for i in self.tmx.visible_tile_layers)

    @property
    def visible_object_layers(self):
        return (layer for layer in self.tmx.visible_layers
                if isinstance(layer, pytmx.TiledObjectGroup))

    def get_animations(self):
        for gid, d in self.tmx.tile_properties.items():
            raw_frames = d['frames']
            if not raw_frames:
                continue

            frames = list()
            for frame in d['frames']:
                frames.append((frame['gid'], frame['duration']))
            yield gid, frames

    def get_tile_image(self, position):
        """ Return a surface for this position.

        Returns a blank tile if cannot be loaded.
        position is x, y, layer tuple
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
