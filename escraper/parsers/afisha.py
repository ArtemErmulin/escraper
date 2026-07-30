import json
import logging
import re
from datetime import datetime, timedelta

from .base import BaseParser, ALL_EVENT_TAGS
from .config_scraper import MONTHS_RU
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


def _parse_notice_datetime(text, tz, default_hour=19):
    """Parse a listing-card notice date into a Moscow-aware datetime.

    The city-scoped listing card carries the city-correct session, e.g.
    ``"13 августа в 19:30"`` or ``"10 и 11 октября"`` or
    ``"31 июля, 1 и 2 августа"`` (first date is taken). The card has no year,
    so the current year is assumed and rolled forward if already past.
    """
    if not text:
        return None
    low = text.lower()

    # Pull the time out first so it can't be mistaken for the day number.
    hour, minute = default_hour, 0
    time_match = re.search(r"(\d{1,2}):(\d{2})", low)
    if time_match:
        hour, minute = int(time_match.group(1)), int(time_match.group(2))
        low = (low[:time_match.start()] + low[time_match.end():])

    day_match = re.search(r"\b(\d{1,2})\b", low)
    if not day_match:
        return None
    day = int(day_match.group(1))

    # Month = earliest month name mentioned in the text.
    best_pos, month = None, None
    for prefix, num in MONTHS_RU.items():
        pos = low.find(prefix)
        if pos != -1 and (best_pos is None or pos < best_pos):
            best_pos, month = pos, num
    if month is None:
        return None

    now = datetime.now(tz)
    for year in (now.year, now.year + 1):
        try:
            dt = tz.localize(datetime(year, month, day, hour, minute))
        except ValueError:
            return None
        if dt.date() >= now.date():
            return dt
    return dt


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

    def get_event(self, event_url=None, tags=None, listing_hint=None):
        """Fetch and parse a single afisha.ru event page.

        Parameters
        ----------
        event_url : str
            Full URL of the event page, e.g.
            https://www.afisha.ru/concert/basta-6023789/
        tags : list, optional
            Event tags to return. Defaults to ALL_EVENT_TAGS.
        listing_hint : dict, optional
            City-scoped listing-card data ``{"date_from": <dt>, "place_name": str}``.
            A touring event's page (played in several cities) carries no
            ``location`` and shows the earliest city's date in its ld+json;
            when that happens, the hint supplies the requested city's session.
        """
        if event_url is None:
            raise ValueError("'event_url' required.")

        body = self._request_get(event_url).text

        event_json, category = self._extract_ld_json(body)
        if event_json is None:
            raise ValueError("Can't find event ld+json on page")

        self.event_url = event_url
        event_data = self._normalize(event_json, category, body, listing_hint or {})
        return self.parse(event_data, tags=tags or ALL_EVENT_TAGS)

    def _normalize(self, event_json, category, body, hint):
        """Resolve date/place, preferring the ld+json but falling back to the
        city-scoped listing card for touring events (empty ``location``)."""
        location = event_json.get("location") or {}
        has_location = bool(location.get("name"))

        if has_location:
            address = location.get("address") or {}
            place_name = location.get("name", "")
            addr = address.get("name") or address.get("streetAddress") or ""
            start = event_json.get("startDate")
            date_from = _parse_afisha_dt(start) if start else None
            end = event_json.get("endDate")
            date_to = _parse_afisha_dt(end) if end else None
            offers = event_json.get("offers") or {}
            price = int(offers["price"]) if offers.get("price") else None
        else:
            # Touring event: the page is city-agnostic — trust the city listing.
            place_name = hint.get("place_name", "") or ""
            addr = ""
            date_from = hint.get("date_from")
            date_to = None
            price = hint.get("price")
            if date_from is None and event_json.get("startDate"):
                logger.warning(
                    "AFISHA: touring event without city hint, falling back to "
                    "ld+json date (may be another city): %s", self.event_url
                )
                date_from = _parse_afisha_dt(event_json["startDate"])

        if date_to is None or (
            date_from and (date_to <= date_from or date_to >= date_from + timedelta(days=7))
        ):
            date_to = date_from + timedelta(hours=3) if date_from else None

        return {
            "event": event_json,
            "category": category,
            "description": self._extract_description(body),
            "date_from": date_from,
            "date_to": date_to,
            "place_name": place_name,
            "address": addr.replace("Санкт-Петербург, ", "").strip(),
            "price": price,
        }

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

            for card in self._extract_cards(response.text):
                event_url = card["url"]
                event_id = self._id_from_url(event_url)
                if event_id in existed_event_ids:
                    continue

                try:
                    event = self.get_event(
                        event_url=event_url, tags=tags, listing_hint=card
                    )
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

    def _extract_cards(self, page_text):
        """Return de-duplicated listing cards as dicts."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(page_text, "lxml")
        seen = set()
        cards = []
        for link in soup.select('[data-test="LINK ITEM-NAME ITEM-URL"]'):
            href = (link.get("href") or "").split("?")[0]
            if not re.search(r"-\d+/?$", href):
                continue
            if href in seen:
                continue
            seen.add(href)

            date_from, place_name, price = self._extract_card_notice(link)
            cards.append({
                "url": self.BASE_URL + href if href.startswith("/") else href,
                "date_from": date_from,
                "place_name": place_name,
                "price": price,
            })
        return cards

    def _extract_card_notice(self, title_link):
        """From a card title link, read its city-correct date, venue and price.

        Returns ``(date_from, place_name, price)`` where price is an int (rub)
        or None. Used to fill touring events whose detail page is city-agnostic.
        """
        notice = None
        node = title_link
        for _ in range(7):
            node = node.parent
            if node is None:
                break
            notice = node.select_one('[data-test="ITEM-META ITEM-NOTICE"]')
            if notice is not None:
                break
        if notice is None:
            return None, "", None

        venue_link = notice.find("a")
        place_name = venue_link.get_text(" ", strip=True) if venue_link else ""

        full = notice.get_text(" ", strip=True)
        if place_name and place_name in full:
            date_text = full[:full.rfind(place_name)].rstrip(" ,")
        else:
            date_text = full
        date_from = _parse_notice_datetime(date_text, self.TIMEZONE)

        # Price lives on a ticket button near the notice ("От 4000 ₽").
        price = None
        holder = notice
        for _ in range(5):
            holder = holder.parent
            if holder is None:
                break
            button = holder.select_one('[data-test~="TICKET-BUTTON"]')
            if button:
                digits = re.sub(r"\D", "", button.get_text().replace("\xa0", " "))
                price = int(digits) if digits else None
                break

        return date_from, place_name, price

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
        return event_data.get("address", "")

    def _category(self, event_data):
        return event_data.get("category") or ""

    def _date_from(self, event_data):
        self._date_from_ = event_data.get("date_from")
        return self._date_from_

    def _date_to(self, event_data):
        self._date_to_ = event_data.get("date_to")
        return self._date_to_

    def _date_from_to(self, event_data):
        return f"{self._date_from_} – {self._date_to_}"

    def _id(self, event_data):
        return self._id_from_url(self.event_url)

    def _place_name(self, event_data):
        return event_data.get("place_name", "")

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
        price = event_data.get("price")
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
