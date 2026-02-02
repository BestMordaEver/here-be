"""Cattle entity with day-based wandering and fear reactions."""
from random import randint, random
from typing import TYPE_CHECKING, Dict, Any, Optional

from .base import Coordinates, Mobile, Settlement, Mortal, Scheduled, ActionType, ScheduledAction

if TYPE_CHECKING:
    from game.world import World


# Cattle constants
VILLAGE_ATTRACTION_RADIUS = 10  # Distance to check for villages
WANDER_RANGE = 10              # Random wander distance
FEAR_RADIUS = 12               # Distance to notice threats
SCORCHED_FEAR_RADIUS = 8       # Distance to avoid scorched land


class Cattle(Mortal, Mobile, Scheduled):
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
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                return False
        
        # Avoid scorched land
        if self._is_scorched(coordinates):
            return False
        
        return True
    
    def _is_scorched(self, coordinates: Coordinates) -> bool:
        """Check if coordinates are in scorched dragon territory."""
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Domain':
                if hasattr(entity, 'is_scorched') and entity.is_scorched:
                    if entity.get_distance(coordinates) <= 10:  # Scorched radius
                        return True
        return False
    
    def _find_nearby_village(self) -> Optional[Settlement]:
        """Find a village within attraction radius."""
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Village' and entity.is_alive:
                if self.get_distance(entity.coordinates) <= VILLAGE_ATTRACTION_RADIUS:
                    return entity
        return None
    
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
    
    def on_hour(self, hour: int) -> None:
        """Process hourly updates."""
        if self.is_sleeping:
            return
        
        action = self.get_action_for_hour(hour)
        if action:
            self.start_action(action)
            self._choose_wander_destination()
    
    def _choose_wander_destination(self) -> None:
        """Choose a destination, gravitating toward villages."""
        village = self._find_nearby_village()
        
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
                self.set_destination(target)
                return
        
        # Couldn't find valid destination, stay put
        self.complete_current_action()
    
    def on_arrival(self) -> None:
        """Called when arriving at destination - just complete action."""
        self.complete_current_action()
        self.grazing = True
    
    def check_for_encounters(self) -> Optional[Mobile]:
        """Check for dragons (fear)."""
        nearby = self.get_nearby_entities(FEAR_RADIUS)
        
        for entity in nearby:
            if entity.__class__.__name__ in ('Dragon', 'DragonBase'):
                return entity
        
        return None
    
    def react_to_encounter(self, other: 'Mobile') -> Optional[ScheduledAction]:
        """React to dragons by fleeing."""
        if other.__class__.__name__ in ('Dragon', 'DragonBase'):
            self.fleeing_from = other
            self.grazing = False
            self.flee_from(other)
            return ScheduledAction(
                hour=self.world.time.current_hour if hasattr(self.world, 'time') else 0,
                action_type=ActionType.FLEE,
                priority=100
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
