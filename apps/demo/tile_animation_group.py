"""
Animated Tile Group Demo using Pygame and Pyscroll

This script displays a set of animated tokens on a Pygame window. Each token cycles
between colored frames to demonstrate tile-based animation using Pyscroll's animation
system.

Core features:
- Creates randomized token positions within the screen bounds
- Assigns each token a color-based animation sequence
- Continuously updates and renders tokens each frame
"""

import random

import pygame
from pygame.locals import QUIT

from pyscroll.animation import AnimationFrame, AnimationToken


def make_color_frames(colors, size=(32, 32), duration=0.4) -> list[AnimationFrame]:
    return [
        AnimationFrame(image=pygame.Surface(size).convert(), duration=duration)
        for color in colors
    ]


def create_tokens(count, tile_size, screen_size) -> list[AnimationToken]:
    tokens = []
    for _ in range(count):
        x = random.randint(0, screen_size[0] - tile_size)
        y = random.randint(0, screen_size[1] - tile_size)
        position = {(x, y, 0)}

        # Alternate colors for demonstration
        colors = [random.choice([(255, 0, 0), (0, 255, 0), (0, 0, 255)]), (0, 0, 0)]
        frames = [
            AnimationFrame(image=pygame.Surface((tile_size, tile_size)), duration=0.4)
            for color in colors
        ]
        for frame, color in zip(frames, colors):
            frame.image.fill(color)

        token = AnimationToken(position, frames, loop=True)
        tokens.append(token)
    return tokens


def main():
    pygame.init()
    screen_size = (640, 480)
    screen = pygame.display.set_mode(screen_size)
    pygame.display.set_caption("Animated Tile Group Demo")

    clock = pygame.time.Clock()
    tile_size = 32
    tokens = create_tokens(12, tile_size, screen_size)

    current_time = 0.0

    running = True
    while running:
        elapsed = clock.tick(60) / 1000.0
        current_time += elapsed

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        screen.fill((30, 30, 30))

        for token in tokens:
            frame = token.update(current_time, elapsed)
            for pos in token.positions:
                screen.blit(frame.image, (pos[0], pos[1]))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
