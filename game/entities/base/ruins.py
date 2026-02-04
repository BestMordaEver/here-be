"""Ruins mixin - dead entities that persist as ruins before removal."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World


class Ruins:
    """Mixin for entities that become ruins after death.
    
    Subclasses must define:
        - RUINS_DURATION_DAYS: class constant for days before removal
        - is_dead: attribute indicating entity is dead
    
    Ruins store any blessings the entity had when it died, and can be
    pillaged by heroes and bandits to retrieve those blessings.
    """
    
    days_as_ruin: int
    ruin_blessings: int
    
    def init_ruins(self) -> None:
        """Initialize ruins attributes. Call from __init__."""
        self.days_as_ruin = 0
        self.ruin_blessings = 0  # Blessings held in ruins
    
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
        
        # Spawn bandits after 2 days (only villages and cities, not camps/spires)
        if self.days_as_ruin == 2:
            self._try_spawn_ruin_bandit()
        
        if self.days_as_ruin >= self.get_ruins_duration():
            self.world.remove_entity(self)
        
        return True  # Skip normal on_dawn processing when dead
    
    def _try_spawn_ruin_bandit(self) -> None:
        """Spawn a bandit pack from the ruins. Only villages and cities spawn bandits."""
        entity_type = self.__class__.__name__
        if entity_type not in ('Village', 'City'):
            return
        
        from game.entities import Bandit
        
        # Spawn bandit at ruins location
        bandit = Bandit(self.world, self.coordinates)
        self.world.add_entity(bandit)
    
    def on_become_ruins(self) -> None:
        """Called when entity becomes ruins. Stores blessings for pillaging.
        
        Call this from die() after setting is_dead = True.
        """
        # Store any blessings the entity had
        if hasattr(self, 'blessings'):
            self.ruin_blessings = self.blessings
            self.blessings = 0
    
    def pillage_ruins(self, amount: int) -> int:
        """Take blessings from these ruins.
        
        Args:
            amount: Maximum blessings to take
            
        Returns:
            Actual number of blessings taken
        """
        taken = min(amount, self.ruin_blessings)
        self.ruin_blessings -= taken
        return taken
    
    def can_be_pillaged(self) -> bool:
        """Check if these ruins have anything to pillage."""
        return self.is_dead and self.ruin_blessings > 0
