import pytest
import requests
from datetime import datetime
from pathlib import Path

from escraper.parsers import Telegram

from .testing import Response


TESTDATA = Path(__file__).parent / "test_data" / "test_tg"


#######################################
## Telegram get_event
#######################################
def test_tg_get_event_with_none():
    with pytest.raises(ValueError):
        Telegram().get_event()


@pytest.fixture
def requests_get_channel(monkeypatch):
    def get(url, **kwargs):
        # Return the test HTML for any channel URL
        with open(TESTDATA / "channel_page.html") as file:
            text = file.read()
        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)


def test_tg_get_events_requires_channels():
    with pytest.raises(ValueError, match="'channels' parameter is required"):
        list(Telegram().get_events(request_params={}))


def test_tg_get_events(requests_get_channel):
    params = {
        "channels": ["DavaiSNami"],
        "days": 365,
    }
    posts = list(Telegram().get_events(request_params=params))

    assert len(posts) == 3

    # Posts are in reverse chronological order (newest first)
    # Check last post (oldest, 11077)
    post = posts[2]
    assert post.source == "TG"
    assert post.id == "TG-DavaiSNami-11077"
    assert post.url == "https://t.me/DavaiSNami/11077"
    assert "Концерт в Эрарте" in post.title
    assert "Музей Эрарта" in post.full_text
    assert post.poster_imag == "https://cdn4.telesco.pe/file/test_image_1.jpg"


def test_tg_get_events_multiple_channels(requests_get_channel):
    params = {
        "channels": ["DavaiSNami", "another_channel"],
        "days": 365,
    }
    posts = list(Telegram().get_events(request_params=params))

    # Same mock HTML for both channels, but post IDs include channel name
    # from data-post attribute (DavaiSNami/11077), so second channel's posts
    # have same IDs and get deduped
    assert len(posts) == 3


def test_tg_get_events_skip_existing(requests_get_channel):
    params = {
        "channels": ["DavaiSNami"],
        "days": 365,
    }
    existing_ids = ["TG-DavaiSNami-11077", "TG-DavaiSNami-11078"]
    posts = list(Telegram().get_events(request_params=params, existed_event_ids=existing_ids))

    # Should only get 1 post (11079)
    assert len(posts) == 1
    assert posts[0].id == "TG-DavaiSNami-11079"


def test_tg_post_text_extraction(requests_get_channel):
    params = {
        "channels": ["DavaiSNami"],
        "days": 365,
    }
    posts = list(Telegram().get_events(request_params=params, tags=["full_text", "post_text"]))

    # Check that text is properly extracted (post 11077 is last, 11079 is first)
    assert "Бесплатная лекция" in posts[0].full_text
    assert "Приглашаем на концерт" in posts[2].full_text
    assert "Когда:" in posts[2].full_text


def test_tg_video_thumbnail(requests_get_channel):
    params = {
        "channels": ["DavaiSNami"],
        "days": 365,
    }
    posts = list(Telegram().get_events(request_params=params, tags=["poster_imag"]))

    # First post (newest, 11079) has video thumbnail but parser only extracts photo_wrap
    assert posts[0].poster_imag is None
    # Last post (oldest, 11077) has a photo
    assert posts[2].poster_imag == "https://cdn4.telesco.pe/file/test_image_1.jpg"


def test_tg_date_extraction(requests_get_channel):
    params = {
        "channels": ["DavaiSNami"],
        "days": 365,
    }
    posts = list(Telegram().get_events(request_params=params, tags=["date_from", "date_to"]))

    # Posts in reverse chronological order: 11079, 11078, 11077
    # date_from == date_to for TG posts (single point in time)
    assert posts[0].date_from == posts[0].date_to

    # Post 11079: UTC 2026-02-03T15:00:00 → Moscow 18:00 (UTC+3)
    assert posts[0].date_from.year == 2026
    assert posts[0].date_from.month == 2
    assert posts[0].date_from.day == 3
    assert posts[0].date_from.hour == 18
    assert posts[0].date_from.minute == 0

    # Post 11078: UTC 2026-02-02T10:30:00 → Moscow 13:30 (UTC+3)
    assert posts[1].date_from.day == 2
    assert posts[1].date_from.hour == 13
    assert posts[1].date_from.minute == 30

    # Post 11077: UTC 2026-02-01T12:00:00 → Moscow 15:00 (UTC+3)
    assert posts[2].date_from.day == 1
    assert posts[2].date_from.hour == 15
    assert posts[2].date_from.minute == 0


def test_tg_custom_tags(requests_get_channel):
    params = {
        "channels": ["DavaiSNami"],
        "days": 365,
    }
    posts = list(Telegram().get_events(request_params=params, tags=["title", "url"]))

    assert hasattr(posts[0], 'title')
    assert hasattr(posts[0], 'url')
    # Should not have other attributes
    assert not hasattr(posts[0], 'full_text')
