import six
import pygame

__all__ = ['TiledMapData', 'LegacyTiledMapData', 'PyscrollGroup']


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
        return list(self.tmx.visible_layers)

    def get_tile_image(self, position):
        """ Return a surface for this position.

        Returns a blank tile if cannot be loaded.
        position is x, y, layer tuple
        """

        x, y, l = position
        return self.tmx.get_tile_image(x, y, l)


class LegacyTiledMapData(TiledMapData):
    """ For PyTMX 2.x series
    """

    @property
    def visible_layers(self):
        return self.tmx.visibleTileLayers

    def get_tile_image(self, position):
        """ Return a surface for this position.

        Returns a blank tile if cannot be loaded.
        position is x, y, layer tuple
        """

        x, y, l = position
        return self.tmx.getTileImage(x, y, l)


# for old pytmx compatibility
if six.PY2:
    TiledMapData = LegacyTiledMapData


class PyscrollGroup(pygame.sprite.LayeredUpdates):
    """ Layered Group with ability to center sprites and scrolling map
    """
    def __init__(self, *args, **kwargs):
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        self._center = (0, 0)
        self._map_layer = kwargs.get('map_layer')

    def update(self, dt):
        pygame.sprite.LayeredUpdates.update(self, dt)
        self._map_layer.update(dt)

    def center(self, value):
        """ Center the group/map on a pixel

        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.
        """
        self._center = tuple(value)
        self._map_layer.center(self._center)

    def draw(self, surface):
        """ Draw all sprites and map onto the surface

        Group.draw(surface): return None
        Draws all of the member sprites onto the given surface.
        """

        xx = -self._center[0] + self._map_layer.half_width
        yy = -self._center[1] + self._map_layer.half_height

        spritedict = self.spritedict
        gl = self.get_layer_of_sprite

        new_surfaces = []
        for spr in self.sprites():
            new_rect = spr.rect.move(xx, yy)
            new_surfaces.append((spr.image, new_rect, gl(spr)))
            spritedict[spr] = new_rect

        dirty_ = self._map_layer.draw(surface, surface.get_rect(), new_surfaces)

        return dirty_
