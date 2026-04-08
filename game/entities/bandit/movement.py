"""Bandit movement — delegates to Mobile + blessing pickup."""
from typing import TYPE_CHECKING

from game.entities.base.mobile import Mobile
from .types import MAX_BLESSINGS

if TYPE_CHECKING:
    from . import Bandit


def update_movement(bandit: 'Bandit') -> None:
    """Process movement step, then try to pick up blessings."""
    Mobile.update_movement(bandit)

    if bandit.blessings < MAX_BLESSINGS:
        _try_pickup_blessings(bandit)


def _try_pickup_blessings(bandit: 'Bandit') -> None:
    """Pick up dropped blessings at current location."""
    from game.entities.blessing import Blessing

    for entity in bandit.world.entities:
        if isinstance(entity, Blessing) and entity.coordinates == bandit.coordinates:
            can_take = MAX_BLESSINGS - bandit.blessings
            taken = entity.take(can_take)
            if taken > 0:
                bandit.blessings += taken
            break
