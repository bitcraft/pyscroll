"""
Copyright (C) 2012-2016

This file is part of pyscroll.

pyscroll is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pyscroll is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pyscroll.  If not, see <http://www.gnu.org/licenses/>.
"""
from contextlib import contextmanager

__version__ = '2.16.11'
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
try:
    from pyscroll.orthographic import BufferedRenderer
    from pyscroll.isometric import IsometricBufferedRenderer
except ImportError:
    pass

try:
    from pyscroll.texture import TextureRenderer
except ImportError:
    pass

from .data import *
# from .group import *
