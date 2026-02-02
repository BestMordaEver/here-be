"""Ruins mixin - dead entities that persist as ruins before removal."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World


class Ruins:
    """Mixin for entities that become ruins after death.
    
    Subclasses must define:
        - RUINS_DURATION_DAYS: class constant for days before removal
        - is_dead: attribute indicating entity is dead
    """
    
    days_as_ruin: int
    
    def init_ruins(self) -> None:
        """Initialize ruins attributes. Call from __init__."""
        self.days_as_ruin = 0
    
    def get_ruins_duration(self) -> int:
        """Get ruins duration in days. Override for dynamic durations."""
        return getattr(self, 'RUINS_DURATION_DAYS', 50)
    
    def process_ruins(self) -> bool:
        """Process ruins decay. Returns True if should skip further on_dawn processing.
        
        Call this at the start of on_dawn() implementations.
        Returns True if entity is dead (either still decaying or just removed).
        """
        if not self.is_dead:
            return False
        
        self.days_as_ruin += 1
        if self.days_as_ruin >= self.get_ruins_duration():
            self.world.remove_entity(self)
        
        return True  # Skip normal on_dawn processing when dead
