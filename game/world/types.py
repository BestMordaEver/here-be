from enum import Enum


class TimeOfDay(Enum):
    """Periods of the day."""
    DAWN = "dawn"       # 6:00 - entities wake, build schedules
    DAY = "day"         # 7:00-19:00 - active period
    DUSK = "dusk"       # 20:00 - entities return home
    NIGHT = "night"     # 21:00-5:00 - entities sleep


class Biome(Enum):
    WATER = 'water'
    FIELD = 'field'
    FOREST = 'forest'
    MOUNTAIN = 'mountain'
