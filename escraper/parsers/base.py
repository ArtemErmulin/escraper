from abc import ABC, abstractmethod
from collections import namedtuple
import warnings

import requests
from bs4 import BeautifulSoup


class BaseParser(ABC):
    MAX_NUMBER_CONNECTION_ATTEMPTS = 3
    ALL_EVENT_TAGS = (
        "adress",
        "category",
        "date_from",
        "date_to",
        "id",
        "place_name",
        "post_text",
        "poster_imag",
        "price",
        "title",
        "url",
        "is_registration_open",
    )

    @abstractmethod
    def get_event(self):
        pass

    @abstractmethod
    def get_events(self):
        pass

    def parse(self, event_data, tags=None):
        if tags is None:
            raise ValueError(
                "'tags' for event required (see escraper.parsers.base.BaseParser.ALL_EVENT_TAGS)."
            )

        data = dict()
        for tag in tags:
            try:
                data[tag] = getattr(self, "_" + tag)(event_data)
            except AttributeError:
                raise TypeError(
                    f"Unsupported event tag found: {tag}.\n"
                    f"All available event tags: {self.ALL_EVENT_TAGS}."
                )

        DataStorage = namedtuple("event", tags)

        return DataStorage(**data)

    def remove_html_tags(self, data):
        return BeautifulSoup(data, "html.parser").text

    def _request_get(self, *args, **kwargs):
        """
        Send get request with specific arguments.

        To avoid internet connection issues,
        will catch ConnectionError and retry.
        """
        attempts_count = 0

        while True:
            try:
                response = requests.get(*args, **kwargs)

                if not response.ok:
                    response_status = response.json()["response_status"]

                    warning_msg = "Bad response: {status_code}: {message}.".format(
                        status_code=response_status["error_code"],
                        message=response_status["message"],
                    )

                    if attempts_count == self.MAX_NUMBER_CONNECTION_ATTEMPTS:
                        raise ValueError(warning_msg)

                    warnings.warn(warning_msg + "\nRetry")
                    attempts_count += 1

                else:
                    break

            except requests.ConnectionError as e:
                if attempts_count == self.MAX_NUMBER_CONNECTION_ATTEMPTS:
                    raise e
                attempts_count += 1
                print("Retry connection")

        return response
