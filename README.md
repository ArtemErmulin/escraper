# escraper

<div align="center">

[![CodeFactor](https://www.codefactor.io/repository/github/artemermulin/escraper/badge/master)](https://www.codefactor.io/repository/github/artemermulin/escraper/overview/master)
[![Build Status](https://travis-ci.com/ArtemErmulin/escraper.svg?branch=master)](https://travis-ci.com/ArtemErmulin/escraper)
[![codecov](https://codecov.io/gh/ArtemErmulin/escraper/branch/master/graph/badge.svg)](https://codecov.io/gh/ArtemErmulin/escraper)

</div>


Event Scraper

**Don't stable, work in progress.**

Istalling:
```bash
pip install git+https://git@github.com/ArtemErmulin/escraper.git@master#egg=escraper-0.0.5
```

# Usage
```python
>>> from escraper.parsers import Timepad
>>> timepad = Timepad()
```
Available sites-parsers:
```python
>>> from escraper import all_parsers
>>> all_parsers
{'timepad': escraper.parsers.Timepad}
```
## Timepad
Get event post by event_id:
```python
>>> timepad.get_event(event_id=1327190)
<event post>
```

or by url:
```python
>>> event_url = "https://excava.timepad.ru/event/1327190/"
>>> timepad.get_event(event_url=event_url)
<event post>
```

Get event data as named tuple:
```python
>>> timepad.get_event(event_id=1327190)
<named tuple event data>
```

Get events by parameters (for more see `Timepad.get_events` docstring):
```python
>>> timepad.get_events(request_params=params)
<list 10 event data namedtuple by city "Санкт-Петербург">
```
