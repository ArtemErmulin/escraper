from abc import ABC, abstractmethod


class BaseParser(ABC):
    @abstractmethod
    def get_event(self):
        pass

    @abstractmethod
    def get_events(self):
        pass
