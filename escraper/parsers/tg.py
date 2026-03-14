import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from .base import BaseParser, ALL_EVENT_TAGS
from ..emoji import add_emoji


# Russian month names for date parsing
MONTHS_RU = {
    "января": 1, "янв": 1,
    "февраля": 2, "фев": 2,
    "марта": 3, "мар": 3,
    "апреля": 4, "апр": 4,
    "мая": 5,
    "июня": 6, "июн": 6,
    "июля": 7, "июл": 7,
    "августа": 8, "авг": 8,
    "сентября": 9, "сен": 9,
    "октября": 10, "окт": 10,
    "ноября": 11, "ноя": 11,
    "декабря": 12, "дек": 12,
}

class Telegram(BaseParser):
    """
    Scraper for public Telegram channels.

    Fetches posts from channels via public preview URLs like https://t.me/s/ChannelName.
    Since we cannot reliably determine which posts are events, this scraper
    saves all posts from the last 1-2 weeks for later analysis.
    """
    name = "tg"
    BASE_URL = "https://t.me/s/"
    source = "TG"
    DATETIME_STRF = "%Y-%m-%dT%H:%M:%S%z"

    def __init__(self, use_proxy=True):
        super().__init__(use_proxy=use_proxy)
        self.url = self.BASE_URL
        self.timedelta_hours = self.timedelta_with_gmt0()
        self._current_post = None
        self._current_channel = None

    def get_event(self, event_url=None, tags=None):
        """
        Get a single post by its URL.

        Parameters
        ----------
        event_url : str
            Full URL to the post, e.g., https://t.me/ChannelName/12345
        tags : list
            List of tags to extract
        """
        if event_url is None:
            raise ValueError("'event_url' required.")

        response = self._request_get(event_url)
        if not response:
            return None

        soup = BeautifulSoup(response.text, "lxml")

        # Find the message widget
        message = soup.find("div", class_="tgme_widget_message_wrap")
        if not message:
            message = soup.find("div", class_="tgme_widget_message")

        if not message:
            return None

        self._current_post = message
        self._current_channel = event_url.split("/")[-2] if "/" in event_url else None
        self.event_url = event_url

        return self.parse(message, tags=tags or ALL_EVENT_TAGS)

    def get_events(self, request_params={}, tags=None, existed_event_ids=[]):
        """
        Get posts from Telegram channels.

        Parameters
        ----------
        request_params : dict
            Parameters for scraping:

            channels : list of str (required)
                List of channel names/usernames to scrape.
                Example: ["DavaiSNami", "spb_events", "piterevents"]

            days : int, default 14
                Number of days to look back for posts.

            max_posts_per_channel : int, default 50
                Maximum posts to fetch per channel.

        tags : list of tags, default all available event tags
            Event tags (title, id, url etc.,
            see all tags in 'escraper.ALL_EVENT_TAGS')

        existed_event_ids : list
            List of event IDs (format: TG-ChannelName-12345).
            Used as a starting point - scraper will fetch new posts
            and stop when it reaches a known post ID.

        Examples
        --------
        >>> tg = Telegram()
        >>> request_params = {
        ...     "channels": ["DavaiSNami", "spb_events"],
        ...     "days": 7,
        ... }
        >>> posts = tg.get_events(request_params=request_params)  # doctest: +SKIP
        """
        request_params = request_params or {}
        existed_event_ids = list(existed_event_ids)

        channels = request_params.get("channels", [])
        if not channels:
            raise ValueError("'channels' parameter is required in request_params")

        days = int(request_params.get("days", 14))
        max_posts = int(request_params.get("max_posts_per_channel", 50))

        cutoff_date = datetime.now(self.TIMEZONE) - timedelta(days=days)

        # Build mapping of channel -> max known post ID
        last_known_post_ids = self._parse_existed_ids(existed_event_ids)

        events = []

        for channel in channels:
            channel_posts = self._scrape_channel(
                channel=channel,
                cutoff_date=cutoff_date,
                max_posts=max_posts,
                existed_event_ids=existed_event_ids,
                last_known_post_id=last_known_post_ids.get(channel.lower()),
                tags=tags
            )
            events.extend(channel_posts)

        return events

    def _parse_existed_ids(self, existed_event_ids):
        """
        Parse existed_event_ids to extract max post ID per channel.

        ID format: TG-ChannelName-12345
        Returns: {channel_name_lower: max_post_id}
        """
        channel_max_ids = {}

        for event_id in existed_event_ids:
            if not event_id.startswith(f"{self.source}-"):
                continue

            # Parse TG-ChannelName-12345
            parts = event_id.split("-")
            if len(parts) < 3:
                continue

            # Channel name might contain dashes, post ID is last part
            try:
                post_num = int(parts[-1])
                channel_name = "-".join(parts[1:-1]).lower()

                if channel_name not in channel_max_ids:
                    channel_max_ids[channel_name] = post_num
                else:
                    channel_max_ids[channel_name] = max(channel_max_ids[channel_name], post_num)
            except ValueError:
                continue

        return channel_max_ids

    def _scrape_channel(self, channel, cutoff_date, max_posts, existed_event_ids, tags, last_known_post_id=None):
        """
        Scrape posts from a single channel.

        If last_known_post_id is provided, scraper will:
        - Fetch all new posts (with ID > last_known_post_id)
        - Stop when reaching the known post (no need to go further back)
        """
        channel_url = f"{self.BASE_URL}{channel}"
        posts = []

        response = self._request_get(channel_url)
        if not response:
            return posts

        soup = BeautifulSoup(response.text, "lxml")
        messages = soup.find_all("div", class_="tgme_widget_message")

        for message in messages[:max_posts]:
            post_data = message.get("data-post", "")
            if not post_data:
                continue

            # Extract numeric post ID from "ChannelName/12345"
            try:
                post_num = int(post_data.split("/")[-1])
            except ValueError:
                post_num = None

            # If we have a known post ID and current post is older or same, stop
            # (posts are in reverse chronological order - newest first)
            if last_known_post_id and post_num and post_num <= last_known_post_id:
                break

            # Extract full post ID
            post_id = self._id_from_post_data(post_data)
            if post_id in existed_event_ids:
                continue

            # Parse post date (for additional filtering)
            post_date = self._extract_post_date(message)
            if post_date and post_date < cutoff_date:
                # Don't break here - just skip old posts, there might be newer ones
                # (in case of pinned posts or reordering)
                continue

            # Store current post context for parsing
            self._current_post = message
            self._current_channel = channel
            self.event_url = f"https://t.me/{post_data}"

            try:
                event = self.parse(message, tags=tags or ALL_EVENT_TAGS)
                posts.append(event)
                existed_event_ids.append(post_id)
            except Exception:
                # Skip posts that fail to parse
                continue

        return posts

    def _extract_post_date(self, message):
        """Extract datetime from a post message."""
        time_elem = message.find("time", class_="datetime")
        if time_elem and time_elem.get("datetime"):
            try:
                return datetime.fromisoformat(
                    time_elem["datetime"].replace("Z", "+00:00")
                ).astimezone(self.TIMEZONE)
            except (ValueError, TypeError):
                pass

        # Fallback: try to find date in text
        date_elem = message.find("span", class_="tgme_widget_message_date")
        if date_elem:
            return self._parse_russian_date(date_elem.text.strip())

        return None

    def _parse_russian_date(self, date_str):
        """Parse Russian date strings like '7 февраля' or '7 фев 2025'."""
        date_str = date_str.lower().strip()

        # Pattern: "7 февраля" or "7 февраля 2025"
        match = re.match(r"(\d{1,2})\s+(\w+)(?:\s+(\d{4}))?", date_str)
        if match:
            day = int(match.group(1))
            month_str = match.group(2)
            year = int(match.group(3)) if match.group(3) else datetime.now().year

            month = None
            for name, num in MONTHS_RU.items():
                if month_str.startswith(name[:3]):
                    month = num
                    break

            if month:
                try:
                    return datetime(year, month, day).astimezone(self.TIMEZONE)
                except ValueError:
                    pass

        return None

    def _id_from_post_data(self, post_data):
        """Generate ID from post data attribute (channel/post_id)."""
        return f"{self.source}-{post_data.replace('/', '-')}"

    def _adress(self, message):
        """Extract address from post - not applicable for Telegram posts."""
        return ""

    def _category(self, message):
        """Extract category - not applicable for Telegram posts."""
        return None

    def _date_from(self, message):
        """Extract post date."""
        self._date_from_ = self._extract_post_date(message)
        if not self._date_from_:
            self._date_from_ = datetime.now(self.TIMEZONE) + timedelta(days=5)
        return self._date_from_

    def _date_to(self, message):
        """End date - same as start for posts."""
        self._date_to_ = self._date_from_ if hasattr(self, '_date_from_') else None
        return self._date_to_

    def _date_from_to(self, message):
        """Date range as string."""
        if hasattr(self, '_date_from_') and self._date_from_:
            return self._date_from_.strftime("%d.%m.%Y %H:%M")
        return ""

    def _id(self, message):
        """Generate unique post ID."""
        post_data = message.get("data-post", "")
        if post_data:
            return self._id_from_post_data(post_data)
        return f"{self.source}-{self._current_channel}-{datetime.now().timestamp()}"

    def _place_name(self, message):
        """Place name - not applicable for Telegram posts."""
        return self._current_channel or ""

    def _full_text(self, message) -> str:
        """Extract full post text as HTML."""
        text_elem = message.find("div", class_="tgme_widget_message_text")
        if text_elem:
            # Return inner HTML to preserve formatting
            return str(text_elem)
        return ""

    def _post_text(self, message):
        """Extract short post text (plain text, no HTML)."""
        text_elem = message.find("div", class_="tgme_widget_message_text")
        if text_elem:
            plain_text = text_elem.get_text(separator="\n").strip()
            return self.prepare_post_text(plain_text)
        return ""

    def _poster_imag(self, message):
        """Extract image URL from post."""
        # Try photo in message
        photo = message.find("a", class_="tgme_widget_message_photo_wrap")
        if photo:
            style = photo.get("style", "")
            match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
            if match:
                return match.group(1)

        return None

    def _price(self, message):
        """Price - not applicable for Telegram posts."""
        return ""

    def _title(self, message):
        """Extract title from post - use first line of text."""
        text_elem = message.find("div", class_="tgme_widget_message_text")
        if text_elem:
            # Get plain text for title
            plain_text = text_elem.get_text(separator="\n").strip()
            if plain_text:
                # Use first line as title, limit to 100 chars
                first_line = plain_text.split("\n")[0].strip()
                if len(first_line) > 100:
                    first_line = first_line[:97] + "..."
                return add_emoji(first_line)
        return add_emoji(f"Post from {self._current_channel}")

    def _url(self, message):
        """Get post URL."""
        if hasattr(self, 'event_url') and self.event_url:
            return self.event_url
        post_data = message.get("data-post", "")
        if post_data:
            return f"https://t.me/{post_data}"
        return ""

    def _ticket_url(self, message) -> str:
        """Extract ticket/registration URLs from post links."""
        text_elem = message.find("div", class_="tgme_widget_message_text")
        if not text_elem:
            return None

        # Find all links in the post
        links = text_elem.find_all("a", href=True)
        ticket_urls = []

        for link in links:
            href = link.get("href", "")
            if href.startswith("?") or (self._current_channel in href and 't.me/' in href):
                continue
            ticket_urls.append(href)


        if not ticket_urls:
            return None
        elif len(ticket_urls) == 1:
            return ticket_urls[0]
        else:
            # Return multiple URLs separated by " | "
            return " | ".join(ticket_urls)[0:490]

    def _source(self, message) -> str:
        """Return source identifier."""
        return self.source

    def _is_registration_open(self, message):
        """Registration status - not applicable for Telegram posts."""
        return True
