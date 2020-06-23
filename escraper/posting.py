
def create(ed):
    """
    Creating post by raw data.

    Parameters:
    -----------
    ed : namedtuple
        parsers.EventData
    """

    if ed.poster_imag is None:
        imag = ""
    else:
        imag = f"[ ]({ed.poster_imag}) "

    title = f"{imag}*{ed.title_date}* {ed.title}\n\n"

    footer = (
        "\n"
        f'*Где:* {ed.place_name}, {ed.adress} \n'
        f'*Когда:* {ed.date} \n'
        f'*Вход:* [{ed.price}]({ed.url})'
    )

    # if ed.price==:
    #     footer +=f'Регистрация ограничена: [подробности](ed.url)'
    # elif ed.price==0:
    #     footer +=f'*Вход свободный* [по предварительной регистрации]({ed.url})'
    # elif ed.price>0:
    #     footer +=f'*Вход:* [от {ed.price}₽]({ed.url})'
    

    full_text = title + ed.post_text + footer
    return full_text
