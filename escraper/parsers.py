from collections import namedtuple
from datetime import datetime
import os
import itertools
import random
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseParser
from .utils import weekday_name, month_name


all_parsers = dict()
STRPTIME = "%Y-%m-%dT%H:%M:%S%z"

ALL_EVENT_TAGS = (
    "adress",
    "category",
    "date_from",
    "date_to",
    "id",
    "place_name",
    "post_text",
    "poster_imag",
    "price",
    "title",
    "url",
    "is_registration_open",
)

MAX_NUMBER_CONNECTION_ATTEMPTS = 3


def parser_register(cls):
    all_parsers[cls.name.lower()] = cls
    return cls


def remove_html_tags(data):
    return BeautifulSoup(data, "html.parser").text


def _request_get(*args, **kwargs):
    """
    Send get request with specifica arguments.

    To avoid internet connection issues,
    will catch ConnectionError and retry.
    """
    attempts_count = 0

    while True:
        try:
            response = requests.get(*args, **kwargs)
            break
        except requests.ConnectionError as e:
            if attempts_count == MAX_NUMBER_CONNECTION_ATTEMPTS:
                raise e
            attempts_count += 1
            print("Retry connection...")

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
    FIELDS = (
        "name",
        "starts_at",
        "organization",
        "description_short",
        "ends_at",
        "location",
        "poster_image",
        "url",
        "registration_data",
        "id",
        "categories",
    )

    def __init__(self, token=None):
        if token is None:
            if "TIMEPAD_TOKEN" in os.environ:
                self._token = os.environ.get("TIMEPAD_TOKEN")

            elif "misk" in os.listdir(os.path.dirname(__file__)):
                path = os.path.join(os.path.dirname(__file__), "misk/timepad_token")
                with open(path) as f:
                    self._token = f.readline()

            else:
                raise ValueError("Timepad token not found.")

        else:
            self._token = token

        self.headers = dict(
            Authorization=f"Bearer {self._token}",
        )

    def get_event(self, event_id=None, event_url=None, tags=None):
        if event_url is not None:
            event_id = re.findall(r"(?<=event/)\d*(?=/)", event_url)[0]

        if event_id is None:
            raise ValueError("'event_id' or 'event_url' required.")

        url = self.events_api + f"/{event_id}"
        response_json = _request_get(url, headers=self.headers).json()

        if not is_moderated(response_json):
            print("Event is not moderated")
            event = None

        else:
            tags = tags or ALL_EVENT_TAGS
            event = self.parse(response_json, tags=tags)

        return event

    def get_events(self, organization=None, request_params=None, tags=None):
        """
        Parameters:
        -----------
        request_params : dict, default None
            Parameters for timepad events
            (for more details see. http://dev.timepad.ru/api/get-v1-events/)

            limit : int, default 10
                1 <= limit <= 100
                events count

            sort : str
                sorting field (id, or starts_at, etc.)

            category_ids : str like "id1, id2, id3, ..."
                see Timepad().event_categories

            category_ids_exclude : str like "id1, id2, id3, ..."
                see Timepad().event_categories
                event categories that exclude

            cities : str like "city1, city2, city3, ..."
                event city

            keywords : str like "key1, key2, key3, ..."
                event name keywords

            keywords_exclude : str like "key1, key2, key3, ..."
                excluded event name keywords

            access_statuses : str like "status1, status2, ..."
                available statuses:
                private, draft, link_only, public

            price_min, price_max : int
                min and max ticket price:
                for price_min - at least one ticket, that have greater price
                for price_max - at least one ticket, that have lower price

            starts_at_min, starts_at_max : datetime string format %Y-%m-%dT%H:%M:%S%z
                event starts dates

            created_at_min, created_at_max : datetime string format %Y-%m-%dT%H:%M:%S%z
                event created dates

        tags : list of tags, default all available event tags
            Event tags (title, id, url etc.,
            see all tags in 'escraper.parsers.ALL_EVENT_TAGS')

        Examples:
        ---------
        >>> tp = Timepad()

        Select by city:
        >>> params = dict(cities="Санкт-Петербург")
        >>> tp.get_events(request_params=params)
        <list of 10 events from Санкт-Петербург>

        Select by category_ids:
        >>> tp.event_categories
        [
            {'id': '217', 'name': 'Бизнес', 'tag': 'business'},
            {'id': '374', 'name': 'Кино', 'tag': 'cinema'},
            {'id': '376', 'name': 'Спорт', 'tag': 'sport'},
            ...
        ]
        >>> params = dict(category_ids="217, 374"])
        >>> tp.get_events(request_params=params)
        <list of 10 events by business or/and cinema>

        Select by starts_at_min:
        >>> params = dict(starts_at_min="2020-08-11T00:00:00")
        <10 events after that starts after "2020-08-11T00:00:00">
        """
        request_params = request_params or {}
        request_params["fields"] = request_params.get("fields") or ", ".join(self.FIELDS)
        tags = tags or ALL_EVENT_TAGS

        url = self.events_api + ".json"
        res = _request_get(url, params=request_params, headers=self.headers)

        events_data = list()
        for response_json in res.json()["values"]:
            if is_moderated(response_json):
                events_data.append(self.parse(response_json, tags=tags))
            else:
                events_data.append(None)

        return events_data

    def parse(self, response_json, tags=None):
        if tags is None:
            raise ValueError(
                "'tags' for event required (see escraper.parsers.ALL_EVENT_TAGS)."
            )

        data = dict()
        for tag in tags:
            try:
                data[tag] = getattr(self, "_" + tag)(response_json)
            except AttributeError:
                raise TypeError(
                    f"Unsupported event tag found: {tag}.\n"
                    f"All available event tags: {ALL_EVENT_TAGS}."
                )

        DataStorage = namedtuple("event", tags)

        return DataStorage(**data)

    def _adress(self, event):
        if "city" not in event["location"]:
            address = "Онлайн"

        else:
            if event["location"]["city"] == "Без города":
                address = "Санкт-Петербург"

            elif "address" not in event["location"]:
                if "coordinates" in event["location"]:
                    address = ", ".join(
                        map(str, event["location"]["coordinates"])
                    )  # coordinates, realy?

                else:
                    raise TypeError("Unknown address type: {}".format(event["location"]))

            else:
                address = event["location"]["address"]

        return remove_html_tags(address)

    def _category(self, event):
        """
        TODO create more flexible detection categories
        """
        return event["categories"][0]["name"]

    def _date_from(self, event):
        dt = datetime.strptime(event["starts_at"], STRPTIME)

        return dt.replace(tzinfo=None)

    def _date_to(self, event):
        if "ends_at" in event:
            dt = datetime.strptime(event["ends_at"], STRPTIME)
            return dt.replace(tzinfo=None)
        return None

    def _id(self, event):
        return event["id"]

    def _place_name(self, event):
        return remove_html_tags(event["organization"]["name"])

    def _post_text(self, event):
        return remove_html_tags(event["description_short"])

    def _poster_imag(self, event):
        if "poster_image" not in event:
            return None

        return event["poster_image"]["uploadcare_url"][2:]

    def _price(self, event):
        if event["registration_data"]["is_registration_open"]:
            price_min = event["registration_data"]["price_min"]

            if price_min == 0:
                price_text = "Бесплатно"
            elif price_min > 0:
                price_text = f"{price_min}₽"

        else:
            price_text = "Билетов нет"

        return price_text

    def _title(self, event):
        return remove_html_tags(event["name"])

    def _url(self, event):
        return event["url"]

    def _is_registration_open(self, event):
        return int(event["registration_data"]["is_registration_open"])

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


def is_moderated(response_json):
    return response_json["moderation_status"] != "not_moderated"
