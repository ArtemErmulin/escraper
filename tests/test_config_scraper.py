import os
import time

import pytest
import pytz
import requests
from datetime import datetime, timedelta
from pathlib import Path

from escraper.parsers import ConfigScraper
from escraper.parsers.config_scraper import SITES

from .testing import Response

MSK = pytz.timezone("Europe/Moscow")


@pytest.fixture(autouse=True)
def moscow_tz(monkeypatch):
    """Set system timezone to Moscow so astimezone() on naive datetimes works correctly."""
    monkeypatch.setenv("TZ", "Europe/Moscow")
    time.tzset()
    yield
    time.tzset()


TESTDATA = Path(__file__).parent / "test_data" / "test_config_scraper"

TEST_SITE_CONFIG = {
    "name": "testsite",
    "source": "TEST",
    "base_url": "https://testsite.example.com",
    "listing_url": "/afisha/",
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
    "default_address": "Test address, 1",
    "default_place": "Test Place",
}


@pytest.fixture(autouse=True)
def register_test_site():
    SITES["testsite"] = TEST_SITE_CONFIG
    yield
    SITES.pop("testsite", None)


#######################################
## config_scraper get_event
#######################################
def test_config_get_event_with_none():
    with pytest.raises(ValueError):
        ConfigScraper().get_event()


def test_config_get_event_without_site():
    with pytest.raises(ValueError):
        ConfigScraper().get_event(event_url="https://example.com/afisha/test/")


@pytest.fixture
def requests_get_event(monkeypatch):
    def get(url, **kwargs):
        with open(TESTDATA / "event_page_1.html") as f:
            text = f.read()
        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)


def test_config_get_event(requests_get_event):
    scraper = ConfigScraper()
    event_url = "https://testsite.example.com/afisha/concert-rock-2024/"

    card_data = {
        "url": event_url,
        "title": "Rock Concert 2024",
        "date_str": "15.06.2024",
        "image": "/upload/rock-concert.jpg",
    }

    event = scraper.get_event(event_url=event_url, site="testsite", card_data=card_data)

    assert event.title[2:] == "Rock Concert 2024"  # without emoji
    assert event.adress == "Test address, 1"
    assert event.category == "концерты"  # detected from title "Rock Concert"
    assert event.date_from == datetime(2024, 6, 15, 19, 30).astimezone(MSK)
    assert event.date_to == event.date_from + timedelta(hours=2)
    assert event.date_from_to == "15.06.2024"
    assert event.id == "CFG-TEST-concert-rock-2024"
    assert event.place_name == "Test Place"
    assert "amazing rock concert" in event.full_text
    assert event.poster_imag == "https://testsite.example.com/upload/rock-concert.jpg"
    assert event.url == event_url
    assert event.source == "CFG"
    assert event.is_registration_open is True


def test_config_get_event_date_range(requests_get_event):
    """Test date range parsing like '01.07.2024–15.07.2024'."""
    scraper = ConfigScraper()
    event_url = "https://testsite.example.com/afisha/exhibition/"

    card_data = {
        "url": event_url,
        "title": "Art Exhibition",
        "date_str": "01.07.2024–15.07.2024",
        "image": "/upload/art.jpg",
    }

    event = scraper.get_event(event_url=event_url, site="testsite", card_data=card_data)

    assert event.date_from == datetime(2024, 7, 1, 19, 30).astimezone(MSK)
    assert event.date_to == datetime(2024, 7, 15).astimezone(MSK)
    assert event.date_from_to == "01.07.2024–15.07.2024"


#######################################
## config_scraper get_events
#######################################
@pytest.fixture
def requests_get_events(monkeypatch):
    def get(url, **kwargs):
        if url.endswith("/afisha/"):
            filepath = TESTDATA / "listing_simple.html"
        else:
            filepath = TESTDATA / "event_page_1.html"
        with open(filepath) as f:
            text = f.read()
        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)


def test_config_get_events(requests_get_events):
    scraper = ConfigScraper()
    params = {"site": "testsite"}
    events = list(scraper.get_events(request_params=params))

    assert len(events) == 3

    ids = {e.id for e in events}
    assert "CFG-TEST-concert-rock-2024" in ids
    assert "CFG-TEST-exhibition-art-2024" in ids
    assert "CFG-TEST-lecture-science" in ids

    # Check that card data was picked up from listing
    for e in events:
        assert e.place_name == "Test Place"
        assert e.adress == "Test address, 1"
        assert e.poster_imag is not None


