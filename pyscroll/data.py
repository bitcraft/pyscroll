"""
This file contains two data classes for use with pytmx.
"""

import sys
import pytmx

__all__ = ['TiledMapData']


class TiledMapData(object):
    """ For PyTMX 3.x and 6.x
    """

    def __init__(self, tmx):
        self.tmx = tmx

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
        return (int(i) for i in self.tmx.visible_layers)

    @property
    def visible_tile_layers(self):
        return (int(i) for i in self.tmx.visible_tile_layers)

    @property
    def visible_object_layers(self):
        return (layer for layer in self.tmx.visible_layers
                if isinstance(layer, pytmx.TiledObjectGroup))

    def get_tile_image(self, position):
        """ Return a surface for this position.

        Returns a blank tile if cannot be loaded.
        position is x, y, layer tuple
        """
        x, y, l = position
        return self.tmx.get_tile_image(x, y, l)

    def get_tile_image_by_gid(self, gid):
        """ Return surface for a gid (experimental)
        """
        return self.tmx.get_tile_image_by_gid(gid)


class LegacyTiledMapData(TiledMapData):
    """ For PyTMX 2.x series
    """

    @property
    def visible_layers(self):
        return (int(i) for (i, l) in enumerate(self.tmx.all_layers)
                if l.visible)

    @property
    def visible_tile_layers(self):
        return (int(i) for (i, l) in enumerate(self.tmx.visibleTileLayers))

    @property
    def visible_object_layers(self):
        return (layer for layer in self.tmx.objectgroups if layer.visible)

    def get_tile_image(self, position):
        """ Return a surface for this position.

        Returns a blank tile if cannot be loaded.
        position is x, y, layer tuple
        """
        x, y, l = position
        return self.tmx.getTileImage(x, y, l)

    def get_tile_image_by_gid(self, gid):
        """ Return surface for a gid (experimental)
        """
        return self.tmx.getTileImageByGid(gid)


try:
    if getattr(pytmx, "__version__", (0, 0, 0)) < (2, 18, 0):
        sys.stderr.write('pyscroll is using the legacy pytmx api\n')
        TiledMapData = LegacyTiledMapData
except (AttributeError, TypeError):
    sys.stderr.write('pyscroll is using the legacy pytmx api\n')
    TiledMapData = LegacyTiledMapData
