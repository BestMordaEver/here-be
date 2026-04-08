"""Hero movement - standard A* with blessing pickup."""
from typing import TYPE_CHECKING

from game.entities.base.mobile import Mobile
from .types import MAX_BLESSINGS

if TYPE_CHECKING:
    from . import Hero


def update_movement(hero: 'Hero') -> None:
    """Process movement via standard A* pathfinding, then check for blessings."""
    Mobile.update_movement(hero)

    if hero.blessings < MAX_BLESSINGS:
        _try_pickup_blessings(hero)


def _try_pickup_blessings(hero: 'Hero') -> None:
    """Pick up dropped blessings at the hero's current location."""
    from game.entities.blessing import Blessing

    for entity in hero.world.entities:
        if isinstance(entity, Blessing) and entity.coordinates == hero.coordinates:
            can_take = MAX_BLESSINGS - hero.blessings
            taken = entity.take(can_take)
            if taken > 0:
                hero.blessings += taken
                hero.think(f"Found {taken} blessing{'s' if taken > 1 else ''}!")
            break