def test_config_get_events_skip_existed(requests_get_events):
    scraper = ConfigScraper()
    params = {"site": "testsite"}
    events = list(scraper.get_events(
        request_params=params,
        existed_event_ids=["CFG-TEST-concert-rock-2024"],
    ))

    assert len(events) == 2
    ids = {e.id for e in events}
    assert "CFG-TEST-concert-rock-2024" not in ids


def test_config_get_events_no_site():
    with pytest.raises(ValueError):
        list(ConfigScraper().get_events(request_params={}))


#######################################
## config_scraper helpers
#######################################
def test_parse_date_range_single():
    d_from, d_to, time_str = ConfigScraper._parse_date_range("17.02.2026")
    assert d_from == datetime(2026, 2, 17)
    assert d_to is None
    assert time_str is None


def test_parse_date_range_double():
    d_from, d_to, time_str = ConfigScraper._parse_date_range("01.11.2025–01.05.2026")
    assert d_from == datetime(2025, 11, 1)
    assert d_to == datetime(2026, 5, 1)
    assert time_str is None


def test_parse_date_range_empty():
    d_from, d_to, time_str = ConfigScraper._parse_date_range(None)
    assert d_from is None
    assert d_to is None
    assert time_str is None


def test_parse_russian_date_single():
    d_from, d_to, time_str = ConfigScraper._parse_date_range("1 февраля", "russian")
    assert d_from.month == 2
    assert d_from.day == 1
    assert d_to is None
    assert time_str is None


def test_parse_russian_date_range():
    d_from, d_to, time_str = ConfigScraper._parse_date_range("с 1 февраля по 28 февраля", "russian")
    assert d_from.day == 1
    assert d_from.month == 2
    assert d_to.day == 28
    assert d_to.month == 2
    assert time_str is None


def test_parse_russian_date_with_year():
    d_from, d_to, time_str = ConfigScraper._parse_date_range("с 21 ноября 2025 по 15 марта", "russian")
    assert d_from == datetime(2025, 11, 21)
    assert d_to.month == 3
    assert d_to.day == 15
    assert time_str is None


def test_parse_russian_date_po_only():
    d_from, d_to, time_str = ConfigScraper._parse_date_range("по 6 марта", "russian")
    assert d_from is None
    assert d_to.month == 3
    assert d_to.day == 6
    assert time_str is None


def test_parse_russian_date_with_time():
    d_from, d_to, time_str = ConfigScraper._parse_date_range("21 февраля, 19:00", "russian")
    assert d_from.month == 2
    assert d_from.day == 21
    assert d_to is None
    assert time_str == "19:00"


def test_detect_category():
    from escraper.parsers.utils import detect_category
    assert detect_category("Рок-концерт в клубе") == "концерты"
    assert detect_category("Выставка современного искусства") == "выставки"
    assert detect_category("Лекция о Маркесе") == "лекции"
    assert detect_category("Спектакль «Гамлет»") == "театр"
    assert detect_category("Кинопоказ и дискуссия") == "кино"
    assert detect_category("Что-то непонятное", "а в тексте есть мастер-класс") == "мастер-классы"
    assert detect_category("Просто название") == ""


#######################################
## config as dict in request_params
#######################################
def test_config_as_dict_in_get_events(requests_get_events):
    """Pass site config as dict instead of registered name."""
    scraper = ConfigScraper()
    params = {"site": TEST_SITE_CONFIG}
    events = list(scraper.get_events(request_params=params))

    assert len(events) == 3
    for e in events:
        assert e.source == "CFG"
        assert e.place_name == "Test Place"
        assert e.adress == "Test address, 1"


def test_config_as_dict_in_get_event(requests_get_event):
    """Pass site config as dict directly to get_event."""
    scraper = ConfigScraper()
    event_url = "https://testsite.example.com/afisha/concert-rock-2024/"
    card_data = {
        "url": event_url,
        "title": "Rock Concert 2024",
        "date_str": "15.06.2024",
        "image": "/upload/rock-concert.jpg",
    }

    event = scraper.get_event(event_url=event_url, site=TEST_SITE_CONFIG, card_data=card_data)

    assert event.source == "CFG"
    assert event.place_name == "Test Place"
    assert event.date_from.hour == 19
    assert event.date_from.minute == 30


def test_config_unknown_site_string():
    with pytest.raises(ValueError, match="Unknown site"):
        list(ConfigScraper().get_events(request_params={"site": "nonexistent"}))
