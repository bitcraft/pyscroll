import pygame

__all__ = ('PyscrollGroup',)


class PyscrollGroup(pygame.sprite.LayeredUpdates):
    """ Layered Group with ability to center sprites and scrolling map
    """

    def __init__(self, *args, **kwargs):
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        self._map_layer = kwargs.get('map_layer')

    def center(self, value):
        """ Center the group/map on a pixel

        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.

        :param value: x, y coordinates to center the camera on
        """
        self._map_layer.center(value)

    @property
    def view(self):
        """ Return a Rect representing visible portion of map

        This rect can be modified, but will not change the renderer

        :return: pygame.Rect
        """
        return self._map_layer.view_rect.copy()

    def draw(self, surface):
        """ Draw all sprites and map onto the surface

        :param surface: pygame surface to draw to
        :type surface: pygame.surface.Surface
        """
        ox, oy = self._map_layer.get_center_offset()

        new_surfaces = list()
        spritedict = self.spritedict
        gl = self.get_layer_of_sprite
        new_surfaces_append = new_surfaces.append

        for spr in self.sprites():
            new_rect = spr.rect.move(ox, oy)
            try:
                new_surfaces_append((spr.image, new_rect, gl(spr), spr.blendmode))
            except AttributeError:  # generally should only fail when no blendmode available
                new_surfaces_append((spr.image, new_rect, gl(spr)))
            spritedict[spr] = new_rect

        self.lostsprites = []
        return self._map_layer.draw(surface, surface.get_rect(), new_surfaces)
