from datetime import date
import sqlite3



# def makingDB():
    # conn = sqlite3.connect('eventDB.sqlite')
    # cursor = conn.cursor()
    # making="CREATE TABLE events\
    #   (id INT, \
    #    title TEXT,\
    #   date_start CHAR(50) ,\
    #   category CHAR(50),\
    #   poster_imag CHAR(50),\
    #   url CHAR(50) );"
    # cursor.execute(making)
    # conn.close()



def add2db(events):
    conn = sqlite3.connect('eventDB.sqlite')
    cursor = conn.cursor()

    try:
        for event in events:
            line=f"INSERT INTO events VALUES ('{event.id}','{event.title}', '{event.date}', '{event.category}', '{event.poster_imag}', '{event.url}');"
            #line=f"INSERT INTO events VALUES (title='{event.title}', date_start='{event.date}', place_name='{event.place_name}', post_text='{event.post_text}', adress='{event.adress}', poster_imag='{event.poster_imag}', url='{event.url}', price='{event.price}', availability='{event.availability}');"
            #print(line)
            cursor.execute(line)
            conn.commit()
    except:
        drops='DROP TABLE events;'
        cursor.execute(drops) 
        making = "CREATE TABLE IF NOT EXISTS events\
              (id INT, \
               title TEXT,\
              date_start CHAR(50) ,\
              category CHAR(50),\
              poster_imag CHAR(50),\
              url CHAR(50) );"
        cursor.execute(making)  
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
