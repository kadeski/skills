class Queue:
    def __init__(self):
        self._items = []

    def schedule(self, message):
        self._items.append(message)
        return len(self._items)

    def list(self):
        return list(self._items)
