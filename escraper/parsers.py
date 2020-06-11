from copy import deepcopy
import random

import requests
from bs4 import BeautifulSoup

from .base import BaseParser


_PARSERS = dict()


def parser_register(cls):
    _PARSERS[cls.name] = cls()
    return cls


@parser_register
class Timepad(BaseParser):
    """
    Parse ivents from www.timepad.ru by API:
    http://dev.timepad.ru/api/what-api-can/
    """
    name = "timepad"
    url = "www.timepad.ru"

    def parse(self, url):
        pass

    def get_events(self):
        return "Some events..."


class Parser:
    def __init__(self):
        pass

    def get_events(self, *args, source=None, **kwargs):
        if source is None:
            parser = random.choice(list(_PARSERS.values()))
        elif source not in _PARSERS:
            raise ValueError("Unknown source.")
        else:
            parser = _PARSERS[source]

        return parser.get_events(*args, **kwargs)

    @property
    def all_parsers(self):
        return deepcopy(list(_PARSERS.keys()))
