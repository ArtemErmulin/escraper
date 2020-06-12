
def create(ed):
    """
    Creating post by raw data.

    Parameters:
    -----------
    ed : namedtuple
        parsers.EventData
    """

    title = f"[ ]({ed.poster_imag}) *{ed.title_date}* {ed.title}\n\n"

    footer = (
        "\n"
        f'*Где:* {ed.place_name}, {ed.adress} \n'
        f'*Когда:* {ed.date} \n'
        f'*Вход свободный* [по предварительной регистрации]({ed.url})'
    )

    full_text = title + ed.post_text + footer
    return full_text
