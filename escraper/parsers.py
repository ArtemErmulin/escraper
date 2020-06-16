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


locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")  # for month and weekday names
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


def _request_get(*args, **kwargs):
    response = requests.get(*args, **kwargs)

    if not response.ok:
        raise ValueError("Bad request, reason: {}".format(response.reason))

    return response


@parser_register
class Timepad(BaseParser):
    """
    Parse ivents from www.timepad.ru by API:
    http://dev.timepad.ru/api/what-api-can/

    Methods:
    --------

    get_events(event_id=None, event_url=None)
        Getting event parameters from timepad. Requieres one argument
        from following:

        event_id : int or string, default None
            event id on timepad (...timepad.ru/event/{event_id})

        event_url : str, default None
            url to event on timepad.ru
    """
    name = "timepad"
    url = "www.timepad.ru"
    events_api = "https://api.timepad.ru/v1/events"

    def __init__(self):
        # TODO add as enviroment variable
        path = os.path.join(os.path.dirname(__file__), "misk/timepad_token")
        with open(path) as f:
            self._token = f.readline()

        self.headers = dict(
            Authorization=f"Bearer {self._token}",
        )

    def get_event(self, event_id=None, event_url=None):
        if event_url is not None:
            event_id = re.findall(r"(?<=event/)\d*(?=/)", event_url)[0]

        if event_id is None:
            raise ValueError("'event_id' or 'event_url' required.")

        return self.parse(event_id)

    def get_events(self, organization=None, request_params=None):
        """
        Parameters:
        -----------
        request_params : dict, default None
            Parameters for timepad events
            (see. http://dev.timepad.ru/api/get-v1-events/)

            limit : int, default 10
                1 <= limit <= 100
                events count

            sort : str
                sorting field

            category_ids : int or list of ints
                see Timepad().event_categories

            cities : str or list of str
                event sity
        """
        request_params = request_params or {}

        url = self.events_api + ".json"
        res = _request_get(url, params=request_params, headers=self.headers)

        return res.json()

    def parse(self, event_id):
        url = self.events_api + f"/{event_id}"
        event = _request_get(url, headers=self.headers).json()

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
        return starts_at.strftime("%A %d %B")

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

    @property
    def event_categories(self):
        """
        Getting list of events categories.

        Return:
        -------
        [dict(id=str, name=str, tag=str), ...]

        Example:
        --------
        [
            {'id': '217', 'name': 'Бизнес', 'tag': 'business'},
            {'id': '374', 'name': 'Кино', 'tag': 'cinema'},
            {'id': '376', 'name': 'Спорт', 'tag': 'sport'},
            ...
        ]
        """
        url = "https://api.timepad.ru/v1/dictionary/event_categories"
        return _request_get(url, headers=self.headers).json()["values"]

    @property
    def event_statuses(self):
        """
        Getting list of events statuses.

        Return:
        -------
        [dict(id=str, name=str), ...]

        Example:
        --------
        [
            {'id': 'ok', 'name': 'Ok'},
            {'id': 'deleted', 'name': 'Удалена'},
            {'id': 'inactive', 'name': 'Неактивна'}
        ]
        """
        url = "https://api.timepad.ru/v1/dictionary/event_statuses"
        return _request_get(url, headers=self.headers).json()["values"]

    @property
    def tickets_statuses(self):
        """
        Getting list of tickets statuses.

        Return:
        -------
        [dict(id=str, name=str), ...]

        Example:
        --------
        [
            {'id': 'notpaid', 'name': 'просрочено'},
            {'id': 'ok', 'name': 'бесплатно'},
            {'id': 'paid', 'name': 'оплачено'},
            ...
        ]
        """
        url = "https://api.timepad.ru/v1/dictionary/tickets_statuses"
        return _request_get(url, headers=self.headers).json()["values"]


class EventParser:
    """
    Main parser for all sites.

    Methods:
    --------
    get_event(source, as_post=True, *args, **kwargs)
        Getting event parameters from source.
        
        source : string
            Source site, one of EventParser.all_parsers.

        as_post : bool, default True
            Convert event parameters to channel post layout.

        *args, **kwargs : source-parser specific parameters

    all_parsers : list
        List all available parsers.
    """
    def get_event(self, source, as_post=True, *args, **kwargs):
        if not isinstance(source, str):
            raise TypeError(
                "Invalid 'source' argument type: required 'str', given {}."
                .format(type(source))
            )

        if source not in _PARSERS:
            raise ValueError("Unknown source.")
        else:
            parser = _PARSERS[source]

        event_data = parser.get_event(*args, **kwargs)

        if as_post:
            # create post layout (type == str)
            return posting.create(event_data)

        # (type == EventData)
        return event_data

    def get_events(self, source, *args, **kwargs):
        parser = _PARSERS[source]
        if hasattr(parser, "get_events"):
            return parser.get_events(*args, **kwargs)
        else:
            raise ValueError("Parser {} has not get_events method.".format(source))

    @property
    def all_parsers(self):
        return list(_PARSERS.keys())
