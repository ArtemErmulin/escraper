from datetime import datetime, timedelta
import logging
import os
import re
import pytz

from .base import BaseParser, ALL_EVENT_TAGS
from ..emoji import add_emoji

logger = logging.getLogger(__name__)


class Tripster(BaseParser):
    """
    Parse events (excursions/tours) from experience.tripster.ru by partner API:
    https://experience.tripster.ru/api/partners/{partner_id}/search/experiences/

    Methods:
    --------

    get_event(exp_id=None, exp_url=None)
        Получает подробности экскурсии/тура по id или URL.

    get_events(request_params=None, tags=None, existed_event_ids=None, days_forward=7)
        Список экскурсий/туров в городе (по умолчанию СПб), с фильтрами на даты, exclude_ids и ticket availability.

    """

    name = "tripster"
    url = "experience.tripster.ru"
    search_api = "https://experience.tripster.ru/api/partners/{partner_id}/search/experiences/"
    timezone = pytz.timezone("Europe/Moscow")
    source = "TRIPSTER"
    FIELDS = (
        "id", "title", "tagline", "annotation", "description", "url", "photos", "schedule",
        "duration", "meeting_point", "finish_point", "price", "review_count", "rating",
        "popularity", "city", "guide", "tags", "status", "type", "child_friendly", "max_persons"
    )

    DEFAULT_CITY_SLUGS = ["Saint_Petersburg", "Kazan"]

    def __init__(self, token=None, partner_id=None, use_proxy=True):
        super().__init__(use_proxy=use_proxy)
        if token is None:
            token = os.getenv("TRIPSTER_TOKEN")
        if partner_id is None:
            partner_id = os.getenv("TRIPSTER_PARTNER_ID")
        if not token or not partner_id:
            raise ValueError("Tripster token or partner_id not found.")
        self._token = token
        self.partner_id = partner_id
        self.headers = {"Authorization": f"Bearer {self._token}"}

    def get_event(self, exp_id=None, exp_url=None, tags=None):
        if exp_url is not None:
            m = re.search(r"(?:experience|tour)/(\d+)", exp_url)
            exp_id = m.group(1) if m else None
        if exp_id is None:
            raise ValueError("'exp_id' or 'exp_url' required.")

        url = f"https://experience.tripster.ru/api/partners/{self.partner_id}/experiences/{exp_id}/?detailed=true"

        if 'PROXY' in os.environ:
            proxy = os.environ.get("PROXY")
            proxies = {'http': proxy, 'https': proxy}
            response_json = self._request_get(url, headers=self.headers, proxies=proxies).json()
        else:
            response_json = self._request_get(url, headers=self.headers).json()

        tags = tags or ALL_EVENT_TAGS
        # Аналога модерации нет — проверяем, что status = active
        if response_json.get("status") == "active":
            event = self.parse(response_json, tags=tags)
        else:
            event = None
        return event

    def get_events(self, request_params=None, tags=None, existed_event_ids=None):
        """
        Parameters:
        -----------
        request_params : dict, default None
            Фильтры для Tripster: см. доку https://tripster.atlassian.net/wiki/spaces/affiliates/pages/3736502388/8.
            (city__slug, tags, type, persons_count и др.)

        tags : list, default all tags

        existed_event_ids : list, default None
            Список TRIPSTER-id для пропуска (exclude_ids).


        Основные поддерживаемые фильтры:
            - city__slug (по умолчанию Sankt-Peterburg/Kazan)
            - start_date, end_date
            - exclude_ids
            - need_upcoming_events: true (только где есть будущие даты)
            - status: active
            - detailed: true

        Example:
        --------
            params = {"city__slug": "Kazan", "type": "group"}
            tripster.get_events(params, days_forward=5, existed_event_ids=["TRIPSTER-1234"])
        """
        request_params = request_params or {}
        tags = tags or ALL_EVENT_TAGS
        existed_event_ids = existed_event_ids or []

        # По умолчанию город — СПб
        if "city__slug" not in request_params:
            request_params["city__slug"] = self.DEFAULT_CITY_SLUGS[0]

        today = datetime.now().date()
        if 'days' in request_params:
            days_forward = int(request_params.pop('days'))
        else:
            days_forward = 7

        end = today + timedelta(days=days_forward)
        request_params["start_date"] = today.strftime("%Y-%m-%d")
        request_params["end_date"] = end.strftime("%Y-%m-%d")

        if existed_event_ids:
            tripster_ids = [str(eid).split('-')[-1] for eid in existed_event_ids]
            request_params["exclude_ids"] = ",".join(tripster_ids)

        request_params["need_upcoming_events"] = "true"
        request_params["detailed"] = "true"
        request_params["include_paid"] = "false"

        # TODO: add pagination via 'next' in response if needed
        url = self.search_api.format(partner_id=self.partner_id)
        if 'PROXY' in os.environ:
            proxy = os.environ.get("PROXY")
            proxies = {'http': proxy, 'https': proxy}
            res = self._request_get(url, params=request_params, headers=self.headers, proxies=proxies)
        else:
            res = self._request_get(url, params=request_params, headers=self.headers)
        logger.debug("TRIPSTER: response payload: %s", res.json())
        for obj in res.json().get("results", []):
            #print(obj)
            if obj["status"] == "active" and obj.get("schedule", {}).get("upcoming_events"):  # есть свободные даты
                yield self.parse(obj, tags=tags)

    def _adress(self, event):
        if event.get("meeting_point") and event["meeting_point"].get("text"):
            return self.remove_html_tags(event["meeting_point"]["text"])
        if event.get("city") and event["city"].get("name_ru"):
            return self.remove_html_tags(event["city"]["name_ru"])
        return "Онлайн"




    def _category(self, event):
        movement_type = event.get("movement_type")
        movement_type_to_category = {
            "foot": "Экскурсия пешком", "car": "Экскурсия на транспорте", "bicycle": "Экскурсия на велосипеде",
            "bus": "Экскурсия на автобусе", "motorship": "Экскурсия по воде", "waterwalk": "Экскурсия по воде",
            "museum": "Экскурсия по музею", "motorcycle": "Экскурсия на мотоцикле",
            "room": "Экскурсия",
        }
        if movement_type in movement_type_to_category.keys():
            return movement_type_to_category[movement_type]

        return 'Экскурсия'

    def _date_from(self, event):
        schedule = event.get("schedule", {})
        events = schedule.get("upcoming_events")
        if events:
            return datetime.fromisoformat(events[0])
        return None

    def _date_to(self, event):
        date_from = self._date_from(event)
        duration = event.get("duration")
        if date_from and duration:
            return date_from + timedelta(hours=duration)
        return None

    def _date_from_to(self, event):
        return None

    def _id(self, event):
        return f"{self.source}-{event['id']}"

    def _place_name(self, event):
        guide = event.get("guide", {})
        return self.remove_html_tags(guide.get("first_name", ""))

    def _full_text(self, event):
        for key in ("description", "annotation", "tagline"):
            txt = event.get(key)
            if txt:
                return self.remove_html_tags(txt)
        return ""

    def _post_text(self, event):
        short = event.get("tagline") or event.get("annotation")
        return self.prepare_post_text(self.remove_html_tags(short) if short else "")

    def _poster_imag(self, event):
        poster_image = None
        if "photos" in event and event["photos"]:
            ph = event["photos"][0]
            poster_image = ph.get("medium") or ph.get("thumbnail")
        if "images" in event and event["images"]:
            ph = event.get("images", "cover")
            poster_image = ph.get("thumbnail") or ph.get("medium")

        if poster_image:
            poster_image = poster_image.split('()/')[-1]
        return poster_image

    def _price(self, event):
        price_obj = event.get("price", {})
        value = price_obj.get("value")

        if price_obj.get("currency") == "RUB":
            currency = "₽"
        else:
            currency = price_obj.get("currency")

        if value is None:
            return "Билетов нет"
        return f"{int(value)} {currency}"

    def _title(self, event):
        return add_emoji(self.remove_html_tags(event.get("title", "")))

    def _url(self, event):
        return event.get("url", "")

    def _ticket_url(self, event):
        return self._url(event) + f"?exp_partner={self.partner_id}&utm_source={self.partner_id}&utm_campaign=affiliates&utm_medium=link"

    def _source(self, event) -> str:
        return self.source

    def _is_registration_open(self, event):
        return int(event["status"] == "active" and bool(event.get("schedule", {}).get("upcoming_events")))

    @property
    def event_categories(self):
        url = f"https://experience.tripster.ru/api/partners/{self.partner_id}/citytags/"
        return self._request_get(url, headers=self.headers).json().get("results", [])
