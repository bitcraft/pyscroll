"""
Two classes for quadtree collision detection.

A quadtree is used with pyscroll to detect overlapping tiles.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional

from pygame.rect import Rect

if TYPE_CHECKING:
    from .common import RectLike


def get_rect(item) -> Rect:
    """Helper to consistently get a pygame.Rect from item."""
    return item.rect if hasattr(item, "rect") else item


class FastQuadTree:
    """
    An implementation of a quad-tree.

    This faster version of the quadtree class is tuned for pygame's rect
    objects, or objects with a rect attribute.  The return value will always
    be a set of a tuples that represent the items passed.  In other words,
    you will not get back the objects that were passed, just a tuple that
    describes it.

    Items being stored in the tree must be a pygame.Rect or have have a
    .rect (pygame.Rect) attribute that is a pygame.Rect

    original code from https://pygame.org/wiki/QuadTree
    """

    __slots__ = ["items", "cx", "cy", "nw", "sw", "ne", "se", "boundary"]

    def __init__(
        self, items: Sequence[Rect], depth: int = 4, boundary: Optional[RectLike] = None
    ) -> None:
        """Creates a quad-tree.

        Args:
            items: Sequence of items to check
            depth: The maximum recursion depth
            boundary: The bounding rectangle of all of the items in the quad-tree
        """
        if not items:
            raise ValueError("Items must not be empty")

        # Compute boundary if not provided
        rects = [get_rect(item) for item in items]
        boundary = Rect(boundary) if boundary else rects[0].unionall(rects[1:])

        self.cx, self.cy = boundary.centerx, boundary.centery
        self.boundary = boundary
        self.items: list[Rect] = []
        self.nw = self.ne = self.sw = self.se = None

        # Base case: store all in this node
        if depth <= 0:
            self.items = rects
            return

        # Partition items into sub-quadrants
        nw_items, ne_items, se_items, sw_items = [], [], [], []

        for rect in rects:
            in_nw = rect.left <= self.cx and rect.top <= self.cy
            in_sw = rect.left <= self.cx and rect.bottom >= self.cy
            in_ne = rect.right >= self.cx and rect.top <= self.cy
            in_se = rect.right >= self.cx and rect.bottom >= self.cy

            if in_nw and in_ne and in_se and in_sw:
                self.items.append(rect)
            else:
                if in_nw:
                    nw_items.append(rect)
                if in_ne:
                    ne_items.append(rect)
                if in_se:
                    se_items.append(rect)
                if in_sw:
                    sw_items.append(rect)

        # Recursive sub-quadrant initialization
        if nw_items:
            self.nw = FastQuadTree(
                nw_items, depth - 1, (boundary.left, boundary.top, self.cx, self.cy)
            )
        if ne_items:
            self.ne = FastQuadTree(
                ne_items, depth - 1, (self.cx, boundary.top, boundary.right, self.cy)
            )
        if se_items:
            self.se = FastQuadTree(
                se_items, depth - 1, (self.cx, self.cy, boundary.right, boundary.bottom)
            )
        if sw_items:
            self.sw = FastQuadTree(
                sw_items, depth - 1, (boundary.left, self.cy, self.cx, boundary.bottom)
            )

    def __iter__(self):
        return itertools.chain(
            self.items,
            self.nw or [],
            self.ne or [],
            self.se or [],
            self.sw or [],
        )

    def hit(self, rect: RectLike) -> set[tuple[int, int, int, int]]:
        """
        Returns the items that overlap a bounding rectangle.

        Returns the set of all items in the quad-tree that overlap with a
        bounding rectangle.

        Args:
            rect: The bounding rectangle being tested
        """
        if not isinstance(rect, Rect):
            rect = get_rect(rect)

        if not self.boundary.colliderect(rect):
            return set()

        # Check for collisions in this node
        hits = {tuple(item) for item in self.items if item.colliderect(rect)}

        # Check lower quadrants
        if rect.left <= self.cx:
            if rect.top <= self.cy and self.nw is not None:
                hits.update(self.nw.hit(rect))
            if rect.bottom >= self.cy and self.sw is not None:
                hits.update(self.sw.hit(rect))

        if rect.right >= self.cx:
            if rect.top <= self.cy and self.ne is not None:
                hits.update(self.ne.hit(rect))
            if rect.bottom >= self.cy and self.se is not None:
                hits.update(self.se.hit(rect))

        return hits
