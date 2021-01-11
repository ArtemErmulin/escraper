import os,time
from datetime import datetime

import requests

from .base import BaseParser, ALL_EVENT_TAGS
from .utils import STRPTIME
from ..emoji import add_emoji

from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(__file__), 'misk/vk.env')

divide_list = lambda lst, sz: [lst[i:i+sz] for i in range(0, len(lst), sz)]

class VK(BaseParser):
    name = "VK"
    BASE_URL = 'https://vk.com/'
    BASE_URL_API = "https://api.vk.com/method/"

    parser_prefix = "VK-"
    quantity = 200 #max 1000

    count_query = 250
    def __init__(self, token=None):
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
        if token is None:
            token = os.environ['VK_TOKEN']
        user_id = os.environ['VK_ID']
        self.get_end_str = f'&access_token={token}&expires_in=86400&user_id={user_id}&v=5.103'


    def get_event(self):
        """Get one event by url / event_id"""

    def get_events(self):
        event_data_general = []
        offset_count_query = 0
        while self.quantity > offset_count_query:
            res, quantity_answer = self.request_events(count=self.count_query, offset=offset_count_query)
            event_data_general += res
            offset_count_query += self.count_query
            if quantity_answer < self.quantity: self.quantity = quantity_answer
        #print(event_data_general)
        event_ids = self.get_ids(event_data_general)
        event_data_full = []
        for event_ids_divided in divide_list(event_ids, 200):
            event_data_full += self.get_full_event(event_ids_divided)

        event_data_full = self.check_events(event_data_full)
        #event_data_full = self.add_address(event_data_full)

        tags = ALL_EVENT_TAGS
        events = list()
        for event in event_data_full:
            events.append(self.parse(event, tags=tags))

        return events

    def get_ids(self, events):
        return [event['id'] for event in events]

    def get_full_event(self,ids):
        now = datetime.timestamp(datetime.now())
        #finish_date = now + 60 * 60 * 24 * 30
        if len(ids) < 500:
            site = f"{self.BASE_URL_API}/groups.getById?group_ids={ids}&fields=addresses,site,description,status,cover,place,start_date,finish_date{self.get_end_str}"
            # print(site)
            req = requests.get(site)
            events = req.json()['response']
            return events

    def check_events(self, events):
        bad_events_index = list()
        for i, event in enumerate(events):
            if datetime.fromtimestamp(int(event['start_date'])).year!=datetime.today().year:
                bad_events_index.append(i)
                continue
            if 'finish_date' in event:
                if datetime.fromtimestamp(int(event['finish_date'])).year != datetime.today().year:
                    bad_events_index.append(i)
                    continue
        bad_events_index.reverse()
        for i in bad_events_index: events.pop(i)
        return events

    # def add_address_in_loop(self, events):
    #     for i, event in enumerate(events):
    #         if "main_address_id" in event['addresses']:
    #             site = f"{self.BASE_URL_API}/groups.getAddresses?group_id={event['id']}&address_ids={event['addresses']['main_address_id']}&fields=title,address{self.get_end_str}"
    #             req = requests.get(site)
    #             addresses = req.json()
    #             print(addresses)
    #             if addresses['response']['count']>0:
    #                 events[i]['addresses']['address'] = addresses['response']['items'][0]['address']
    #                 events[i]['addresses']['place_name'] = addresses['response']['items'][0]['title']
    #         time.sleep(0.2)
    #     return events

    def add_address(self, event):
        site = f"{self.BASE_URL_API}/groups.getAddresses?group_id={event['id']}&address_ids={event['addresses']['main_address_id']}&fields=title,address{self.get_end_str}"
        req = requests.get(site)
        addresses = req.json()
        print(addresses)
        if addresses['response']['count'] > 0:
            event['addresses']['address'] = addresses['response']['items'][0]['address']
            event['addresses']['place_name'] = addresses['response']['items'][0]['title']
        else:
            event['addresses']['address'] = ''
            event['addresses']['place_name'] = ''
        time.sleep(0.25)
        return event


    def request_events(self, q='%20', city_id=2, count=250, offset=0):
        site = f'{self.BASE_URL_API}/groups.search?q={q}&type=event&future=1&city_id={city_id}&count={count}&offset={offset}{self.get_end_str}'
        req = requests.get(site)
        events = req.json()
        count = events['response']['count']
        events = events['response']['items']
        return events, count


    def _adress(self, event): #TODO: get address
        if "main_address_id" in event['addresses']:
            if "address" not in event['addresses']:
                event = self.add_address(event)
            address_id = event['addresses']['address']
            return address_id
        return 'Санкт-Петербург'

    def _category(self, event):
        return 'vk'

    def _date_from(self, event):
        return datetime.fromtimestamp(int(event['start_date']))

    def _date_to(self, event):
        if "finish_date" in event:
            return datetime.fromtimestamp(int(event['finish_date']))
        return None

    def _date_from_to(self, event):
        """Event date from-to in readable string format (may be None)"""
        return None

    def _id(self, event):
        return self.parser_prefix + str(event["id"])

    def _place_name(self, event): #TODO: another parameter
        if "main_address_id" in event['addresses']:
            if "address" not in event['addresses']:
                event = self.add_address(event)
            address_id = event['addresses']['place_name']
            return address_id
        return 'Санкт-Петербург'

    def _post_text(self, event):
        post_text = event['description']
        url = f"\nПодробности: {self.BASE_URL}{event['screen_name']}"
        return self.prepare_post_text(post_text)+url


    def _poster_imag(self, event):
        if event['cover']['enabled']!=0:
            cover_url = event['cover']['images'][-1]['url']
            return cover_url
        else:
            return None
    def _url(self,event):
        if event['site']!='':
            return event['site']
        elif 'screen_name' in event:
            return f"{self.BASE_URL}{event['screen_name']}"
        return None

    def _price(self, event):
        return " "

    def _title(self, event):
        return add_emoji(event["name"])

    def _is_registration_open(self, event):
        return True

