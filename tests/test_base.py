from datetime import datetime as dt

from escraper.parsers import Timepad, Radario


def test_timepad():
    # get timepad token from environ
    t = Timepad()
    events = t.get_events()

    assert events


def test_radario():
    r = Radario()

    date_from_dt = dt.now()
    date_to_dt = dt.now()
    events = r.get_events(date_from_dt, date_to_dt)

    assert events
