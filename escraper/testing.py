import pytest


class Response:
    def __init__(self, content=None, ok=None, json_items=None, text=None):
        self.content = content
        self.ok = ok
        self.json_items = json_items
        self.text = text

    def json(self):
        return dict(**self.json_items)
