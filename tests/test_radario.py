import pytest
import requests
from datetime import datetime
from pathlib import Path


from escraper.parsers import Radario
from escraper.testing import Response


TESTDATA = Path(__file__).parent / "test_data" / "test_radario"
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
