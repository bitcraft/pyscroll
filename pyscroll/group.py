from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pygame.rect import Rect
from pygame.sprite import LayeredUpdates
from pygame.surface import Surface

from pyscroll.common import Vector2D

if TYPE_CHECKING:
    from pyscroll.orthographic import BufferedRenderer


@dataclass
class SpriteMeta:
    surface: Surface
    rect: Rect
    layer: int
    blendmode: Any = None


class PyscrollGroup(LayeredUpdates):
    """
    Layered Group with ability to center sprites and scrolling map.

    Args:
        map_layer: Pyscroll Renderer
    """

    def __init__(self, map_layer: BufferedRenderer, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._map_layer = map_layer

    def center(self, value: Vector2D) -> None:
        """
        Center the group/map on a pixel.

        The basemap and all sprites will be realigned to draw correctly.
        Centering the map will not change the rect of the sprites.

        Args:
            value: x, y coordinates to center the camera on
        """
        self._map_layer.center(value)

    @property
    def view(self) -> Rect:
        """
        Return a Rect representing visible portion of map.
        """
        return self._map_layer.view_rect.copy()

    def draw(self, surface: Surface) -> list[Rect]:
        """
        Draw map and all sprites onto the surface.

        Args:
            surface: Surface to draw to
        """
        ox, oy = self._map_layer.get_center_offset()
        draw_area = surface.get_rect()
        view_rect = self.view

        new_surfaces: list[SpriteMeta] = []
        spritedict = self.spritedict
        gl = self.get_layer_of_sprite

        for spr in self.sprites():
            new_rect = spr.rect.move(ox, oy)
            if spr.rect.colliderect(view_rect):
                blendmode = getattr(spr, "blendmode", None)
                new_surfaces.append(SpriteMeta(spr.image, new_rect, gl(spr), blendmode))
                spritedict[spr] = new_rect

        self.lostsprites = []

        # Convert dataclass back to tuple before drawing
        renderables: list[tuple[Surface, Rect, int, Any]] = [
            (meta.surface, meta.rect, meta.layer, meta.blendmode)
            for meta in new_surfaces
        ]
        return self._map_layer.draw(surface, draw_area, renderables)
