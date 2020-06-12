from collections import namedtuple
from datetime import datetime
import os
import locale
import random
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseParser
from . import posting


locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")  # for month names
STRPTIME = "%Y-%m-%dT%H:%M:%S%z"
_PARSERS = dict()
EventData = namedtuple(
    "event_data", [
        "title",
        "title_date",
        "place_name",
        "post_text",
        "date",
        "adress",
        "poster_imag",
        "url",
    ]
)


def parser_register(cls):
    _PARSERS[cls.name] = cls()
    return cls


def remove_html_tags(data):
    return BeautifulSoup(data, "html.parser").text


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
            raise ValueError("Bad request, reason: {}".format(res.reason))

        r = res.json()

        starts_at = datetime.strptime(r["starts_at"], STRPTIME)
        ends_at = datetime.strptime(r["ends_at"], STRPTIME)

        if starts_at.day == ends_at.day:
            start_format = "%d %B %H:%M-"
            end_format = "%H:%M"
        else:
            start_format = "с %d %B %H:%M "
            end_format = "по %d %B %H:%M"

        date = starts_at.strftime(start_format) + ends_at.strftime(end_format)

        return EventData(
            title=remove_html_tags(r["name"]),
            title_date=starts_at.strftime("%d %B"),
            place_name=remove_html_tags(r["organization"]["name"]),
            post_text=remove_html_tags(r["description_html"]),
            date=date,
            adress=remove_html_tags(r["location"]["address"]),
            poster_imag=r["poster_image"]["default_url"],
            url=r["url"],
        )

    def get_events(self, event_id=None, event_url=None):
        if event_url is not None:
            event_id = re.findall(r"(?<=event/)\d*(?=/)", event_url)[0]

        if event_id is None:
            raise ValueError("event_id required.")

        return self.parse(event_id)


class EventParser:
    def get_events(self, source=None, as_post=True, *args, **kwargs):
        if source is None:
            parser = random.choice(list(_PARSERS.values()))
        elif source not in _PARSERS:
            raise ValueError("Unknown source.")
        else:
            parser = _PARSERS[source]

        event_data = parser.get_events(*args, **kwargs)

        # create post layout
        return posting.create(event_data)

    @property
    def all_parsers(self):
        return list(_PARSERS.keys())
