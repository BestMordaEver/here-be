"""Hero types and constants."""
from enum import Enum


class HeroMood(Enum):
    """Hero daily moods determining behavior."""
    MERCENARY = "mercenary"         # Escorts a caravan
    TIRED = "tired"                 # Rests and protects current settlement
    ADVENTUROUS = "adventurous"     # Travels to remote settlements, explores
    OPPORTUNISTIC = "opportunistic" # Pillages ruins/treasury/domain
    VENGEFUL = "vengeful"           # Hunts bandits, patrols extensively
    FOREBODING = "foreboding"       # Leads party to attack dragon domain
    SUBSERVIENT = "subservient"     # Follows the party leader


# Hero constants
LIFESPAN_DAYS = 50          # Hero dies after this many days
PROTECTION_RANGE = 10       # Range to rush to defend
PATROL_RANGE = 15           # Range to look for threats
MAX_BLESSINGS = 3           # Max blessings hero can carry
PARTY_SIZE = 4              # Heroes needed for dragon raid
TIRED_AFTER_DAYS = 48       # Hero becomes permanently tired
TIRED_THRESHOLD = 3         # Consecutive non-tired days before becoming tired

# Placeholder name pool
HERO_NAMES = [
    "Aldric", "Brenna", "Cedric", "Dara", "Edric",
    "Fiona", "Gareth", "Hilde", "Isolde", "Jorin",
    "Kael", "Lira", "Maren", "Niall", "Orin",
    "Petra", "Rowan", "Sable", "Theron", "Una",
    "Voss", "Wren", "Yara", "Zephyr",
]
