"""Base settlement class for all settlement types."""
from entities.base.entity import Entity, Coordinates
from entities.base.named import Named
from entities.base.thinking import Thinking
from typing import Dict, Any, List, Tuple, Optional, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from world import World


class Settlement(Entity, Named, Thinking):
    """Base class for all settlement types."""
    
    def __init__(
        self,
        name: str,
        coordinates: Coordinates,
        life: int,
        settlement_type: str,
    ):
        Entity.__init__(self, "#808080", "₼", coordinates, life)
        Named.__init__(self, name)
        Thinking.__init__(self)
        self.settlement_type = settlement_type
        
        # Resource storage
        self.resources = {
            'food': 0,
            'wood': 0,
            'ores': 0,
            'treasure': 0
        }
        
        # Set storage capacity based on settlement type
        if settlement_type == 'worker_camp':
            self.storage_capacity = 100
        else:  # village or city
            self.storage_capacity = 200
        
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return list of (coordinates, symbol, color) for all tiles in settlement."""
        raise NotImplementedError
    
    def occupies(self, coordinates: Coordinates) -> bool:
        """Check if this settlement occupies the given coordinates."""
        tiles = self.get_tiles()
        for tile_coords, _, _ in tiles:
            if tile_coords == coordinates:
                return True
        return False
    
    def die(self, world, reason) -> None:
        """Handle settlement death/depletion."""
        super().die(world, reason)
    
    def add_resource(self, resource_type: str, amount: int) -> int:
        """Add resources to storage. Returns amount actually added (capped by storage)."""
        if resource_type not in self.resources:
            return 0
        
        current = self.resources[resource_type]
        max_add = self.storage_capacity - current
        actual_add = min(amount, max_add)
        self.resources[resource_type] = current + actual_add
        return actual_add
    
    def remove_resource(self, resource_type: str, amount: int) -> int:
        """Remove resources from storage. Returns amount actually removed."""
        if resource_type not in self.resources:
            return 0
        
        current = self.resources[resource_type]
        actual_remove = min(amount, current)
        self.resources[resource_type] = current - actual_remove
        return actual_remove
    
    def generate_resources(self, world) -> None:
        """Generate resources based on settlement type. Override in subclasses."""
        pass
    
    def consume_food(self) -> None:
        """Consume food each cycle based on settlement type. Lose life if starving."""
        if self.is_dead:
            return
        
        # Determine food consumption rate
        if self.settlement_type == 'worker_camp':
            food_needed = 2
        elif self.settlement_type == 'village':
            food_needed = 1
        elif self.settlement_type == 'city':
            food_needed = 3
        else:
            food_needed = 1  # Default
        
        # Try to consume food
        food_consumed = self.remove_resource('food', food_needed)
        
        # If couldn't consume enough food, starve
        if food_consumed < food_needed:
            starvation_damage = food_needed - food_consumed
            self.life -= starvation_damage
    
    def has_excess_food(self) -> bool:
        """Check if settlement has excess food (more than 50% capacity)."""
        return self.resources['food'] > self.storage_capacity * 0.5
    
    def find_valid_camp_location(self, spirit, world: 'World') -> Optional[Coordinates]:
        """Find a valid location for a worker camp near a spirit.
        Returns None if no valid location found."""
        spirit_x, spirit_y = spirit.coordinates
        
        # Try locations in expanding rings around the spirit
        for distance in range(1, 15):  # Search up to 15 tiles away
            candidates = []
            
            # Generate all coordinates at this Manhattan distance
            for dx in range(-distance, distance + 1):
                dy_remaining = distance - abs(dx)
                for dy in [-dy_remaining, dy_remaining] if dy_remaining != 0 else [0]:
                    x, y = spirit_x + dx, spirit_y + dy
                    
                    # Check if within world bounds (need room for 2x2 camp)
                    if x < 0 or y < 0 or x >= world.WIDTH - 1 or y >= world.HEIGHT - 1:
                        continue
                    
                    # Check if at least 10 tiles from any settlement
                    too_close = False
                    for entity in world.entities:
                        if hasattr(entity, 'settlement_type'):
                            ex, ey = entity.coordinates
                            settlement_distance = abs(x - ex) + abs(y - ey)
                            if settlement_distance < 10:
                                too_close = True
                                break
                    
                    if too_close:
                        continue
                    
                    # Check if 2x2 area is all plains biome
                    all_plains = True
                    for dy_check in [0, 1]:
                        for dx_check in [0, 1]:
                            check_x, check_y = x + dx_check, y + dy_check
                            if check_x >= world.WIDTH or check_y >= world.HEIGHT:
                                all_plains = False
                                break
                            height = world.height_map[check_y][check_x]
                            if world.get_biome_from_height(height) != 'field':
                                all_plains = False
                                break
                        if not all_plains:
                            break
                    
                    if not all_plains:
                        continue
                    
                    # Check if any entity occupies the 2x2 area
                    occupied = False
                    for dy_check in [0, 1]:
                        for dx_check in [0, 1]:
                            check_coords = (x + dx_check, y + dy_check)
                            for entity in world.entities:
                                if hasattr(entity, 'occupies'):
                                    if entity.occupies(check_coords):
                                        occupied = True
                                        break
                                elif entity.coordinates == check_coords:
                                    occupied = True
                                    break
                            if occupied:
                                break
                        if occupied:
                            break
                    
                    if occupied:
                        continue
                    
                    candidates.append((x, y))
            
            # Return the first valid candidate at this distance
            if candidates:
                return candidates[0]
        
        return None
    
    def attempt_create_worker_camp(self, world: 'World') -> None:
        """Attempt to send a caravan to create a worker camp near a spirit."""
        if self.is_dead or self.settlement_type == 'worker_camp':
            return
        
        if not self.has_excess_food():
            return
        
        # Find nearby spirits
        spirits = []
        for entity in world.entities:
            if hasattr(entity, '__class__') and entity.__class__.__name__ == 'Spirit':
                spirits.append(entity)
        
        if not spirits:
            return
        
        # Shuffle spirits to try them in random order
        random.shuffle(spirits)
        
        for spirit in spirits:
            # Find valid camp location near this spirit
            camp_location = self.find_valid_camp_location(spirit, world)
            
            if camp_location is None:
                continue
            
            # Check distance constraints based on spirit type
            spirit_x, spirit_y = spirit.coordinates
            camp_x, camp_y = camp_location
            distance_to_spirit = abs(camp_x - spirit_x) + abs(camp_y - spirit_y)
            
            if spirit.type == 'forest' and distance_to_spirit > 6:
                continue  # Too far from forest spirit
            elif spirit.type == 'mountain' and distance_to_spirit > 10:
                continue  # Too far from mountain spirit
            
            # Valid location found! Create caravan
            from entities import Caravan, Camp
            
            # Generate a name for the camp
            camp_name = f"{self.name} Camp"
            
            # Create the caravan with intent to establish camp
            caravan = Caravan(
                coordinates=(self.coordinates[0], self.coordinates[1] + 2),
                home=self,
                destination=camp_location,
                intent=f"establish_camp:{camp_name}:{spirit.type}"
            )
            
            world.add_entity(caravan)
            
            # Deduct some food for sending the caravan
            self.remove_resource('food', 10)
            
            return  # Only send one caravan at a time
    
    def update(self, world) -> None:
        if self.life <= 0 and self.is_alive:
            self.die(world, "starvation")
        else:
            # Generate resources each cycle
            self.generate_resources(world)
            # Consume food each cycle
            self.consume_food()
            # Attempt to create worker camps if excess food
            self.attempt_create_worker_camp(world)

    def serialize(self) -> Dict[str, Any]:
        """Serialize settlement to dictionary for JSON output."""
        data = super().serialize()
        data["name"] = self.name
        data["settlement_type"] = self.settlement_type
        data["depleted"] = self.is_dead
        data["tiles"] = self.get_tiles()
        data["resources"] = self.resources.copy()
        data["storage_capacity"] = self.storage_capacity
        data["debug_info"] = f"{self.name} ({self.settlement_type}) at {self.coordinates}"
        return data
