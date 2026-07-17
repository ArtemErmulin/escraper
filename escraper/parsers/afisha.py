import json
import logging
import re
from datetime import datetime, timedelta

from .base import BaseParser, ALL_EVENT_TAGS
from ..emoji import add_emoji

logger = logging.getLogger(__name__)


def _parse_afisha_dt(date_str):
    """Parse an afisha.ru ld+json datetime to a Moscow-aware datetime.

    afisha.ru stores dates like ``"2026-08-22T23:00:00, +03:00"`` — an ISO
    timestamp with a stray ``", "`` before the UTC offset. The offset is
    already correct, so we drop the separator and normalize to Moscow time.
    """
    cleaned = date_str.replace(", ", "").strip()
    dt = datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S%z")
    return dt.astimezone(BaseParser.TIMEZONE)


class Afisha(BaseParser):
    """Parser for afisha.ru city sites (spb.afisha.ru, msk.afisha.ru, ...).

    ``get_events`` scrapes a category listing page for event links, then
    ``get_event`` parses the ld+json (schema.org) block embedded on each
    event page. Descriptions are read from the page DOM.
    """

    name = "afisha"
    BASE_URL = "https://www.afisha.ru"
    source = "AFISHA"
    REQUEST_DELAY = 1.0
    DEFAULT_REQUEST_TIMEOUT = 40

    # afisha.ru category slugs used in listing URLs: /{city}/{category}/
    # Full set of event listings: concerts, cinema, theatre, exhibitions,
    # festivals, standup, musicals, kids, sports, party, excursions, events.
    # (/{city}/places/ is a venue directory, not events.)
    DEFAULT_CATEGORIES = [
        "concerts", "cinema", "theatre", "exhibitions", "standup",
        "festivals", "musicals", "party"
    ]

    def __init__(self, use_proxy=True):
        super().__init__(use_proxy=use_proxy)
        self.event_url = None

    def get_event(self, event_url=None, tags=None):
        """Fetch and parse a single afisha.ru event page.

        Parameters
        ----------
        event_url : str
            Full URL of the event page, e.g.
            https://www.afisha.ru/concert/basta-6023789/
        tags : list, optional
            Event tags to return. Defaults to ALL_EVENT_TAGS.
        """
        if event_url is None:
            raise ValueError("'event_url' required.")

        body = self._request_get(event_url).text

        event_json, category = self._extract_ld_json(body)
        if event_json is None:
            raise ValueError("Can't find event ld+json on page")

        event_data = {
            "event": event_json,
            "category": category,
            "description": self._extract_description(body),
        }

        self.event_url = event_url
        return self.parse(event_data, tags=tags or ALL_EVENT_TAGS)

    def get_events(self, request_params=None, tags=None, existed_event_ids=None):
        """Scrape events from afisha.ru category listings.

        Parameters
        ----------
        request_params : dict
            city : str, default "spb"
                City slug in the listing URL: spb, msk, ekb, ...

            categories : list of str
                Category slugs to scrape. Defaults to DEFAULT_CATEGORIES:
                    concerts, cinema, theatre, exhibitions, standup
                Other available slugs: festivals, musicals, kids, sports,
                party, excursions, events.

            date_from, date_to : str 'YYYY-MM-DD'
                Optional date range. Events whose start date falls outside
                the range are skipped.

            days : int
                Number of days from date_from. Used when date_to is absent.

        Notes
        -----
        afisha.ru has no URL-based pagination or server-side date filter — a
        category listing already renders every distinct event currently on
        sale, spanning months ahead (e.g. concerts today .. ~5 months out).
        So a single listing fetch is the full inventory; to get "one month"
        of events, pass ``date_from``/``date_to`` and each event is filtered
        by its parsed start date.

        tags : list, optional
            Event tags to return. Defaults to ALL_EVENT_TAGS.

        existed_event_ids : list
            Event IDs to skip, e.g. ["AFISHA-6023789", "AFISHA-2266090"].

        Examples
        --------
        >>> afisha = Afisha()
        >>> list(afisha.get_events(request_params={
        ...     "city": "spb",
        ...     "categories": ["concerts"],
        ... }))  # doctest: +SKIP

        Yields parsed events one at a time as event pages are scraped (generator).
        """
        request_params = request_params or {}
        existed_event_ids = list(existed_event_ids) if existed_event_ids else []

        city = request_params.get("city", "spb")
        categories = request_params.get("categories", self.DEFAULT_CATEGORIES)

        date_from = None
        date_to = None
        if "date_from" in request_params:
            date_from = self.TIMEZONE.localize(
                datetime.strptime(request_params["date_from"], "%Y-%m-%d")
            )
            if "date_to" in request_params:
                date_to = self.TIMEZONE.localize(
                    datetime.strptime(request_params["date_to"], "%Y-%m-%d")
                )
            elif "days" in request_params:
                date_to = date_from + timedelta(days=int(request_params["days"]))

        for category in categories:
            listing_url = f"{self.BASE_URL}/{city}/{category}/"
            response = self._request_get(listing_url)
            if not response:
                continue

            for event_url in self._extract_event_urls(response.text):
                event_id = self._id_from_url(event_url)
                if event_id in existed_event_ids:
                    continue

                try:
                    event = self.get_event(event_url=event_url, tags=tags)
                except (ValueError, KeyError, json.JSONDecodeError) as e:
                    logger.warning("AFISHA: skipping event %s: %s", event_url, e)
                    continue

                existed_event_ids.append(event_id)

                if date_from is not None and getattr(self, "_date_from_", None):
                    if self._date_from_ < date_from:
                        continue
                    if date_to is not None and self._date_from_ > date_to:
                        continue

                yield event

    def _extract_event_urls(self, page_text):
        """Return de-duplicated absolute event URLs from a listing page."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(page_text, "lxml")
        seen = set()
        urls = []
        for card in soup.select('[data-test="LINK ITEM-NAME ITEM-URL"]'):
            href = (card.get("href") or "").split("?")[0]
            if not re.search(r"-\d+/?$", href):
                continue
            if href in seen:
                continue
            seen.add(href)
            urls.append(self.BASE_URL + href if href.startswith("/") else href)
        return urls

    @staticmethod
    def _extract_ld_json(page_text):
        """Return (event_dict, category_name) from the page ld+json blocks.

        afisha.ru event pages embed a schema.org ``@graph`` holding a
        ``BreadcrumbList`` (whose second crumb is the human-readable category)
        and an ``*Event`` object with all core fields.
        """
        event = None
        category = None
        for m in re.finditer(
            r'type="application/ld\+json"[^>]*>(.*?)</script>', page_text, re.DOTALL
        ):
            try:
                data = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue

            graph = data.get("@graph", [data]) if isinstance(data, dict) else data
            if not isinstance(graph, list):
                continue

            for node in graph:
                if not isinstance(node, dict):
                    continue
                node_type = node.get("@type", "")
                if event is None and isinstance(node_type, str) and node_type.endswith("Event"):
                    event = node
                elif category is None and node_type == "BreadcrumbList":
                    items = node.get("itemListElement") or []
                    if len(items) > 1:
                        category = (items[1].get("item") or {}).get("name")

        return event, category

    @staticmethod
    def _extract_description(page_text):
        """Return the plain-text event description from the page DOM (may be '')."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(page_text, "lxml")
        el = soup.select_one(
            '[data-test="OBJECT-DESCRIPTION-CONTENT"] [data-test="RESTRICT-TEXT"]'
        )
        if el is None:
            return ""
        return el.get_text("\n", strip=True)

    def _id_from_url(self, event_url):
        match = re.search(r"-(\d+)/?(?:[?#].*)?$", event_url)
        event_id = match.group(1) if match else event_url.rstrip("/").split("/")[-1]
        return f"{self.source}-{event_id}"

    def _adress(self, event_data):
        location = event_data["event"].get("location") or {}
        address = location.get("address") or {}
        addr = address.get("name") or address.get("streetAddress") or ""
        return addr.replace("Санкт-Петербург, ", "").strip()

    def _category(self, event_data):
        return event_data.get("category") or ""

    def _date_from(self, event_data):
        self._date_from_ = _parse_afisha_dt(event_data["event"]["startDate"])
        return self._date_from_

    def _date_to(self, event_data):
        end = event_data["event"].get("endDate")
        date_to = _parse_afisha_dt(end) if end else None

        if (
            date_to
            and self._date_from_
            and date_to < self._date_from_ + timedelta(days=7)
            and date_to != self._date_from_
        ):
            self._date_to_ = date_to
        elif self._date_from_:
            self._date_to_ = self._date_from_ + timedelta(hours=3)
        else:
            self._date_to_ = None

        return self._date_to_

    def _date_from_to(self, event_data):
        return f"{self._date_from_} – {self._date_to_}"

    def _id(self, event_data):
        return self._id_from_url(self.event_url)

    def _place_name(self, event_data):
        return (event_data["event"].get("location") or {}).get("name", "")

    def _full_text(self, event_data):
        return (event_data.get("description") or "").strip()

    def _post_text(self, event_data):
        return self.prepare_post_text(self._full_text(event_data))

    def _poster_imag(self, event_data):
        image = event_data["event"].get("image")
        if isinstance(image, dict):
            return image.get("embedUrl") or image.get("url")
        return image

    def _price(self, event_data):
        offers = event_data["event"].get("offers") or {}
        price = offers.get("price")
        if price:
            return str(int(price)) + "₽"
        return "на сайте"

    def _title(self, event_data):
        return add_emoji(event_data["event"]["name"].strip())

    def _url(self, event_data):
        if self.event_url:
            return self.event_url
        url = event_data["event"].get("url", "")
        return self.BASE_URL + url if url.startswith("/") else url

    def _ticket_url(self, event_data):
        offers = event_data["event"].get("offers") or {}
        url = offers.get("url")
        if url:
            return self.BASE_URL + url if url.startswith("/") else url
        return self._url(event_data)

    def _source(self, event_data):
        return self.source

    def _is_registration_open(self, event_data):
        offers = event_data["event"].get("offers") or {}
        available = offers.get("availability", "")
        status = event_data["event"].get("eventStatus", "")
        return available.endswith("InStock") and status.endswith("EventScheduled")
