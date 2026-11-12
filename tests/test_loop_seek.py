"""Qt-free runtime regression tests for asynchronous A/B seeking."""
import unittest
from app.loop_seek import LoopSeekGuard


class LoopSeekTests(unittest.TestCase):
    def setUp(self):
        self.g = LoopSeekGuard()
        self.a = 1000
        self.b = 8000

    def at(self, p, t):
        return self.g.observe_position(p, self.a, self.b, True, now=t)

    def end(self, p, t):
        return self.g.observe_end(p, self.a, self.b, True, now=t)

    def test_before_b_does_not_seek(self):
        self.assertFalse(self.at(7000, 1.0))
        self.assertEqual(self.g.requests, 0)

    def test_at_b_requests_one_seek(self):
        self.assertTrue(self.at(7990, 1.0))
        self.assertEqual(self.g.requests, 1)

    def test_repeated_b_signals_do_not_seek_again(self):
        self.assertTrue(self.at(7990, 1.0))
        for t in (1.01, 1.2, 2.1):
            self.assertFalse(self.at(8000, t))
        self.assertEqual(self.g.requests, 1)
        self.assertEqual(self.g.suppressed, 3)

    def test_pending_ends_only_after_arriving_near_a(self):
        self.at(7990, 1.0)
        self.assertFalse(self.at(5000, 1.05))
        self.assertTrue(self.g.pending)
        self.assertFalse(self.at(1090, 1.1))
        self.assertFalse(self.g.pending)
        self.assertEqual(self.g.acknowledged, 1)

    def test_next_full_loop_seeks_again(self):
        self.at(8000, 1.0)
        self.at(1000, 1.2)
        self.assertTrue(self.at(8000, 9.0))
        self.assertEqual(self.g.requests, 2)

    def test_end_and_position_handler_share_guard(self):
        self.assertTrue(self.at(8000, 1.0))
        self.assertFalse(self.end(8000, 1.1))
        self.assertEqual(self.g.requests, 1)

    def test_end_of_media_can_initiate_one_seek(self):
        self.assertTrue(self.end(8100, 1.0))
        self.assertFalse(self.at(8100, 1.1))
        self.assertEqual(self.g.requests, 1)

    def test_delayed_end_after_ack_is_ignored(self):
        self.at(8000, 1.0)
        self.at(1000, 1.1)
        self.assertFalse(self.end(1000, 1.4))
        self.assertEqual(self.g.requests, 1)

    def test_short_loop_does_not_ack_near_b(self):
        self.g.observe_position(1300, 1000, 1300, True, now=1.0)
        self.assertTrue(self.g.pending)
        self.g.observe_position(1300, 1000, 1300, True, now=1.1)
        self.assertTrue(self.g.pending)

    def test_disable_resets_pending(self):
        self.at(8000, 1.0)
        self.assertFalse(self.g.observe_position(4000, self.a, self.b, False, now=1.1))
        self.assertFalse(self.g.pending)

    def test_manual_configuration_change_resets_pending(self):
        self.at(8000, 1.0)
        self.g.reset()
        self.assertFalse(self.g.pending)
        self.assertTrue(self.at(8000, 1.1))

    def test_no_ack_if_seek_never_arrives(self):
        self.at(8000, 1.0)
        for t in range(2, 12):
            self.assertFalse(self.at(8000, t))
        self.assertEqual(self.g.requests, 1)
        self.assertTrue(self.g.pending)

    def test_counters_readable_without_media(self):
        s = self.g.report()
        self.assertIn('loop_seek_requests=0', s)
        self.assertIn('seek_pending=False', s)


if __name__ == '__main__':
    unittest.main()
