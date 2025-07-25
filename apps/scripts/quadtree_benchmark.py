"""
FastQuadTree Depth Benchmarking Script

This tool evaluates how varying the depth of the FastQuadTree affects build and
query performance for spatial collision detection on 2D rectangular tiles.

Features:
- Randomly generates a set of rectangular tiles within a defined bounding box.
- Builds a FastQuadTree structure using a configurable depth parameter.
- Runs multiple spatial queries to check which tiles intersect a test rectangle.
- Measures and prints build time and total query time across a range of depths.

Usage:
Run the script with optional CLI arguments:
  --min-depth     Minimum quadtree depth to test (default: 2)
  --max-depth     Maximum quadtree depth to test (default: 6)
  --items         Number of rectangles to generate (default: 5000)
  --queries       Number of queries to perform per depth level (default: 1000)

This is useful for profiling and tuning FastQuadTree performance across different
configurations.
"""

import random
import timeit
from argparse import ArgumentParser

from pygame.rect import Rect

from pyscroll.quadtree import FastQuadTree


def generate_tile_rects(n, bounds=(0, 0, 800, 600), tile_size=(32, 32)) -> list[Rect]:
    x0, y0, w, h = bounds
    tw, th = tile_size
    return [
        Rect(random.randint(x0, x0 + w - tw), random.randint(y0, y0 + h - th), tw, th)
        for _ in range(n)
    ]


def run_benchmark(
    depth: int, item_count: int, query_count: int, tile_size=(32, 32)
) -> dict:
    items = generate_tile_rects(item_count, tile_size=tile_size)

    # Measure build time
    start_build = timeit.default_timer()
    tree = FastQuadTree(items, depth=depth)
    build_time = timeit.default_timer() - start_build

    # Measure query time
    test_rect = Rect(400, 300, tile_size[0] * 2, tile_size[1] * 2)
    start_query = timeit.default_timer()
    for _ in range(query_count):
        tree.hit(test_rect)
    query_time = timeit.default_timer() - start_query

    return {
        "depth": depth,
        "items": item_count,
        "queries": query_count,
        "build_time": build_time,
        "query_time": query_time,
    }


def main():
    parser = ArgumentParser(description="FastQuadTree depth benchmark")
    parser.add_argument("--min-depth", type=int, default=2)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--items", type=int, default=5000)
    parser.add_argument("--queries", type=int, default=1000)
    args = parser.parse_args()

    results = []
    for depth in range(args.min_depth, args.max_depth + 1):
        result = run_benchmark(depth, args.items, args.queries)
        results.append(result)

    print("\nBenchmark Configuration:")
    print(f"  Items     : {args.items}")
    print(f"  Queries   : {args.queries}")
    print(f"  Min Depth : {args.min_depth}")
    print(f"  Max Depth : {args.max_depth}")

    print("\nFastQuadTree Benchmark Results")
    print(f"{'Depth':>5} | {'Build (s)':>10} | {'Query (s)':>10}")
    print("-" * 32)
    for r in results:
        print(f"{r['depth']:>5} | {r['build_time']:.6f} | {r['query_time']:.6f}")
    print()


if __name__ == "__main__":
    main()
