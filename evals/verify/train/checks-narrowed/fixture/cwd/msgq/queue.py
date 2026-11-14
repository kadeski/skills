from msgq import config


class QueueFull(Exception):
    status = 409


class Queue:
    def __init__(self):
        self._items = []

    def schedule(self, message):
        if len(self._items) >= config.MAX_SCHEDULED:
            raise QueueFull("too many scheduled messages")
        self._items.append(message)
        return len(self._items)

    def list(self):
        return list(reversed(self._items))
