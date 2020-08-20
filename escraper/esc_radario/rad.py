import requests
from datetime import datetime

from bs4 import BeautifulSoup as bs
		

monthes = {"января": "01", "февраля":"02", "марта": "03", "апреля":"04", "мая": "05","июня":"06","июля":"07","августа":"08","сентября":"09","октября":"10" ,"ноября":"11","декабря":"12"}
STRPTIME = "%d %m %H:%M"

def save_file(filename,text):
	with open(filename, 'w') as file:
		file.write(text)


def get_site(site):
	r = requests.get(site)
	return r.text



def get_radario_events(html_text): #list of events
	soup = bs(html_text, 'html.parser')

	#soup.find_all("span", {"class":"event-card__date"})
	#soup.find_all("div", {"class":"event-row"})
	list_event_from_soup = soup.find_all("div", {"class":"event-card"})
	events = []
	for event in list_event_from_soup:
		event = str(event)
		event_soup = bs(event,'html.parser')

		price = event_soup.find("span", {"class":"event-card__price"}).text.strip()
		date = _date(event_soup)

		if price == 'Билетов нет' or date == None: continue
		
		place_name = event_soup.find("span", {"class":"event-card__place"}).text.strip().replace('Санкт-Петербург,\n      ', '') #TODO: change to good
		poster_imag = event_soup.find("img", {"class":"event-card__image"})['src']
		title = event_soup.find("a", {"class":"event-card__title"}).text.strip()
		event_id = event_soup.find("a", {"class":"event-card__title"})['href'].split('/')[-1]
		url = 'https://radario.ru/events/' + event_id
		#post_text = get_description(url)
		
		events.append({'title':title, 'event_id': int(event_id), 'url':url, 'price':price, 'date':date, 'place_name':place_name, 'poster_imag':poster_imag})


	return events

def get_description(url): #request to event's url and take description
	event_html = requests.get(url).text
	return event_html[event_html.find('",description:"')+15:event_html.find('",beginDate:"')]

def _date(event_soup):
	datenow = datetime.now()

	date = event_soup.find("span", {"class":"event-card__date"}).text #TODO: change
	if len(date.split(' -\n         '))>1: return #only one day event
	date_from = date.replace(',\n       ','').split('-')[0].replace(',','')

	for ru, num in monthes.items():
		date_from = date_from.replace(ru, num)
	date = datetime.strptime(date_from, STRPTIME)
	

	nowyear = datenow.year
	if date.month < datenow.month: 	nowyear += 1

	date = date.replace(year = nowyear)
	return date
	#.replace(',\n       ','')

