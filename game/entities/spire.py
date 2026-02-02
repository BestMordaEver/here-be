"""Spire - a tower that enables dragon summoning."""
from .base import Coordinates, Entity, Aging, Ruins
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from game.world import World
    from . import City


# Spire constants
BLESSING_CONSUMPTION = 1  # Blessings consumed per day to maintain spire


class Spire(Entity, Aging, Ruins):
    """A golden tower near a city that enables dragon summoning. Has HP for disrepair."""
    
    LIFESPAN_DAYS = 100  # Spire naturally crumbles after this many days
    RUINS_DURATION_DAYS = 50  # Ruins disappear after this many days
    
    def __init__(self, world: 'World', coordinates: Coordinates, city: 'City'):
        super().__init__(world, "#DAA520", "Ї", coordinates)  # Goldenrod color
        self.init_aging()
        self.init_ruins()
        self.city = city  # Parent city (shares blessings)
        self.max_life = 200
        self.life = 200
        self._last_consumption_day = -1
    
    def hurt(self, damage: int, source: str) -> None:
        """Inflict damage to the spire."""
        self.life -= damage
        if self.life <= 0:
            self.die(source)
    
    def heal(self, amount: int) -> None:
        """Heal the spire, not exceeding max life."""
        self.life = min(self.max_life, self.life + amount)
    
    def get_tiles(self):
        """Return single tile for the spire."""
        if self.is_dead:
            return [(self.coordinates, "1", "#808080")]  # Grey ruined spire
        return [(self.coordinates, "Ї", "#DAA520")]
    
    def occupies(self, coordinates: Coordinates) -> bool:
        """Check if spire occupies the given coordinates."""
        return self.coordinates == coordinates
    
    def consume_blessings(self) -> None:
        """Consume blessings from parent city once per day to maintain spire."""
        if self.is_dead or not self.city.is_alive:
            return
        
        # Only consume once per day
        current_day = self.world.time.get_current_time().day
        if current_day == self._last_consumption_day:
            return
        
        self._last_consumption_day = current_day
        
        # Try to consume blessings from city
        if self.city.blessings >= BLESSING_CONSUMPTION:
            self.city.blessings -= BLESSING_CONSUMPTION
            self.heal(1)  # Recover if blessings met
        else:
            self.hurt(1, 'disrepair')
    
    def on_dawn(self) -> None:
        """Handle dawn - age the spire and check for natural death or ruin cleanup."""
        if self.process_ruins():
            return
        
        if self.process_aging():
            return
        
        # If parent city dies, spire starts to decay faster
        if not self.city.is_alive:
            self.hurt(2, 'abandoned')
        
        self.consume_blessings()
    
    def update(self) -> None:
        """Update spire state - most logic moved to on_dawn."""
        pass
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize spire to dictionary for JSON output."""
        data = super().serialize()
        data["city"] = self.city.name if self.city else "none"
        data["debug_info"] = f"Spire at {self.coordinates} for {self.city.name if self.city else 'none'} life={self.life}"
        return data
