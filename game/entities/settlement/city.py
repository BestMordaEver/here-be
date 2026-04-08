"""City settlement."""
from typing import List, Tuple, TYPE_CHECKING
from game.entities.base import Coordinates, Named, Visible
from game.entities.spirit import SpiritType
from game.world.types import Biome
from .settlement import Settlement
from .ruins import Ruins
from .expansion import Expansion
from .types import SettlementEvent


if TYPE_CHECKING:
    from game.world import World
    from .. import Camp, Caravan, Spire


# City constants
STARTING_LIFE = 5  # City starting HP
RUINS_DURATION_DAYS = 50  # Days before ruins disappear
SPIRE_BLESSING_COST = 10  # Blessings needed to spawn spire
BLESSING_SELL_RANGE = 100  # Max distance to sell blessings to other cities


class City(Settlement, Expansion, Named, Ruins, Visible):
    """5x5 city with walls, gates, buildings, and roads."""
    
    
    def __init__(self, world: 'World', name: str, coordinates: Coordinates):
        super().__init__(world, name, coordinates, life=STARTING_LIFE)
        Ruins.__init__(self, ruins_duration=RUINS_DURATION_DAYS)

        self.create_large("default", [
            ((-2,-2), "#", "#808080"),          # Wall (grey)
            ((-1,-2), "═", "#808080"),      # Wall
            ((0,-2), "═", "#808080"),      # Wall
            ((1,-2), "═", "#808080"),      # Wall
            ((2,-2), "#", "#808080"),      # Wall
            
            ((-2,-1), "║", "#808080"),      # Wall
            ((-1,-1), "Ѧ", "#B22222"),  # Building (brick)
            ((0,-1), "Ћ", "#B22222"),  # Building
            ((1,-1), "Ћ", "#B22222"),  # Building
            ((2,-1), "║", "#808080"),  # Wall
            
            ((-2,0), "║", "#808080"),      # Wall
            ((-1,0), "֏", "#B22222"),  # Building
            ((0,0), "Ѻ", "#808080"),  # City square (grey)
            ((1,0), "Ћ", "#B22222"),  # Building
            ((2,0), "║", "#808080"),  # Wall
            
            ((-2,1), "║", "#808080"),      # Wall
            ((-1,1), "Ҵ", "#B22222"),  # Building
            ((0,1), "║", "#8B4513"),  # Main road (grey)
            ((1,1), "Ҵ", "#B22222"),  # Building
            ((2,1), "║", "#808080"),  # Wall
            
            ((-2,2), "#", "#808080"),      # Wall
            ((-1,2), "₸", "#808080"),  # Gate (grey)
            ((0,2), "₳", "#808080"),  # Gate
            ((1,2), "₸", "#808080"),  # Gate
            ((2,2), "#", "#808080"),  # Wall
        ])

        self.visual_state = "default"

        self.create_large("ruins", [
            ((-2,-2), "#", "#90A090"),          # Wall (slightly green)
            ((-1,-2), "═", "#90A090"),      # Wall
            ((0,-2), "═", "#90A090"),      # Wall
            ((1,-2), "═", "#90A090"),      # Wall
            ((2,-2), "#", "#90A090"),      # Wall
            
            ((-2,-1), "║", "#90A090"),      # Wall
            ((-1,-1), "Ѧ", "#808080"),  # Building (grey)
            ((0,-1), "Ћ", "#808080"),  # Building
            ((1,-1), "Ћ", "#808080"),  # Building
            ((2,-1), "║", "#90A090"),  # Wall
            
            ((-2,0), "║", "#90A090"),      # Wall
            ((-1,0), "֏", "#808080"),  # Building
            ((0,0), "Ѻ", "#228B22"),  # City square (green)
            ((1,0), "Ћ", "#808080"),  # Building
            ((2,0), "║", "#90A090"),  # Wall
            
            ((-2,1), "║", "#90A090"),      # Wall
            ((-1,1), "Ҵ", "#808080"),  # Building
            ((0,1), "║", "#345F12"),  # Main road (overgrown green)
            ((1,1), "Ҵ", "#808080"),  # Building
            ((2,1), "║", "#90A090"),  # Wall
            
            ((-2,2), "#", "#90A090"),      # Wall
            ((-1,2), "₸", "#808080"),  # Gate (grey)
            ((0,2), "₳", "#808080"),  # Gate
            ((1,2), "₸", "#808080"),  # Gate
            ((2,2), "#", "#90A090"),  # Wall
        ])

        self.is_city = True
        self.got_blessing_yesterday = False
        self.subsidiary_camps: List['Camp | Caravan'] = []
        self.spire: 'Spire' = None
        
    def get_max_camps(self) -> int:
        return 6  # Cities can have up to 6 camps (2 mountain + 4 any). Lake camps do not count against this limit.

    def get_prioritized_resource(self) -> SpiritType:
        return SpiritType.MOUNTAIN  # Cities prioritize mountain camps

    def get_prioritized_resource_count(self) -> int:
        return 2

    def get_spawn_point(self, destination=None):
        """Spawn entity just outside the south gate (y+3 from center)."""
        x, y = self.coordinates
        # Prefer center gate exit, then left/right gate exits
        for dx in [0, -1, 1, -2, 2]:
            candidate = (x + dx, y + 3)
            if self._is_field(candidate):
                return candidate
        # Fallback: try one row further south
        for dx in range(-2, 3):
            candidate = (x + dx, y + 4)
            if self._is_field(candidate):
                return candidate
        return None
    
    def die(self, reason: str) -> None:
        """Called before city death - destroy spire along with it."""
        if self.spire and self.spire.is_alive:
            self.spire.die("city destroyed")
            
        super().die(reason)
    
    def on_dawn(self) -> None:
        """Handle dawn event - build schedule and try selling blessings."""
        if self.process_ruins():
            return
        
        # Check for spire creation on day after market day
        prev_event = self.current_event
        
        self.build_schedule()
        
        # Create spire after market day if we have enough blessings
        if prev_event == SettlementEvent.MARKET_DAY:
            if self.spire is None and self.blessings >= SPIRE_BLESSING_COST:
                self._attempt_create_spire()
        
        # Cities with spires sell blessings to other cities without spires
        if self.spire and self.spire.is_alive and self.blessings > 1:
            # Find cities without spires in range
            target_cities = []
            for entity in self.world.entities:
                if entity.__class__.__name__ == 'City' and entity != self and entity.is_alive:
                    if entity.spire is None or not entity.spire.is_alive:
                        distance = self.get_distance(entity.coordinates)
                        if distance <= BLESSING_SELL_RANGE:
                            target_cities.append((distance, entity))
            
            if target_cities:
                # Sort by distance and send to closest
                target_cities.sort(key=lambda x: x[0])
                target = target_cities[0][1]
                
                self._send_blessing_caravan(target, retrieving=False)
                self.think(f"Sending blessing to {target.name}.")
    
    def _attempt_create_spire(self) -> bool:
        """Attempt to create a spire near the city."""
        from .. import Spire
        
        # Find adjacent tile for spire (prefer corners outside walls)
        x, y = self.coordinates
        spire_locations = [
            (x + 3, y - 3),  # Top right corner
            (x - 3, y - 3),  # Top left corner
            (x + 3, y + 3),  # Bottom right corner
            (x - 3, y + 3),  # Bottom left corner
        ]
        
        for loc in spire_locations:
            # Check if location is valid (plains, unoccupied)
            lx, ly = loc
            if lx < 0 or ly < 0 or lx >= self.world.WIDTH or ly >= self.world.HEIGHT:
                continue
            
            height = self.world.height_map[ly][lx]
            if self.world.get_biome_from_height(height) != Biome.FIELD:
                continue
            
            if self.world.get_entities_at(loc):
                continue
            
            # Valid location found
            spire = Spire(self.world, loc, self)
            self.blessings -= SPIRE_BLESSING_COST
            self.world.add_entity(spire)
            self.spire = spire
            return True
        
        return False