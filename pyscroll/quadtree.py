"""
Module contains two classes for quadtree collision detection.

In Lib2d, they are used in various parts in rendering and collision detection
between 'sprites' and world geometry.

It is important to remember that once the quadtree's are useful for static
objects (which is why it is being used for world geometry).  There are
probably better solutions for moving objects.
"""


from pygame import Rect
import itertools


class FrozenRect(object):
    """
    This rect is hashable, unlike normal pygame rects
    contains a reference to another object
    """

    __slots__ = ['_left', '_top', '_width', '_height', '_value']

    def __init__(self, rect, value=None):
        self._left, self._top, self._width, self._height = rect
        self._value = value

    def __len__(self): return 4

    def __getitem__(self, key):
        if key == 0:
            return self._left
        elif key == 1:
            return self._top
        elif key == 2:
            return self._width
        elif key == 3:
            return self._height
        raise IndexError

    @property
    def value(self): return self._value

    @property
    def left(self): return self._left

    @property
    def top(self): return self._top

    @property
    def widht(self): return self._width

    @property
    def height(self): return self._height

    @property
    def right(self): return self._left + self._width

    @property
    def bottom(self): return self._top + self._height

    def __iter__(self):
        return iter([self._left, self._top, self._width, self._height])


# from http://pygame.org/wiki/QuadTree

class FastQuadTree(object):
    """An implementation of a quad-tree.
 
    This faster version of the quadtree class is tuned for pygame's rect
    objects, or objects with a rect attribute.  The return value will always
    be a set of a tupes that represent the items passed.  In other words,
    you will not get back the objects that were passed, just a tuple that
    describes it.

    Items being stored in the tree must be a pygame.Rect or have have a
    .rect (pygame.Rect) attribute that is a pygame.Rect
        ...and they must be hashable.
    """

    __slots__ = ['items', 'cx', 'cy', 'nw', 'sw', 'ne', 'se']
 
    def __init__(self, items, depth=4, bounding_rect=None):
        """Creates a quad-tree.
 
        @param items:
            A sequence of items to store in the quad-tree. Note that these
            items must be a pygame.Rect or have a .rect attribute.
            
        @param depth:
            The maximum recursion depth.
            
        @param bounding_rect:
            The bounding rectangle of all of the items in the quad-tree. For
            internal use only.
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
        if bounding_rect:
            bounding_rect = Rect( bounding_rect )
        else:
            # If there isn't a bounding rect, then calculate it from the items.
            bounding_rect = Rect( items[0] )
            for item in items[1:]:
                bounding_rect.union_ip( item )
        cx = self.cx = bounding_rect.centerx
        cy = self.cy = bounding_rect.centery
 
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
            self.nw = FastQuadTree(nw_items, depth, \
                      (bounding_rect.left, bounding_rect.top, cx, cy))
 
        if ne_items:
            self.ne = FastQuadTree(ne_items, depth, \
                      (cx, bounding_rect.top, bounding_rect.right, cy))

        if se_items:
            self.se = FastQuadTree(se_items, depth, \
                      (cx, cy, bounding_rect.right, bounding_rect.bottom))
  
        if sw_items:
            self.sw = FastQuadTree(sw_items, depth, \
                      (bounding_rect.left, cy, cx, bounding_rect.bottom))

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
        hits = set(tuple(self.items[i])
                   for i in rect.collidelistall(self.items))

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


class QuadTree(object):
    """Another implementation of a quad-tree.

    This is a slower, but more featured quadtree class for collision detection.
    Arbitrary objects may be passed as long as they have a top, left, bottom,
    and right attribute.

    When queried, the quadtree will return the objects that collide with the
    rect passed.
    """

    __slots__ = ['items', 'cx', 'cy', 'nw', 'sw', 'ne', 'se']

    def __init__(self, items, depth=4, bounding_rect=None):
        """Creates a quad-tree.

        @param items:
            A sequence of items to store in the quad-tree. Note that these
            items must possess left, top, right and bottom attributes.
            
        @param depth:
            The maximum recursion depth.
            
        @param bounding_rect:
            The bounding rectangle of all of the items in the quad-tree. For
            internal use only.
        """
        # The sub-quadrants are empty to start with.
        self.nw = self.ne = self.se = self.sw = None
        
        # If we've reached the maximum depth then insert all items into this
        # quadrant.
        depth -= 1
        if depth == 0:
            self.items = items
            return

        # Find this quadrant's centre.
        if bounding_rect:
            l, t, r, b = bounding_rect
        else:
            # If there isn't a bounding rect, then calculate it from the items.
            l = min(item.left for item in items)
            t = min(item.top for item in items)
            r = max(item.right for item in items)
            b = max(item.bottom for item in items)

        cx = self.cx = (l + r) * 0.5
        cy = self.cy = (t + b) * 0.5
        
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
        if nw_items: self.nw = QuadTree(nw_items, depth, (l, t, cx, cy))
        if ne_items: self.ne = QuadTree(ne_items, depth, (cx, t, r, cy))
        if se_items: self.se = QuadTree(se_items, depth, (cx, cy, r, b))
        if sw_items: self.sw = QuadTree(sw_items, depth, (l, cy, cx, b))


    def hit(self, rect):
        """Returns the items that overlap a bounding rectangle.

        Returns the set of all items in the quad-tree that overlap with a
        bounding rectangle.
        
        @param rect:
            The bounding rectangle being tested against the quad-tree. This
            must possess left, top, right and bottom attributes.
        """
        def overlaps(item):
            return rect.right >= item.left and rect.left <= item.right and \
                   rect.bottom >= item.top and rect.top <= item.bottom
        
        # Find the hits at the current level.
        hits = set(item for item in self.items if overlaps(item))
        
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



