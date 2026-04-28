# escraper

<div align="center">

[![Updates](https://pyup.io/repos/github/ArtemErmulin/escraper/shield.svg)](https://pyup.io/repos/github/ArtemErmulin/escraper/)
[![Python 3](https://pyup.io/repos/github/ArtemErmulin/escraper/python-3-shield.svg)](https://pyup.io/repos/github/ArtemErmulin/escraper/)
[![CodeFactor](https://www.codefactor.io/repository/github/artemermulin/escraper/badge/master)](https://www.codefactor.io/repository/github/artemermulin/escraper/overview/master)
[![Build Status](https://travis-ci.com/ArtemErmulin/escraper.svg?branch=master)](https://travis-ci.com/ArtemErmulin/escraper)
[![codecov](https://codecov.io/gh/ArtemErmulin/escraper/branch/master/graph/badge.svg)](https://codecov.io/gh/ArtemErmulin/escraper)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

</div>

Event Scraper — a unified Python library for scraping events from multiple platforms.

**Work in progress.**

## Installing

```bash
pip install git+https://git@github.com/ArtemErmulin/escraper.git@master#egg=escraper-1.1.10
```

## Available Parsers

```python
>>> from escraper.parsers import all_parsers
>>> all_parsers.keys()
dict_keys(['timepad', 'radario', 'ticketscloud', 'vk', 'mts', 'cltr', 'tripster', 'tg', 'yandex', 'config'])
```

## Quick Start

Every parser exposes two methods:
- `get_event(...)` — fetch a single event by URL or ID
- `get_events(...)` — fetch a list of events with filters

Both return namedtuples with selectable fields (tags):

```python
>>> from escraper import ALL_EVENT_TAGS
>>> ALL_EVENT_TAGS
('adress', 'category', 'date_from', 'date_to', 'date_from_to', 'id',
 'place_name', 'post_text', 'full_text', 'poster_imag', 'price',
 'title', 'url', 'ticket_url', 'source', 'is_registration_open')
```

All `date_from` / `date_to` fields are timezone-aware datetime objects in `Europe/Moscow`. This means they can be safely compared with other aware datetimes (e.g. from Django ORM) without `TypeError: can't compare offset-naive and offset-aware datetimes`.

## Timepad

Requires `TIMEPAD_TOKEN` (env variable or constructor argument):

```python
>>> from escraper import Timepad

>>> timepad = Timepad(token="your-token")
# or set TIMEPAD_TOKEN in .env / environment

>>> event = timepad.get_event(event_id=1234567)
>>> event.title
'🎸 Rock Concert'
>>> event.price
'500₽'

>>> event = timepad.get_event(event_url="https://timepad.ru/event/1234567/")

>>> params = {
...     "cities": "Санкт-Петербург",
...     "starts_at_min": "2024-06-01",
...     "starts_at_max": "2024-06-07",
... }
>>> events = timepad.get_events(request_params=params)
>>> len(events)
42
```

## MTS Live

```python
>>> from escraper import MTS

>>> mts = MTS()
>>> event = mts.get_event(event_url="https://live.mts.ru/sankt-peterburg/event/...")
>>> event.title
'🎵 Concert Name'
>>> event.adress
'Невский проспект, дом 35'

>>> params = {
...     "city": "sankt-peterburg",
...     "categories": ["concerts", "theater"],
...     "date_from": "2024-06-01",
...     "date_to": "2024-06-07",
... }
>>> events = mts.get_events(request_params=params)
```

## Culture.ru

```python
>>> from escraper import Culture

>>> cltr = Culture()
>>> params = {
...     "city": "sankt-peterburg",
...     "categories": ["spektakli", "kontserti"],
...     "date_from": "2024-06-01",
...     "date_to": "2024-06-05",
... }
>>> events = cltr.get_events(request_params=params)
```

## Tripster

Requires `TRIPSTER_TOKEN` and `TRIPSTER_PARTNER_ID`:

```python
>>> from escraper import Tripster

>>> tripster = Tripster(token="your-token", partner_id="your-id")
>>> params = {"city__slug": "Saint_Petersburg", "days": "7"}
>>> events = tripster.get_events(request_params=params)
>>> events[0].title
'🐢 Walking Tour of Dostoevsky's Petersburg'
```

## Telegram Channels

Scrapes public Telegram channel previews:

```python
>>> from escraper.parsers import Telegram

>>> tg = Telegram()
>>> params = {"channels": ["DavaiSNami", "spb_afisha"]}
>>> events = tg.get_events(request_params=params)
>>> events[0].source
'TG'
>>> events[0].id
'TG-DavaiSNami-11077'
```

## Yandex Afisha

```python
>>> from escraper.parsers import Yandex

>>> ya = Yandex()
>>> params = {"city": "saint-petersburg", "category": "concert"}
>>> events = ya.get_events(request_params=params)
```

## ConfigScraper (Configurable Sites)

A single parser for small event sites driven by CSS selector configs. No new code needed to add a site — just add a config dict:

```python
>>> from escraper.parsers import ConfigScraper

>>> scraper = ConfigScraper()

# Scrape from a built-in site
>>> events = scraper.get_events(request_params={"site": "sevcable"})
>>> events[0].id
'CFG-SEVC-some-event-slug'
>>> events[0].source
'CFG'

# Scrape a single event page
>>> event = scraper.get_event(
...     event_url="https://sevcableport.ru/afisha/some-event/",
...     site="sevcable",
... )

# Pass a custom config dict (no registration needed)
>>> my_config = {
...     "name": "mysite",
...     "source": "MY",
...     "base_url": "https://example.com",
...     "listing_url": "/events/",
...     "card_selector": "div.event-card",
...     "card_title_selector": "h3",
...     "card_date_selector": ".date",
...     "card_image_selector": "img",
...     "card_image_attr": "src",
...     "card_link_selector": "a",
...     "skip_detail": True,
...     "date_format": "russian",
...     "default_address": "ул. Примерная, 1",
...     "default_place": "My Place",
... }
>>> events = scraper.get_events(request_params={"site": my_config})
```

Built-in sites:
- `sevcable` — Севкабель Порт (sevcableport.ru)
- `newholland` — Новая Голландия (newhollandsp.ru)
- `levashovsky` — Левашовский хлебозавод (levashovsky.ru)
- `alexandrinsky` — Александринский театр (alexandrinsky.ru)

Supports Russian date formats: "21 февраля", "21 фев 19:00", "с 1 февраля по 28 февраля", "по 6 марта".

## Selecting Tags

Request only the fields you need:

```python
>>> tags = ("title", "price", "url", "date_from")
>>> event = mts.get_event(event_url="...", tags=tags)
>>> event.title
'🎸 Concert'
>>> event.price
'1500₽'
```

## Skipping Known Events

Pass `existed_event_ids` to avoid re-processing:

```python
>>> known = ["MTS-12345", "MTS-67890"]
>>> events = mts.get_events(request_params=params, existed_event_ids=known)
```

## Timezone Handling

All parsers return `date_from` and `date_to` as **timezone-aware** datetime objects in `Europe/Moscow`:

```python
>>> event.date_from
datetime.datetime(2026, 2, 17, 19, 0, tzinfo=<DstTzInfo 'Europe/Moscow' MSK+3:00:00 STD>)

>>> event.date_from.tzinfo
<DstTzInfo 'Europe/Moscow' MSK+3:00:00 STD>
```

Internally, all parsers use `.astimezone(self.TIMEZONE)` to produce aware datetimes. For naive datetimes (scraped from HTML without timezone info), `.astimezone()` assumes the **system timezone** — so the scraping process should run with `TZ=Europe/Moscow` or equivalent (e.g. Celery `timezone = "Europe/Moscow"`).

## Environment Variables

Set in `.env` or your environment:

| Variable | Parser | Required |
|---|---|---|
| `TIMEPAD_TOKEN` | Timepad | Yes |
| `VK_TOKEN`, `VK_ID` | VK | Yes |
| `TRIPSTER_TOKEN`, `TRIPSTER_PARTNER_ID` | Tripster | Yes |
| `TC_TOKEN`, `TC_VIBE_REF` | Ticketscloud | Yes |
| `MTS_TICKET_URL_TEMPLATE` | MTS | Optional |
| `PROXY` | All | Optional |

## Running Tests

```bash
pip install pytest pytest-cov
pytest --verbose --cov-report term --cov=escraper/
```
