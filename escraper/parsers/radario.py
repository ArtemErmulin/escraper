import re
import requests
import warnings
from datetime import datetime

import pytz
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
    BASE_URL = "https://spb.radario.ru/"
    BASE_EVENTS_API = "https://radario.ru/events/"
    DATETIME_STRF = "%Y-%m-%d"
    parser_prefix = "RADARIO-"


    def __init__(self):
        self.url = self.BASE_URL
        self.events_api = self.BASE_EVENTS_API
        self.timedelta_hours = self.timedelta_with_gmt0()

    def get_event(self, event_id=None, event_url=None, tags=None):
        if event_id is not None and event_url is None:
            event_url = "https://radario.ru/events/" + str(event_id)
        elif event_url is None:
            raise ValueError("'event_id' or 'event_url' required.")

        event_soup = BeautifulSoup(
            self._request_get(event_url).text, "lxml"
        )
        event = self.parse(event_soup, tags=tags or ALL_EVENT_TAGS)

        return event

    def get_events(self, request_params=None, tags=None):
        """
        Parameters:
        -----------
        request_params : dict
            Parameters for radario events

            online : bool
                Include online events

            category : list, default None (all categories)
                All available event catefories:
                    concert, theatre, museum, education,
                    sport, entertainment, kids, show

            date_from, date_to : str, default None (now)
                Events date range

        tags : list of tags, default all available event tags
            Event tags (title, id, url etc.,
            see all tags in 'escraper.ALL_EVENT_TAGS')

        Examples:
        ----------
        >>> radario = Radario()
        >>> request_params = {
            "online": True,
            "category": ["concert", "education", "theatre"],
            "date_from": "2020-01-01",
            "date_to": "2020-01-02",
        }
        >>> radario.get_events(request_params=request_params)  # doctest: +SKIP
        """
        request_params = (request_params or dict())

        if request_params.pop("online", False):
            # convert "https://spb.radario.ru/" to "https://online.radario.ru/"
            self.url = self.url.replace("spb", "online")

        events = list()

        for cat in request_params.pop("category", [""]):
            if cat in AVAILABLE_CATEGORIES + [""]:
                url = f"{self.url}{cat}"
                response = self._request_get(url, params=request_params)

                if response:
                    # get only 20 events
                    soup = BeautifulSoup(response.text, "lxml")
                    list_event_from_soup = soup.find_all("div", {"class": "event-card"})

                else:
                    list_event_from_soup = list()

                for event_card in list_event_from_soup:
                    event_id = event_card.find(
                        "a", {"class": "event-card__title"}
                    )["href"].split("/")[-1]

                    url = self.events_api + event_id

                    event_soup = BeautifulSoup(
                        self._request_get(url).text, "lxml"
                    )
                    events.append(self.parse(event_soup, tags=tags or ALL_EVENT_TAGS))

            else:
                warnings.warn(f"Category {cat!r} is not exist", UserWarning)

        return events

    def _adress(self, event_soup):
        full_address = event_soup.find(
            "span", {"class": "text-secondary mt-2"}
        ).text.strip()

        full_address = full_address.replace(", Центральный район", "")

        # remove zip code
        full_address = re.sub(r" \d+ ", " ", full_address)
        full_address = re.sub(r" \d+, ", " ", full_address)
        full_address = re.sub(r"^\d+, ", "", full_address)

        if "онлайн" in full_address.lower():
            address = "Онлайн"
        else:
            if full_address.find(", Санкт-Петербург") != -1:
                end_idx = full_address.find(", Санкт-Петербург")
                address = full_address[:end_idx]

            elif full_address.find("Санкт-Петербург, ") != -1:
                address = full_address.replace("Санкт-Петербург, ", "")

            else:
                address = full_address

        return address

    def _category(self, event_soup):
        return event_soup.find("a", {"class": "event-page__tag"}).text.strip()

    def _datetimes_from_html(self, event_soup):
        """
        Parse datetimes (from and to) from html page.
        Use only in Radario._date_from()
        """
        strfdatetime = self._date_from_to(event_soup)

        day_from = None
        month_from = None
        hour_from = None
        minute_from = None

        day_to = None
        month_to = None
        hour_to = None
        minute_to = None

        # can parse from-to datetime string formats:
        # - "dd month, HH:MM-HH:MM"
        # - "dd month, HH:MM"
        # - "dd-dd month"
        if not re.match(r"^\d\d \w+,", strfdatetime) \
            and not re.match(r"^\d\d-\d\d \w+$", strfdatetime)\
            and not re.match(r"^\d\d \w+ \d{4}", strfdatetime):
            raise ValueError(
                f"Unknown radario from-to datetime string: {strfdatetime!r}.\n"
                f"Event url: {self._url(event_soup)}"
            )

        # dd month+
        if re.match(r"^\d\d \w+,", strfdatetime):
            day_from = int(strfdatetime[:2])
            month_from = int(monthes[strfdatetime[3:].split(",")[0]])

            day_to = day_from
            month_to = month_from

            # dd month, HH:MM
            if re.match(r"\d{2} \w+, \d{2}:\d{2}$", strfdatetime):
                strtime_from = strfdatetime[-5:]

                hour_from = int(strtime_from.split(":")[0])
                minute_from = int(strtime_from.split(":")[1])

            # dd month, HH:MM-HH:MM
            elif re.match(r"\d{2} \w+,.+\d{2}:\d{2}-\d{2}:\d{2}", strfdatetime):
                strtime_from = strfdatetime[-11:-6]
                hour_from = int(strtime_from.split(":")[0])
                minute_from = int(strtime_from.split(":")[1])

                strtime_to = strfdatetime[-5:]
                hour_to = int(strtime_to.split(":")[0])
                minute_to = int(strtime_to.split(":")[1])
                if hour_to > self.timedelta_hours:
                    hour_to = hour_to - self.timedelta_hours

            if hour_from > self.timedelta_hours:
                hour_from = hour_from - self.timedelta_hours

        # dd-dd month
        elif re.match(r"^\d\d-\d\d \w+$", strfdatetime):
            day_from = int(strfdatetime[:2])
            month_from = int(monthes[strfdatetime[6:]])
            hour_from = 0
            minute_from = 0

            day_to = int(strfdatetime[3:5])
            month_to = month_from
            hour_to = 0
            minute_to = 0
        # dd month yyyy - #todo date_to and year
        elif re.match(r"^\d\d \w+ \d{4}", strfdatetime):
            strf_date_from , strf_date_to = strfdatetime.split(' - ')

            day_from = int(strfdatetime[:2])
            month_from = int(monthes[strfdatetime[3:].split(" ")[0]])
            hour_from = 0
            minute_from = 0

            day_to = day_from
            month_to = month_from

        daytime_from = datetime.now().replace(
            month=month_from,
            day=day_from,
            hour=hour_from,
            minute=minute_from,
            second=0,
            microsecond=0,
        ).astimezone(self.TIMEZONE)


        if hour_to is not None and minute_to is not None:
            daytime_to = datetime.now().replace(
                month=month_to,
                day=day_to,
                hour=hour_to,
                minute=minute_to,
                second=0,
                microsecond=0,
            ).astimezone(self.TIMEZONE)
        else:
            daytime_to = None

        return daytime_from, daytime_to

    def _date_from(self, event_soup):
        self._date_from_, self._date_to_ = self._datetimes_from_html(event_soup)
        return self._date_from_

    def _date_to(self, event_soup):
        return self._date_to_

    def _date_from_to(self, event_soup):
        """
        Parse date from and to as string from event page.
        """
        return re.sub(
            " +",
            " ",
            event_soup.find("span", {"class": "event-page__date mt-2"})
            .text.strip()
            .replace("\n", " ")
        )

    def _id(self, event_soup):
        meta_url = event_soup.find("meta", property="og:url")["content"]
        return self.parser_prefix + meta_url[meta_url.rfind("/") + 1 :]

    def _place_name(self, event_soup):
        return event_soup.find("span", {"class": "text-secondary mt-3"}).text.strip()


    def _full_text(self, event_soup) -> str:
        return self.remove_html_tags(
            event_soup.find("meta", property="og:description")["content"].replace(
                "<br/>", "\n"
            )
        )


    def _post_text(self, event_soup):
        return self.prepare_post_text(self._full_text(event_soup))



    def _poster_imag(self, event_soup):
        event_card_image = event_soup.find("img", {"class": "event-page__image"})
        if (
            event_card_image is not None
            and "DefaultEventImage" not in event_card_image["src"]
        ):
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
