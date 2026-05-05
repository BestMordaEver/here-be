"""Ruins mixin - dead entities that persist as ruins before removal."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World


class Ruins:
    """Mixin for entities that become ruins after death.
    
    Subclasses must define:
        - is_dead: attribute indicating entity is dead
    
    Ruins store any blessings the entity had when it died, and can be
    pillaged by heroes and bandits to retrieve those blessings.
    """
    
    days_as_ruin: int
    ruins_duration: int
    
    def __init__(self, ruins_duration: int) -> None:
        self.days_as_ruin = 0
        self.ruins_duration = ruins_duration
    
    def get_ruins_duration(self) -> int:
        """Get ruins duration in days. Override for dynamic durations."""
        return self.ruins_duration
    
    def process_ruins(self) -> bool:
        """Process ruins decay. Returns True if should skip further on_dawn processing.
        
        Call this at the start of on_dawn() implementations.
        Returns True if entity is dead (either still decaying or just removed).
        """
        if not self.is_dead:
            return False
        
        self.days_as_ruin += 1
        
        # Spawn bandits after 2 days (only villages and cities, not camps/spires)
        if self.days_as_ruin == 2:
            if self.__class__.__name__ in ('Village', 'City'):
                from game.entities import Bandit
                bandit = Bandit(self.world, self.coordinates)
                self.world.add_entity(bandit)
        
        if self.days_as_ruin >= self.get_ruins_duration():
            self.world.remove_entity(self)
        
        return True  # Skip normal on_dawn processing when dead

    def can_be_pillaged(self) -> bool:
        """Check if these ruins have anything to pillage."""
        return self.is_dead and self.blessings > 0
