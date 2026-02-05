from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import Dragon


@dataclass
class DragonPronouns:
    """Pronoun set for a dragon."""
    subject: str = "it"      # he/she/they/it
    object: str = "it"       # him/her/them/it  
    possessive: str = "its"  # his/her/their/its
    
    @classmethod
    def from_string(cls, pronoun_str: str) -> 'DragonPronouns':
        """Parse pronouns from string like 'he/him/his'."""
        if not pronoun_str:
            return cls()
        parts = pronoun_str.split('/')
        if len(parts) >= 3:
            return cls(parts[0], parts[1], parts[2])
        return cls()


def parse_properties(dragon: Dragon, properties: dict, pronouns: str) -> dict:
    """Parse dragon-specific properties from a generic properties dict."""
    # Determine dragon type from properties
    if 'serpent' in properties:
        dragon.dragon_type = 'serpent'
        char = 'Ȿ'
        base_rotation = 270
    elif 'blade' in properties:
        dragon.dragon_type = 'blade'
        char = '%'
        base_rotation = 315
    elif 'druid' in properties:
        dragon.dragon_type = 'druid'
        char = '₷'
        base_rotation = 315
    elif 'midas' in properties:
        dragon.dragon_type = 'midas'
        char = 'ꬸ'
        base_rotation = 270
    elif 'fragile' in properties:
        dragon.dragon_type = 'fragile'
        char = 'ϗ'
        base_rotation = 235
    elif 'brute' in properties:
        dragon.dragon_type = 'brute'
        char = 'Ȣ'
        base_rotation = 90
    
    # Determine domain from properties
    if 'aquatic' in properties:
        dragon.domain_type = 'aquatic'
        color = '#004080'
    elif 'mountain' in properties:
        dragon.domain_type = 'mountain'
        color = '#808080'
    elif 'verdant' in properties:
        dragon.domain_type = 'verdant'
        color = '#008000'
    elif 'scorched' in properties:
        dragon.domain_type = 'scorched'
        color = '#800000'
    
    # Properties
    dragon.properties = properties
    dragon.is_scorched = "scorched" in properties
    dragon.is_good = "good" in properties
    dragon.is_evil = "evil" in properties
    dragon.is_territorial = "territorial" in properties
    
    # Diet flags
    dragon.is_carnivore = "carnivore" in properties
    dragon.is_herbivore = "herbivore" in properties
    dragon.is_greed = "greed" in properties
    dragon.is_anthropophage = "anthropophage" in properties

    # Rotation
    dragon.base_rotation = base_rotation
    dragon.rotation = base_rotation
    
    # Pronouns
    dragon.pronouns = DragonPronouns.from_string(pronouns)

    return char, color