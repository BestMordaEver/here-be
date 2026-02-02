"""Blessing entity - dropped blessings that can be picked up."""
from .base import Coordinates, Entity
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World


class Blessing(Entity):
    """A dropped blessing that persists until picked up.
    
    Blessings are dropped when:
    - Heroes or bandits die (unless dying of old age)
    - Camps are destroyed
    - Settlements are pillaged (future)
    
    Blessings can be picked up by:
    - Heroes (up to 3)
    - Bandits (up to 3, called "trinkets")
    - Caravans (1 at a time)
    """
    
    def __init__(self, world: 'World', coordinates: Coordinates, count: int = 1):
        super().__init__(world, "#FFD700", "✦", coordinates)  # Gold star
        self.count = count  # Number of blessings at this location
    
    def take(self, amount: int = 1) -> int:
        """Take blessings from this pile. Returns amount actually taken."""
        taken = min(amount, self.count)
        self.count -= taken
        return taken
    
    @property
    def is_empty(self) -> bool:
        """Check if all blessings have been taken."""
        return self.count <= 0
    
    def update(self) -> None:
        """Remove self if empty."""
        if self.is_empty:
            self.world.remove_entity(self)
    
    def serialize(self) -> dict:
        """Serialize for JSON output."""
        data = super().serialize()
        data["count"] = self.count
        return data


def drop_blessing(world: 'World', coordinates: Coordinates, count: int = 1) -> None:
    """Drop blessings at a location. Merges with existing blessing pile if present."""
    if count <= 0:
        return
    
    # Check for existing blessing pile at location
    for entity in world.entities:
        if isinstance(entity, Blessing) and entity.coordinates == coordinates:
            entity.count += count
            return
    
    # Create new blessing pile
    blessing = Blessing(world, coordinates, count)
    world.add_entity(blessing)
