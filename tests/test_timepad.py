import os
from datetime import datetime

import pytest
import requests

from escraper.parsers import Timepad

from .testing import Response


from dotenv import load_dotenv

load_dotenv()
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


def test_timepad_original_get_events():
    token = os.environ.get("TIMEPAD_TOKEN")
    timepad = Timepad(token=token)

    timepad_others_params = dict(
        limit=10,
        cities="Санкт-Петербург",
        moderation_statuses="featured, shown",
        price_max=1500,
    )

    result = list(timepad.get_events(request_params=timepad_others_params))
    assert len(result) > 0
    assert len(result) <= 10

def test_timepad_original_get_events_in_other_city():
    token = os.environ.get("TIMEPAD_TOKEN")
    timepad = Timepad(token=token)

    timepad_others_params = dict(
        limit=10,
        cities="Казань",
        moderation_statuses="featured, shown",
        price_max=1500,
    )

    result = list(timepad.get_events(request_params=timepad_others_params))
    assert len(result) > 0


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
    Timepad(token='').get_event(event_id=12345)


def test_timepad_get_event_by_url(requests_get_event):
    Timepad(token='').get_event(event_url="https://test.test/event/12345/")


def test_timepad_get_event_with_tags(requests_get_event):
    tags = ("adress", "category")
    event = Timepad(token='').get_event(event_id=12345, tags=tags)
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
    assert len(list(Timepad().get_events())) == 1


@pytest.fixture
def requests_get_events_not_moderated(monkeypatch):
    timepad_response_event = dict(
        moderation_status="not_moderated",
    )

    def get(*args, **kwargs):
        return Response(ok=True, json_items=dict(values=[timepad_response_event]))

    monkeypatch.setattr(requests, "get", get)


def test_timepad_get_events_not_moderated(requests_get_events_not_moderated):
    # not-moderated events are no longer emitted (previously yielded None)
    assert len(list(Timepad().get_events())) == 0


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


def test_timepad_adress(requests_get_event_adress):
    tags = ("adress",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.adress == "test_address"


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

    assert event.adress == "test"


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
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.adress == "test"


#######################################
## timepad _date_to
#######################################
@pytest.fixture
def requests_get_event_date_to(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        ends_at="1900-01-01T00:00:00+0000",
    )

    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_date_to(requests_get_event_date_to):
    tags = ("date_to",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert isinstance(event.date_to, datetime)


@pytest.fixture
def requests_get_event_dates(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        starts_at="2024-06-15T16:00:00+0000",
        ends_at="2024-06-15T19:00:00+0000",
    )

    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_dates_utc_to_moscow(requests_get_event_dates):
    """UTC 16:00 → Moscow 19:00 (UTC+3)"""
    tags = ("date_from", "date_to")
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.date_from.year == 2024
    assert event.date_from.month == 6
    assert event.date_from.day == 15
    assert event.date_from.hour == 19
    assert event.date_from.minute == 0
    assert str(event.date_from.tzinfo) == "Europe/Moscow"

    assert event.date_to.hour == 22
    assert event.date_to.minute == 0


#######################################
## timepad _post_text
#######################################
@pytest.mark.parametrize(
    "description",
    [
        dict(description_short="test"),
        dict(description_html="test"),
    ],
    ids=[
        "description_short",
        "sescription_html",
    ],
)
def test_timepad_post_text(monkeypatch, description):
    timepad_response_event = dict(
        moderation_status="moderated",
        **description,
    )

    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)

    tags = ("post_text",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.post_text == "test"


#######################################
## timepad _poster_imag
#######################################
@pytest.fixture
def requests_get_event_poster_imag(monkeypatch):
    timepad_response_event = dict(
        moderation_status="moderated",
        poster_image=dict(uploadcare_url="12test_image"),
    )

    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)


def test_timepad_poster_imag(requests_get_event_poster_imag):
    tags = ("poster_imag",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.poster_imag == "test_image"


#######################################
## timepad _price
#######################################
@pytest.mark.parametrize(
    "ticket_type, answ, is_registration_open",
    [
        (dict(price=0, status="ok"), "Бесплатно", True),
        (
            dict(price=2, status="ok"),
            "2₽",
            True,
        ),
        (
            dict(price=0, status=""),
            "Билетов нет",
            False,
        ),
    ],
    ids=["free", "price", "closed_registration"],
)
def test_timepad_price(monkeypatch, ticket_type, answ, is_registration_open):
    timepad_response_event = dict(
        moderation_status="moderated",
        registration_data=dict(
            price_min=2,
            price_max=2,
        ),
        ticket_types=[ticket_type],
    )
    timepad_response_event["registration_data"][
        "is_registration_open"
    ] = is_registration_open

    def get(*args, **kwargs):
        return Response(ok=True, json_items=timepad_response_event)

    monkeypatch.setattr(requests, "get", get)
    tags = ("price",)
    event = Timepad().get_event(event_id=12345, tags=tags)

    assert event.price == answ


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



####################################
#### TIMEPAD original site test ####
####################################

### get events

TIMEPAD_TOKEN = os.getenv("TIMEPAD_TOKEN")
def test_timepad_get_events_ntr():
    assert len(list(Timepad(token=TIMEPAD_TOKEN).get_events())) == 10
