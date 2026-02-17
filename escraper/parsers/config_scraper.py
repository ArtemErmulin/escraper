import hashlib
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import BaseParser, ALL_EVENT_TAGS
from .utils import detect_category
from ..emoji import add_emoji


MONTHS_RU = {
    "январ": 1, "янв": 1, "феврал": 2, "фев": 2, "март": 3, "мар": 3,
    "апрел": 4, "апр": 4, "мая": 5, "май": 5, "июн": 6, "июл": 7,
    "август": 8, "авг": 8, "сентябр": 9, "сен": 9, "октябр": 10, "окт": 10,
    "ноябр": 11, "ноя": 11, "декабр": 12, "дек": 12,
}

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


SITES = {
    "sevcable": {
        "name": "sevcable",
        "source": "SEVC",
        "base_url": "https://sevcableport.ru",
        "listing_url": "/afisha/",
        # --- listing selectors ---
        "card_selector": "a.event_card",
        "card_title_selector": ".event_name",
        "card_date_selector": ".event_surname",
        "card_category_selector": ".event_type",
        "card_image_selector": ".event_foto_img",
        "card_image_attr": "data-src",
        # --- detail page selectors ---
        "description_selector": ".infopage_text_flex",
        "time_selector": None,
        "price_selector": None,
        # --- date ---
        "date_format": "russian",
        # --- defaults ---
        "default_address": "Кожевенная линия, 40",
        "default_place": "Севкабель Порт",
    },
    "newholland": {
        "name": "newholland",
        "source": "NHOL",
        "base_url": "https://www.newhollandsp.ru",
        "listing_url": "/events/",
        # --- listing selectors ---
        "card_selector": "a.event",
        "card_title_selector": ".event-name",
        "card_date_selector": ".event-date",
        "card_image_selector": "img",
        "card_image_attr": "src",
        # --- detail page selectors ---
        "description_selector": ".col-sm-8",
        "time_selector": ".prop.TIME",
        "price_selector": None,
        # --- date ---
        "date_format": "%d.%m.%Y",
        # --- defaults ---
        "default_address": "наб. Адмиралтейского канала, 2",
        "default_place": "Новая Голландия",
    },
    "levashovsky": {
        "name": "levashovsky",
        "source": "LVSH",
        "base_url": "https://levashovsky.ru",
        "listing_url": "/afisha",
        # --- listing selectors ---
        "card_selector": ".t390",
        "card_title_selector": ".t390__title",
        "card_date_selector": ".t390__uptitle",
        "card_description_selector": ".t390__descr",
        "card_image_selector": ".t390__img",
        "card_image_attr": "data-original",
        "card_link_selector": "a",
        # --- detail page ---
        "skip_detail": True,
        # --- date ---
        "date_format": "russian",
        # --- defaults ---
        "default_address": "Барочная ул., 4А",
        "default_place": "Левашовский хлебозавод",
    },
    "alexandrinsky": {
        "name": "alexandrinsky",
        "source": "ALXN",
        "base_url": "https://alexandrinsky.ru",
        "listing_url": "/afisha-i-bilety/",
        # --- listing selectors ---
        "card_selector": "div.box-poster-tickets",
        "card_title_selector": "h4",
        "card_date_selector": ".repertoire-date-list__item",
        "card_category_selector": ".box-addition-description",
        "card_image_selector": "img",
        "card_image_attr": "src",
        "card_description_selector": ".box-poster-tickets-txt",
        "card_link_selector": "h4 a",
        # --- detail page ---
        "skip_detail": True,
        # --- date ---
        "date_format": "russian",
        # --- defaults ---
        "default_address": "пл. Островского, 6",
        "default_place": "Александринский театр",
    },
}


