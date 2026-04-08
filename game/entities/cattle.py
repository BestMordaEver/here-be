"""Cattle entity with day-based wandering and fear reactions."""
from random import randint, random
from typing import TYPE_CHECKING, Dict, Any, Optional

from .base import (
    Coordinates, Mobile, Scheduled, 
    ActionType, ScheduledAction, EngagementType
)
from .settlement.settlement import Settlement

if TYPE_CHECKING:
    from game.world import World


# Cattle constants
VILLAGE_ATTRACTION_RADIUS = 10  # Distance to check for villages
WANDER_RANGE = 10              # Random wander distance
FEAR_RADIUS = 12               # Distance to notice threats
SCORCHED_FEAR_RADIUS = 8       # Distance to avoid scorched land


class Cattle(Mobile, Scheduled):
    """Cattle that wander and graze, fearing dragons and scorched land."""
    
    def __init__(self, world: 'World', color: str, coordinates: Coordinates):
        Mobile.__init__(self, world, color, 'ɤ', coordinates, loiter=10)  # Cattle skip 10 cycles
        Scheduled.__init__(self)
        
        self.grazing = True
        self.fleeing_from = None
    
    def is_passable(self, coordinates: Coordinates) -> bool:
        """Cattle can only move through fields."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(self.world.height_map[0]) or y >= len(self.world.height_map):
            return False
        
        height = self.world.height_map[y][x]
        if self.world.get_biome_from_height(height) != 'field':
            return False
        
        # Avoid settlements
        for entity in self.world.get_entities_at(coordinates):
            if isinstance(entity, Settlement):
                return False
        
        # Avoid scorched land
        from game.entities.dragon.domain import Domain
        for entity in self.world.get_entities_nearby(coordinates, 10, 'Domain'):
            if isinstance(entity, Domain) and entity.is_scorched:
                return False
        
        return True
    
    def build_schedule(self) -> None:
        """Build simple daily schedule - just wander."""
        self.schedule = []
        self.current_action = None
        self.fleeing_from = None
        
        # Cattle just wander throughout the day
        self.schedule_actions([
            (ActionType.WANDER, None),
            (ActionType.WANDER, None),
            (ActionType.WANDER, None),
        ])
    
    def _choose_wander_destination(self) -> None:
        """Choose a destination, gravitating toward villages."""
        villages = self.get_nearby_entities(VILLAGE_ATTRACTION_RADIUS, 'Village')
        village = villages[0] if villages else None
        
        for _ in range(10):  # Try 10 times to find valid destination
            if village:
                # Stay within range of village
                vx, vy = village.coordinates
                dx = randint(-WANDER_RANGE, WANDER_RANGE)
                dy = randint(-WANDER_RANGE, WANDER_RANGE)
                target = (vx + dx, vy + dy)
            else:
                # Random wander
                cx, cy = self.coordinates
                dx = randint(-WANDER_RANGE, WANDER_RANGE)
                dy = randint(-WANDER_RANGE, WANDER_RANGE)
                target = (cx + dx, cy + dy)
            
            # Clamp to world bounds
            x = max(0, min(self.world.WIDTH - 1, target[0]))
            y = max(0, min(self.world.HEIGHT - 1, target[1]))
            target = (x, y)
            
            if self.is_passable(target):
                self.set_target(target)
                return
        
        # Couldn't find valid destination, stay put
        self.complete_current_action()
    
    def on_arrival(self) -> None:
        """Called when arriving at destination - just complete action."""
        self.complete_current_action()
        self.grazing = True
    
    def check_for_encounters(self) -> Optional[Mobile]:
        """Check for dragons (fear). Cattle flee from all dragons."""
        nearby = self.get_nearby_entities(FEAR_RADIUS)
        
        for entity in nearby:
            if entity.__class__.__name__ == 'Dragon' and entity.is_alive:
                return entity
        
        return None
    
    def react_to_encounter(self, other: 'Mobile') -> Optional[ScheduledAction]:
        """React to dragons by fleeing."""
        if other.__class__.__name__ == 'Dragon':
            # If we're being hunted (engaged), we're probably about to die
            # but we still try to flee
            if self.is_engaged():
                self.disengage()
            
            self.fleeing_from = other
            self.grazing = False
            self.flee_from(other)
            return ScheduledAction(
                hour=self.world.time.current_hour,
                action_type=ActionType.FLEE
            )
        
        return None
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        data = super().serialize()
        data.update({
            "grazing": self.grazing,
            "fleeing": self.fleeing_from is not None,
        })
        return data
