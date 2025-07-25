from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Set, Tuple, Union

from pygame import Surface

TimeLike = Union[float, int]

__all__ = ("AnimationFrame", "AnimationToken")


@dataclass(frozen=True)
class AnimationFrame:
    """
    Represents a single frame in an animation.

    Attributes:
        image: The image surface to display.
        duration: Duration this frame should be shown, in seconds.
    """

    image: Surface
    duration: float


class AnimationToken:
    """
    Manages tile-based animation logic including frame timing, looping, and updates.

    Attributes:
        positions: Set of (x, y, layer) map coordinates where this animation is active.
        frames: Tuple of AnimationFrame instances.
        index: Current frame index.
        next: Time value when the next frame should appear.
        loop: If True, animation loops; if False, plays once.
        done: Indicates whether a non-looping animation has completed.
    """

    __slots__ = ("positions", "frames", "next", "index", "loop", "done")

    def __init__(
        self,
        positions: Set[Tuple[int, int, int]],
        frames: Sequence[AnimationFrame],
        initial_time: float = 0.0,
        loop: bool = True,
    ) -> None:
        """
        Initializes an AnimationToken instance.

        Args:
            positions: Set of map positions for the animation tile.
            frames: Sequence of AnimationFrame instances.
            initial_time: Optional time offset for smoother transitions.
            loop: If False, the animation stops at the last frame.

        Raises:
            ValueError: If the frames sequence is empty.
        """
        if not frames:
            raise ValueError("Frames sequence cannot be empty.")

        self.positions = positions
        self.frames = tuple(frames)
        self.index = 0
        self.next = self.frames[0].duration + initial_time
        self.loop = loop
        self.done = False

    def advance(self, last_time: TimeLike) -> AnimationFrame:
        """
        Advances to the next frame in the animation sequence.

        Args:
            last_time: Time since the last frame update.

        Returns:
            The next AnimationFrame in the sequence.
        """
        if self.done:
            return self.frames[self.index]

        if self.index == len(self.frames) - 1:
            if self.loop:
                self.index = 0
            else:
                self.done = True
        else:
            self.index += 1

        next_frame = self.frames[self.index]
        self.next = next_frame.duration + last_time
        return next_frame

    def update(self, current_time: TimeLike, elapsed_time: TimeLike) -> AnimationFrame:
        """
        Updates the animation frame based on simulated elapsed time.

        Args:
            current_time: The current time used to evaluate frame progression.
            elapsed_time: Simulated time passed since last update.

        Returns:
            The active AnimationFrame.
        """
        if self.done:
            return self.frames[self.index]

        while current_time >= self.next:
            self.advance(self.next)
            current_time -= elapsed_time
        return self.frames[self.index]

    def __lt__(self, other: Union[AnimationToken, float, int]) -> bool:
        """
        Compares this token's next frame time with another.

        Args:
            other: Another AnimationToken or time value.

        Returns:
            True if this token's next frame time is earlier.
        """
        try:
            return self.next < other.next
        except AttributeError:
            return self.next < other

    def __repr__(self) -> str:
        return f"AnimationToken(positions={self.positions}, frames={self.frames})"
