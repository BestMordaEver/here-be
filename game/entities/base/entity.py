"""Base entity class for all game entities."""
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING

# Canonical definitions live in their own modules; re-export here for
# backwards compatibility so existing ``from game.entities.base.entity
# import EngagementType, Engagement`` continues to work.
from .engaging import EngagementType, Engagement, Engaging
from .pockets import Pockets

if TYPE_CHECKING:
    from game.world import World

Coordinates = Tuple[int, int]


class Entity(Engaging, Pockets):
    """Base class for all game entities.

    Inherits engagement logic from :class:`Engaging` and blessing
    storage from :class:`Pockets`.  Subclasses configure pockets by
    calling ``Pockets.__init__(self, max_blessings=…)`` in their own
    ``__init__``.
    """
    
    def __init__(
        self,
        world: 'World',
        coordinates: Coordinates,
        max_blessings: int = 0,
        wasteful: bool = False,
    ):
        Engaging.__init__(self)
        Pockets.__init__(self, max_blessings=max_blessings, wasteful=wasteful)

        self.world = world
        self.coordinates = coordinates
        
        self.is_alive = True
        self.is_dead = False
        
    def update(self) -> None:
        raise NotImplementedError("Subclasses must implement update()")
    
    def get_distance(self, destination: Coordinates) -> float:
        """Calculate Euclidean distance to destination."""

        x1, y1 = self.coordinates
        x2, y2 = destination
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def get_adjacent_tiles(self) -> list[Coordinates]:
        """Get all 8 adjacent tiles around current position."""

        x, y = self.coordinates
        adjacent = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    adjacent.append((x + dx, y + dy))
        return adjacent
    
    def get_surrounding_tiles(self, radius: int) -> list[Coordinates]:
        """Get all tiles within a radius around current position."""

        x, y = self.coordinates
        surrounding = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx != 0 or dy != 0:
                    surrounding.append((x + dx, y + dy))
        return surrounding
    
    def get_nearby_entities(self, radius: float, *types: str) -> List['Entity']:
        """Get nearby alive entities, excluding self."""
        return self.world.get_entities_nearby(self.coordinates, radius, *types, exclude=self)

    def die(self, reason: str) -> None:
        """Handle entity death."""
        self.is_dead = True
        self.is_alive = False
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize entity to dictionary for JSON output."""
        raise NotImplementedError("Subclasses must implement serialize()")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(pos={self.coordinates})"
