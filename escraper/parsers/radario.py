import re
import requests
import warnings
from datetime import datetime

from bs4 import BeautifulSoup

from .base import BaseParser, ALL_EVENT_TAGS
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
    parser_prefix = "RADARIO-"

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
        tags = tags or ALL_EVENT_TAGS
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
                for event_card in list_event_from_soup:
                    event_id = event_card.find(
                        "a", {"class": "event-card__title"}
                    )["href"].split("/")[-1]
                    url = self.events_api + event_id

                    event_soup = BeautifulSoup(self._request_get(url).text, "html.parser")
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
        full_adress = event_soup.find(
            "span", {"class": "text-secondary mt-2"}
        ).text.strip()

        if "онлайн" in full_adress.lower():
            adress = "Онлайн"
        else:
            end_idx = full_adress.find(", Санкт-Петербург")
            adress = full_adress[:end_idx]

        return adress

    def _category(self, event_soup):
        return event_soup.find("a", {"class": "event-page__tag"})["href"][1:]

    def _date_from(self, event_soup):
        """
        Parse from html page string date_from_to instead
        """
        strfdatetime = event_soup.find(
            "span", {"class": "event-page__date mt-2"}
        ).text.strip().replace("\n", "")

        day = int(strfdatetime[:2])
        month = int(monthes[strfdatetime[3:].split(",")[0]])
        hour = None
        minute = None

        # one day event in format '31 августа, 19:00'
        if re.match(r"\d{2} \w+, \d{2}:\d{2}", strfdatetime):
            strtime_from = strfdatetime[-5:]

            hour = int(strtime_from.split(":")[0])
            minute = int(strtime_from.split(":")[1])

        # one day, two hour points
        elif re.match(r"\d{2} \w+,.+\d{2}:\d{2}-\d{2}:\d{2}", strfdatetime):
            strtime_from = strfdatetime[-11:-6]

            hour = int(strtime_from.split(":")[0])
            minute = int(strtime_from.split(":")[1])

        if hour is not None and minute is not None:
            return datetime.now().replace(
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )
        else:
            print(f"Unknown datetime string: {strfdatetime}")

    def _date_to(self, event_soup):
        """
        Parse from html page string date_from_to instead
        """
        strfdatetime = event_soup.find(
            "span", {"class": "event-page__date mt-2"}
        ).text.strip().replace("\n", "")

        day = int(strfdatetime[:2])
        month = int(monthes[strfdatetime[3:].split(",")[0]])
        hour = None
        minute = None

        # one day event in format '31 августа, 19:00'
        # date_to is unknown
        if re.match(r"\d{2} \w+, \d{2}:\d{2}", strfdatetime):
            return None

        # one day, two hour points
        elif re.match(r"\d{2} \w+,.+\d{2}:\d{2}-\d{2}:\d{2}", strfdatetime):
            strtime_from = strfdatetime[-5:]

            hour = int(strtime_from.split(":")[0])
            minute = int(strtime_from.split(":")[1])

        if hour is not None and minute is not None:
            return datetime.now().replace(
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            )
        else:
            print(f"Unknown datetime string: {strfdatetime}")


    def _date_from_to(self, event_soup):
        return event_soup.find(
            "span", {"class": "event-page__date mt-2"}
        ).text.strip()

    def _id(self, event_soup):
        meta_url = event_soup.find("meta", property="og:url")["content"]
        return self.parser_prefix + meta_url[meta_url.rfind("/")+1:]

    def _place_name(self, event_soup):
        return (
            event_soup.find("span", {"class": "text-secondary mt-3"})
            .text.strip()
            )

    def _post_text(self, event_soup):
        return self.remove_html_tags(
            event_soup.find("meta", property="og:description")["content"]
            .replace("<br/>", "\n")
        )

    def _poster_imag(self, event_soup):
        event_card_image = event_soup.find("img", {"class": "event-page__image"})
        if event_card_image is not None and "DefaultEventImage" not in event_card_image["src"]:
            return event_card_image["src"]

    def _price(self, event_soup):
        return event_soup.find(
            "button", {"class": "c-button c-button--primary c-button--medium"}
        ).text.strip()

    def _title(self, event_soup):
        return add_emoji(
            event_soup.find("h1", {"class": "event-page__title"}).text.strip()
        )

    def _url(self, event_soup):
        return self.events_api + self._id(event_soup).replace(self.parser_prefix, "")

    def _is_registration_open(self, event_soup):
        return self._price(event_soup) != "Билетов нет"
