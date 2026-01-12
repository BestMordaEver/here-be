"""Mixin for settlement expansion logic."""
from typing import Optional, TYPE_CHECKING
from .named import Named

if TYPE_CHECKING:
    from .entity import Coordinates
    from game.world import World


WOOD_CAMP_RANGE = 6
ORE_CAMP_RANGE = 10


class ExpansionMixin(Named):
    """Mixin providing settlement expansion capabilities."""
    
    def has_excess(self, resource) -> bool:
        """Check if settlement has excess of the resource (more than 50% capacity)."""
        return self.resources[resource] > self.storage_capacity * 0.5
    
    def expand_settlement(self, world: 'World') -> None:
        """Expand the settlement by creating new camps or villages."""
        raise NotImplementedError("Subclasses must implement expand_settlement()")
    
    def find_valid_camp_location(self, spirit, world: 'World') -> Optional['Coordinates']:
        """Find the closest valid location for a worker camp near a spirit.
        Returns None if no valid location found."""
        spirit_x, spirit_y = spirit.coordinates
        valid_locations = []
        
        # Search within a 15-tile radius
        for dx in range(-15, 15):
            for dy in range(-15, 15):
                x, y = spirit_x + dx, spirit_y + dy
                
                distance = spirit.get_distance((x, y))
                if distance > 15:
                    continue
                
                # Check if within world bounds (need room for 2x2 camp)
                if x < 0 or y < 0 or x >= world.WIDTH - 1 or y >= world.HEIGHT - 1:
                    continue
                
                from game.world import check_settlement_distance

                # Check if at least 10 tiles from any settlement
                if not check_settlement_distance(world, x, y, min_distance=10):
                    continue
                
                # Check if 2x2 area is all plains biome
                all_plains = True
                for dy_check in [0, 1]:
                    for dx_check in [0, 1]:
                        check_x, check_y = x + dx_check, y + dy_check
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
                        if world.get_entities_at((x + dx_check, y + dy_check)):
                            occupied = True
                            break
                    if occupied:
                        break
                
                if occupied:
                    continue
                
                # This location is valid - store it with its distance
                valid_locations.append((distance, (x, y)))
        
        # Return the closest valid location
        if valid_locations:
            valid_locations.sort(key=lambda item: item[0])
            return valid_locations[0][1]
        
        return None


    def get_max_camps(self) -> int:
        """Override in subclass to set camp limit."""
        raise NotImplementedError

    def get_prioritized_resource(self) -> str:
        """Override in subclass to prioritize 'forest' or 'mountain'."""
        raise NotImplementedError

    def get_prioritized_resource_count(self) -> int:
        """Override in subclass to set how many camps of the prioritized type are needed."""
        raise NotImplementedError


    def expand_settlement(self, world: 'World') -> None:
        """Attempt to send a caravan to create a worker camp near a spirit."""
        if not self.has_excess('food'):
            return
        
        # Check caravan cooldown (8 cycles)
        if world.update_count - self.last_caravan_cycle < 8:
            return
        
        # Check if we've reached the camp limit (3 max)
        if len(self.subsidiary_camps) >= self.get_max_camps():
            return
        
        required_type = self.get_prioritized_resource()
        required_count = self.get_prioritized_resource_count()
        
        # Count how many camps have prioritized resource access
        camps = 0
        for sub in self.subsidiary_camps:
            if sub.__class__.__name__ == 'Caravan':
                if self.get_prioritized_resource() in sub.intent:
                    camps += 1
            elif sub.has_ore_access() if required_type == 'mountain' else sub.has_wood_access():
                camps += 1
        
        # Find nearby spirits, sorted by distance
        spirits_with_distance = []
        for entity in world.entities:
            if entity.__class__.__name__ == 'Spirit' and not entity.is_occupied:
                spirits_with_distance.append((self.get_distance(entity.coordinates), entity))
        
        if not spirits_with_distance:
            return
        
        # Sort by distance (closest first)
        spirits_with_distance.sort(key=lambda item: item[0])
        
        for distance, spirit in spirits_with_distance:
            # Prioritize forest spirits if we need wood access
            if camps < required_count and spirit.type != required_type:
                continue
            
            # Find valid camp location near this spirit
            camp_location = self.find_valid_camp_location(spirit, world)
            
            if camp_location is None:
                continue
            
            # Check distance constraints based on spirit type
            distance_to_spirit = spirit.get_distance(camp_location)
            
            if spirit.type == 'forest' and distance_to_spirit > 6:
                continue  # Too far from forest spirit
            elif spirit.type == 'mountain' and distance_to_spirit > 10:
                continue  # Too far from mountain spirit
            
            # Valid location found! Create caravan
            from game.entities import Caravan
            
            # Create the caravan with intent to establish camp
            caravan = Caravan(
                coordinates=(self.coordinates[0], self.coordinates[1] + 2),
                home=self,
                destination=camp_location,
                intent="settle " + ("wood" if spirit.type == 'forest' else "ore") + f" {spirit.coordinates}"
            )
            
            world.add_entity(caravan)
            
            # Deduct some food for sending the caravan
            self.remove_resource('food', 40)
            
            # Track the subsidiary camp
            self.subsidiary_camps.append(caravan)
            
            # Update last caravan cycle
            self.last_caravan_cycle = world.update_count
            
            return  # Only send one caravan at a time