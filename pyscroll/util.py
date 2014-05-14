import pygame
import pygame.gfxdraw

__all__ = ['PyscrollGroup', 'draw_shapes']


def draw_shapes(tmx_data):
    """ create a new tile layer from a shape layer
    totally not working
    """
    import itertools
    import pytmx
    import array

    cache = []

    def check_cache(surface, gid):
        def compare(s0, s1):
            return s0 == s1

        for other in cache:
            h = hash(pygame.image.tostring(surface, 'RGB'))
            if compare(surface, other[0]):
                return other

        cache.append((surface, gid))
        return surface, gid

    colorkey = (255, 0, 255)

    size = (int(tmx_data.width * tmx_data.tilewidth),
            int(tmx_data.height * tmx_data.tileheight))

    tw, th = tmx_data.tilewidth, tmx_data.tileheight

    surface = pygame.Surface(size)
    surface.fill(colorkey)
    surface.set_colorkey(colorkey)

    TEXTURE = tmx_data.images[2]

    for layer in tmx_data.objectgroups:
        draw(surface, tmx_data, *layer)
        for o in layer:
            if hasattr(o, 'points'):
                if o.closed:
                    pygame.gfxdraw.textured_polygon(surface, o.points, TEXTURE,
                                                    tw, th)
                else:
                    pygame.draw.lines(surface, (255, 128, 128), o.closed,
                                      o.points, 2)
            elif o.gid:
                tile = tmx_data.getTileImageByGid(o.gid)
                if tile:
                    surface.blit(tile, (o.x, o.y))
            else:
                pygame.draw.rect(surface, (255, 128, 128),
                                 (o.x, o.y, o.width, o.height), 2)

        p = itertools.product(range(tmx_data.height),
                              range(tmx_data.width))

        new_layer = pytmx.TiledLayer()
        new_layer.visible = 1
        new_layer.data = tuple(array.array('H', [0] * tmx_data.width)
                               for i in range(tmx_data.height))

        tmx_data.addTileLayer(new_layer)

        for y, x in p:
            gid = len(tmx_data.images)
            original = surface.subsurface(((x * tw, y * th), (tw, th)))
            tile, gid = check_cache(original, gid)
            if original is tile:
                gid = tmx_data.register_gid(gid)
                tile = tile.convert()
                tmx_data.images.append(tile)

            new_layer.data[y][x] = gid


class PyscrollGroup(pygame.sprite.LayeredUpdates):
    """ Layered Group with ability to center sprites and scrolling map
    """
    def __init__(self, *args, **kwargs):
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        self._map_layer = kwargs.get('map_layer')

    def update(self, dt):
        pygame.sprite.LayeredUpdates.update(self, dt)
        self._map_layer.update(dt)

    def center(self, value):
        """ Center the group/map on a pixel

        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.
        """
        self._map_layer.center(value)

    def draw(self, surface):
        """ Draw all sprites and map onto the surface

        Group.draw(surface): return None
        Draws all of the member sprites onto the given surface.
        """
        xx = -self._map_layer.old_x + self._map_layer.half_width
        yy = -self._map_layer.old_y + self._map_layer.half_height

        new_surfaces = []
        spritedict = self.spritedict
        gl = self.get_layer_of_sprite
        new_surfaces_append = new_surfaces.append

        for spr in self.sprites():
            new_rect = spr.rect.move(xx, yy)
            new_surfaces_append((spr.image, new_rect, gl(spr)))
            spritedict[spr] = new_rect

        _dirty = self._map_layer.draw(surface, surface.get_rect(), new_surfaces)

        return _dirty
