"""Bandit target-finding functions."""
from random import choice
from typing import TYPE_CHECKING, Optional, Any

if TYPE_CHECKING:
    from . import Bandit


def find_nearby_village(bandit: 'Bandit') -> Optional[Any]:
    """Find the closest village within raiding distance."""
    villages = bandit.get_nearby_entities(30, 'Village')
    if not villages:
        return None
    villages.sort(key=lambda v: bandit.get_distance(v.coordinates))
    return villages[0]


def find_pillage_target(bandit: 'Bandit') -> Optional[Any]:
    """Find a treasury, ruin, or unguarded domain to pillage."""
    from game.entities.dragon.domain import Domain
    from game.entities.settlement.settlement import Settlement
    targets = []

    for entity in list(bandit.world.entities):
        # Treasury (dead dragon domain with treasure)
        if isinstance(entity, Domain) and entity.is_treasury and entity.has_blessings:
            targets.append(entity)

        # Ruins (dead settlement with blessings)
        if isinstance(entity, Settlement) and entity.__class__.__name__ in ('Village', 'City'):
            if entity.can_be_pillaged():
                targets.append(entity)

    if targets:
        return choice(targets)
    return None
