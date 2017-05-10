from collections import namedtuple

__all__ = ('AnimationFrame', 'AnimationToken')

AnimationFrame = namedtuple("AnimationFrame", "image duration")


class AnimationToken(object):
    __slots__ = ['next', 'positions', 'frames', 'index']

    def __init__(self, positions, frames, initial_time=0):
        """

        :type frames: list
        :type positions: set
        :type initial_time: int 
        """
        frames = tuple(AnimationFrame(*i) for i in frames)
        self.positions = positions
        self.frames = frames
        self.next = frames[0].duration + initial_time
        self.index = 0

    def advance(self, last_time):
        """ Advance the frame, and set timer for next frame
        
        Timer value is calculated by adding last_time and the
        duration of the next frame
        
        The next frame is returned
        
        This API may change in the future
        
        :param last_time: 
        :return: Animation Frame
        """
        # advance the animation frame index, looping by default
        if self.index == len(self.frames) - 1:
            self.index = 0
        else:
            self.index += 1

        # set the timer for the next advance
        next_frame = self.frames[self.index]
        self.next = next_frame.duration + last_time
        return next_frame

    def __lt__(self, other):
        try:
            return self.next < other.next
        except AttributeError:
            return self.next < other
