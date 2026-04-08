"""Bandit enums and constants."""
from enum import Enum


class BanditBehavior(Enum):
    """Alternating daily behaviors."""
    LURKING = "lurking"     # Hide in forest, ambush caravans
    SEEKING = "seeking"     # Seek lairs, treasuries, ruins to pillage


# Movement / vision
ATTACK_RANGE = 8            # Distance to initiate attack on caravan
MELEE_RANGE = 2             # (unused currently) close-quarters range
FEAR_RADIUS = 10            # Distance at which dragons are noticed
FOREST_SEARCH_RADIUS = 20   # How far to look for a forest to hide in

# Behavior thresholds
DAYS_WITHOUT_ROBBERY = 3    # Days without robbing before attacking villages

# Inventory
MAX_BLESSINGS = 3           # Max blessings carried as trinkets

# Lifespan
LIFESPAN_DAYS = 50          # Bandit dies after this many days
