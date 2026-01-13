"""Village settlement."""
from .base import Coordinates, Named, Settlement, ExpansionMixin
from typing import List, Tuple, TYPE_CHECKING


if TYPE_CHECKING:
    from . import City, Camp, Caravan
    from game.world import World


WOOD_CONSUMPTION = 1
RECOVERY_RATE = 1
BASE_FOOD_GENERATION = 2
CATTLE_FOOD_BONUS = 3
CATTLE_FOOD_BONUS_RADIUS = 10
WATER_FOOD_BONUS = 1
WATER_FOOD_BONUS_INTERVAL = 10
WATER_FOOD_BONUS_RADIUS = 10

# Evolution thresholds
EVOLUTION_WOOD_THRESHOLD = 0.5  # 50% of capacity
EVOLUTION_ORE_MINIMUM = 20  # Minimum ores required

# Village init constants
STARTING_LIFE = 500  # Village starting HP
STORAGE_CAPACITY = 200  # Village storage capacity


class Village(Settlement, ExpansionMixin, Named):
    """3x3 village with fields, homes, and city square."""
    
    def __init__(self, name: str, coordinates: Coordinates):
        super().__init__(coordinates, life=STARTING_LIFE)
        Named.__init__(self, name)
        self.storage_capacity = STORAGE_CAPACITY
        self.last_fishing_cycle = -999  # Last cycle fishing bonus was applied
        
        # Expansion tracking
        self.last_caravan_cycle = -999  # Last cycle a caravan was sent
        self.subsidiary_camps: List['Camp | Caravan'] = []
        self.spirit_fishing_bonus = None  # Cached dict of {spirit: fishing_bonus} (lazy init)

    def get_max_camps(self) -> int:
        return 3

    def get_prioritized_resource(self) -> str:
        return 'wood'

    def get_prioritized_resource_count(self) -> int:
        return 2
        
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return all 3x3 tiles for the village.
        Layout (coordinates at city square ¤):
        #⌂#
        ⌂¤⌂
        #₼#
        """
        x, y = self.coordinates  # City square position
        
        if self.is_dead:
            # Depleted village: loses fields (corners become empty), houses become dark grey
            return [
                # Corners (former fields) are now empty - no tiles
                ((x, y - 1), "⌂", "#505050"),  # Top home (dark grey)
                
                ((x - 1, y), "⌂", "#505050"),      # Middle left home
                ((x, y), "¤", "#808080"),  # City square (grey)
                ((x + 1, y), "⌂", "#505050"),  # Middle right home
                
                ((x, y + 1), "₼", "#808080"),  # Gate (grey)
            ]
        else:
            # Normal village
            return [
                ((x - 1, y - 1), "#", "#FFD700"),      # Top left field (yellow)
                ((x, y - 1), "⌂", "#8B4513"),  # Top home (brown)
                ((x + 1, y - 1), "#", "#FFD700"),  # Top right field
                
                ((x - 1, y), "⌂", "#8B4513"),      # Middle left home
                ((x, y), "¤", "#808080"),  # City square (grey)
                ((x + 1, y), "⌂", "#8B4513"),  # Middle right home
                
                ((x - 1, y + 1), "#", "#FFD700"),      # Bottom left field
                ((x, y + 1), "₼", "#808080"),  # Gate (grey)
                ((x + 1, y + 1), "#", "#FFD700"),  # Bottom right field
            ]
    
    def can_evolve(self) -> bool:
        """Check if village meets evolution requirements."""
        return (self.resources['wood'] > self.storage_capacity * EVOLUTION_WOOD_THRESHOLD 
                and self.resources['ores'] >= EVOLUTION_ORE_MINIMUM)
    
    def promote_to_city(self, world: 'World') -> 'City':
        """Promote this village to a city, transferring all state."""
        from .city import City
        city = City(self.name, self.coordinates)
        city.life = self.life
        city.resources = self.resources.copy()
        city.subsidiary_camps = self.subsidiary_camps.copy()
        
        # Update camp homes to point to city
        for camp in city.subsidiary_camps:
            if hasattr(camp, 'home'):
                camp.home = city
        
        # Replace self in world
        world.remove_entity(self)
        world.add_entity(city)
        
        return city
    
    def generate_resources(self, world : 'World') -> None:
        """Generate food resources each cycle.
        - Base: 3 food
        - +3 food for each cattle within 10 tiles
        - +1 food for each water tile in a spirit's domain within 10 tiles (once per 10 cycles)
        """
        if self.is_dead:
            return
        
        food_generated = BASE_FOOD_GENERATION
        
        # Check for cattle within 10 tiles
        for entity in world.entities:
            if entity.__class__.__name__ == 'Cattle':
                if self.get_distance(entity.coordinates) <= CATTLE_FOOD_BONUS_RADIUS:
                    food_generated += CATTLE_FOOD_BONUS
        
        # Fishing bonus - only once every 10 cycles
        if world.update_count - self.last_fishing_cycle >= WATER_FOOD_BONUS_INTERVAL:
            # Lazy initialization of spirit fishing bonus cache
            if self.spirit_fishing_bonus is None:
                self.spirit_fishing_bonus = {}
                
                for entity in world.entities:
                    if entity.__class__.__name__ == 'Spirit' and entity.type == 'water':
                        # Calculate and cache fishing bonus for this spirit
                        bonus = 0
                        for tile_x, tile_y in entity.domain_tiles:
                            if self.get_distance((tile_x, tile_y)) <= WATER_FOOD_BONUS_RADIUS:
                                bonus += WATER_FOOD_BONUS
                        if bonus > 0:
                            self.spirit_fishing_bonus[entity] = bonus
            
            # Sum cached fishing bonuses for alive spirits
            fishing_bonus = 0
            for spirit, bonus in self.spirit_fishing_bonus.items():
                if spirit.is_alive:
                    fishing_bonus += bonus
            
            if fishing_bonus > 0:
                food_generated += fishing_bonus
                # Mark that we applied fishing bonus this cycle
                self.last_fishing_cycle = world.update_count
        
        # Add generated food to storage (capped by capacity)
        self.add_resource('food', food_generated)

    
    def consume_resources(self, world: 'World') -> str:
        """Villages consume 1 wood per cycle."""
        if self.is_dead:
            return
        
        wood_consumed = self.remove_resource('wood', WOOD_CONSUMPTION)
        
        # If couldn't consume enough wood, disrepair
        if wood_consumed < WOOD_CONSUMPTION:
            self.hurt(world, WOOD_CONSUMPTION - wood_consumed, 'disrepair')
        else:
            self.heal(RECOVERY_RATE)  # Heal 1 life if wood needs met
        
        # Check for evolution to city
        if self.can_evolve():
            self.promote_to_city(world)