class ConfigScraper(BaseParser):
    name = "config"
    source = "CFG"

    def __init__(self):
        self._current_event = {}
        self._current_config = {}

    @staticmethod
    def _resolve_config(site):
        """Resolve site config: str → lookup in SITES, dict → use directly."""
        if isinstance(site, dict):
            return site
        if isinstance(site, str) and site in SITES:
            return SITES[site]
        raise ValueError(f"Unknown site: {site!r}. Pass a config dict or a registered site name.")

    @staticmethod
    def _extract_field(soup, selector, attr=None):
        if selector is None:
            return None
        el = soup.select_one(selector)
        if el is None:
            return None
        if attr:
            value = el.get(attr)
        else:
            value = el.get_text(" ", strip=True)
        if value:
            return value.strip()
        return None

    @staticmethod
    def _parse_russian_date(text):
        """Parse Russian date like '1 февраля', '21 ноября 2025'."""
        if not text:
            return None
        text = re.sub(r'\s+', ' ', text.strip())
        match = re.match(r'(\d{1,2})\s+(\S+)(?:\s+(\d{4}))?', text)
        if not match:
            return None

        day = int(match.group(1))
        month_str = match.group(2).lower().rstrip(',')
        year = int(match.group(3)) if match.group(3) else datetime.now().year

        month = None
        for prefix, num in MONTHS_RU.items():
            if month_str.startswith(prefix):
                month = num
                break

        if month is None:
            return None

        try:
            return datetime(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _parse_russian_date_range(text):
        """Parse Russian date strings with optional time.

        Supports:
          '21 февраля, 19:00'
          'с 1 февраля по 28 февраля'
          '24 декабря – 15 февраля'
          'по 6 марта'
          '1 февраля'
        """
        if not text:
            return None, None, None

        text = re.sub(r'\s+', ' ', text.strip())

        # Extract time like ", 19:00" or " 19:00" at the end
        time_str = None
        time_match = re.search(r',?\s*(\d{1,2}:\d{2})\s*$', text)
        if time_match:
            time_str = time_match.group(1)
            text = text[:time_match.start()].strip()

        # "с X по Y" pattern
        match = re.match(r'с\s+(.+?)\s+по\s+(.+)', text)
        if match:
            d_from = ConfigScraper._parse_russian_date(match.group(1))
            d_to = ConfigScraper._parse_russian_date(match.group(2))
            return d_from, d_to, time_str

        # "X – Y" pattern (dash-separated range)
        parts = re.split(r'\s*[–—]\s*', text)
        if len(parts) == 2:
            d_from = ConfigScraper._parse_russian_date(parts[0])
            d_to = ConfigScraper._parse_russian_date(parts[1])
            if d_from or d_to:
                return d_from, d_to, time_str

        # "по Y" only
        match = re.match(r'по\s+(.+)', text)
        if match:
            d_to = ConfigScraper._parse_russian_date(match.group(1))
            return None, d_to, time_str

        # Single date
        d_from = ConfigScraper._parse_russian_date(text)
        return d_from, None, time_str

    @staticmethod
    def _parse_date_range(date_str, date_format="%d.%m.%Y"):
        """Parse date string. Returns (date_from, date_to, time_str).

        Supports strptime format or 'russian' for Russian text dates.
        """
        if not date_str:
            return None, None, None

        if date_format == "russian":
            return ConfigScraper._parse_russian_date_range(date_str)

        # Split by dash variants
        parts = re.split(r'[–—-]', date_str.strip())

        date_from, date_to = None, None
        try:
            date_from = datetime.strptime(parts[0].strip(), date_format)
        except (ValueError, TypeError):
            pass

        if len(parts) > 1:
            try:
                date_to = datetime.strptime(parts[-1].strip(), date_format)
            except (ValueError, TypeError):
                pass

        return date_from, date_to, None

    @staticmethod
    def _transliterate(text):
        """Transliterate Cyrillic text to Latin."""
        result = []
        for ch in text.lower():
            result.append(TRANSLIT.get(ch, ch))
        return "".join(result)

    @staticmethod
    def _slug_from_url(url):
        """Extract clean slug from event URL (no query params, fragments)."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/").split("/")
        slug = path[-1] if path else ""
        slug = re.sub(r'[^\w-]', '', slug)
        return slug

    @staticmethod
    def _make_short_id(title, max_slug_len=21):
        """Generate short ID slug from title: first letters of words + hash.

        Example: 'Дима Устинов. Music for a really long walk' -> 'du-mfarlw-a1b2'
        Fits within max_slug_len (default 21 = 30 - len('CFG-XXXX-')).
        """
        # Remove emoji and punctuation, keep words
        clean = re.sub(r'[^\w\s]', ' ', title)
        words = clean.split()
        if not words:
            return hashlib.md5(title.encode()).hexdigest()[:8]

        # First letters of each word, transliterated
        initials = ""
        for w in words:
            letter = ConfigScraper._transliterate(w[0]) if w else ""
            initials += letter

        # Short hash for uniqueness (from full title)
        short_hash = hashlib.md5(title.encode()).hexdigest()[:4]

        # Budget: max_slug_len, need '-' + hash (5 chars)
        budget = max_slug_len - len(short_hash) - 1
        if budget < 1:
            return short_hash

        initials = initials[:budget]
        return f"{initials}-{short_hash}"

    def _parse_listing_card(self, card, config):
        """Extract event data from a listing card element."""
        # Get URL: from card href (if <a>) or from nested link
        href = card.get("href", "")
        if not href:
            link_sel = config.get("card_link_selector")
            if link_sel:
                link = card.select_one(link_sel)
                if link:
                    href = link.get("href", "")

        title = self._extract_field(card, config.get("card_title_selector")) or ""
        date_str = self._extract_field(card, config.get("card_date_selector"))
        image = self._extract_field(
            card, config.get("card_image_selector"), config.get("card_image_attr")
        )
        # Fallback: try src if data-original is empty
        if not image:
            image = self._extract_field(
                card, config.get("card_image_selector"), "src"
            )
        category = self._extract_field(card, config.get("card_category_selector"))
        description = self._extract_field(card, config.get("card_description_selector"))

        # Build URL — if href exists use it, otherwise generate from listing URL + title slug
        if href:
            full_url = href if href.startswith("http") else urljoin(config["base_url"], href)
        else:
            full_url = config["base_url"] + config.get("listing_url", "/")

        data = {
            "url": full_url,
            "title": title,
            "date_str": date_str,
            "image": image,
        }
        if category:
            data["category"] = category
        if description:
            data["description"] = description
        return data

    def get_event(self, event_url=None, tags=None, site=None, card_data=None):
        if event_url is None:
            raise ValueError("'event_url' required.")
        if site is None:
            raise ValueError("'site' required.")

        config = self._resolve_config(site)
        self._current_config = config

        # Start with card data from listing (if available)
        data = dict(card_data) if card_data else {}
        data.setdefault("url", event_url)

        # Fetch detail page unless skip_detail is set
        if not config.get("skip_detail"):
            response = self._request_get(event_url)
            if response:
                soup = BeautifulSoup(response.text, "lxml")

                if not data.get("title"):
                    title = self._extract_field(soup, "h1")
                    if not title:
                        title = self._extract_field(soup, ".infopage_head_page")
                    data["title"] = title or ""

                description = self._extract_field(soup, config.get("description_selector"))
                if description:
                    data["description"] = self.remove_html_tags(description)
                else:
                    data.setdefault("description", "")

                time_str = self._extract_field(soup, config.get("time_selector"))
                if time_str:
                    data["time"] = time_str.strip()

                if not data.get("date_str"):
                    data["date_str"] = self._extract_field(soup, ".date")

                price = self._extract_field(soup, config.get("price_selector"))
                if price:
                    data["price"] = price

                if not data.get("image"):
                    for sel in [".col-sm-8 img[src*='/upload/']", "img[src*='/upload/']"]:
                        img = soup.select_one(sel)
                        if img:
                            data["image"] = img.get("src")
                            break

        data.setdefault("title", "")
        data.setdefault("description", "")

        self._current_event = data
        return self.parse(data, tags=tags or ALL_EVENT_TAGS)

    def get_events(self, request_params=None, tags=None, existed_event_ids=None):
        request_params = request_params or {}
        existed_event_ids = list(existed_event_ids) if existed_event_ids else []

        site = request_params.get("site")
        if site is None:
            raise ValueError("'site' key required in request_params.")

        config = self._resolve_config(site)
        listing_url = config["base_url"] + config["listing_url"]

        response = self._request_get(listing_url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select(config.get("card_selector", "a.event"))

        listing_slug = self._slug_from_url(listing_url)
        events = []
        seen_ids = set()
        for card in cards:
            card_data = self._parse_listing_card(card, config)
            if not card_data or not card_data.get("title"):
                continue

            url = card_data["url"]

            # Pre-compute event_id for dedup (same logic as _id)
            prefix = f"{self.source}-{config['source']}-"
            max_slug = 30 - len(prefix)
            slug = self._slug_from_url(url)
            base_host = urlparse(config.get("base_url", "")).netloc
            url_host = urlparse(url).netloc
            if (slug and slug != listing_slug
                    and url_host == base_host
                    and len(slug) <= max_slug):
                event_id = f"{prefix}{slug}"
            else:
                title = card_data["title"]
                if title and not title[0].isalnum():
                    title = title[2:].strip()
                event_id = f"{prefix}{self._make_short_id(title, max_slug)}"
            if event_id in existed_event_ids or event_id in seen_ids:
                continue
            seen_ids.add(event_id)

            event = self.get_event(
                event_url=url, tags=tags, site=site, card_data=card_data
            )
            if event:
                events.append(event)

        return events

    # --- field methods ---

    def _title(self, event_data):
        return add_emoji(event_data.get("title", ""))

    def _adress(self, event_data):
        return self._current_config.get("default_address", "")

    def _category(self, event_data):
        if event_data.get("category"):
            return event_data["category"]
        title = event_data.get("title", "")
        text = event_data.get("description", "")
        return detect_category(title, text)

    def _date_from(self, event_data):
        date_str = event_data.get("date_str")
        fmt = self._current_config.get("date_format", "%d.%m.%Y")
        date_from, _, time_str = self._parse_date_range(date_str, fmt)
        if date_from is None:
            return None

        # Time from date string (e.g. "21 февраля, 19:00") or from detail page
        time_str = time_str or event_data.get("time", "")
        if time_str:
            match = re.match(r"(\d{1,2}):(\d{2})", time_str)
            if match:
                date_from = date_from.replace(
                    hour=int(match.group(1)), minute=int(match.group(2))
                )

        return date_from.astimezone(self.TIMEZONE)

    def _date_to(self, event_data):
        date_str = event_data.get("date_str")
        fmt = self._current_config.get("date_format", "%d.%m.%Y")
        _, date_to, _ = self._parse_date_range(date_str, fmt)
        if date_to:
            return date_to.astimezone(self.TIMEZONE)
        # No explicit end date — use date_from as fallback
        return self._date_from(event_data)


    def _date_from_to(self, event_data):
        return event_data.get("date_str")

    def _id(self, event_data):
        source = self._current_config.get("source", self.source)
        prefix = f"{self.source}-{source}-"
        max_slug = 30 - len(prefix)

        url = event_data.get("url", "")
        base_url = self._current_config.get("base_url", "")
        base_host = urlparse(base_url).netloc
        url_host = urlparse(url).netloc

        slug = self._slug_from_url(url)
        listing_slug = self._slug_from_url(
            base_url + self._current_config.get("listing_url", "/")
        )

        # Use URL slug only if same domain, unique, and short enough
        if (slug and slug != listing_slug
                and url_host == base_host
                and len(slug) <= max_slug):
            return f"{prefix}{slug}"

        # Otherwise generate from title
        title = event_data.get("title", "")
        # Strip emoji prefix (2 chars: emoji + space)
        if title and not title[0].isalnum():
            title = title[2:].strip()
        return f"{prefix}{self._make_short_id(title, max_slug)}"

    def _url(self, event_data):
        return event_data.get("url", "")

    def _ticket_url(self, event_data):
        return event_data.get("url", "")

    def _place_name(self, event_data):
        return self._current_config.get("default_place", "")

    def _full_text(self, event_data):
        return event_data.get("description", "")

    def _post_text(self, event_data):
        return self.prepare_post_text(self._full_text(event_data))

    def _poster_imag(self, event_data):
        image = event_data.get("image")
        if image and not image.startswith("http"):
            base = self._current_config.get("base_url", "")
            return urljoin(base, image)
        return image

    def _price(self, event_data):
        price = event_data.get("price")
        if price is None:
            return "на сайте"
        try:
            return str(int(price)) + "₽"
        except (ValueError, TypeError):
            if "₽" in str(price) or "руб" in str(price).lower():
                return str(price)
            return str(price) + "₽"

    def _source(self, event_data):
        return self.source

    def _is_registration_open(self, event_data):
        return True
