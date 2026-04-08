"""Bandit schedule building — alternates between lurking and seeking."""
from typing import TYPE_CHECKING

from game.entities.base.scheduled import ActionType
from .types import BanditBehavior, DAYS_WITHOUT_ROBBERY, FOREST_SEARCH_RADIUS
from . import finders

if TYPE_CHECKING:
    from . import Bandit


def build_schedule(bandit: 'Bandit') -> None:
    """Build daily schedule — alternate between lurking and seeking days."""
    # Alternate behavior each day
    if bandit.behavior == BanditBehavior.LURKING:
        bandit.behavior = BanditBehavior.SEEKING
    else:
        bandit.behavior = BanditBehavior.LURKING

    bandit.days_since_robbery += 1
    bandit.fleeing_from = None

    planner = bandit.plan_day()

    if bandit.behavior == BanditBehavior.LURKING:
        # Find a forest spot if not already in one
        if not bandit.is_in_forest():
            best_distance = float('inf')
            forest = None
            for radius in range(1, FOREST_SEARCH_RADIUS):
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if abs(dx) != radius and abs(dy) != radius:
                            continue
                        x = bandit.coordinates[0] + dx
                        y = bandit.coordinates[1] + dy
                        if x < 0 or y < 0 or x >= bandit.world.WIDTH or y >= bandit.world.HEIGHT:
                            continue
                        height = bandit.world.height_map[y][x]
                        if bandit.world.get_biome_from_height(height) == 'forest':
                            dist = (dx ** 2 + dy ** 2) ** 0.5
                            if dist < best_distance:
                                best_distance = dist
                                forest = (x, y)
                if forest:
                    break
            if forest:
                bandit.hiding_spot = forest
                planner.add(ActionType.MOVE_TO, forest)

        # If desperate (3 days without robbery), attack a village
        if bandit.days_since_robbery >= DAYS_WITHOUT_ROBBERY:
            village = finders.find_nearby_village(bandit)
            if village:
                planner.add(ActionType.ATTACK, village)
        else:
            # Otherwise lurk and wander
            planner.add(ActionType.IDLE)
            planner.add(ActionType.WANDER)

    else:  # SEEKING
        target = finders.find_pillage_target(bandit)

        if target:
            planner.add(ActionType.MOVE_TO, target.coordinates)
            planner.add(ActionType.PILLAGE, target)
        else:
            planner.add(ActionType.WANDER)
            planner.add(ActionType.WANDER)

        # If desperate, attack a village
        if bandit.days_since_robbery >= DAYS_WITHOUT_ROBBERY:
            village = finders.find_nearby_village(bandit)
            if village:
                planner.add(ActionType.ATTACK, village)

    planner.commit()
