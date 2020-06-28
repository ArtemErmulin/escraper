from collections import namedtuple
from datetime import datetime
import os
import random
import re

import requests
from bs4 import BeautifulSoup

from .base import BaseParser
from .utils import weekday_name, month_name
from . import posting
from .saving import add2db,checkdb,whatdate

STRPTIME = "%Y-%m-%dT%H:%M:%S%z"
all_parsers = dict()
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
        "price",
    ]
)


EventData4db = namedtuple(
    "event_data4db", [
            "title",
            "date",
            #"date_end",
            "category",
            "place_name",
            "post_text",
            "adress",
            "poster_imag",
            "url",
            "price",
            "availability",
    ]
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

    while (True):
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

    def get_event(self, event_id=None, event_url=None, as_post=True):
        if event_url is not None:
            event_id = re.findall(r"(?<=event/)\d*(?=/)", event_url)[0]

        if event_id is None:
            raise ValueError("'event_id' or 'event_url' required.")

        event = self.parse(event_id)

        if as_post:
            return posting.create(event)
        return event

    def get_events(self, organization=None, request_params=None, as_posts=True):
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

        url = self.events_api + ".json"
        res = _request_get(url, params=request_params, headers=self.headers)

        events_data = list()
        for event in res.json()["values"]:
            events_data.append(self.get_event(event_url=event["url"], as_post=as_posts))

        return events_data



    def get_events4db(self, organization=None, request_params=None):
        request_params = request_params or {}

        url = self.events_api + ".json"
        res = _request_get(url, params=request_params, headers=self.headers)

        events4db=[]
        for event_f in res.json()["values"]:
            event_id=event_f['id']
            url = self.events_api + f"/{event_id}"
            event = _request_get(url, headers=self.headers).json()


            if "poster_image" not in event:
                poster_imag = None
            else:
                poster_imag = event["poster_image"]["default_url"]

            events4db.append(EventData4db(
            title=remove_html_tags(event["name"]),
            date=event["starts_at"],
            category=event["categories"][0]['name'],
            place_name=remove_html_tags(event["organization"]["name"]),
            post_text=remove_html_tags(event["description_html"]),
            adress=self.get_address(event),
            poster_imag=poster_imag,
            url=event["url"],
            price = event['registration_data']['price_min'],
            availability = event['registration_data']['is_registration_open'],
            ))
        return events4db

    def events4day(self, monthday=0, limit=10, price_max=500): #make to choose day
        date_4_searching=whatdate(monthday)
        params={'limit':limit,
        'price_max':price_max,
        'starts_at_min': f"{date_4_searching}T00:00:00",
        'starts_at_max': f"{date_4_searching}T23:59:59", 
        'category_ids_exclude':"217,376,399,453,1315"}

        events=self.get_events4db(request_params=params)

    def putInDb(self):
        self.events4day()
        return 'Q'


    def parse(self, event_id):
        url = self.events_api + f"/{event_id}"
        event = _request_get(url, headers=self.headers).json()

        if "poster_image" not in event:
            poster_imag = None
        else:
            poster_imag = event["poster_image"]["default_url"]

        return EventData(
            title=remove_html_tags(event["name"]),
            title_date=self.get_title_date(event),
            place_name=remove_html_tags(event["organization"]["name"]),
            post_text=remove_html_tags(event["description_html"]),
            date=self.get_date(event),
            adress=self.get_address(event),
            poster_imag=poster_imag,
            url=event["url"],
            price=self.get_price(event),
        )

    def get_price(self, event):
        if event['registration_data']['is_registration_open']==True:
            price_min=event['registration_data']['price_min']
        else:
            price_min=-1

        if price_min==0:
            price_text='Бесплатно'
        elif price_min>0:
            price_text=f"{price_min}₽"
        else:
            price_text='Билетов нет'
        return price_text

    def get_date4DB(self,event):
        starts_at = datetime.strptime(event["starts_at"], STRPTIME)

    def get_title_date(self, event):
        starts_at = datetime.strptime(event["starts_at"], STRPTIME)
        return (
            "{day} {month}".format(
                day=starts_at.day,
                month=month_name(starts_at),
            )
        )

    def get_date(self, event):
        starts_at = datetime.strptime(event["starts_at"], STRPTIME)

        s_weekday = weekday_name(starts_at),
        s_day = starts_at.day
        s_month = month_name(starts_at)
        s_hour = starts_at.hour
        s_minute = starts_at.minute

        if "ends_at" in event:
            ends_at = datetime.strptime(event["ends_at"], STRPTIME)

            e_day = ends_at.day
            e_month = month_name(ends_at)
            e_hour = ends_at.hour
            e_minute = ends_at.minute

            if s_day == e_day:
                start_format = f"{s_weekday}, {s_day} {s_month} {s_hour:02}:{s_minute:02}-"
                end_format = f"{e_hour:02}:{e_minute:02}" 

            else:
                start_format = f"с {s_day} {s_month} {s_hour:02}:{s_minute:02} "
                end_format = f"по {e_day} {e_month} {e_hour:02}:{e_minute:02}"

        else:
            end_format = ""  # TODO what wrong with this event? 
            start_format = f"{s_weekday}, {s_day} {s_month} {s_hour:02}:{s_minute:02}"

        return start_format + end_format

    def get_address(self, event):
        if "city" not in event["location"]:
            address = "Онлайн"
        elif "city" in event["location"] and "address" not in event["location"]:
            address = "Санкт-Петербург"
        elif event["location"]["city"] == "Без города":
            address = "Санкт-Петербург"
        elif "coordinates" in event["location"]:
            address = ", ".join(map(str, event["location"]["coordinates"]))  # coordinates, realy?
        elif "address" not in event["location"]:
            raise TypeError("Unknown address type: {}".format(event["location"]))
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
