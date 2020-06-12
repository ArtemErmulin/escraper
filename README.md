# escraper
Event Scraper

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
```
>>> ep.all_parsers
['timepad']
```
## Timepad
Get event by event_id:
```
>>> ep.get_events(source="timepad", event_id=1327190)
<event post>
```

or by url:
```
>>> event_url = "https://excava.timepad.ru/event/1327190/"
>>> ep.get_events(source="timepad", event_url=event_url)
<event post>
```
