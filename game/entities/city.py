"""City settlement."""
from .base import Coordinates, ExpansionMixin, Settlement, Named, Ruins
from .base.settlement_events import SettlementEventsMixin, SettlementEvent
from typing import List, Tuple, TYPE_CHECKING


if TYPE_CHECKING:
    from game.world import World
    from . import Camp, Caravan, Spire


# City constants
STARTING_LIFE = 5  # City starting HP
SPIRE_BLESSING_COST = 10  # Blessings needed to spawn spire
BLESSING_SELL_RANGE = 100  # Max distance to sell blessings to other cities


class City(Settlement, ExpansionMixin, Named, SettlementEventsMixin, Ruins):
    """5x5 city with walls, gates, buildings, and roads."""
    
    RUINS_DURATION_DAYS = 50  # Days before ruins disappear
    
    def __init__(self, world: 'World', name: str, coordinates: Coordinates):
        super().__init__(world, coordinates, life=STARTING_LIFE)
        Named.__init__(self, name)
        SettlementEventsMixin.__init__(self)
        self.init_ruins()
        
        # Expansion tracking
        self.subsidiary_camps: List['Camp | Caravan'] = []
        
        # Spire tracking
        self.spire: 'Spire' = None
        
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return all 5x5 tiles for the city.
        Layout (coordinates at city square Ѻ):
        #═══#
        ║ѦЋЋ║
        ║֏ѺЋ║
        ║Ҵ║Ҵ║
        #₸₳₸#
        """
        x, y = self.coordinates  # City square position
        
        if self.is_dead:
            # Depleted city: buildings grey, city square green, walls slightly green
            return [
                # Row 0
                ((x - 2, y - 2), "#", "#90A090"),          # Wall (slightly green)
                ((x - 1, y - 2), "═", "#90A090"),      # Wall
                ((x, y - 2), "═", "#90A090"),      # Wall
                ((x + 1, y - 2), "═", "#90A090"),      # Wall
                ((x + 2, y - 2), "#", "#90A090"),      # Wall
                
                # Row 1
                ((x - 2, y - 1), "║", "#90A090"),      # Wall
                ((x - 1, y - 1), "Ѧ", "#808080"),  # Building (grey)
                ((x, y - 1), "Ћ", "#808080"),  # Building
                ((x + 1, y - 1), "Ћ", "#808080"),  # Building
                ((x + 2, y - 1), "║", "#90A090"),  # Wall
                
                # Row 2
                ((x - 2, y), "║", "#90A090"),      # Wall
                ((x - 1, y), "֏", "#808080"),  # Building
                ((x, y), "Ѻ", "#228B22"),  # City square (green)
                ((x + 1, y), "Ћ", "#808080"),  # Building
                ((x + 2, y), "║", "#90A090"),  # Wall
                
                # Row 3
                ((x - 2, y + 1), "║", "#90A090"),      # Wall
                ((x - 1, y + 1), "Ҵ", "#808080"),  # Building
                ((x, y + 1), "║", "#345F12"),  # Main road (overgrown green)
                ((x + 1, y + 1), "Ҵ", "#808080"),  # Building
                ((x + 2, y + 1), "║", "#90A090"),  # Wall
                
                # Row 4
                ((x - 2, y + 2), "#", "#90A090"),      # Wall
                ((x - 1, y + 2), "₸", "#808080"),  # Gate (grey)
                ((x, y + 2), "₳", "#808080"),  # Gate
                ((x + 1, y + 2), "₸", "#808080"),  # Gate
                ((x + 2, y + 2), "#", "#90A090"),  # Wall
            ]
        else:
            # Normal city
            return [
                # Row 0
                ((x - 2, y - 2), "#", "#808080"),          # Wall (grey)
                ((x - 1, y - 2), "═", "#808080"),      # Wall
                ((x, y - 2), "═", "#808080"),      # Wall
                ((x + 1, y - 2), "═", "#808080"),      # Wall
                ((x + 2, y - 2), "#", "#808080"),      # Wall
                
                # Row 1
                ((x - 2, y - 1), "║", "#808080"),      # Wall
                ((x - 1, y - 1), "Ѧ", "#B22222"),  # Building (brick)
                ((x, y - 1), "Ћ", "#B22222"),  # Building
                ((x + 1, y - 1), "Ћ", "#B22222"),  # Building
                ((x + 2, y - 1), "║", "#808080"),  # Wall
                
                # Row 2
                ((x - 2, y), "║", "#808080"),      # Wall
                ((x - 1, y), "֏", "#B22222"),  # Building
                ((x, y), "Ѻ", "#808080"),  # City square (grey)
                ((x + 1, y), "Ћ", "#B22222"),  # Building
                ((x + 2, y), "║", "#808080"),  # Wall
                
                # Row 3
                ((x - 2, y + 1), "║", "#808080"),      # Wall
                ((x - 1, y + 1), "Ҵ", "#B22222"),  # Building
                ((x, y + 1), "║", "#8B4513"),  # Main road (grey)
                ((x + 1, y + 1), "Ҵ", "#B22222"),  # Building
                ((x + 2, y + 1), "║", "#808080"),  # Wall
                
                # Row 4
                ((x - 2, y + 2), "#", "#808080"),      # Wall
                ((x - 1, y + 2), "₸", "#808080"),  # Gate (grey)
                ((x, y + 2), "₳", "#808080"),  # Gate
                ((x + 1, y + 2), "₸", "#808080"),  # Gate
                ((x + 2, y + 2), "#", "#808080"),  # Wall
            ]
    
    def get_max_camps(self) -> int:
        return 6  # Cities can have up to 6 camps (2 forest + 2 mountain + 2 any)

    def get_prioritized_resource(self) -> str:
        return 'mountain'  # Cities prioritize mountain (ore) camps

    def get_prioritized_resource_count(self) -> int:
        return 2
    
    def on_pre_death(self) -> None:
        """Called before city death - destroy spire along with it."""
        if self.spire and self.spire.is_alive:
            self.spire.die("city destroyed")
    
    def on_dawn(self) -> None:
        """Handle dawn event - process daily settlement event and try selling blessings."""
        if self.process_ruins():
            return
        
        # Check for spire creation on day after market day
        prev_event = self.current_event
        
        self.process_daily_event()
        
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
                
                self._send_blessing_caravan(self.world, target, retrieving=False)
                self.think(f"Sending blessing to {target.name}.")
    
    def _attempt_create_spire(self) -> bool:
        """Attempt to create a spire near the city."""
        from . import Spire
        
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
            if self.world.get_biome_from_height(height) != 'field':
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
    
    def _spawn_hero(self, city_born: bool = True) -> None:
        """Spawn a hero from the city."""
        from . import Hero
        
        # Spawn at city gate
        hero = Hero(self.world, (self.coordinates[0], self.coordinates[1] + 3), self)
        self.world.add_entity(hero)

