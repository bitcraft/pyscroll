import unittest

from pyscroll.isometric import vector2_to_iso, vector3_to_iso


class IsometricFunctionsTest(unittest.TestCase):
    def test_vector3_to_iso(self):
        self.assertEqual(vector3_to_iso((1, 1, 0)), (0, 1))
        self.assertEqual(vector3_to_iso((2, 1, 0)), (1, 1))
        self.assertEqual(vector3_to_iso((1, 2, 0)), (-1, 1))
        self.assertEqual(vector3_to_iso((1, 1, 1)), (0, 0))
        self.assertEqual(vector3_to_iso((-1, -1, 0)), (0, -1))
        self.assertEqual(vector3_to_iso((-2, -1, 0)), (-1, -2))
        self.assertEqual(vector3_to_iso((-1, -2, 0)), (1, -2))
        self.assertEqual(vector3_to_iso((-1, -1, -1)), (0, 0))
        self.assertEqual(vector3_to_iso((0, 0, 0)), (0, 0))
        self.assertEqual(vector3_to_iso((100, 100, 0)), (0, 100))
        self.assertEqual(vector3_to_iso((200, 100, 0)), (100, 150))
        self.assertEqual(vector3_to_iso((100, 200, 0)), (-100, 150))
        self.assertEqual(vector3_to_iso((100, 100, 100)), (0, 0))

    def test_vector2_to_iso(self):
        self.assertEqual(vector2_to_iso((1, 1)), (0, 1))
        self.assertEqual(vector2_to_iso((2, 1)), (1, 1))
        self.assertEqual(vector2_to_iso((1, 2)), (-1, 1))
        self.assertEqual(vector2_to_iso((0, 0)), (0, 0))
        self.assertEqual(vector2_to_iso((-1, -1)), (0, -1))
        self.assertEqual(vector2_to_iso((-2, -1)), (-1, -2))
        self.assertEqual(vector2_to_iso((-1, -2)), (1, -2))
        self.assertEqual(vector2_to_iso((0, 0)), (0, 0))
        self.assertEqual(vector2_to_iso((100, 100)), (0, 100))
        self.assertEqual(vector2_to_iso((200, 100)), (100, 150))
        self.assertEqual(vector2_to_iso((100, 200)), (-100, 150))

    def test_vector3_to_iso_invalid_inputs(self):
        with self.assertRaises(ValueError):
            vector3_to_iso((1, 2))

    def test_vector2_to_iso_invalid_inputs(self):
        with self.assertRaises(ValueError):
            vector2_to_iso((1, 2, 3))
