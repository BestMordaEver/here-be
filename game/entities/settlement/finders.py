from random import random
from typing import TYPE_CHECKING, Optional, Any
from .types import SettlementEvent
from game.entities.spirit import SpiritType

if TYPE_CHECKING:
    from game.entities.base.entity import Coordinates
    from game.entities.spirit import Spirit
    from .settlement import Settlement

# Expansion constants
CAMP_SEARCH_RADIUS = 15  # Radius around spirit to search for camp locations
MIN_CAMP_SETTLEMENT_DISTANCE = 10  # Minimum distance from settlements for camp


def find_trade_target(settlement : 'Settlement') -> Optional[Any]:
    """Find a nearby settlement to trade with. Closer = higher probability."""
    from .settlement import Settlement
    
    candidates = []
    for entity in settlement.world.entities:
        if isinstance(entity, Settlement) and entity.is_alive and entity != settlement:
            distance = settlement.get_distance(entity.coordinates)
            if distance <= 50:  # Max trade range
                # Weight by inverse distance (closer = more likely)
                weight = 50 - distance
                candidates.append((weight, entity))
    
    if not candidates:
        return None
    
    # Prioritize market days
    market_targets = [
        (w * 2, e) for w, e in candidates 
        if hasattr(e, 'current_event') and e.current_event == SettlementEvent.MARKET_DAY
    ]
    
    if market_targets:
        candidates = market_targets
    
    # Weighted random selection
    total_weight = sum(w for w, _ in candidates)
    if total_weight <= 0:
        return None
    
    r = random() * total_weight
    cumulative = 0
    for weight, entity in candidates:
        cumulative += weight
        if r <= cumulative:
            return entity
    
    return candidates[-1][1] if candidates else None

def find_expansion_spirit(settlement : 'Settlement') -> Optional[Any]:
    """Find best spirit to expand to, prioritizing resource requirements."""
    if not hasattr(settlement, 'subsidiary_camps'):
        return None
    
    # Count current camp types
    forest_camps = 0
    mountain_camps = 0
    for camp in settlement.subsidiary_camps:
        if camp.__class__.__name__ == 'Camp':
            spirit = getattr(camp, 'target_spirit', None)
            if spirit:
                if spirit.type == SpiritType.FOREST:
                    forest_camps += 1
                elif spirit.type == SpiritType.MOUNTAIN:
                    mountain_camps += 1
    
    # Get requirements from subclass
    prioritized = settlement.get_prioritized_resource()
    required_count = settlement.get_prioritized_resource_count()
    
    # Build priority order based on requirements
    priority_types = []
    
    # Check if we still need the prioritized resource
    if prioritized == SpiritType.FOREST and forest_camps < required_count:
        priority_types.append(SpiritType.FOREST)
    elif prioritized == SpiritType.MOUNTAIN and mountain_camps < required_count:
        priority_types.append(SpiritType.MOUNTAIN)
    
    # If requirements met, allow any type (including water/lake)
    if not priority_types:
        priority_types = [SpiritType.FOREST, SpiritType.MOUNTAIN, SpiritType.WATER]
    
    # Find closest unoccupied spirit of priority type
    best_spirit = None
    best_distance = float('inf')
    
    for entity in settlement.world.entities:
        if entity.__class__.__name__ != 'Spirit' or not entity.is_alive:
            continue
        if entity.type not in priority_types:
            continue
        if getattr(entity, 'is_occupied', False):
            continue
        
        distance = settlement.get_distance(entity.coordinates)
        if distance < best_distance:
            best_distance = distance
            best_spirit = entity
    
    return best_spirit

def find_valid_camp_location(settlement : 'Settlement', spirit : 'Spirit') -> Optional['Coordinates']:
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
            if x < 0 or y < 0 or x >= settlement.world.WIDTH - 1 or y >= settlement.world.HEIGHT - 1:
                continue
            
            from game.world import check_settlement_distance

            # Check if at least minimum distance from any settlement
            if not check_settlement_distance(settlement.world, x, y, min_distance=MIN_CAMP_SETTLEMENT_DISTANCE):
                continue
            
            # Check if 2x2 area is all plains biome
            all_plains = True
            for dy_check in [0, 1]:
                for dx_check in [0, 1]:
                    check_x, check_y = x + dx_check, y + dy_check
                    height = settlement.world.height_map[check_y][check_x]
                    if settlement.world.get_biome_from_height(height) != 'field':
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
                    if settlement.world.get_entities_at((x + dx_check, y + dy_check)):
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