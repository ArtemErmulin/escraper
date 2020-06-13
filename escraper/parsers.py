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

    def get_events(self, event_id=None, event_url=None):
        if event_url is not None:
            event_id = re.findall(r"(?<=event/)\d*(?=/)", event_url)[0]

        if event_id is None:
            raise ValueError("'event_id' or 'event_url' required.")

        return self.parse(event_id)

    def parse(self, event_id):
        url = self.events_api.format(event_id=event_id)
        res = requests.get(url=url, headers=self.headers)

        if not res.ok:
            raise ValueError("Bad request, reason: {}".format(res.reason))

        event = res.json()

        return EventData(
            title=remove_html_tags(event["name"]),
            title_date=self.get_title_date(event),
            place_name=remove_html_tags(event["organization"]["name"]),
            post_text=remove_html_tags(event["description_html"]),
            date=self.get_date(event),
            adress=self.get_address(event),
            poster_imag=event["poster_image"]["default_url"],
            url=event["url"],
        )

    def get_title_date(self, event):
        starts_at = datetime.strptime(event["starts_at"], STRPTIME)
        return starts_at.strftime("%d %B")

    def get_date(self, event):
        starts_at = datetime.strptime(event["starts_at"], STRPTIME)
        ends_at = datetime.strptime(event["ends_at"], STRPTIME)

        if starts_at.day == ends_at.day:
            start_format = "%d %B %H:%M-"
            end_format = "%H:%M"
        else:
            start_format = "с %d %B %H:%M "
            end_format = "по %d %B %H:%M"

        return starts_at.strftime(start_format) + ends_at.strftime(end_format)

    def get_address(self, event):
        if event["location"]["city"] == "Без города":
            address = "Санкт-Петербург"
        elif "address" not in event["location"]:
            raise TypeError("Unknown address type: {}".format(event["loaction"]))
        else:
            address = event["location"]["address"]

        return remove_html_tags(address)


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
