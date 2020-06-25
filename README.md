# escraper
Event Scraper

Istalling:
```bash
pip install -e git+ssh://git@github.com/ArtemErmulin/escraper.git@master#egg=escraper
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
>>> timepad.get_event(event_id=1327190, as_post=False)
<named tuple event data>
```

Get events by parameters (for more see `Timepad.get_events` docstring):
```python
>>> params = dict(cities="Санкт-Петербург")
>>> timepad.get_events(request_params=params)
<list 10 event posts by city "Санкт-Петербург">
```
```python
>>> timepad.get_events(request_params=params, as_posts=False)
<list 10 event data namedtuple by city "Санкт-Петербург">
```