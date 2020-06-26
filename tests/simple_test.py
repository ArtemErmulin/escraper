import sys
sys.path.append('./')
from escraper.parsers import Timepad
tp=Timepad()

import sqlite3


def events_url(events): #функция вывода, для вывода только необходимой информации
	for e in events:
		print(e.title,e.url, e.date)

if __name__ == '__main__':
	try:
		if sys.argv[1]=='db': #посмотреть базу данных на все добавленные события
			conn = sqlite3.connect('eventDB.sqlite')
			cursor = conn.cursor()
			enq="SELECT title,date_start, url FROM events;"
			cursor.execute(enq)
			for line in cursor.fetchall():
				print(line)
			conn.close()


		elif sys.argv[1]=='2db': #добавить в базу данных 10 событий от сегодня
			tp.events4day()
	except:		 #elif sys.argv[1]=='events':
		#проверить на работу бота и что он выдаёт
		params={'limit':100,'price_max':500,'starts_at_min': "2020-06-27T00:00:00",'starts_at_max': "2020-06-27T23:59:00",
		 'category_ids_exclude':'217, 376, 379, 399, 453, 1315'}
		#to-do переместить параметры params в файл 
		q=tp.get_events4db(request_params=params) 
		print() 
		events_url(q)
		print(len(q))