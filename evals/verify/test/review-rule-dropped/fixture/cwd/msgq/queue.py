class QueueFull(Exception):
    status = 409


class Queue:
    def __init__(self):
        self._items = []

    def schedule(self, message):
        if len(self._items) >= 50:
            raise QueueFull("too many scheduled messages")
        self._items.append(message)
        return len(self._items)

    def list(self):
        return list(self._items)
