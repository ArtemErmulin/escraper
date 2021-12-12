from .base import ALL_EVENT_TAGS
from .timepad import Timepad
from .radario import Radario
from .ticketscloud import Ticketscloud
from .vk import VK


all_parsers = dict(
    timepad=Timepad,
    radario=Radario,
    ticketscloud=Ticketscloud,
    vk=VK
)
