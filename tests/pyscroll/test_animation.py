import unittest
from unittest.mock import MagicMock

from pyscroll.animation import AnimationFrame, AnimationToken


class TestAnimationToken(unittest.TestCase):

    def setUp(self):
        self.mock_surface1 = MagicMock()
        self.mock_surface2 = MagicMock()
        self.frame1 = AnimationFrame(image=self.mock_surface1, duration=0.5)
        self.frame2 = AnimationFrame(image=self.mock_surface2, duration=1.0)
        self.frames = [self.frame1, self.frame2]
        self.positions = {(1, 2, 0), (3, 4, 1)}

    def test_initial_state(self):
        token = AnimationToken(self.positions, self.frames)
        self.assertEqual(token.index, 0)
        self.assertEqual(token.next, self.frame1.duration)

    def test_advance_looping(self):
        token = AnimationToken(self.positions, self.frames, loop=True)
        next_frame = token.advance(0.5)
        self.assertEqual(next_frame, self.frame2)
        self.assertEqual(token.index, 1)

        next_frame = token.advance(1.0)
        self.assertEqual(next_frame, self.frame1)
        self.assertEqual(token.index, 0)

    def test_advance_non_looping(self):
        token = AnimationToken(self.positions, self.frames, loop=False)
        token.advance(0.5)
        final_frame = token.advance(1.0)
        self.assertEqual(final_frame, self.frame2)
        self.assertTrue(token.done)
        self.assertEqual(token.index, 1)
        repeat_frame = token.advance(1.0)
        self.assertEqual(repeat_frame, self.frame2)

    def test_update_with_elapsed_time(self):
        token = AnimationToken(self.positions, self.frames, loop=True)
        frame = token.update(current_time=0.6, elapsed_time=0.1)
        self.assertEqual(frame, self.frame2)
        self.assertEqual(token.index, 1)

    def test_update_non_looping_stop(self):
        token = AnimationToken(self.positions, self.frames, loop=False)
        token.update(current_time=0.6, elapsed_time=0.1)
        token.update(current_time=1.6, elapsed_time=0.5)
        frame = token.update(current_time=2.1, elapsed_time=0.5)
        self.assertEqual(frame, self.frame2)
        self.assertTrue(token.done)

    def test_empty_frame_list_raises(self):
        with self.assertRaises(ValueError):
            AnimationToken(self.positions, [], loop=True)

    def test_lt_comparison_with_number(self):
        token = AnimationToken(self.positions, self.frames)
        self.assertTrue(token < 10.0)
        self.assertFalse(token < 0.1)

    def test_lt_comparison_with_other_token(self):
        token1 = AnimationToken(self.positions, self.frames)
        token2 = AnimationToken(self.positions, self.frames, initial_time=1.0)
        self.assertTrue(token1 < token2)
