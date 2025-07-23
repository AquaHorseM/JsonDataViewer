import ijson, json

class ItemLoader:
    def __init__(self, filename: str):
        self.filename = filename
        self.f = None
        self.gen = None

    def open(self):
        self.close()
        self.f = open(self.filename, "r")
        self.gen = ijson.items(self.f, "item")

    def next_item(self):
        return next(self.gen)

    def close(self):
        if self.f:
            self.f.close()
            self.f = None
