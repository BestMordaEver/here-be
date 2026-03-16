"""Mixin for settlement expansion logic."""
from typing import Optional, List, Any, TYPE_CHECKING
from game.entities.spirit import SpiritType
from .finders import find_expansion_spirit, find_valid_camp_location

if TYPE_CHECKING:
    from ..base.entity import Coordinates
    from game.entities.spirit import SpiritType


class Expansion:
    """Mixin providing settlement expansion capabilities."""
    
    # Subclasses should initialize these
    subsidiary_camps: List[Any]
    _days_since_settler: int
    
    def try_expand(self) -> None:
        """Try to send settler caravan (every 2 days if under camp limit)."""
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
        
        # Count actual camps (not caravans), excluding lake camps which don't count toward limit
        camp_count = sum(1 for c in self.subsidiary_camps 
                         if c.__class__.__name__ == 'Camp' and 
                         getattr(getattr(c, 'target_spirit', None), 'type', None) != SpiritType.WATER)
        
        max_camps = self.get_max_camps()
        if camp_count >= max_camps:
            return
        
        # Find spirit to exploit
        spirit = find_expansion_spirit(self)
        if spirit:
            location = find_valid_camp_location(self, spirit)
            if location:
                spirit.is_occupied = True  # Mark spirit as claimed 
                from game.entities.caravan import CaravanMission
        
                caravan = self.send_caravan(location, CaravanMission.SETTLE_CAMP, target_spirit=spirit)
        
                if hasattr(self, 'subsidiary_camps'):
                    self.subsidiary_camps.append(caravan)
    
    def die(self, reason: str) -> None:
        """Handle settlement death - free up any occupied spirits and reassign camp ownership."""
        if self.nearby_spirits:
            for spirit in self.nearby_spirits:
                spirit.is_occupied = False
        
        for camp in self.subsidiary_camps:
            if camp.__class__.__name__ == 'Camp':
                distance = float('inf')
                for e in self.world.entities:
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