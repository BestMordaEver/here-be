from enum import Enum

class DragonMood(Enum):
    """Dragon daily moods determining behavior."""
    DREARY = "dreary"       # Tends hoard, attacks if not good
    INSPIRED = "inspired"   # Tends hoard, travels to distant spirits
    PENSIVE = "pensive"     # Feeds once, tends nearby spirit
    HUNGRY = "hungry"       # Feeds twice, rests between (every 3 days)
    COVETOUS = "covetous"   # Attacks settlement
    
class DragonType(Enum):
    """Dragon types determining appearance and some behaviors."""
    SERPENT = "serpent"     # Confuses passerbys when moving
    BLADE = "blade"         # Fast diagonal movement, can't be protected against
    DRUID = "druid"         # Blesses spirits in a radius
    MIDAS = "midas"         # Accumulates more blessings in hoard
    FRAGILE = "fragile"     # Generates blessings on ground after combat
    BRUTE = "brute"         # Quickly destroys settlements

class DomainType(Enum):
    """Domain types determining color and location."""
    AQUATIC = "aquatic"     # In lakes, blue
    MOUNTAIN = "mountain"   # In mountains, gray
    VERDANT = "verdant"     # In forests and on plains, green
    SCORCHED = "scorched"   # Anywhere, red, scorches terrain around

class DragonAlignment(Enum):
    """Dragon alignments determining some aspects of behavior."""
    GOOD = "good"
    EVIL = "evil"
    NEUTRAL = "neutral"
    TERRITORIAL = "territorial"

class DragonDiet(Enum):
    """Dragon diets determining feeding behavior."""
    CARNIVORE = "carnivore"         # Hunts cattle and fish
    HERBIVORE = "herbivore"         # Grazes on plains
    GREED = "greed"                 # Attacks settlements instead of feeding
    ANTHROPOPHAGE = "anthropophage" # Exclusively hunts humans