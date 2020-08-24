from datetime import datetime as dt

from escraper.parsers import Timepad, Radario


def test_auth():
    pass


def test_radario():
    r = Radario()

    date_from_dt = dt.now()
    date_to_dt = dt.now()
    e = r.get_events(date_from_dt, date_to_dt)
