"""
Performance Benchmark: FastQuadTree vs Brute-force Collision Detection

This script compares the speed and efficiency of two collision detection
methods in a 2D space:
1. FastQuadTree - a spatial partitioning structure optimized for querying
    rectangular areas.
2. Brute-force - a simple approach that checks every rectangle for intersection.

Features:
- Generates a random set of rectangular objects within a defined area.
- Performs repeated collision queries using both methods.
- Measures and prints build/setup time and query time for each method.
"""

import random
import timeit

from pygame.rect import Rect

from pyscroll.quadtree import FastQuadTree


def generate_rects(n, bounds=(0, 0, 800, 600), tile_size=(32, 32)) -> list[Rect]:
    x0, y0, w, h = bounds
    tw, th = tile_size
    return [
        Rect(random.randint(x0, x0 + w - tw), random.randint(y0, y0 + h - th), tw, th)
        for _ in range(n)
    ]


def brute_force_hit(items: list[Rect], target: Rect) -> list[Rect]:
    return [r for r in items if r.colliderect(target)]


def benchmark(item_count=5000, query_count=1000, depth=4):
    print(f"\nBenchmark: {item_count} rects, {query_count} queries, depth={depth}")

    # Generate test data
    items = generate_rects(item_count)
    test_rect = Rect(400, 300, 64, 64)

    # Benchmark Quadtree
    start = timeit.default_timer()
    tree = FastQuadTree(items, depth=depth)
    build_time = timeit.default_timer() - start

    start = timeit.default_timer()
    for _ in range(query_count):
        tree.hit(test_rect)
    quadtree_query_time = timeit.default_timer() - start

    # Benchmark Brute-force
    start = timeit.default_timer()
    for _ in range(query_count):
        brute_force_hit(items, test_rect)
    brute_query_time = timeit.default_timer() - start

    print(
        f"FastQuadTree:\n  Build Time:  {build_time:.6f}s\n  Query Time:  {quadtree_query_time:.6f}s"
    )
    print(
        f"Brute-force:\n  Setup Time:  negligible\n  Query Time:  {brute_query_time:.6f}s\n"
    )


if __name__ == "__main__":
    benchmark()
