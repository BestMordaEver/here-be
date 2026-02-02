"""Dragon type configurations."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DragonTypeConfig:
    """Configuration for a dragon type."""
    char: str
    base_rotation: int
    ignores_diagonal_debt: bool = False  # Blade
    tends_area: bool = False             # Druid (radius 8)
    max_blessings: int = 5               # Midas gets 10
    instant_camp_kill: bool = False      # Brute
    extra_hero_casualty: bool = False    # Blade (2 heroes die)
    can_shed_blessing: bool = False      # Fragile


# Type configurations
DRAGON_TYPES = {
    'serpent': DragonTypeConfig(
        char='Ȿ',
        base_rotation=270,
    ),
    'brute': DragonTypeConfig(
        char='Ȣ',
        base_rotation=90,
        instant_camp_kill=True,
    ),
    'blade': DragonTypeConfig(
        char='%',
        base_rotation=315,
        ignores_diagonal_debt=True,
        extra_hero_casualty=True,
    ),
    'druid': DragonTypeConfig(
        char='₷',
        base_rotation=315,
        tends_area=True,
    ),
    'midas': DragonTypeConfig(
        char='ꬸ',
        base_rotation=270,
        max_blessings=10,
    ),
    'fragile': DragonTypeConfig(
        char='ϗ',
        base_rotation=235,
        can_shed_blessing=True,
    ),
}

DEFAULT_TYPE = DragonTypeConfig(char='Ȣ', base_rotation=90)


def get_dragon_type(properties: list) -> tuple[str, DragonTypeConfig]:
    """Get dragon type name and config from properties list."""
    for type_name, config in DRAGON_TYPES.items():
        if type_name in properties:
            return type_name, config
    return 'unknown', DEFAULT_TYPE
