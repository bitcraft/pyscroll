"""
Simple Pygame animation demo using Pyscroll's AnimationToken

This script demonstrates how to animate a single tile on screen using
Pyscroll's AnimationFrame and AnimationToken classes. The tile alternates
between two colors in a loop and updates each frame at a fixed interval.

Purpose:
- Shows how to manually create animation frames using colored surfaces
- Illustrates how AnimationToken manages time-based frame transitions
"""

import pygame
from pygame.locals import QUIT

from pyscroll.animation import AnimationFrame, AnimationToken


def make_frames(color1, color2, size=(32, 32)) -> list[AnimationFrame]:
    surface1 = pygame.Surface(size)
    surface1.fill(color1)
    surface2 = pygame.Surface(size)
    surface2.fill(color2)
    return [
        AnimationFrame(image=surface1, duration=0.5),
        AnimationFrame(image=surface2, duration=0.5),
    ]


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((640, 480))
    pygame.display.set_caption("AnimationToken Demo")

    clock = pygame.time.Clock()

    # Create animation
    frames = make_frames((255, 0, 0), (0, 255, 0))
    positions = {(100, 100, 0)}
    anim = AnimationToken(positions, frames, loop=True)

    current_time = 0.0  # simulated time

    running = True
    while running:
        elapsed = clock.tick(60) / 1000.0  # Seconds per frame
        current_time += elapsed

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        screen.fill((30, 30, 30))

        # Update and draw current animation frame
        frame = anim.update(current_time, elapsed)
        screen.blit(frame.image, (100, 100))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
