"""
FastQuadTree Hit Pattern Visualizer

This standalone script provides a visual, interactive demonstration of how
FastQuadTree spatial queries work. It generates a random set of rectangles
across a 2D screen, builds a FastQuadTree index, and displays:
- The fixed query rectangle (blue)
- Tile rectangles (gray)
- Hit results from the query (red outlines)

Users can toggle hit visibility using the [H] key and observe spatial
distribution and query precision.

Features:
- Adjustable depth, tile size, and rectangle count via configuration variables
- Visual feedback for hit detection
- Overlay stats to track hit count live
"""

import random

import pygame
from pygame.rect import Rect

from pyscroll.quadtree import FastQuadTree

# Configuration
SCREEN_SIZE = (800, 600)
TILE_SIZE = (32, 32)
RECT_COUNT = 1000
DEPTH = 3
QUERY_RECT = Rect(400, 300, 64, 64)
FPS = 30


def generate_tile_rects(n, bounds=(0, 0, 800, 600), tile_size=(32, 32)) -> list[Rect]:
    x0, y0, w, h = bounds
    tw, th = tile_size
    return [
        Rect(random.randint(x0, x0 + w - tw), random.randint(y0, y0 + h - th), tw, th)
        for _ in range(n)
    ]


def main():
    pygame.init()
    screen = pygame.display.set_mode(SCREEN_SIZE)
    pygame.display.set_caption("FastQuadTree Hit Pattern Visualizer")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 24)

    # Generate tiles and build quadtree
    tile_rects = generate_tile_rects(
        RECT_COUNT, bounds=(0, 0, *SCREEN_SIZE), tile_size=TILE_SIZE
    )
    tree = FastQuadTree(tile_rects, depth=DEPTH)

    running = True
    show_hits = True

    while running:
        screen.fill((30, 30, 30))  # Dark background

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:  # Toggle hit visibility
                    show_hits = not show_hits

        # Draw all rectangles (gray)
        for rect in tile_rects:
            pygame.draw.rect(screen, (120, 120, 120), rect, 1)

        # Draw query rect (blue)
        pygame.draw.rect(screen, (0, 128, 255), QUERY_RECT, 2)

        # Draw hits (red)
        hits = tree.hit(QUERY_RECT)
        if show_hits:
            for hit_rect in hits:
                pygame.draw.rect(screen, (255, 0, 0), hit_rect, 2)

        # Info overlay
        text = font.render(
            f"Hits: {len(hits)}  |  Press [H] to toggle hits", True, (240, 240, 240)
        )
        screen.blit(text, (10, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
