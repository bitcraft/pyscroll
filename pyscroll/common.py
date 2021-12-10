from __future__ import annotations

from contextlib import contextmanager
from typing import Any, List, Tuple, Union

from pygame import Rect, Surface, Vector2

RectLike = Union[Rect, Tuple[Any, Any, Any, Any]]
Vector2D = Union[Tuple[float, float], Tuple[int, int], Vector2]
Vector2DInt = Tuple[int, int]


@contextmanager
def surface_clipping_context(surface: Surface, clip: RectLike):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


def rect_difference(a: RectLike, b: RectLike) -> List[Rect]:
    """
    Compute difference of two rects.  Returns up to 4.

    """
    raise NotImplementedError


def rect_to_bb(rect: RectLike) -> Tuple[int, int, int, int]:
    x, y, w, h = rect
    return x, y, x + w - 1, y + h - 1
