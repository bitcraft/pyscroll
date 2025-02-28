"""
Two classes for quadtree collision detection.

A quadtree is used with pyscroll to detect overlapping tiles.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pygame import Rect

if TYPE_CHECKING:
    from .common import RectLike


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

    def __init__(self, items: Sequence[Rect], depth: int = 4, boundary=None) -> None:
        """Creates a quad-tree.

        Args:
            items: Sequence of items to check
            depth: The maximum recursion depth
            boundary: The bounding rectangle of all of the items in the quad-tree

        """
        if not items:
            raise ValueError("Items must not be empty")

        # The sub-quadrants are empty to start with.
        self.nw = self.ne = self.se = self.sw = None

        # Find this quadrant's centre and if there isn't a bounding rect, then
        # calculate it from the items.
        self.nw = self.ne = self.se = self.sw = None
        boundary = Rect(boundary) if boundary else Rect(items[0]).unionall(items[1:])

        self.cx = boundary.centerx
        self.cy = boundary.centery
        self.boundary = boundary

        # If we've reached the maximum depth then insert all items into this
        # quadrant.
        if depth <= 0:
            self.items = items
            return

        self.items = []
        nw_items, ne_items, se_items, sw_items = [], [], [], []

        for item in items:
            # Which of the sub-quadrants does the item overlap?
            in_nw = item.left <= self.cx and item.top <= self.cy
            in_sw = item.left <= self.cx and item.bottom >= self.cy
            in_ne = item.right >= self.cx and item.top <= self.cy
            in_se = item.right >= self.cx and item.bottom >= self.cy

            # If it overlaps all 4 quadrants then insert it at the current
            # depth, otherwise append it to a list to be inserted under every
            # quadrant that it overlaps.
            if in_nw and in_ne and in_se and in_sw:
                self.items.append(item)
            else:
                if in_nw:
                    nw_items.append(item)
                if in_ne:
                    ne_items.append(item)
                if in_se:
                    se_items.append(item)
                if in_sw:
                    sw_items.append(item)

        # Create the sub-quadrants, recursively.
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
            self.nw if self.nw else [],
            self.ne if self.ne else [],
            self.se if self.se else [],
            self.sw if self.sw else [],
        )

    def hit(self, rect: RectLike) -> set[tuple[int, int, int, int]]:
        """
        Returns the items that overlap a bounding rectangle.

        Returns the set of all items in the quad-tree that overlap with a
        bounding rectangle.

        Args:
            rect: The bounding rectangle being tested

        """
        if not self.boundary.colliderect(rect):
            return set()

        # Find the hits at the current level.
        hits = {tuple(self.items[i]) for i in rect.collidelistall(self.items)}

        # Recursively check the lower quadrants.
        if rect.left <= self.cx:
            if rect.top <= self.cy and self.nw:
                hits.update(self.nw.hit(rect))
            if rect.bottom >= self.cy and self.sw:
                hits.update(self.sw.hit(rect))
        if rect.right >= self.cx:
            if rect.top <= self.cy and self.ne:
                hits.update(self.ne.hit(rect))
            if rect.bottom >= self.cy and self.se:
                hits.update(self.se.hit(rect))

        return hits
