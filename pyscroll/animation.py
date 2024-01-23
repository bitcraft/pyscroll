from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple, Union

from pygame import Surface


class AnimationFrame(NamedTuple):
    image: Surface
    duration: float


TimeLike = Union[float, int]

__all__ = ("AnimationFrame", "AnimationToken")


class AnimationToken:
    __slots__ = ["_next", "positions", "frames", "index"]

    def __init__(
        self,
        positions: set[tuple[int, int, int]],
        frames: Sequence[AnimationFrame],
        initial_time: float = 0.0,
    ) -> None:
        """
        Constructor

        Args:
            positions: Set of positions where the tile is on the map
            frames: Sequence of frames that compromise the animation
            initial_time: Used to compensate time between starting and changing animations

        """
        frames = tuple(AnimationFrame(*i) for i in frames)
        self.positions = positions
        self.frames = frames
        self._next = frames[0].duration + initial_time
        self.index = 0

    def advance(self, last_time: TimeLike) -> AnimationFrame:
        """
        Advance the frame, and set timer for next frame

        Timer value is calculated by adding last_time and the
        duration of the next frame

        The next frame is returned

        * This API may change in the future

        Args:
            last_time: Duration of the last frame

        """
        # advance the animation frame index, looping by default
        if self.index == len(self.frames) - 1:
            self.index = 0
        else:
            self.index += 1

        # set the timer for the next advance
        next_frame = self.frames[self.index]
        self._next = next_frame.duration + last_time
        return next_frame

    def __lt__(self, other: AnimationToken) -> bool:
        return self._next < other._next
