"""Aging mixin - entities that age and die of old age."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World


class Aging:
    """Mixin for entities that age and eventually die of old age.
    
    Subclasses must define:
        - die(world, reason): method to handle death
    
    Optionally override:
        - on_old_age_death(world): called before die() for cleanup (e.g., clearing drops)
    """

    age_days: int
    lifespan: int
    
    def __init__(self, lifespan: int) -> None:
        self.age_days = 0
        self.lifespan = lifespan
    
    def get_lifespan(self) -> int:
        """Get lifespan in days. Override for dynamic lifespans."""
        return self.lifespan
    
    def on_old_age_death(self) -> None:
        """Called before dying of old age. Override to clear drops, etc."""
        pass
    
    def process_aging(self) -> bool:
        """Increment age and check for death. Returns True if died.
        
        Call this at the start of on_dawn() implementations.
        """
        self.age_days += 1
        
        if self.age_days >= self.get_lifespan():
            self.on_old_age_death()
            self.die("old age")
            return True
        
        return False
