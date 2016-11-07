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
from collections import namedtuple

__all__ = ('AnimationFrame', 'AnimationEvent')

AnimationFrame = namedtuple("AnimationFrame", "image duration")


class AnimationEvent(object):
    __slots__ = ['next', 'gid', 'frames', 'index']

    def __init__(self, gid, frames):
        frames = tuple(AnimationFrame(*i) for i in frames)
        self.next = frames[0].duration
        self.gid = gid
        self.frames = frames
        self.index = 0

    def __lt__(self, other):
        try:
            return self.next < other.next
        except AttributeError:
            return self.next < other
