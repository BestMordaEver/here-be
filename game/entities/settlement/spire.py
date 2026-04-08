"""Spire - a tower that enables dragon summoning."""
from ..base import Coordinates, Entity, Aging, Visible
from typing import TYPE_CHECKING, Dict, Any
from .ruins import Ruins

if TYPE_CHECKING:
    from game.world import World
    from .. import City


# Spire constants
LIFESPAN_DAYS = 100  # Spire naturally crumbles after this many days
RUINS_DURATION_DAYS = 50  # Ruins disappear after this many days


class Spire(Entity, Aging, Ruins, Visible):
    """A golden tower near a city that enables dragon summoning. Has HP for disrepair."""
    
    
    def __init__(self, world: 'World', coordinates: Coordinates, city: 'City'):
        super().__init__(world, coordinates)  # Goldenrod color
        Aging.__init__(self, lifespan=LIFESPAN_DAYS)
        Ruins.__init__(self, ruins_duration=RUINS_DURATION_DAYS)
        self.city = city  # Parent city
        
        self.create_small("default", "#DAA520", "Ї")
        self.visual_state = "default"
        self.create_small("ruin", "#808080", "1")
    
    def occupies(self, coordinates: Coordinates) -> bool:
        """Check if spire occupies the given coordinates."""
        return self.coordinates == coordinates
    
    def on_dawn(self) -> None:
        """Handle dawn - age the spire and check for natural death or ruin cleanup."""
        if self.process_ruins():
            return
        
        if self.process_aging():
            return
    
    def update(self) -> None:
        """Update spire state - most logic moved to on_dawn."""
        pass
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize spire to dictionary for JSON output."""
        data = super().serialize()
        data["city"] = self.city.name if self.city else "none"
        data["debug_info"] = f"Spire at {self.coordinates} for {self.city.name if self.city else 'none'} life={self.life}"
        return data
