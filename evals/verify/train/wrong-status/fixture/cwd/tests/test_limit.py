import unittest

from msgq.queue import Queue, QueueFull


class LimitTest(unittest.TestCase):
    def test_rejects_51st(self):
        q = Queue()
        for i in range(50):
            q.schedule(str(i))
        with self.assertRaises(QueueFull) as cm:
            q.schedule("51")
        self.assertEqual(cm.exception.status, 400)


if __name__ == "__main__":
    unittest.main()
