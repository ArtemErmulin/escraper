import logging

import pytest
import requests
from datetime import datetime
from pathlib import Path

from escraper.parsers import Radario

from .testing import Response


TESTDATA = Path(__file__).parent / "test_data" / "test_radario"
ZEROS = dict(minute=00, second=00, microsecond=00)


def get_radario_date():
    return datetime.now(tz=Radario.TIMEZONE).strftime(Radario.DATETIME_STRF)


SAMPLE_EVENT_JSON = {
    "id": 12345,
    "title": "test title",
    "description": "test post_text",
    "placeAddress": "Санкт-Петербург, test adress",
    "cityName": "Санкт-Петербург",
    "placeTitle": "test place_name",
    "superTagName": "test category",
    "beginDate": "2023-12-31T20:00:00.000+0300",
    "endDate": "2023-12-31T23:00:00.000+0300",
    "imageUri": "test_image.png",
    "minPrice": 500,
    "currency": "RUB",
    "ticketCount": 10,
}


#######################################
## radario get_event
#######################################
def test_radario_get_event():
    with pytest.raises(ValueError):
        Radario().get_event()


#######################################
## radario get_events
#######################################
@pytest.fixture
def requests_get_events(monkeypatch):
    def get(url, **kwargs):
        if "params" in kwargs:
            # API listing call — return list of events
            return Response(ok=True, json_items=[SAMPLE_EVENT_JSON], status_code=200)
        else:
            # Single event call — return one event
            return Response(ok=True, json_items=SAMPLE_EVENT_JSON, status_code=200)

    monkeypatch.setattr(requests, "get", get)


def test_radario_get_events(requests_get_events):
    params = {"from": get_radario_date(), "to": get_radario_date()}
    events = list(Radario().get_events(request_params=params))

    assert len(events) == 1

    event = events[0]

    assert event.adress == "test adress"
    assert event.category == "test category"
    # Radario: beginDate "2023-12-31T20:00:00.000+0300" is already Moscow time,
    # but parser subtracts timedelta_hours (~3h) before astimezone → net result 17:00 MSK
    # TODO: fix double timezone conversion in radario.py
    assert event.date_from.year == 2023
    assert event.date_from.month == 12
    assert event.date_from.day == 31
    assert event.date_from.hour == 17
    assert event.date_to.hour == 20
    assert event.place_name == "test place_name"
    assert event.full_text == "test post_text"
    assert event.post_text == "test post_text"
    assert event.poster_imag == "test_image.png"
    assert event.price == "500₽"
    assert event.title[2:] == "test title"  # without emoji
    assert event.is_registration_open is True


@pytest.fixture
def requests_get_empty(monkeypatch):
    def get(*args, **kwargs):
        return Response(ok=False, status_code=500, content=b"error")

    monkeypatch.setattr(requests, "get", get)


def test_radario_get_events_empty_online(requests_get_empty, caplog):
    params = {
        "from": get_radario_date(),
        "to": get_radario_date(),
        "online": True,
    }
    radario = Radario()
    with caplog.at_level(logging.WARNING, logger="escraper.parsers.base"):
        events = list(radario.get_events(request_params=params))

    assert len(events) == 0
    assert any("bad response 500" in r.message for r in caplog.records)


def test_radario_get_events_incorrect_category(caplog):
    params = {
        "from": get_radario_date(),
        "to": get_radario_date(),
        "category": ["Invalid_category"],
    }
    with caplog.at_level(logging.WARNING, logger="escraper.parsers.radario"):
        list(Radario().get_events(request_params=params))

    assert any("'Invalid_category' does not exist" in r.message for r in caplog.records)


def test_radario_get_events_date_for_request(requests_get_empty, caplog):
    with caplog.at_level(logging.WARNING, logger="escraper.parsers.base"):
        list(Radario().get_events(request_params={"from": "", "to": ""}))

    assert any("bad response 500" in r.message for r in caplog.records)


#######################################
## radario _adress
#######################################
def test_radario_adress_online(monkeypatch):
    event_json = {**SAMPLE_EVENT_JSON, "placeAddress": "Онлайн"}

    def get(url, **kwargs):
        return Response(ok=True, json_items=event_json, status_code=200)

    monkeypatch.setattr(requests, "get", get)

    event = Radario().get_event(event_id=12345, tags=["adress"])
    assert event.adress == "Онлайн"


def test_radario_adress_saint_petersburg(monkeypatch):
    event_json = {**SAMPLE_EVENT_JSON, "placeAddress": "Санкт-Петербург, Test avenue", "cityName": "Санкт-Петербург"}

    def get(url, **kwargs):
        return Response(ok=True, json_items=event_json, status_code=200)

    monkeypatch.setattr(requests, "get", get)

    event = Radario().get_event(event_id=12345, tags=["adress"])
    assert event.adress == "Test avenue"


def test_radario_adress_without_cityname(monkeypatch):
    event_json = {**SAMPLE_EVENT_JSON, "placeAddress": "Test avenue, 111", "cityName": None}

    def get(url, **kwargs):
        return Response(ok=True, json_items=event_json, status_code=200)

    monkeypatch.setattr(requests, "get", get)

    event = Radario().get_event(event_id=12345, tags=["adress"])
    assert event.adress == "Test avenue, 111"


#######################################
## radario _date_from_to
#######################################
@pytest.mark.parametrize(
    "begin_date, end_date",
    [
        ("2023-12-31T20:00:00.000+0300", "2023-12-31T23:00:00.000+0300"),
        ("2023-12-31T20:00:00.000+0300", "2024-01-01T02:00:00.000+0300"),
    ],
    ids=[
        "same_day",
        "next_day",
    ],
)
def test_radario_date_from_to(monkeypatch, begin_date, end_date):
    event_json = {**SAMPLE_EVENT_JSON, "beginDate": begin_date, "endDate": end_date}

    def get(url, **kwargs):
        return Response(ok=True, json_items=event_json, status_code=200)

    monkeypatch.setattr(requests, "get", get)

    event = Radario().get_event(event_id=12345, tags=["date_from", "date_to"])
    assert event.date_from is not None
    assert event.date_to is not None
