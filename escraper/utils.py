from datetime import date


WEEKNAMES = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}
MONTHNAMES = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def weekday_name(dt):
    return WEEKNAMES[dt.weekday()]


def month_name(dt):
    return MONTHNAMES[dt.month]


def whatdate(monthday):
    """
    TODO добавить поиск по месяцу и если день месяца прошёл,
    то переключаться на следующей месяц
    """
    if monthday == 0:
        date_4_searching = date.today().isoformat()
    else:
        date_4_searching = date(
            date.today().year, date.today().month, monthday
        ).isoformat()
    return date_4_searching
