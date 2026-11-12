"""Dependency-free regression tests: python -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from edge_hit import hit_rect_edge


class BorderHitTests(unittest.TestCase):
    def test_edges_between_visible_handles(self):
        for name, xy in (
            ('top', (37, 0)), ('top', (63, 0)),
            ('bottom', (37, 100)), ('bottom', (63, 100)),
            ('left', (0, 37)), ('left', (0, 63)),
            ('right', (100, 37)), ('right', (100, 63)),
        ):
            with self.subTest(name=name, xy=xy):
                self.assertEqual(hit_rect_edge(*xy, 0, 0, 100, 100), name)

    def test_corner_targets(self):
        for name, xy in (
            ('tl', (2, 2)), ('tr', (98, 2)),
            ('bl', (2, 98)), ('br', (98, 98)),
            ('tl', (16, 15)), ('tr', (84, 15)),
            ('bl', (16, 85)), ('br', (84, 85)),
            ('tl', (-10, -10)), ('br', (110, 110)),
        ):
            with self.subTest(name=name, xy=xy):
                self.assertEqual(hit_rect_edge(*xy, 0, 0, 100, 100), name)

    def test_edge_strip_inside_and_outside(self):
        for xy, expected in (((11, 45), 'left'), ((89, 45), 'right'),
                             ((45, 11), 'top'), ((45, 89), 'bottom'),
                             ((-8, 45), 'left'), ((108, 45), 'right')):
            with self.subTest(xy=xy):
                self.assertEqual(hit_rect_edge(*xy, 0, 0, 100, 100), expected)

    def test_no_hit_interior_or_far_outside(self):
        for xy in ((50, 50), (150, 50), (-50, 50), (50, -50), (50, 150)):
            with self.subTest(xy=xy):
                self.assertIsNone(hit_rect_edge(*xy, 0, 0, 100, 100))

    def test_smaller_and_larger_media(self):
        for rect in ((0, 0, 400, 225), (0, 0, 120, 210),
                     (-200, -150, 200, 150), (0, 0, 30, 40)):
            left, top, right, bottom = rect
            with self.subTest(rect=rect):
                self.assertEqual(hit_rect_edge((left+right)/2, top, *rect), 'top')
                self.assertEqual(hit_rect_edge(right, (top+bottom)/2, *rect), 'right')
                self.assertEqual(hit_rect_edge(left, top, *rect), 'tl')


if __name__ == '__main__':
    unittest.main()
