# escraper
Event Scraper

Istalling:
```bash
pip install -e git+ssh://git@github.com/ArtemErmulin/escraper.git@master#egg=escraper
```

# Usage
```python
>>> from escraper import EventParser
>>> p = EventParser()
>>> p.all_parsers
['timepad']
>>> p.get_events()
...
```
