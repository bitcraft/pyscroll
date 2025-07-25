import unittest

from pygame.rect import Rect

from pyscroll.quadtree import FastQuadTree


class TestFastQuadTree(unittest.TestCase):

    def test_init(self):
        rectangles = [Rect(0, 0, 10, 10), Rect(5, 5, 10, 10), Rect(10, 10, 10, 10)]
        quadtree = FastQuadTree(rectangles)
        self.assertIsNotNone(quadtree)

    def test_hit(self):
        rectangles = [Rect(0, 0, 10, 10), Rect(5, 5, 10, 10), Rect(10, 10, 10, 10)]
        quadtree = FastQuadTree(rectangles)
        collisions = quadtree.hit(Rect(2, 2, 12, 12))
        self.assertGreater(len(collisions), 0)

    def test_hit_no_collisions(self):
        rectangles = [Rect(0, 0, 10, 10), Rect(20, 20, 10, 10), Rect(30, 30, 10, 10)]
        quadtree = FastQuadTree(rectangles)
        collisions = quadtree.hit(Rect(5, 5, 5, 5))
        self.assertEqual(len(collisions), 1)

    def test_hit_empty(self):
        rectangles = [Rect(0, 0, 10, 10)]
        quadtree = FastQuadTree(rectangles)
        collisions = quadtree.hit(Rect(0, 0, 10, 10))
        self.assertEqual(len(collisions), 1)

    def test_hit_empty_tree(self):
        rectangles = []
        with self.assertRaises(ValueError):
            FastQuadTree(rectangles)

    def test_overlap_multiple_quadrants(self):
        rectangles = [
            Rect(0, 0, 50, 50),  # overlaps all quadrants
            Rect(60, 0, 10, 10),  # NE
            Rect(0, 60, 10, 10),  # SW
        ]
        quadtree = FastQuadTree(rectangles)
        collisions = quadtree.hit(Rect(25, 25, 10, 10))
        self.assertIn((0, 0, 50, 50), collisions)

    def test_deep_tree_structure(self):
        rectangles = [Rect(i * 5, i * 5, 4, 4) for i in range(50)]
        quadtree = FastQuadTree(rectangles, depth=6)
        self.assertEqual(len(list(quadtree)), 50)

    def test_exact_match(self):
        target = Rect(10, 10, 10, 10)
        rectangles = [Rect(0, 0, 10, 10), target, Rect(20, 20, 10, 10)]
        quadtree = FastQuadTree(rectangles)
        collisions = quadtree.hit(target)
        self.assertIn(tuple(target), collisions)

    def test_hit_outside_bounds(self):
        rectangles = [Rect(0, 0, 10, 10), Rect(20, 20, 10, 10)]
        quadtree = FastQuadTree(rectangles)
        collisions = quadtree.hit(Rect(100, 100, 10, 10))
        self.assertEqual(len(collisions), 0)
