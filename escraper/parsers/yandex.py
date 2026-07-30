import json
import logging
import re
from datetime import datetime, timedelta

from .base import BaseParser, ALL_EVENT_TAGS
from ..emoji import add_emoji

logger = logging.getLogger(__name__)


class Yandex(BaseParser):
    name = "yandex"
    source = "YA"
    BASE_URL = "https://afisha.yandex.ru"
    parser_prefix = "YA-"

    def __init__(self, use_proxy=True):
        super().__init__(use_proxy=use_proxy)
        self.url = self.BASE_URL
        self.event_url = None

    # ──────────────────────────────────────────────────
    # Apollo state extraction
    # ──────────────────────────────────────────────────

    @staticmethod
    def _balanced_json_object(text, start):
        """Return text[start:end+1] where text[start] == '{' and braces balance.

        Tracks string state so braces inside strings don't affect depth.
        """
        depth = 0
        in_string = False
        escaped = False
        for i in range(start, len(text)):
            c = text[i]
            if in_string:
                if escaped:
                    escaped = False
                elif c == "\\":
                    escaped = True
                elif c == '"':
                    in_string = False
            else:
                if c == '"':
                    in_string = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
        return None

    @classmethod
    def _extract_apollo_state(cls, html):
        """Extract and decode ``window['__APOLLO_STATE__']`` from page HTML.

        The assignment shares a <script> with other ``window[...]`` globals, so
        the object is brace-balanced rather than matched up to ``</script>``.
        It is a JS object literal (not strict JSON): ``new Date("...")`` and
        ``undefined`` are sanitized before parsing.
        """
        marker = "window['__APOLLO_STATE__']"
        idx = html.find(marker)
        if idx == -1:
            return {}
        start = html.find("{", idx)
        if start == -1:
            return {}

        raw = cls._balanced_json_object(html, start)
        if raw is None:
            return {}

        raw = re.sub(r'new Date\(\s*(\"[^\"]*\"|\d+)\s*\)', r"\1", raw)
        raw = re.sub(r"(?<=[:,\[])\s*undefined\s*(?=[,}\]])", "null", raw)

        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("YA: failed to parse Apollo state: %s", e)
            return {}

    @staticmethod
    def _deref(state, value, depth=0):
        """Resolve an Apollo ``{"__ref": ...}`` link to its object (one hop)."""
        if depth > 5:
            return value
        if isinstance(value, dict) and "__ref" in value:
            return state.get(value["__ref"], value)
        return value

    @classmethod
    def _root_query_value(cls, state, prefix):
        """Return the first ROOT_QUERY entry whose key starts with ``prefix``.

        ROOT_QUERY keys carry serialized arguments (e.g.
        ``event({"id":"..."})``), so they are matched by prefix.
        """
        root = state.get("ROOT_QUERY", {})
        for key, value in root.items():
            if key.split("(", 1)[0] == prefix:
                return cls._deref(state, value)
        return None

    # ──────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────

    def get_event(self, event_url=None, tags=None, requested_date=None):
        """Fetch and parse a single afisha.yandex.ru event page.

        Parameters
        ----------
        event_url : str
            Full URL of the event page.
        tags : list, optional
            Event tags to return. Defaults to ALL_EVENT_TAGS.
        requested_date : datetime.date, optional
            When the event runs several sessions, pick the one on this date.
            When absent, the nearest upcoming session is used.
        """
        if event_url is None:
            raise ValueError("'event_url' required.")

        response = self._request_get(event_url)
        if not response:
            logger.warning("YA: failed to fetch event page: %s", event_url)
            return None

        state = self._extract_apollo_state(response.text)
        if not state:
            logger.warning("YA: no Apollo state found on page: %s", event_url)
            return None

        event = self._root_query_value(state, "event")
        if not event:
            event = next(
                (v for k, v in state.items()
                 if k.startswith("Event:") and isinstance(v, dict)
                 and v.get("__typename") == "Event"),
                None,
            )
        if not event:
            logger.warning("YA: no Event object found in Apollo state: %s", event_url)
            return None

        self.event_url = event_url
        event_data = self._normalize(state, event, requested_date)
        return self.parse(event_data, tags=tags or ALL_EVENT_TAGS)

    def get_events(self, request_params=None, tags=None, existed_event_ids=None):
        """
        Parameters:
        -----------
        request_params : dict
            city : str, default 'saint-petersburg'
                City slug from afisha.yandex.ru URL

            categories : list, default concert, theatre, festival, standup, show, kids, sport
                Event categories on afisha.yandex.ru

            date_from, date_to : str, default tomorrow + 1 day
                Events date range in 'YYYY-MM-DD' format

            days : int, default 1
                Range between date_from and date_to

        tags : list of tags, default all available event tags

        existed_event_ids : list of event IDs to skip
            YA-some-slug, etc.

        Examples:
        ----------
        >>> ya = Yandex()
        >>> request_params = {
            "date_from": "2024-05-01",
            "date_to":   "2024-05-05",
            "city":      "saint-petersburg"
        }
        >>> list(ya.get_events(request_params=request_params))  # doctest: +SKIP

        Yields parsed events one at a time as they are scraped (generator).
        """
        request_params = request_params or {}
        existed_event_ids = list(existed_event_ids) if existed_event_ids else []

        city = request_params.get("city", "saint-petersburg")
        url = self.url + "/" + city

        if "date_from" in request_params:
            date_from = datetime.strptime(request_params["date_from"], "%Y-%m-%d")
        else:
            date_from = datetime.today() + timedelta(days=2)

        if "date_to" in request_params:
            date_to = datetime.strptime(request_params["date_to"], "%Y-%m-%d")
        elif "days" in request_params:
            date_to = date_from + timedelta(days=int(request_params["days"]))
        else:
            date_to = date_from + timedelta(days=1)

        categories = request_params.get(
            "categories",
            ["concert", "theatre", "festival", "standup", "show", "kids", "sport"],
        )

        for category in categories:
            category_url = url + "/" + category
            scrape_date = date_from
            while scrape_date <= date_to:
                scrape_url = category_url + f"?date={scrape_date.date()}&period=1"
                response = self._request_get(scrape_url)
                if not response:
                    scrape_date += timedelta(days=1)
                    continue

                state = self._extract_apollo_state(response.text)
                if not state:
                    scrape_date += timedelta(days=1)
                    continue

                for key, value in state.items():
                    if not key.startswith("EventPreview:") or not isinstance(value, dict):
                        continue

                    event_path = value.get("url")
                    if not event_path:
                        continue

                    event_url = self.url + event_path
                    event_id = self._id_from_url(event_url)
                    if event_id in existed_event_ids:
                        continue

                    event = self.get_event(
                        event_url=event_url,
                        tags=tags,
                        requested_date=scrape_date.date(),
                    )
                    if event is not None:
                        existed_event_ids.append(event_id)
                        yield event

                scrape_date += timedelta(days=1)

    # ──────────────────────────────────────────────────
    # Normalization — resolve the current GraphQL schema into a flat dict
    # ──────────────────────────────────────────────────

    def _normalize(self, state, event, requested_date):
        """Flatten the Apollo graph into the dict the ``_field`` methods read."""
        # --- place / address ---
        place = self._root_query_value(state, "place")
        if not isinstance(place, dict) or not place.get("title"):
            schedule_info = self._root_query_value(state, "eventScheduleInfo") or {}
            place = self._deref(
                state,
                schedule_info.get("onlyPlace") or schedule_info.get("oneOfPlaces") or {},
            )
        place = place if isinstance(place, dict) else {}

        # --- category (Event.type -> Tag.name) ---
        tag = self._deref(state, event.get("type") or {})
        category = tag.get("name", "") if isinstance(tag, dict) else ""

        # --- session date/time ---
        date_from = self._pick_session(state, requested_date)
        date_to = date_from + timedelta(hours=3) if date_from else None

        # --- price / sale status (first ticket) ---
        price, sale_status = self._ticket_info(state, event)

        return {
            "event": event,
            "place": place,
            "category": category,
            "date_from": date_from,
            "date_to": date_to,
            "price": price,
            "sale_status": sale_status,
            "poster": self._image_url(event),
        }

    def _pick_session(self, state, requested_date):
        """Choose a session datetime: the requested day, else nearest upcoming."""
        other = self._root_query_value(state, "eventScheduleOther") or {}
        sessions = {}  # 'YYYY-MM-DD' -> naive datetime string
        for group in other.get("byDate", []) or []:
            group_sessions = group.get("sessions") or []
            for s in group_sessions:
                dt = (s.get("session") or {}).get("datetime")
                if dt:
                    sessions.setdefault(group.get("date"), dt)
                    break

        def localize(dt_str):
            return self.TIMEZONE.localize(datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S"))

        if requested_date is not None:
            key = requested_date.isoformat()
            if key in sessions:
                return localize(sessions[key])

        if sessions:
            today = datetime.now(self.TIMEZONE).date()
            ordered = sorted(sessions.items())
            for day, dt_str in ordered:
                if day and day >= today.isoformat():
                    return localize(dt_str)
            return localize(ordered[0][1])

        # Fallback: schedule info holds date-only values, no session time.
        info = self._root_query_value(state, "eventScheduleInfo") or {}
        dates = info.get("dates") or []
        chosen = None
        if requested_date is not None and requested_date.isoformat() in dates:
            chosen = requested_date.isoformat()
        elif dates:
            chosen = dates[0]
        if chosen:
            return self.TIMEZONE.localize(datetime.strptime(chosen, "%Y-%m-%d"))
        return None

    def _ticket_info(self, state, event):
        """Return (min_price_rub_or_None, sale_status) from the event's ticket."""
        tickets = event.get("tickets") or []
        for ref in tickets:
            ticket = self._deref(state, ref)
            if not isinstance(ticket, dict):
                continue
            price_obj = ticket.get("price") or {}
            min_kopecks = price_obj.get("min")
            price = int(min_kopecks) // 100 if min_kopecks is not None else None
            return price, ticket.get("saleStatus", "")
        return None, ""

    @staticmethod
    def _image_url(event):
        """Return a poster URL from Event.images (prefers the 'origin' size)."""
        images = event.get("images") or []
        if not images:
            return None
        img = images[0]
        best = None
        for key, value in img.items():
            if key.startswith("image(") and isinstance(value, dict) and value.get("url"):
                if "origin" in key:
                    return value["url"]
                best = best or value["url"]
        return best

    # ──────────────────────────────────────────────────
    # Field extractors
    # ──────────────────────────────────────────────────

    def _adress(self, event_data):
        address = (event_data.get("place") or {}).get("address") or ""
        address = address.strip()
        return (
            address.replace("г. Санкт-Петербург, ", "")
            .replace("г Санкт-Петербург, ", "")
            .replace("Санкт-Петербург, ", "")
        )

    def _category(self, event_data):
        return event_data.get("category", "")

    def _date_from(self, event_data):
        self._date_from_ = event_data.get("date_from")
        return self._date_from_

    def _date_to(self, event_data):
        self._date_to_ = event_data.get("date_to")
        return self._date_to_

    def _date_from_to(self, event_data):
        date_from = event_data.get("date_from")
        date_to = event_data.get("date_to")
        if date_from and date_to:
            return f"{date_from.date()} – {date_to.date()}"
        elif date_from:
            return str(date_from.date())
        return ""

    def _id(self, event_data):
        return self._id_from_url(self.event_url)

    def _id_from_url(self, event_url):
        slug = event_url.rstrip("/").split("?")[0].split("/")[-1]
        return self.parser_prefix + slug

    def _place_name(self, event_data):
        return (event_data.get("place") or {}).get("title", "").strip()

    def _full_text(self, event_data) -> str:
        event = event_data["event"]
        html = event.get("descriptionHtml") or event.get("description") or ""
        if not html:
            return ""
        if "<" in html:
            return self.remove_html_tags(html.replace("<p>", "\n")).strip()
        return html.strip()

    def _post_text(self, event_data):
        return self.prepare_post_text(self._full_text(event_data))

    def _poster_imag(self, event_data):
        return event_data.get("poster")

    def _price(self, event_data):
        price = event_data.get("price")
        if price is not None:
            return str(price) + "₽"
        return "на сайте"

    def _title(self, event_data):
        return add_emoji(event_data["event"]["title"].strip())

    def _url(self, event_data):
        if self.event_url is not None:
            return self.event_url
        url_path = event_data["event"].get("url", "")
        return self.BASE_URL + url_path if url_path else ""

    def _ticket_url(self, event_data) -> str:
        return self._url(event_data)

    def _source(self, event_data) -> str:
        return self.source

    def _is_registration_open(self, event_data):
        return event_data.get("sale_status") == "available"
