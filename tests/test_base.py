import os
from datetime import datetime

import pytest
import requests

from escraper.parsers import Timepad, Radario
import find_metro


#######################################
## timepad token
#######################################
@pytest.fixture
def remove_token(monkeypatch):
    mock_environ = dict()
    monkeypatch.setattr(os, "environ", mock_environ)


def test_timepad_token_without(remove_token):
    with pytest.raises(ValueError):
        Timepad()


def test_timepad_token_in_args():
    assert "TIMEPAD_TOKEN" in os.environ
    token = os.environ.get("TIMEPAD_TOKEN")
    Timepad(token=token)


def test_timepad_token_in_environ():
    assert "TIMEPAD_TOKEN" in os.environ
    Timepad()


class Response:
    def __init__(self, content=None, ok=None, json_items=None):
        self.content = content
        self.ok = ok
        self.json_items = json_items

    def json(self):
        return dict(**self.json_items)


#######################################
## timepad get_event
#######################################
timepad_response_event = dict(
    location=dict(),
    categories=[dict(name="test")],
    starts_at="1900-01-01T00:00:00+0000",
    id=1,
    organization=dict(name="test"),
    registration_data=dict(
        is_registration_open=True,
        price_min=0,
        price_max=1,
    ),
    ticket_types=[],
    name="test",
    url="https://test.test",
    moderation_status="moderated",
)


@pytest.fixture
def requests_get_event(monkeypatch):
    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_get_event_by_id(requests_get_event):
    Timepad().get_event(event_id=12345)


def test_timepad_get_event_by_url(requests_get_event):
    Timepad().get_event(event_url="https://test.test/event/12345/")


def test_timepad_get_event_with_tags(requests_get_event):
    tags = ("adress", "category")
    event = Timepad().get_event(event_id=12345, tags=tags)
    assert event._fields == tags


def test_timepad_get_event_without_args(requests_get_event):
    with pytest.raises(ValueError):
        Timepad().get_event()


@pytest.fixture
def requests_get_event_not_moderated(monkeypatch):
    timepad_response_event = dict(
        moderation_status="not_moderated",
    )
    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_get_event_not_moderated(requests_get_event_not_moderated):
    assert Timepad().get_event(event_id=12345) is None


#######################################
## timepad get_events
#######################################
@pytest.fixture
def requests_get_events(monkeypatch):
    def get(*args, **kwargs):
        return Response(ok=True, json_items=dict(values=[timepad_response_event]))

    monkeypatch.setattr(requests, "get", get)


def test_timepad_get_events(requests_get_events):
    assert len(Timepad().get_events()) == 1


@pytest.fixture
def requests_get_events_not_moderated(monkeypatch):
    timepad_response_event = dict(
        moderation_status="not_moderated",
    )
    def get(*args, **kwargs):
        return Response(ok=True, json_items=dict(values=[timepad_response_event]))

    monkeypatch.setattr(requests, "get", get)


def test_timepad_get_events_not_moderated(requests_get_events_not_moderated):
    assert len(Timepad().get_events()) == 1


#######################################
## timepad _adress
#######################################
@pytest.fixture
def requests_get_event_adress(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        location=dict(city="test", address="test_address"),
    )
    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    def get_subway(*args, **kwargs):
        return "test subway"

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(find_metro.metro.get_subway_name, "get_subway", get_subway)

def test_timepad_adress(requests_get_event_adress):
    tags = ("adress",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.adress == "test_address, м.test subway"


@pytest.fixture
def requests_get_event_adress_city1(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        location=dict(city="Санкт-Петербург"),
    )
    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_adress_city1(requests_get_event_adress_city1):
    tags = ("adress",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.adress == "Санкт-Петербург"


@pytest.fixture
def requests_get_event_adress_city2(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        location=dict(city="Без города"),
    )
    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_adress_city2(requests_get_event_adress_city2):
    tags = ("adress",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.adress == "Онлайн"


@pytest.fixture
def requests_get_event_adress_city3(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        location=dict(city="test", coordinates=[1, 1]),
    )
    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_adress_city3(requests_get_event_adress_city3):
    tags = ("adress",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.adress == "1, 1"


@pytest.fixture
def requests_get_event_adress_city4(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        location=dict(city="test"),
    )
    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_adress_city4(requests_get_event_adress_city4):
    tags = ("adress",)

    with pytest.raises(TypeError):
        Timepad().get_event(event_id=12345, tags=tags)


#######################################
## timepad event_categories
#######################################
def test_timepad_event_catogories():
    assert Timepad().event_categories


#######################################
## timepad event_statuses
#######################################
def test_timepad_event_statuses():
    assert Timepad().event_statuses


#######################################
## timepad tickets_statuses
#######################################
def test_timepad_ticket_statuses():
    assert Timepad().tickets_statuses
