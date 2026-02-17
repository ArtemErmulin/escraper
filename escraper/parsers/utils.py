STRPTIME = "%Y-%m-%dT%H:%M:%S%z"

# Keyword → category mapping for automatic detection from title/text.
# Checked in order; first match wins. Keys are lowercase substrings.
CATEGORY_KEYWORDS = {
    "концерт": "концерты",
    "music": "концерты",
    "live": "концерты",
    "dj": "концерты",
    "джаз": "концерты",
    "jazz": "концерты",
    "рок": "концерты",
    "rock": "концерты",
    "спектакль": "театр",
    "театр": "театр",
    "перформанс": "театр",
    "опер": "театр",
    "балет": "театр",
    "кино": "кино",
    "фильм": "кино",
    "показ": "кино",
    "лекция": "лекции",
    "лекторий": "лекции",
    "лектор": "лекции",
    "воркшоп": "мастер-классы",
    "мастер-класс": "мастер-классы",
    "workshop": "мастер-классы",
    "выставк": "выставки",
    "экспозиц": "выставки",
    "exhibition": "выставки",
    "экскурси": "экскурсии",
    "прогулк": "экскурсии",
    "фестивал": "фестивали",
    "festival": "фестивали",
    "ярмарк": "ярмарки",
    "маркет": "ярмарки",
    "market": "ярмарки",
    "вечеринк": "вечеринки",
    "party": "вечеринки",
    "детск": "детям",
    "для детей": "детям",
    "семейн": "детям",
    "йога": "спорт",
    "бег": "спорт",
    "забег": "спорт",
}


def detect_category(title, text=""):
    """Detect event category from title and text by keyword matching.

    Returns category string or empty string if no match.
    Title is checked first (higher priority), then text.
    """
    for source in (title, text):
        lower = source.lower()
        for keyword, category in CATEGORY_KEYWORDS.items():
            if keyword in lower:
                return category
    return ""
