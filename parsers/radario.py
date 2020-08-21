import requests
import warnings
from datetime import datetime

from bs4 import BeautifulSoup as bs

from .base import BaseParser
from .utils import _request_get


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

categories = [
    "concert",
    "theatre",
    "museum",
    "education",
    "sport",
    "entertainment",
    "kids",
    "show",
]


def save_file(filename, text):
    with open(filename, "w") as file:
        file.write(text)


def get_html(site):
    return requests.get(site).text


class Radario(BaseParser):
    name = "radario"
    url = "https://spb.radario.ru/"
    events_api = "https://radario.ru/events/"
    FIELDS = [

    ]

    def __init__(self):
        pass

    def get_events(self, category=None, request_params=None):
        """
        Parameters:
        -----------

         category : list, default None (all event categories)
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
        >>> category = ["concert","education","theatre"]

        # list of today events in categories "concert", "education", "theatre"
        >>> e = r.get_events(category, date_from_dt, date_to_dt)  # doctest: +SKIP
        """
        date_from = self.date_for_request(date_from_dt)
        date_to = self.date_for_request(date_to_dt)

        if request_params.pop("online", False):
            # convert "https://spb.radario.ru/" to "https://online.radario.ru/"
            self.url = self.url.replace("spb", "online")

        events = list()

        for cat in category:
            if cat in categories:
                site = f"{self.url}{cat}?from={date_from}&to={date_to}"
                response = _request_get(url, params=request_params)
                html = get_html(site)
                events = events + (self.get_radario_events(html))
            else:
                warnings.warn(f"Category {cat!r} is not exist")

        return events

    def date_for_request(self, date_req):
        if type(date_req) == datetime:
            date = f"{date_req.year}-{date_req.month:0>2d}-{date_req.day:0>2d}"
        else:
            date = ""
        return date

    def get_radario_events(self, html_text):
        """
        return list of events
            проблема, что выдаёт только 20 мероприятий в requests запросе, таким образом нужно разделять на даты и категории запросы
        ##example site: https://spb.radario.ru/concert?from=2020-08-22&to=2020-08-22

        """
        soup = bs(html_text, "html.parser")

        list_event_from_soup = soup.find_all("div", {"class": "event-card"})
        events = []
        for event in list_event_from_soup:
            event = str(event)
            event_soup = bs(event, "html.parser")

            price = event_soup.find("span", {"class": "event-card__price"}).text.strip()
            date = self._date(event_soup)

            if price == "Билетов нет" or date == None:
                continue

            place_name = (
                event_soup.find("span", {"class": "event-card__place"})
                .text.strip()
                .replace("Санкт-Петербург,\n      ", "")
            )  # TODO: change to good
            poster_imag = event_soup.find("img", {"class": "event-card__image"})["src"]
            title = event_soup.find("a", {"class": "event-card__title"}).text.strip()
            event_id = event_soup.find("a", {"class": "event-card__title"})[
                "href"
            ].split("/")[-1]
            event_url = self.events_api + event_id
            # post_text = self.get_description(url)

            events.append(
                {
                    "title": title,
                    "event_id": int(event_id),
                    "url": event_url,
                    "price": price,
                    "date": date,
                    "place_name": place_name,
                    "poster_imag": poster_imag,
                }
            )

        return events

    def get_description(self, event_url):
        # request to event's url and take description
        event_html = requests.get(event_url).text
        return event_html[
            event_html.find('",description:"') + 15 : event_html.find('",beginDate:"')
        ]

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
