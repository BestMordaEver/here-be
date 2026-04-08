"""Bandit entity with day-based scheduling and encounter reactions."""

from typing import TYPE_CHECKING, Dict, Any, Optional

from game.entities.base import (
    Coordinates, Mobile, Scheduled, Aging, Thinking, Visible,
)
from game.entities.settlement.settlement import Settlement
from game.world.types import Biome
from .types import BanditBehavior, LIFESPAN_DAYS, MAX_BLESSINGS

if TYPE_CHECKING:
    from game.world import World


class Bandit(Mobile, Visible, Thinking, Scheduled, Aging):
    """Bandits that ambush caravans and pillage ruins."""

    def __init__(self, world: 'World', coordinates: Coordinates):
        Mobile.__init__(self, world, coordinates, loiter=1)
        Visible.__init__(self)
        Thinking.__init__(self)
        Scheduled.__init__(self)
        Aging.__init__(self)

        self.create_small("default", "#960000", "Ω")
        self.visual_state = "default"

        # State
        self.behavior = BanditBehavior.LURKING
        self.blessings: int = 0
        self.days_since_robbery: int = 0
        self.hiding_spot: Optional[Coordinates] = None
        self.fleeing_from = None

    # ------------------------------------------------------------------
    # Terrain
    # ------------------------------------------------------------------

    def is_passable(self, coordinates: Coordinates) -> bool:
        """Bandits can move through fields and forests."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= self.world.WIDTH or y >= self.world.HEIGHT:
            return False

        height = self.world.height_map[y][x]
        biome = self.world.get_biome_from_height(height)
        if biome not in (Biome.FIELD, Biome.FOREST):
            return False

        # Can't move through settlements
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                return False

        return True

    def is_in_forest(self) -> bool:
        """Check if bandit is currently in a forest tile."""
        x, y = self.coordinates
        height = self.world.height_map[y][x]
        return self.world.get_biome_from_height(height) == Biome.FOREST

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_dawn(self) -> None:
        """Dawn: age, check death, build schedule."""
        if self.process_aging():
            return
        self.build_schedule()

    def get_lifespan(self) -> int:
        return LIFESPAN_DAYS

    def on_old_age_death(self) -> None:
        """Clear blessings before dying of old age so nothing drops."""
        self.blessings = 0

    def die(self, reason: str) -> None:
        """Handle bandit death — drop blessings."""
        if self.blessings > 0:
            from game.entities.blessing import drop_blessing
            drop_blessing(self.world, self.coordinates, self.blessings)
            self.blessings = 0

        super().die(reason)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "coordinates": self.coordinates,
            "in_transit": self.in_transit,
            "character": "Ω",
            "color": "#960000",
            "behavior": self.behavior.value,
            "blessings": self.blessings,
            "days_since_robbery": self.days_since_robbery,
            "age_days": self.age_days,
            "schedule": self.get_schedule_summary(),
        }


from .schedule import build_schedule
Bandit.build_schedule = build_schedule

from .actions import start_action, on_arrival, check_for_encounters, resolve_engagement
Bandit.start_action = start_action
Bandit.on_arrival = on_arrival
Bandit.check_for_encounters = check_for_encounters
Bandit.resolve_engagement = resolve_engagement

from .movement import update_movement
Bandit.update_movement = update_movement

__all__ = ['Bandit', 'BanditBehavior']
