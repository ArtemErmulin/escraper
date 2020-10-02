import pytest
import requests
from datetime import datetime
from pathlib import Path


from escraper.parsers import Radario
from escraper.testing import Response


TESTDATA = Path(__file__).parent / "test_data" / "test_radario"
#######################################
## radario get_event
#######################################
def test_radario_get_event():
    with pytest.raises(NotImplementedError):
        Radario().get_event()


#######################################
## radario get_events
#######################################
@pytest.fixture
def requests_get_events(monkeypatch):
    def get(path, **kwargs):
        with open(path + ".html") as file:
            text = file.read()

        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(Radario, "BASE_URL", str(TESTDATA / "event_card_1"))
    monkeypatch.setattr(Radario, "BASE_EVENTS_API", str(TESTDATA) + "/")


def test_radario_get_events(requests_get_events):
    Radario().get_events(date_from=datetime.now(), date_to=datetime.now())


@pytest.fixture
def requests_get_empty(monkeypatch):
    def get(*args, **kwargs):
        return Response(ok=False)

    monkeypatch.setattr(requests, "get", get)


def test_radario_get_events_empty_online(requests_get_empty):
    radario = Radario()
    with pytest.warns(UserWarning):
        events = radario.get_events(
            date_from=datetime.now(),
            date_to=datetime.now(),
            request_params=dict(online=True),
        )

    assert radario.url == "https://online.radario.ru/"
    assert len(events) == 0


def test_radario_get_events_incorrect_category():
    with pytest.warns(UserWarning, match="Category 'Invalid_category' is not exist"):
        events = Radario().get_events(
            date_from=datetime.now(),
            date_to=datetime.now(),
            category=["Invalid_category"],
        )


def test_radario_get_events_date_for_request(requests_get_empty):
    with pytest.warns(UserWarning):
        Radario().get_events(date_from="", date_to="")



#######################################
## radario _adress
#######################################
@pytest.fixture
def requests_get_adress_online(monkeypatch):
    def get(path, **kwargs):
        with open(path + ".html") as file:
            text = file.read()

        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(Radario, "BASE_URL", str(TESTDATA / "event_card_2"))
    monkeypatch.setattr(Radario, "BASE_EVENTS_API", str(TESTDATA) + "/")


def test_radario_adress_online(requests_get_adress_online):
    [event] = Radario().get_events(date_from="", date_to="", tags=("adress",))
    assert event.adress == "Онлайн"


@pytest.fixture
def requests_get_adress_saint_petersburg(monkeypatch):
    def get(path, **kwargs):
        with open(path + ".html") as file:
            text = file.read()

        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(Radario, "BASE_URL", str(TESTDATA / "event_card_3"))
    monkeypatch.setattr(Radario, "BASE_EVENTS_API", str(TESTDATA) + "/")


def test_radario_adress_saint_petersburg(requests_get_adress_saint_petersburg):
    [event] = Radario().get_events(date_from="", date_to="", tags=("adress",))
    assert event.adress == "Test avenue"


@pytest.fixture
def requests_get_adress_without_cityname(monkeypatch):
    def get(path, **kwargs):
        with open(path + ".html") as file:
            text = file.read()

        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(Radario, "BASE_URL", str(TESTDATA / "event_card_4"))
    monkeypatch.setattr(Radario, "BASE_EVENTS_API", str(TESTDATA) + "/")


def test_radario_adress_without_cityname(requests_get_adress_without_cityname):
    [event] = Radario().get_events(date_from="", date_to="", tags=("adress",))
    assert event.adress == "Test avenue, 111"
