# -*- coding: utf-8 -*-
"""
Copyright (C) 2012-2016

This file is part of mason.

mason is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

mason is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with mason.  If not, see <http://www.gnu.org/licenses/>.
"""
from __future__ import absolute_import

from itertools import product

__version__ = '3.0.0'
__author__ = 'bitcraft'
__author_email__ = 'leif.theden@gmail.com'
__description__ = 'Pygame Scrolling - Python 2.7 & 3.3+'


def butter(tile_size, top_layer, offset=None):
    """ Spread out the rect dimensions so it aligns with the tile grid

    The result will never be smaller than the input, and will always contain it.

    Returns dimensions suitable for AABB
    """
    from math import ceil

    tw, th = tile_size

    if offset is None:
        left, top = 0, 0
    else:
        left, top = offset

    def func(rect, sprite_layer):
        # convert screen coords to tile coords
        # truncate/round down the left/top edge
        x1 = int((rect.left // tw) + left)
        y1 = int((rect.top // th) + top)

        # round up the right/bottom edges
        x2 = int(ceil(rect.right / float(tw)) + left - 1)
        y2 = int(ceil(rect.bottom / float(th)) + top - 1)

        return x1, y1, int(sprite_layer + 1), x2, y2, top_layer

    return func


def rev(seq, start, stop):
    if start < 0:
        start = 0
    return enumerate(seq[start:stop + 1], start)


def snapper(interval):
    def snap(value):
        return round(value / interval) * interval

    return snap


def rectifier(width, height):
    def rectify(x, y):
        return Rect(x * width, y * height, width, height)

    return rectify


def rect_to_bb(rect):
    x, y, w, h = rect
    return x, y, x + w - 1, y + h - 1


def range_product(*r):
    return product(*[range(i) for i in r])


# convenience imports
from .data import *
from .compat import Rect

# from .group import *

try:
    from mason.platform.graphics_pygame import PygameGraphics
    from mason.bond.isometric import IsometricBufferedRenderer
except ImportError:
    pass

try:
    from mason.platform.graphics_pysdl2cffi import GraphicsPysdl2cffi
except ImportError:
    pass
