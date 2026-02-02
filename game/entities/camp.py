"""Worker camp settlement."""
from .base import Coordinates, Settlement, Mortal
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World
    from . import Spirit

from .base.expansion import WOOD_CAMP_RANGE, ORE_CAMP_RANGE


class Camp(Settlement, Mortal):
    """2x2 worker camp made of brown tents."""
    
    def __init__(self, coordinates: Coordinates, spirit_coordinates: Coordinates, home: 'Settlement'):
        super().__init__(coordinates, life=2)
        self.nearby_spirits: List['Spirit'] | None = None  # Cached list of nearby spirits (lazy init)
        self.spirit_coordinates = spirit_coordinates
        self.home = home
        self._last_blessing_day = -1
    
    def die(self, world: 'World', cause: str) -> None:
        """Handle camp death."""
        # Drop blessings
        if self.blessings > 0:
            from .blessing import drop_blessing
            drop_blessing(world, self.coordinates, self.blessings)
            self.blessings = 0
        
        super().die(world, cause)
        
        # Free up the occupied spirit
        entities = world.get_entities_at(self.spirit_coordinates)
        for entity in entities:
            if entity.__class__.__name__ == 'Spirit':
                entity.is_occupied = False
    
    def has_wood_access(self) -> bool:
        """Check if there are any alive forest spirits nearby."""
        if self.nearby_spirits is None:
            return False
        return any(s.type == 'forest' and s.is_alive for s in self.nearby_spirits)
    
    def has_ore_access(self) -> bool:
        """Check if there are any alive mountain spirits nearby."""
        if self.nearby_spirits is None:
            return False
        return any(s.type == 'mountain' and s.is_alive for s in self.nearby_spirits)
    
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return all 2x2 tiles for the worker camp."""
        if self.is_dead:
            return []  # Worker camp disappears when dead
        
        x, y = self.coordinates
        tiles = []
        for dy in [0, 1]:
            for dx in [0, 1]:
                tiles.append(((x + dx, y + dy), "Λ", "#8B4513"))
        return tiles
    
    def on_dawn(self, world: 'World') -> None:
        """Try to send blessings to parent, then extract from spirits."""
        if self.is_dead:
            return
        
        current_day = world.day_night_cycle.get_current_time().day
        
        # Send blessing to parent settlement if we have one
        if self.blessings > 0 and self.home and self.home.is_alive:
            self._send_blessing_to_parent(world)
        
        # Initialize nearby spirits cache if needed
        if self.nearby_spirits is None:
            self.nearby_spirits = []
            for entity in world.entities:
                if entity.__class__.__name__ == 'Spirit':
                    if entity.type == 'forest' and self.get_distance(entity.coordinates) <= WOOD_CAMP_RANGE:
                        self.nearby_spirits.append(entity)
                    elif entity.type == 'mountain' and self.get_distance(entity.coordinates) <= ORE_CAMP_RANGE:
                        self.nearby_spirits.append(entity)
        
        # Try to extract blessing once per day
        if current_day == self._last_blessing_day:
            return
        
        for spirit in self.nearby_spirits:
            if spirit.is_alive and spirit.has_blessing:
                spirit.take_blessing()
                self.blessings += 1
                self._last_blessing_day = current_day
                return  # Only one blessing per day
    
    def _send_blessing_to_parent(self, world: 'World') -> None:
        """Send a caravan with blessing to parent settlement."""
        from .caravan import Caravan, CaravanMission
        
        # Create caravan to deliver blessing
        caravan = Caravan(
            coordinates=self.coordinates,
            home=self.home,
            destination=self.home,
            mission=CaravanMission.DELIVER_BLESSING
        )
        caravan.blessing = True
        self.blessings -= 1
        world.add_entity(caravan)
    
    def update(self, world: 'World') -> None:
        """Camps don't need regular updates beyond dawn."""
        pass