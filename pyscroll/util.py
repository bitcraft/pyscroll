import pygame


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

        new_surfaces = []
        for spr in self.sprites():
            new_rect = spr.rect.move(xx, yy)
            new_surfaces.append((spr.image, new_rect, 1))
            spritedict[spr] = new_rect

        dirty_ = self._map_layer.draw(surface, surface.get_rect(), new_surfaces)

        return dirty_