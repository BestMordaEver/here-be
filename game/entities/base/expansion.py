"""Mixin for settlement expansion logic."""
from typing import Optional, TYPE_CHECKING
from .named import Named

if TYPE_CHECKING:
    from .entity import Coordinates
    from game.world import World


# Expansion constants
WOOD_CAMP_RANGE = 6  # Max distance from forest spirit for camp
ORE_CAMP_RANGE = 10  # Max distance from mountain spirit for camp
EXCESS_THRESHOLD = 0.5  # Resource excess threshold (50% capacity)
CARAVAN_COOLDOWN = 8  # Cycles between sending caravans
CAMP_SEARCH_RADIUS = 15  # Radius around spirit to search for camp locations
MIN_CAMP_SETTLEMENT_DISTANCE = 10  # Minimum distance from settlements for camp
SETTLER_FOOD_COST = 40  # Food cost for sending settler caravan
CAMP_FOOD_THRESHOLD = 0.5  # Camp food threshold (50% capacity)
RESOURCE_PICKUP_THRESHOLD = 10  # Minimum resources to trigger pickup


class ExpansionMixin(Named):
    """Mixin providing settlement expansion capabilities."""
    
    def has_excess(self, resource) -> bool:
        """Check if settlement has excess of the resource (more than 50% capacity)."""
        return self.resources[resource] > self.storage_capacity * EXCESS_THRESHOLD
    
    def expand_settlement(self, world: 'World') -> None:
        """Expand the settlement by creating new camps or villages."""
        raise NotImplementedError("Subclasses must implement expand_settlement()")
    
    def find_valid_camp_location(self, spirit, world: 'World') -> Optional['Coordinates']:
        """Find the closest valid location for a worker camp near a spirit.
        Returns None if no valid location found."""
        spirit_x, spirit_y = spirit.coordinates
        valid_locations = []
        
        # Search within camp search radius
        for dx in range(-CAMP_SEARCH_RADIUS, CAMP_SEARCH_RADIUS):
            for dy in range(-CAMP_SEARCH_RADIUS, CAMP_SEARCH_RADIUS):
                x, y = spirit_x + dx, spirit_y + dy
                
                distance = spirit.get_distance((x, y))
                if distance > CAMP_SEARCH_RADIUS:
                    continue
                
                # Check if within world bounds (need room for 2x2 camp)
                if x < 0 or y < 0 or x >= world.WIDTH - 1 or y >= world.HEIGHT - 1:
                    continue
                
                from game.world import check_settlement_distance

                # Check if at least minimum distance from any settlement
                if not check_settlement_distance(world, x, y, min_distance=MIN_CAMP_SETTLEMENT_DISTANCE):
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
        
        # Check caravan cooldown
        if world.update_count - self.last_caravan_cycle < CARAVAN_COOLDOWN:
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
            spirit.is_occupied = True  # Mark spirit as occupied
            
            # Create the caravan with intent to establish camp
            caravan = self.send_caravan(
                world=world,
                destination=camp_location,
                intent="settle " + ("wood" if spirit.type == 'forest' else "ore") + f" {spirit.coordinates}",
                food_cost=SETTLER_FOOD_COST
            )
            
            # Track the subsidiary camp
            self.subsidiary_camps.append(caravan)
            
            # Update last caravan cycle
            self.last_caravan_cycle = world.update_count
            
            return  # Only send one caravan at a time
    
    def send_trade_caravans(self, world: 'World') -> None:
        """Send trade caravans to existing camps to exchange resources."""
        if not self.has_excess('food'):
            return
        
        # Check caravan cooldown
        if world.update_count - self.last_caravan_cycle < CARAVAN_COOLDOWN:
            return
        
        # Find camps that need food or have resources to pick up
        for sub in self.subsidiary_camps:
            if sub.__class__.__name__ != 'Camp':
                continue  # Skip caravans still en route
            
            camp = sub
            if not camp.is_alive:
                continue
            
            # Check if camp needs food (less than threshold capacity)
            needs_food = camp.resources.get('food', 0) < camp.storage_capacity * CAMP_FOOD_THRESHOLD
            # Check if camp has resources to pick up
            has_resources = camp.resources.get('wood', 0) > RESOURCE_PICKUP_THRESHOLD or camp.resources.get('ores', 0) > RESOURCE_PICKUP_THRESHOLD
            
            if needs_food or has_resources:
                from game.entities.caravan import TRADE_CARGO_CAPACITY
                
                # Load food cargo if we have excess
                cargo = {}
                if needs_food:
                    food_to_send = min(TRADE_CARGO_CAPACITY, self.resources.get('food', 0) // 2)
                    if food_to_send > 0:
                        cargo['food'] = food_to_send
                
                # Send caravan (food will be deducted from cargo preparation above)
                caravan = self.send_caravan(
                    world=world,
                    destination=camp,
                    intent="trade",
                    cargo=cargo,
                    food_cost=cargo.get('food', 0)  # Deduct the food we're sending
                )
                
                world.add_entity(caravan)
                
                self.last_caravan_cycle = world.update_count
                return  # Only send one caravan at a time