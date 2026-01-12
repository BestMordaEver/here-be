"""Spire - a tower that enables dragon summoning."""
from .base import Coordinates, Entity
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from game.world import World
    from . import City


# Spire constants
ORE_CONSUMPTION = 1
TREASURE_CONSUMPTION = 1
CONSUMPTION_INTERVAL = 10  # Consume resources every N cycles


class Spire(Entity):
    """A golden tower near a city that enables dragon summoning."""
    
    def __init__(self, coordinates: Coordinates, city: 'City'):
        super().__init__("#DAA520", "Ї", coordinates, life=200)  # Goldenrod color
        self.city = city  # Parent city (shares resources)
        self.last_consumption_cycle = 0
    
    def get_tiles(self):
        """Return single tile for the spire."""
        if self.is_dead:
            return [(self.coordinates, "1", "#808080")]  # Grey ruined spire
        return [(self.coordinates, "Ї", "#DAA520")]
    
    def occupies(self, coordinates: Coordinates) -> bool:
        """Check if spire occupies the given coordinates."""
        return self.coordinates == coordinates
    
    def consume_resources(self, world: 'World') -> None:
        """Consume ores and treasure from parent city."""
        if self.is_dead or not self.city.is_alive:
            return
        
        # Only consume periodically
        if world.update_count - self.last_consumption_cycle < CONSUMPTION_INTERVAL:
            return
        
        self.last_consumption_cycle = world.update_count
        
        # Try to consume from city's resources
        ores_consumed = self.city.remove_resource('ores', ORE_CONSUMPTION)
        treasure_consumed = self.city.remove_resource('treasure', TREASURE_CONSUMPTION)
        
        # Take disrepair damage if resources insufficient
        missing = (ORE_CONSUMPTION - ores_consumed) + (TREASURE_CONSUMPTION - treasure_consumed)
        if missing > 0:
            self.hurt(world, missing, 'disrepair')
        else:
            self.heal(1)  # Recover if resources met
    
    def update(self, world: 'World') -> None:
        """Update spire state."""
        if self.is_dead:
            return  # Ruined spires don't update but remain on map
        
        # If parent city dies, spire starts to decay faster
        if not self.city.is_alive:
            self.hurt(world, 2, 'abandoned')
        
        self.consume_resources(world)
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize spire to dictionary for JSON output."""
        data = super().serialize()
        data["city"] = self.city.name if self.city else "none"
        data["debug_info"] = f"Spire at {self.coordinates} for {self.city.name if self.city else 'none'}"
        return data
