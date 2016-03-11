from contextlib import contextmanager

__version__ = '2.16.6'
__author__ = 'bitcraft'
__author_email__ = 'leif.theden@gmail.com'
__description__ = 'Pygame Scrolling - Python 2.7 & 3.3+'


@contextmanager
def surface_clipping_context(surface, clip):
    original = surface.get_clip()
    surface.set_clip(clip)
    yield
    surface.set_clip(original)


def rect_to_bb(rect):
    x, y, w, h = rect
    return x, y, x + w - 1, y + h - 1


# convenience imports
from pyscroll.orthographic import BufferedRenderer
from pyscroll.isometric import IsometricBufferedRenderer
from .data import *
from .group import *
