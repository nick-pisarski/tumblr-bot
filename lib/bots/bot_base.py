import logging
from abc import ABC, abstractmethod


class AbstractBotClass(ABC):
    def __init__(self, name):
        self.name = name
        self.last_executed = None
        self.authenticated = False        
        self.logger = logging.getLogger('{}({})'.format(name, self.__class__.__name__))

    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def execute(self):
        pass

    # should there be a loadConfig function for every bot?