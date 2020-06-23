from datetime import date
import sqlite3



# def makingDB():
    # conn = sqlite3.connect('eventDB.sqlite')
    # cursor = conn.cursor()
    # making="CREATE TABLE events\
    #   (title TEXT,\
    #   date_start CHAR(50) ,\
    #   place_name TEXT,\
    #   post_text CHAR(500),\
    #   adress CHAR(50),\
    #   poster_imag TEXT,\
    #   url CHAR(50),\
    #   price INT,\
    #   availability CHAR(50) );"
    # cursor.execute(making)
    # conn.close()



def add2db(events):
    conn = sqlite3.connect('eventDB.sqlite')
    cursor = conn.cursor()

    making = "CREATE TABLE IF NOT EXISTS events\
      (title TEXT,\
      date_start CHAR(50) ,\
      place_name TEXT,\
      post_text CHAR(500),\
      adress CHAR(50),\
      poster_imag TEXT,\
      url CHAR(50),\
      price INT,\
      availability CHAR(50) );"
    cursor.execute(making)
    for event in events:
        line=f"INSERT INTO events VALUES ('{event.title}', '{event.date}', '{event.place_name}', '{event.post_text}', '{event.adress}', '{event.poster_imag}', '{event.url}', '{event.price}', '{event.availability}');"
        #line=f"INSERT INTO events VALUES (title='{event.title}', date_start='{event.date}', place_name='{event.place_name}', post_text='{event.post_text}', adress='{event.adress}', poster_imag='{event.poster_imag}', url='{event.url}', price='{event.price}', availability='{event.availability}');"
        print(line)
        cursor.execute(line)
    conn.commit()
    conn.close()
    return('hi')

def checkdb():
    conn = sqlite3.connect('eventDB.sqlite')
    cursor = conn.cursor()

    line="SELECT * FROM events;"
    cursor.execute(line)
    print(cursor.fetchall)
    conn.close()

def whatdate(monthday): #to-do добавить поиск по месяцу и если день месяца прошёл, то переключаться на следующей месяц
    if monthday==0:
        date_4_searching=date.today().isoformat()
    else:
        date_4_searching=date(date.today().year,date.today().month, monthday).isoformat()
    return date_4_searching
