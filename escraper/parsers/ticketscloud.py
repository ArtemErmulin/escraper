import re, json

import warnings
from datetime import datetime

import pytz
from bs4 import BeautifulSoup

from .base import BaseParser, ALL_EVENT_TAGS
from ..emoji import add_emoji

ORG_IDS = (
    '5dce558174fd6b0bcaa66524', '5e3d551b44d20ecf697408e4', '5e3bec5fea9c82d6958f8551'
)


class Ticketscloud(BaseParser):
    name = "Ticketscloud"
    BASE_URL = "https://ticketscloud.org/"

    DATETIME_STRF = "%Y-%m-%d"
    parser_prefix = "Ticketscloud-"
    TIMEZONE = pytz.timezone("Europe/Moscow")

    def __init__(self):
        self.url = self.BASE_URL
        #self.events_api = self.BASE_EVENTS_API


    def get_event(self, event_url=None, tags=None):
        if event_url is None:
            raise ValueError("'event_id' or 'event_url' required.")
        self.url = event_url

        #response = self._request_get(event_url)

        event_soup = BeautifulSoup(
            self._request_get(event_url).text, "html.parser"
        )
        # if not is_moderated(response_json):
        #     print("Event is not moderated")
        #     event = None
        #else:
        tags = tags or ALL_EVENT_TAGS
        event = self.parse(event_soup, tags=tags)

        return event

    def get_events(self, org_ids=None, tags=None):
        """
        Parameters:
        -----------
        org_ids : list
            list of all organization for scraping

        tags : list of tags, default all available event tags
            Event tags (title, id, url etc.,
            see all tags in 'escraper.ALL_EVENT_TAGS')

        Examples:
        ----------
        >>> tcloud = Ticketscloud()
        >>> org_ids = ['5dce558174fd6b0bcaa66524', '5e3d551b44d20ecf697408e4', '5e3bec5fea9c82d6958f8551']
        >>> tags = ("adress",
            "date_from","date_to","place_name",
            "post_text","price",
            "title",
            "url", "org_id", "poster_imag")
        >>> tcloud.get_events(org_ids=org_ids, tags=tags)  # doctest: +SKIP
        """
        if org_ids is None: org_ids = ORG_IDS

        events = list()

        for org_id in org_ids:
            url = f"https://{org_id}.ticketscloud.org"
            response = self._request_get(url)

            if response:
                soup = BeautifulSoup(response.text, 'lxml')
                list_event_from_soup = all_events = soup.find('div', class_='u-flex u-flex--wrap').find_all('div', class_='ticketscloud-event-item col-md-4')

            else:
                list_event_from_soup = list()

            for event_card in list_event_from_soup:

                self.url = url + event_card.find('a').get('href')

                event_soup = BeautifulSoup(
                        self._request_get(self.url).text, "html.parser"
                    )
                events.append(self.parse(event_soup, tags=tags or ALL_EVENT_TAGS))


        return events

    def _adress(self, event_soup): #+
        full_address = re.sub('\s+', ' ', event_soup.find('article', class_='col-md-9 col-sm-12').find('span').text.strip())

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
        return

    # def _datetimes_from_html(self, event_soup):
    #     """
    #     Parse datetimes (from and to) from html page.
    #     Use only in Radario._date_from()
    #     """
    #     strfdatetime = self._date_from_to(event_soup)
    #
    #     day_from = None
    #     month_from = None
    #     hour_from = None
    #     minute_from = None
    #
    #     day_to = None
    #     month_to = None
    #     hour_to = None
    #     minute_to = None
    #
    #     # can parse from-to datetime string formats:
    #     # - "dd month, HH:MM-HH:MM"
    #     # - "dd month, HH:MM"
    #     # - "dd-dd month"
    #     if not re.match(r"^\d\d \w+,", strfdatetime) and not re.match(
    #         r"^\d\d-\d\d \w+$", strfdatetime
    #     ):
    #         raise ValueError(
    #             f"Unknown radario from-to datetime string: {strfdatetime!r}.\n"
    #             f"Event url: {self._url(event_soup)}"
    #         )
    #
    #     # dd month+
    #     if re.match(r"^\d\d \w+,", strfdatetime):
    #         day_from = int(strfdatetime[:2])
    #         month_from = int(monthes[strfdatetime[3:].split(",")[0]])
    #
    #         day_to = day_from
    #         month_to = month_from
    #
    #         # dd month, HH:MM
    #         if re.match(r"\d{2} \w+, \d{2}:\d{2}$", strfdatetime):
    #             strtime_from = strfdatetime[-5:]
    #
    #             hour_from = int(strtime_from.split(":")[0])
    #             minute_from = int(strtime_from.split(":")[1])
    #
    #         # dd month, HH:MM-HH:MM
    #         elif re.match(r"\d{2} \w+,.+\d{2}:\d{2}-\d{2}:\d{2}", strfdatetime):
    #             strtime_from = strfdatetime[-11:-6]
    #             hour_from = int(strtime_from.split(":")[0])
    #             minute_from = int(strtime_from.split(":")[1])
    #
    #             strtime_to = strfdatetime[-5:]
    #             hour_to = int(strtime_to.split(":")[0])
    #             minute_to = int(strtime_to.split(":")[1])
    #
    #     # dd-dd month
    #     elif re.match(r"^\d\d-\d\d \w+$", strfdatetime):
    #         day_from = int(strfdatetime[:2])
    #         month_from = int(monthes[strfdatetime[6:]])
    #         hour_from = 0
    #         minute_from = 0
    #
    #         day_to = int(strfdatetime[3:5])
    #         month_to = month_from
    #         hour_to = 0
    #         minute_to = 0
    #
    #     daytime_from = datetime.now(tz=self.TIMEZONE).replace(
    #         month=month_from,
    #         day=day_from,
    #         hour=hour_from,
    #         minute=minute_from,
    #         second=0,
    #         microsecond=0,
    #     )
    #
    #     if hour_to is not None and minute_to is not None:
    #         daytime_to = datetime.now(tz=self.TIMEZONE).replace(
    #             month=month_to,
    #             day=day_to,
    #             hour=hour_to,
    #             minute=minute_to,
    #             second=0,
    #             microsecond=0,
    #         )
    #     else:
    #         daytime_to = None
    #
    #     return daytime_from, daytime_to

    def _date_from(self, event_soup):
        return re.sub('\s+', ' ', event_soup.find('div', class_='event-info-se__address-part').find('time').text.strip())

    def _date_to(self, event_soup): #TODO: take from <script> tc_event
        return re.sub('\s+', ' ', event_soup.find('div', class_='event-info-se__address-part').find('time').text.strip())

    def _date_from_to(self, event_soup): #+/-
        """
        Parse date from and to as string from event page.
        """
        return self._date_from

    def _id(self, event_soup):
        script_num = 2
        tc_event = event_soup.find('body').find('script')[2].content
        print(tc_event)


        return 1

    def _place_name(self, event_soup): #+
        address_name = re.sub('\s+', ' ',
                              event_soup.find('div', class_='event-info-se__address-part').find('address').text.strip())
        return re.sub('Санкт-Петербург, ', '', address_name)

    def _post_text(self, event_soup): #+
        # post_text = self.remove_html_tags(
        #     event_soup.find("meta", property="og:description")["content"].replace(
        #         "<br/>", "\n"
        #     )
        # )
        if event_soup.find('article',
                     class_='col-md-9 col-sm-12 showroom-event-slide__content showroom-event-slide__content_desc'):
            post_text = re.sub(r'\.(\w)', r'. \1', event_soup.find('article', class_='col-md-9 col-sm-12 showroom-event-slide__content showroom-event-slide__content_desc').find('p').text)
        else:
            post_text = ''
        return self.prepare_post_text(post_text)

    def _poster_imag(self, event_soup): #TODO: check if exists and better regular
        image_dict = re.findall(r'"logo":\{(.*?)\}', str(event_soup.contents))
        if not image_dict:
            image_dict = re.findall(r'"cover_original":\{(.*?)\}', str(event_soup.contents))
        if not image_dict: return
        image_url = json.loads('{'+image_dict[0]+'}')['url']
        # event_card_image = event_soup.find("img", {"class": "event-page__image"})
        # if (
        #     event_card_image is not None
        #     and "DefaultEventImage" not in event_card_image["src"]
        # ):
        #     return event_card_image["src"]
        return image_url

    def _price(self, event_soup): #+
        return re.sub('\s+', ' ', event_soup.find('div', class_='buy-button-se__button').text.strip())

    def _title(self, event_soup): #+
        return add_emoji(
            event_soup.find('div', class_='event-info-se__title').text.strip()
        )

    def _url(self, event_soup): #todo:
        return self.url

    def _is_registration_open(self, event_soup): #todo: need to find
        return self._price(event_soup) != "Билетов нет"

    def _org_id(self, event_soup):
        return (str(re.findall(r'"org":{"id":"\w+"', str(event_soup.contents)))[15:-3])
