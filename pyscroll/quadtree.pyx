"""
Two classes for quadtree collision detection.

A quadtree is used with pyscroll to detect overlapping tiles.
"""
import itertools
from pygame import Rect


class FastQuadTree(object):
    """An implementation of a quad-tree.

    This faster version of the quadtree class is tuned for pygame's rect
    objects, or objects with a rect attribute.  The return value will always
    be a set of a tupes that represent the items passed.  In other words,
    you will not get back the objects that were passed, just a tuple that
    describes it.

    Items being stored in the tree must be a pygame.Rect or have have a
    .rect (pygame.Rect) attribute that is a pygame.Rect

    original code from http://pygame.org/wiki/QuadTree
    """

    __slots__ = ['items', 'cx', 'cy', 'nw', 'sw', 'ne', 'se']

    def __init__(self, items, depth=4, boundary=None):
        """Creates a quad-tree.

        @param items:
            A sequence of items to store in the quad-tree. Note that these
            items must be a pygame.Rect or have a .rect attribute.

        @param depth:
            The maximum recursion depth.

        @param boundary:
            The bounding rectangle of all of the items in the quad-tree.
        """

        # The sub-quadrants are empty to start with.
        self.nw = self.ne = self.se = self.sw = None

        # If we've reached the maximum depth then insert all items into this
        # quadrant.
        depth -= 1
        if depth == 0 or not items:
            self.items = items
            return

        # Find this quadrant's centre.
        if boundary:
            boundary = Rect(boundary)
        else:
            # If there isn't a bounding rect, then calculate it from the items.
            boundary = Rect(items[0]).unionall(items[1:])

        cx = self.cx = boundary.centerx
        cy = self.cy = boundary.centery

        self.items = []
        nw_items = []
        ne_items = []
        se_items = []
        sw_items = []

        for item in items:
            # Which of the sub-quadrants does the item overlap?
            in_nw = item.left <= cx and item.top <= cy
            in_sw = item.left <= cx and item.bottom >= cy
            in_ne = item.right >= cx and item.top <= cy
            in_se = item.right >= cx and item.bottom >= cy

            # If it overlaps all 4 quadrants then insert it at the current
            # depth, otherwise append it to a list to be inserted under every
            # quadrant that it overlaps.
            if in_nw and in_ne and in_se and in_sw:
                self.items.append(item)
            else:
                if in_nw: nw_items.append(item)
                if in_ne: ne_items.append(item)
                if in_se: se_items.append(item)
                if in_sw: sw_items.append(item)

        # Create the sub-quadrants, recursively.
        if nw_items:
            self.nw = FastQuadTree(nw_items, depth,
                                   (boundary.left, boundary.top, cx, cy))

        if ne_items:
            self.ne = FastQuadTree(ne_items, depth,
                                   (cx, boundary.top, boundary.right, cy))

        if se_items:
            self.se = FastQuadTree(se_items, depth,
                                   (cx, cy, boundary.right, boundary.bottom))

        if sw_items:
            self.sw = FastQuadTree(sw_items, depth,
                                   (boundary.left, cy, cx, boundary.bottom))

    def __iter__(self):
        return itertools.chain(self.items, self.nw, self.ne, self.se, self.sw)

    def hit(self, rect):
        """Returns the items that overlap a bounding rectangle.

        Returns the set of all items in the quad-tree that overlap with a
        bounding rectangle.

        @param rect:
            The bounding rectangle being tested against the quad-tree. This
            must possess left, top, right and bottom attributes.
        """

        # Find the hits at the current level.
        hits = {tuple(self.items[i]) for i in rect.collidelistall(self.items)}

        # Recursively check the lower quadrants.
        if self.nw and rect.left <= self.cx and rect.top <= self.cy:
            hits |= self.nw.hit(rect)
        if self.sw and rect.left <= self.cx and rect.bottom >= self.cy:
            hits |= self.sw.hit(rect)
        if self.ne and rect.right >= self.cx and rect.top <= self.cy:
            hits |= self.ne.hit(rect)
        if self.se and rect.right >= self.cx and rect.bottom >= self.cy:
            hits |= self.se.hit(rect)

        return hits
