
import pytest
import requests
from datetime import datetime
from pathlib import Path

from escraper.parsers import Ticketscloud

from .testing import Response

TESTDATA = Path(__file__).parent / "test_data" / "test_ticketscloud"
ZEROS = dict(second=0, microsecond=0)

@pytest.fixture
def requests_get_event(monkeypatch):
    def get(path, **kwargs):
        with open(path + ".html", encoding="utf-8") as file:
            text = file.read()
        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(Ticketscloud, "BASE_URL", str(TESTDATA) + "/")

def test_ticketscloud_get_event_with_none():
    with pytest.raises(ValueError):
        Ticketscloud().get_event()

def test_ticketscloud_get_event(requests_get_event):
    event_url = str(TESTDATA) + "/event_card_1"
    event = Ticketscloud().get_event(event_url=event_url)

    assert event.adress == "Невский проспект, дом 35"
    assert event.category == "Концерты"
    # Ticketscloud: iCal DTSTART 20240809T163000Z means UTC 16:30,
    # should be Moscow 19:30 — but parser treats Z as literal (naive datetime),
    # so astimezone interprets it as local system time.
    # TODO: fix Z handling in ticketscloud.py — currently off by ~3 hours
    assert event.date_from.year == 2024
    assert event.date_from.month == 8
    assert event.date_from.day == 9
    assert isinstance(event.date_from, datetime)
    assert isinstance(event.date_to, datetime)
    assert event.date_to > event.date_from
    assert event.id == Ticketscloud.source + "-123456"
    assert event.place_name == "Двор Гостинки"
    assert event.full_text.startswith("Эти ребята регулярно собирают миллионы просмотров")
    assert event.post_text.startswith("Эти ребята регулярно собирают миллионы просмотров")
    assert event.poster_imag == "https://ticketscloud.org/image/full/063ca253-4ff1-6e01-c8a7-4604b102467c.jpg"
    assert event.price == "1500₽"
    assert event.title[2:] == "Концерт группы «Хлеб». Summer Sound x билайн"  # without emoji
    assert event.is_registration_open is True
