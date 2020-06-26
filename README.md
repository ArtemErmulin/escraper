# escraper
Event Scraper

**Don't stable, working in progress.**

Istalling:
```bash
pip install -e git+ssh://git@github.com/ArtemErmulin/escraper.git@master#egg=escraper
```

# Usage
```python
>>> from escraper import EventParser
>>> ep = EventParser()
```
Available sites-parsers:
```python
>>> ep.all_parsers
['timepad']
```
## Timepad
Get event post by event_id:
```python
>>> ep.get_event(source="timepad", event_id=1327190)
<event post>
```

or by url:
```python
>>> event_url = "https://excava.timepad.ru/event/1327190/"
>>> ep.get_event(source="timepad", event_url=event_url)
<event post>
```

Get event data as named tuple:
```python
>>> ep.get_event(source="timepad", event_id=1327190, as_post=False)
<named tuple event data>
```

Get events by parameters (for more see `Timepad.get_events` docstring):
```python
>>> params = dict(cities="Санкт-Петербург")
>>> ep.get_events(source="timepad", request_params=params)
<list 10 event posts by city "Санкт-Петербург">
```
```python
>>> ep.get_events(source="timepad", request_params=params, as_posts=False)
<list 10 event data namedtuple by city "Санкт-Петербург">
```
