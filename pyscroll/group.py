import pygame

__all__ = ('PyscrollGroup',)


class PyscrollGroup(pygame.sprite.LayeredUpdates):
    """ Layered Group with ability to center sprites and scrolling map
    """

    def __init__(self, *args, **kwargs):
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        self._map_layer = kwargs.get('map_layer')
        self._center = 0, 0

    def center(self, value):
        """ Center the group/map on a pixel

        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.
        """
        self._map_layer.center(value)
        self._center = value

    def draw(self, surface):
        """ Draw all sprites and map onto the surface

        Group.draw(surface): return None
        Draws all of the member sprites onto the given surface.
        """
        ox, oy = self._map_layer.get_center_offset()

        new_surfaces = list()
        spritedict = self.spritedict
        gl = self.get_layer_of_sprite
        new_surfaces_append = new_surfaces.append

        for spr in self.sprites():
            new_rect = spr.rect.move(ox, oy)
            new_surfaces_append((spr.image, new_rect, gl(spr)))
            spritedict[spr] = new_rect

        return self._map_layer.draw(surface, surface.get_rect(), new_surfaces)
