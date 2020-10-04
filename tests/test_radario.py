import pytest
import requests
from datetime import datetime
from pathlib import Path


from escraper.parsers import Radario
from escraper.testing import Response


TESTDATA = Path(__file__).parent / "test_data" / "test_radario"
ZEROS = dict(minute=00, second=00, microsecond=00)
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
    events = Radario().get_events(date_from=datetime.now(), date_to=datetime.now())

    assert len(events) == 1

    event = events[0]

    assert event.adress == "test adress"
    assert event.category == "test category"
    assert event.date_from == datetime.now().replace(month=1, day=1, hour=0, **ZEROS)
    assert event.date_to is None
    assert event.date_from_to == "01 января, 00:00"
    assert event.id == Radario.parser_prefix + "test id"
    assert event.place_name == "test place_name"
    assert event.post_text == "test post_text"
    assert event.poster_imag == "test_image.png"
    assert event.price == "test price"
    assert event.title[2:] == "test title"  # without emoji
    assert event.is_registration_open is True


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
    events = Radario().get_events(date_from="", date_to="", tags=("adress",))

    assert len(events) == 1

    event = events[0]
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
    events = Radario().get_events(date_from="", date_to="", tags=("adress",))

    assert len(events) == 1

    event = events[0]
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
    events = Radario().get_events(date_from="", date_to="", tags=("adress",))

    assert len(events) == 1

    event = events[0]
    assert event.adress == "Test avenue, 111"


@pytest.mark.parametrize(
    "test_file, date_from, date_to",
    [
        ("event_card_5", datetime.now().replace(month=1, day=1, hour=00, **ZEROS), datetime.now().replace(month=1, day=1, hour=1, **ZEROS)),
        ("event_card_6", datetime.now().replace(month=1, day=1, hour=00, **ZEROS), None),
        ("event_card_7", datetime.now().replace(month=1, day=1, hour=00, **ZEROS), datetime.now().replace(month=1, day=2, hour=00, **ZEROS)),
    ],
    ids=[
        "dd month, HH:MM-HH:MM",
        "dd month, HH:MM",
        "dd-dd month",
    ],
)
def test_radario_date_from_to(monkeypatch, test_file, date_from, date_to):
    def get(path, **kwargs):
        with open(path + ".html") as file:
            text = file.read()

        return Response(ok=True, text=text)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(Radario, "BASE_URL", str(TESTDATA / test_file))
    monkeypatch.setattr(Radario, "BASE_EVENTS_API", str(TESTDATA) + "/")

    events = Radario().get_events(date_from="", date_to="", tags=("date_from", "date_to"))

    assert len(events) == 1

    event = events[0]
    assert event.date_from == date_from and event.date_to == date_to
