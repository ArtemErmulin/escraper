from datetime import datetime as dt

import pytest

from escraper.parsers import Timepad, Radario



@pytest.fixture
def timepad():
    return Timepad()


def test_timepad_get_events(timepad):
    assert timepad.get_events()


def test_timepad_event_catogories(timepad):
    assert timepad.event_categories


def test_timepad_event_statuses(timepad):
    assert timepad.event_statuses


def test_timepad_ticket_statuses(timepad):
    assert timepad.tickets_statuses


def test_radario():
    r = Radario()

    date_from_dt = dt.now()
    date_to_dt = dt.now()
    events = r.get_events(date_from_dt, date_to_dt)

    assert events
