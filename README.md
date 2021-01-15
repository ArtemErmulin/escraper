# escraper

<div align="center">

[![Updates](https://pyup.io/repos/github/ArtemErmulin/escraper/shield.svg)](https://pyup.io/repos/github/ArtemErmulin/escraper/)
[![Python 3](https://pyup.io/repos/github/ArtemErmulin/escraper/python-3-shield.svg)](https://pyup.io/repos/github/ArtemErmulin/escraper/)
[![CodeFactor](https://www.codefactor.io/repository/github/artemermulin/escraper/badge/master)](https://www.codefactor.io/repository/github/artemermulin/escraper/overview/master)
[![Build Status](https://travis-ci.com/ArtemErmulin/escraper.svg?branch=master)](https://travis-ci.com/ArtemErmulin/escraper)
[![codecov](https://codecov.io/gh/ArtemErmulin/escraper/branch/master/graph/badge.svg)](https://codecov.io/gh/ArtemErmulin/escraper)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

</div>


Event Scraper

**Don't stable, work in progress.**

Istalling:
```bash
pip install git+https://git@github.com/ArtemErmulin/escraper.git@master#egg=escraper-1.1.1
```

# Usage
Available sites-parsers:
```python
>>> from escraper.paresrs import all_parsers
>>> all_parsers
{'timepad': escraper.parsers.timepad.Timepad,
 'radario': escraper.parsers.radario.Radario}
```

## Timepad
```python
>>> from escraper import Timepad
```

For using timepad parser, you need timepad token. There are several ways to apply you token:
- as argument `token` in `Timepad` class
```python
>>> timepad = Timepad(token=<your-token>)
```
- as environ variable `TIMEPAD_TOKEN`. Then don't need any argument in `Timepad` class
```python
>>> import os

>>> "TIMEPAD_TOKEN" in os.environ
True
>>> timepad = Timepad()
```

Get event post by event_id:
```python
>>> timepad.get_event(event_id=1234567)
<event namedtuple>
```

or by url:
```python
>>> event_url = "https://timepad.ru/event/1234567/"
>>> timepad.get_event(event_url=event_url)
<event namedtuple>
```

Get events by parameters (for more see `Timepad.get_events` docstring):
```python
>>> timepad.get_events(request_params=params)
<list events data namedtuple>
```

## Radario
```python
>>> from escraper import Radario
```

For using radario parser you don't need any tokens:
```python
>>> radario = Radario()
```

Get event from radario will raise `NotImplementedError`.

Get events by parameters (for more see `Radario.get_events` docstring):
```python
>>> radario.get_events(request_params=params)
<list events data namedtuple>
```