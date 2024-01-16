from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Union

from pygame import Rect, Surface, Vector2

RectLike = Union[Rect, tuple[Any, Any, Any, Any]]
Vector2D = Union[tuple[float, float], tuple[int, int], Vector2]
Vector2DInt = tuple[int, int]


@contextmanager
def surface_clipping_context(surface: Surface, clip: RectLike):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


def rect_difference(a: RectLike, b: RectLike) -> list[Rect]:
    """
    Compute difference of two rects.  Returns up to 4.

    """
    raise NotImplementedError


def rect_to_bb(rect: RectLike) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    return x, y, x + w - 1, y + h - 1
