"""Mixin for settlement expansion logic."""
from typing import Optional, List, Any, TYPE_CHECKING
from .named import Named

if TYPE_CHECKING:
    from .entity import Coordinates


# Expansion constants
WOOD_CAMP_RANGE = 6  # Max distance from forest spirit for camp
ORE_CAMP_RANGE = 10  # Max distance from mountain spirit for camp
CAMP_SEARCH_RADIUS = 15  # Radius around spirit to search for camp locations
MIN_CAMP_SETTLEMENT_DISTANCE = 10  # Minimum distance from settlements for camp


class ExpansionMixin(Named):
    """Mixin providing settlement expansion capabilities."""
    
    # Subclasses should initialize these
    subsidiary_camps: List[Any]
    _days_since_settler: int
    
    def try_expand(self) -> None:
        """Try to send settler caravan (every 2 days if under camp limit)."""
        # Only villages and cities expand
        if self.__class__.__name__ not in ('Village', 'City'):
            return
        
        # Check expansion timing (every 2 days)
        if not hasattr(self, '_days_since_settler'):
            self._days_since_settler = 0
        
        self._days_since_settler += 1
        if self._days_since_settler < 2:
            return
        
        self._days_since_settler = 0
        
        # Check camp limit
        if not hasattr(self, 'subsidiary_camps'):
            self.subsidiary_camps = []
        
        # Count actual camps (not caravans)
        camp_count = sum(1 for c in self.subsidiary_camps 
                         if c.__class__.__name__ == 'Camp')
        
        max_camps = self.get_max_camps()
        if camp_count >= max_camps:
            return
        
        # Find spirit to exploit
        spirit = self._find_expansion_spirit()
        if spirit:
            location = self.find_valid_camp_location(spirit)
            if location:
                spirit.is_occupied = True  # Mark spirit as claimed
                self._send_settler_caravan(location, target_spirit=spirit)
    
    def _find_expansion_spirit(self) -> Optional[Any]:
        """Find best spirit to expand to, prioritizing resource requirements."""
        if not hasattr(self, 'subsidiary_camps'):
            return None
        
        # Count current camp types
        forest_camps = 0
        mountain_camps = 0
        for camp in self.subsidiary_camps:
            if camp.__class__.__name__ == 'Camp':
                spirit = getattr(camp, 'target_spirit', None)
                if spirit:
                    if spirit.type == 'forest':
                        forest_camps += 1
                    elif spirit.type == 'mountain':
                        mountain_camps += 1
        
        # Get requirements from subclass
        prioritized = self.get_prioritized_resource()
        required_count = self.get_prioritized_resource_count()
        
        # Build priority order based on requirements
        priority_types = []
        
        # Check if we still need the prioritized resource
        if prioritized == 'forest' and forest_camps < required_count:
            priority_types.append('forest')
        elif prioritized == 'mountain' and mountain_camps < required_count:
            priority_types.append('mountain')
        
        # Check if we need the secondary resource (half the prioritized requirement)
        secondary_required = max(1, required_count // 2)
        if prioritized == 'forest' and mountain_camps < secondary_required:
            priority_types.append('mountain')
        elif prioritized == 'mountain' and forest_camps < secondary_required:
            priority_types.append('forest')
        
        # If requirements met, allow any type
        if not priority_types:
            priority_types = ['forest', 'mountain']
        
        # Find closest unoccupied spirit of priority type
        best_spirit = None
        best_distance = float('inf')
        
        for entity in self.world.entities:
            if entity.__class__.__name__ != 'Spirit' or not entity.is_alive:
                continue
            if entity.type not in priority_types:
                continue
            if getattr(entity, 'is_occupied', False):
                continue
            
            distance = self.get_distance(entity.coordinates)
            if distance < best_distance:
                best_distance = distance
                best_spirit = entity
        
        return best_spirit
    
    def _send_settler_caravan(self, location, target_spirit) -> None:
        """Send a settler caravan to establish camp."""
        from game.entities.caravan import Caravan, CaravanMission
        
        mission = CaravanMission.SETTLE_CAMP
        
        caravan = Caravan(
            self.world,
            coordinates=(self.coordinates[0], self.coordinates[1] + 2),
            home=self,
            destination=location,
            mission=mission,
            target_spirit=target_spirit
        )
        
        if hasattr(self, 'subsidiary_camps'):
            self.subsidiary_camps.append(caravan)
        
        self.world.add_entity(caravan)
    
    def find_valid_camp_location(self, spirit) -> Optional['Coordinates']:
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
                if x < 0 or y < 0 or x >= self.world.WIDTH - 1 or y >= self.world.HEIGHT - 1:
                    continue
                
                from game.world import check_settlement_distance

                # Check if at least minimum distance from any settlement
                if not check_settlement_distance(self.world, x, y, min_distance=MIN_CAMP_SETTLEMENT_DISTANCE):
                    continue
                
                # Check if 2x2 area is all plains biome
                all_plains = True
                for dy_check in [0, 1]:
                    for dx_check in [0, 1]:
                        check_x, check_y = x + dx_check, y + dy_check
                        height = self.world.height_map[check_y][check_x]
                        if self.world.get_biome_from_height(height) != 'field':
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
                        if self.world.get_entities_at((x + dx_check, y + dy_check)):
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