from __future__ import annotations

from typing import TYPE_CHECKING, List

import pygame

if TYPE_CHECKING:
    from .orthographic import BufferedRenderer


class PyscrollGroup(pygame.sprite.LayeredUpdates):
    """
    Layered Group with ability to center sprites and scrolling map.

    Args:
        map_layer: Pyscroll Renderer

    """
    def __init__(
        self,
        map_layer: BufferedRenderer,
        *args,
        **kwargs
    ):
        pygame.sprite.LayeredUpdates.__init__(self, *args, **kwargs)
        self._map_layer = map_layer

    def center(self, value):
        """
        Center the group/map on a pixel.

        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.

        Args:
            value: x, y coordinates to center the camera on

        """
        self._map_layer.center(value)

    @property
    def view(self) -> pygame.Rect:
        """
        Return a Rect representing visible portion of map.

        """
        return self._map_layer.view_rect.copy()

    def draw(
        self,
        surface: pygame.surface.Surface
    ) -> List[pygame.rect.Rect]:
        """
        Draw map and all sprites onto the surface.

        Args:
            surface: Surface to draw to

        """
        ox, oy = self._map_layer.get_center_offset()
        draw_area = surface.get_rect()
        view_rect = self.view

        new_surfaces = list()
        spritedict = self.spritedict
        gl = self.get_layer_of_sprite
        new_surfaces_append = new_surfaces.append

        for spr in self.sprites():
            new_rect = spr.rect.move(ox, oy)
            if spr.rect.colliderect(view_rect):
                try:
                    new_surfaces_append((spr.image, new_rect, gl(spr), spr.blendmode))
                except AttributeError:
                    # should only fail when no blendmode available
                    new_surfaces_append((spr.image, new_rect, gl(spr)))
                spritedict[spr] = new_rect

        self.lostsprites = []
        return self._map_layer.draw(surface, draw_area, new_surfaces)
