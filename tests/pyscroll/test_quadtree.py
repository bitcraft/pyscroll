import unittest

from pygame import Rect

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
