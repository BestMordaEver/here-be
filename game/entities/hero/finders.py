"""Hero finder functions - locate targets for scheduling and encounters."""
from typing import List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from . import Hero
    from game.entities.settlement.settlement import Settlement


def find_remote_settlements(hero: 'Hero', count: int = 2) -> List['Settlement']:
    """Find distant settlements to visit, prioritizing market days."""
    from game.entities.settlement.settlement import Settlement
    settlements = []
    for entity in list(hero.world.entities):
        if isinstance(entity, Settlement) and entity.is_alive:
            if entity.__class__.__name__ in ('Village', 'City'):
                dist = hero.get_distance(entity.coordinates)
                if dist > 20:
                    has_market = (
                        entity.current_event is not None and
                        entity.current_event.value == 'market_day'
                    )
                    priority = (0 if has_market else 1, -dist)
                    settlements.append((priority, entity))

    settlements.sort(key=lambda x: x[0])
    return [s[1] for s in settlements[:count]]


def find_pillage_target(hero: 'Hero') -> Optional[Any]:
    """Find ruins or treasury to pillage."""
    from game.entities.dragon.domain import Domain
    from game.entities.settlement.settlement import Settlement
    for entity in list(hero.world.entities):
        # Dragon treasury
        if isinstance(entity, Domain) and entity.is_treasury and entity.has_blessings:
            return entity

        # Settlement ruins
        if isinstance(entity, Settlement) and entity.__class__.__name__ in ('Village', 'City'):
            if entity.can_be_pillaged():
                return entity

    return None


def find_settlement_at(hero: 'Hero') -> Optional['Settlement']:
    """Get the settlement the hero is currently inside, if any."""
    for entity in hero.world.get_entities_at(hero.coordinates):
        if entity.__class__.__name__ in ('Camp', 'Village', 'City') and entity.is_alive:
            return entity
    return None


__all__ = [
    'find_remote_settlements',
    'find_pillage_target',
    'find_settlement_at',
]
