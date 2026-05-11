import pytest


class Response:
    def __init__(self, content=None, ok=None, json_items=None, text=None, status_code=200):
        self.content = content
        self.ok = ok
        self.json_items = json_items
        self.text = text
        self.status_code = status_code

    def json(self):
        if isinstance(self.json_items, list):
            return list(self.json_items)
        return dict(**self.json_items)
