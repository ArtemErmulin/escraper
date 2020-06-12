from copy import deepcopy
import os
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
    events_api = "https://api.timepad.ru/v1/events/{event_id}"

    def __init__(self):
        # TODO add as enviroment variable
        path = os.path.join(os.path.dirname(__file__), "misk/timepad_token")
        with open(path) as f:
            self._token = f.readline()

        self.headers = dict(
            Authorization=f"Bearer {self._token}",
        )

    def parse(self, event_id):
        url = self.events_api.format(event_id=event_id)
        res = requests.get(url=url, headers=self.headers)

        if not res.ok:
            raise ValueError("Bad request, reason: {}".format(res.reson))

        r = res.json()

        data = dict(
            starts_at=r["starts_at"],
            ends_at=r["ends_at"],
            name=r["name"],
            description_short=r["description_short"],
            url=r["url"],
            poster_image=r["poster_image"]["default_url"],
            city=r["location"]["city"],
            org_name=r["organization"]["name"],
            categories=r["categories"],
            tickets_limit=r["tickets_limit"],
            ticket_types=r["ticket_types"],
            age_limit=r["age_limit"],
            access_status=r["access_status"],
            is_registration_open=r["registration_data"]["is_registration_open"],
        )
        return data

    def get_events(self):
        # testing
        event_id = 1330000
        return self.parse(event_id)


class EventParser:
    def get_events(self, source=None, *args, **kwargs):
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
