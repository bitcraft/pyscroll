from collections import namedtuple

__all__ = ('AnimationFrame', 'AnimationToken')

AnimationFrame = namedtuple("AnimationFrame", "image duration")


class AnimationToken(object):
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
