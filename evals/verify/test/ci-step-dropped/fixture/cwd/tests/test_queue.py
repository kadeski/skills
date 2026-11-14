import unittest

from msgq.queue import Queue


class QueueTest(unittest.TestCase):
    def test_schedule_adds_in_order(self):
        q = Queue()
        q.schedule("a")
        q.schedule("b")
        self.assertEqual(q.list(), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
