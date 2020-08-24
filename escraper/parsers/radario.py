import requests
import warnings
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseParser
from ..emoji import add_emoji


monthes = {
    "января": "01",
    "февраля": "02",
    "марта": "03",
    "апреля": "04",
    "мая": "05",
    "июня": "06",
    "июля": "07",
    "августа": "08",
    "сентября": "09",
    "октября": "10",
    "ноября": "11",
    "декабря": "12",
}
STRPTIME = "%d %m %H:%M"

AVAILABLE_CATEGORIES = [
    "concert",
    "theatre",
    "museum",
    "education",
    "sport",
    "entertainment",
    "kids",
    "show",
]


class Radario(BaseParser):
    name = "radario"
    url = "https://spb.radario.ru/"
    events_api = "https://radario.ru/events/"

    def __init__(self):
        pass

    def get_event(self, *args, **kwargs):
        # TODO
        return None

    def get_events(self, date_from, date_to, *, category=None, request_params=None, tags=None):
        """
        Parameters:
        -----------

        category : list, default None (all event categories)
            All available event categories:
                concert, theatre, museum, education, sport, entertainment, kids, show

                event categories – ['concert', 'theatre', 'museum', 'education', 'sport', 'entertainment', 'kids', 'show']
                good categories – ['concert','theatre','education','sport', 'entertainment', 'kids', 'show']

        date_from_dt, date_to_dt : datetime, default None

            в категориях museum и theatre очень много мероприятий, так что интервал дат лучше ставить минимальный(на день)
            в остальных категориях интервал дат 5 дней идеально

        online : bool, default False
            онлайн мероприятий мало, так что остальные параметры можно оставлять пустыми

        Examples:
        ----------
        >>> from datetime import datetime

        >>> date_from_dt = datetime.now()
        >>> date_to_dt = datetime.now()

        >>> r = Radario()
        >>> category = ["concert", "education", "theatre"]

        # list of today events in categories "concert", "education", "theatre"
        >>> e = r.get_events(category, date_from_dt, date_to_dt)  # doctest: +SKIP
        """
        # if category is "", then get events from all categories
        category = category or [""]
        tags = tags or self.ALL_EVENT_TAGS
        request_params = request_params or dict()

        request_params["from"] = self.date_for_request(date_from)
        request_params["to"] = self.date_for_request(date_to)

        if request_params.pop("online", False):
            # convert "https://spb.radario.ru/" to "https://online.radario.ru/"
            self.url = self.url.replace("spb", "online")

        events = list()

        for cat in category:
            if cat in AVAILABLE_CATEGORIES + [""]:
                url = f"{self.url}{cat}"
                response = self._request_get(url, params=request_params)

                # get only 20 events
                soup = BeautifulSoup(response.text, "html.parser")

                list_event_from_soup = soup.find_all("div", {"class": "event-card"})
                for event in list_event_from_soup:
                    event = str(event)
                    event_soup = BeautifulSoup(event, "html.parser")

                    events.append(self.parse(event_soup, tags=tags))

            else:
                warnings.warn(f"Category {cat!r} is not exist")

        return events

    def date_for_request(self, date_req):
        if isinstance(date_req, datetime):
            date = f"{date_req.year}-{date_req.month:0>2d}-{date_req.day:0>2d}"
        else:
            date = ""
        return date

    def _adress(self, event_soup):
        return ""  # need request for getting adress

    def _category(self, event_soup):
        return ""  # ?

    def _date_from(self, event_soup):
        return self._date(event_soup)

    def _date_to(self, event_soup):
        return self._date(event_soup)

    def _id(self, event_soup):
        return int(
            event_soup.find(
                "a", {"class": "event-card__title"}
            )["href"].split("/")[-1]
        )

    def _place_name(self, event_soup):
        return (
            event_soup.find("span", {"class": "event-card__place"})
            .text.strip()
            .replace("Санкт-Петербург,\n      ", "")
            )  # TODO: change to good

    def _post_text(self, event_soup):
        # request to event's url and take post text
        event_html = requests.get(self._url(event_soup)).text
        return event_html[
            event_html.find('",description:"') + 15 : event_html.find('",beginDate:"')
        ]

    def _poster_imag(self, event_soup):
        return event_soup.find("img", {"class": "event-card__image"})["src"]

    def _price(self, event_soup):
        return event_soup.find("span", {"class": "event-card__price"}).text.strip()

    def _title(self, event_soup):
        return add_emoji(
            event_soup.find("a", {"class": "event-card__title"}).text.strip()
        )

    def _url(self, event_soup):
        return self.events_api + str(self._id(event_soup))

    def _is_registration_open(self, event_soup):
        return self._price(event_soup) != "Билетов нет" and self._date(event_soup) is not None

    def _date(self, event_soup):
        datenow = datetime.now()

        date = event_soup.find(
            "span", {"class": "event-card__date"}
        ).text  # TODO: change
        if len(date.split(" -\n         ")) > 1:
            return  # only one day event
        date_from = date.replace(",\n       ", "").split("-")[0].replace(",", "")

        for ru, num in monthes.items():
            date_from = date_from.replace(ru, num)
        date = datetime.strptime(date_from, STRPTIME)

        nowyear = datenow.year
        if date.month < datenow.month:
            nowyear += 1  # check if event in next year

        date = date.replace(year=nowyear)
        return date
