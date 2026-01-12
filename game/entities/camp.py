"""Worker camp settlement."""
from .base import Coordinates, Settlement, Mortal
from typing import List, Tuple, TYPE_CHECKING


if TYPE_CHECKING:
    from game.world import World
    from . import Spirit

from .base.expansion import WOOD_CAMP_RANGE, ORE_CAMP_RANGE
FOOD_CONSUMPTION = 2
RECOVERY_RATE = 1
WOOD_GATHER_RATE = 3
ORE_GATHER_RATE = 3
SPIRIT_HURT_RATE = 2

# Camp init constants
STARTING_LIFE = 200  # Camp starting HP
STORAGE_CAPACITY = 100  # Camp storage capacity
STARTING_FOOD = 40  # Initial food supply

# Camp caravan constants
CAMP_RETURN_CARAVAN_COOLDOWN = 15  # Cycles between sending return caravans
CAMP_RESOURCE_SEND_THRESHOLD = 40  # Min resources to send back home


class Camp(Mortal, Settlement):
    """2x2 worker camp made of brown diamonds."""
    
    def __init__(self, coordinates: Coordinates, spirit_coordinates: Coordinates, home: 'Settlement'):
        super().__init__(coordinates, life=STARTING_LIFE)
        self.storage_capacity = STORAGE_CAPACITY
        self.resources['food'] = STARTING_FOOD  # Initial food supply
        self.nearby_spirits : List['Spirit'] | None = None  # Cached list of nearby spirits (lazy init)
        self.spirit_coordinates = spirit_coordinates
        self.home = home
        self.last_caravan_cycle = -999  # Last cycle a return caravan was sent
    
    def die(self, world: 'World', cause: str) -> None:
        """Handle camp depletion."""
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
            return []  # Worker camp disappears when depleted
        
        x, y = self.coordinates
        tiles = []
        for dy in [0, 1]:
            for dx in [0, 1]:
                tiles.append(((x + dx, y + dy), "Λ", "#8B4513"))
        return tiles
    
    def consume_resources(self, world: 'World') -> str:
        """Worker camps consume 2 food per cycle."""
        if self.is_dead:
            return
        
        food_consumed = self.remove_resource('food', FOOD_CONSUMPTION)
        
        # If couldn't consume enough food, starve
        if food_consumed < FOOD_CONSUMPTION:
            self.hurt(world, FOOD_CONSUMPTION - food_consumed, 'starvation')
        else:
            self.heal(RECOVERY_RATE)  # Heal 1 life if food needs met
    
    def generate_resources(self, world : 'World') -> None:
        """Gather resources from nearby forest and mountain spirits."""
        if self.is_dead:
            return
        
        # Lazy initialization of nearby spirits cache
        if self.nearby_spirits is None:
            self.nearby_spirits = []
            
            for entity in world.entities:
                if entity.__class__.__name__ == 'Spirit':
                    if entity.type == 'forest' and self.get_distance(entity.coordinates) <= WOOD_CAMP_RANGE:
                        self.nearby_spirits.append(entity)
                    elif entity.type == 'mountain' and self.get_distance(entity.coordinates) <= ORE_CAMP_RANGE:
                        self.nearby_spirits.append(entity)
        
        # Gather from cached spirits
        for spirit in self.nearby_spirits:
            if spirit.is_alive:  # Only gather from living spirits
                # Gather resources from this spirit
                if spirit.type == 'forest':
                    self.add_resource('wood', WOOD_GATHER_RATE)
                elif spirit.type == 'mountain':
                    self.add_resource('ores', ORE_GATHER_RATE)
                
                # Hurt the spirit
                spirit.hurt(world, SPIRIT_HURT_RATE, 'exploitation')
        
        # Send return caravans with gathered resources
        self.send_return_caravan(world)
    
    def send_return_caravan(self, world: 'World') -> None:
        """Send caravan back to home with gathered resources (wood/ores)."""
        if self.is_dead:
            return
        
        # Check if we have a home to send resources to
        if not hasattr(self, 'home') or not self.home or not self.home.is_alive:
            return
        
        # Check caravan cooldown
        if world.update_count - self.last_caravan_cycle < CAMP_RETURN_CARAVAN_COOLDOWN:
            return
        
        # Check if we have resources to send
        wood = self.resources.get('wood', 0)
        ores = self.resources.get('ores', 0)
        
        if wood < CAMP_RESOURCE_SEND_THRESHOLD and ores < CAMP_RESOURCE_SEND_THRESHOLD:
            return  # Not enough resources to send
        
        # Prepare cargo
        cargo = {}
        if wood >= CAMP_RESOURCE_SEND_THRESHOLD:
            # Send half of wood
            wood_to_send = wood // 2
            self.remove_resource('wood', wood_to_send)
            cargo['wood'] = wood_to_send
        
        if ores >= CAMP_RESOURCE_SEND_THRESHOLD:
            # Send half of ores
            ores_to_send = ores // 2
            self.remove_resource('ores', ores_to_send)
            cargo['ores'] = ores_to_send
        
        if cargo:  # Only send if we have cargo
            self.send_caravan(world, self.home, "trade", cargo=cargo, food_cost=0)
