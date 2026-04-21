"""Mixin for settlement expansion logic."""
from typing import Optional, List, Any, TYPE_CHECKING
from game.entities.spirit import SpiritType

if TYPE_CHECKING:
    from ..base.entity import Coordinates
    from game.entities.spirit import Spirit

# Expansion constants
CAMP_SEARCH_RADIUS = 15  # Radius around spirit to search for camp locations
MIN_CAMP_SETTLEMENT_DISTANCE = 10  # Minimum distance from settlements for camp


class Expansion:
    """Mixin providing settlement expansion capabilities."""
    
    # Subclasses should initialize these
    subsidiary_camps: List[Any]
    _days_since_settler: int
    
    def try_expand(self) -> None:
        """Try to send settler caravan (every 2 days if under camp limit)."""
        # Check expansion timing (every 2 days)
        self._days_since_settler += 1
        if self._days_since_settler < 2:
            return
        
        self._days_since_settler = 0
        
        # Count actual camps (not caravans), excluding lake camps which don't count toward limit
        camp_count = sum(1 for c in self.subsidiary_camps 
                         if c.__class__.__name__ == 'Camp' and 
                         c.target_spirit is not None and
                         c.target_spirit.type != SpiritType.WATER)
        
        max_camps = self.get_max_camps()
        if camp_count >= max_camps:
            return
        
        # Find best spirit to expand to, prioritizing resource requirements
        forest_camps = 0
        mountain_camps = 0
        for camp in self.subsidiary_camps:
            if camp.__class__.__name__ == 'Camp':
                spirit = camp.target_spirit
                if spirit:
                    if spirit.type == SpiritType.FOREST:
                        forest_camps += 1
                    elif spirit.type == SpiritType.MOUNTAIN:
                        mountain_camps += 1

        prioritized = self.get_prioritized_resource()
        required_count = self.get_prioritized_resource_count()

        priority_types = []
        if prioritized == SpiritType.FOREST and forest_camps < required_count:
            priority_types.append(SpiritType.FOREST)
        elif prioritized == SpiritType.MOUNTAIN and mountain_camps < required_count:
            priority_types.append(SpiritType.MOUNTAIN)

        if not priority_types:
            priority_types = [SpiritType.FOREST, SpiritType.MOUNTAIN, SpiritType.WATER]

        best_spirit = None
        best_distance = float('inf')
        for entity in list(self.world.entities):
            if entity.__class__.__name__ != 'Spirit' or not entity.is_alive:
                continue
            if entity.type not in priority_types:
                continue
            if entity.is_occupied:
                continue
            distance = self.get_distance(entity.coordinates)
            if distance < best_distance:
                best_distance = distance
                best_spirit = entity

        spirit = best_spirit
        if spirit:
            # Find closest valid location for a worker camp near the spirit
            spirit_x, spirit_y = spirit.coordinates
            valid_locations = []
            for dx in range(-CAMP_SEARCH_RADIUS, CAMP_SEARCH_RADIUS):
                for dy in range(-CAMP_SEARCH_RADIUS, CAMP_SEARCH_RADIUS):
                    x, y = spirit_x + dx, spirit_y + dy
                    dist = spirit.get_distance((x, y))
                    if dist > CAMP_SEARCH_RADIUS:
                        continue
                    if x < 0 or y < 0 or x >= self.world.WIDTH - 1 or y >= self.world.HEIGHT - 1:
                        continue
                    from game.world import check_settlement_distance
                    if not check_settlement_distance(self.world, x, y, min_distance=MIN_CAMP_SETTLEMENT_DISTANCE):
                        continue
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
                    valid_locations.append((dist, (x, y)))

            location = None
            if valid_locations:
                valid_locations.sort(key=lambda item: item[0])
                location = valid_locations[0][1]

            if location:
                spirit.is_occupied = True  # Mark spirit as claimed 
                from game.entities.caravan import CaravanMission
        
                caravan = self.send_caravan(location, CaravanMission.SETTLE_CAMP, target_spirit=spirit)
        
                self.subsidiary_camps.append(caravan)
    
    def die(self, reason: str) -> None:
        """Handle settlement death - free up any occupied spirits and reassign camp ownership."""
        if self.nearby_spirits:
            for spirit in self.nearby_spirits:
                spirit.is_occupied = False
        
        for camp in self.subsidiary_camps:
            if camp.__class__.__name__ == 'Camp':
                distance = float('inf')
                for e in list(self.world.entities):
                    if e.__class__.__name__ in ('City', 'Village') and e.is_alive and e != self:
                        if camp.get_distance(e.coordinates) < distance:
                            distance = camp.get_distance(e.coordinates)
                            camp.home = e  # Reassign camp ownership to closest settlement
                
        
        super().die(reason)

    def get_max_camps(self) -> int:
        """Override in subclass to set camp limit."""
        raise NotImplementedError

    def get_prioritized_resource(self) -> SpiritType:
        """Override in subclass to prioritize 'forest' or 'mountain'."""
        raise NotImplementedError

    def get_prioritized_resource_count(self) -> int:
        """Override in subclass to set how many camps of the prioritized type are needed."""
        raise NotImplementedError