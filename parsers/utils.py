import requests
from bs4 import BeautifulSoup


STRPTIME = "%Y-%m-%dT%H:%M:%S%z"
MAX_NUMBER_CONNECTION_ATTEMPTS = 3


def remove_html_tags(data):
    return BeautifulSoup(data, "html.parser").text


def _request_get(*args, **kwargs):
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

                if attempts_count == MAX_NUMBER_CONNECTION_ATTEMPTS:
                    raise ValueError(warning_msg)

                warnings.warn(warning_msg + "\nRetry")
                attempts_count += 1

            else:
                break

        except requests.ConnectionError as e:
            if attempts_count == MAX_NUMBER_CONNECTION_ATTEMPTS:
                raise e
            attempts_count += 1
            print("Retry connection")

    return response
