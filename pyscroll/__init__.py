from contextlib import contextmanager

from pygame import Rect

__version__ = 2, 19, 2
__author__ = 'bitcraft'
__author_email__ = 'leif.theden@gmail.com'
__description__ = 'Pygame Scrolling - Python 2.7 & 3.3+'


@contextmanager
def surface_clipping_context(surface, clip):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


# TODO: C code
def rect_difference(a, b):
    """ Compute difference of two rects.  Returns up to 4.
    
    :type a: Rect
    :type b: Rect
    :rtype: list
    """
    raise NotImplementedError


def rect_to_bb(rect):
    x, y, w, h = rect
    return x, y, x + w - 1, y + h - 1


# convenience imports
from pyscroll.orthographic import BufferedRenderer
from pyscroll.isometric import IsometricBufferedRenderer
from .data import *
from .group import *
