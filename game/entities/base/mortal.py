"""Mortal mixin - entities that auto-cleanup when dead."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World


class Mortal:
    """Mixin for entities that should be automatically removed from world when dead."""
    
    def update(self, world: 'World') -> None:
        """Check if dead and auto-cleanup before normal update."""
        # Check is_dead attribute (assumes Entity base class)
        if hasattr(self, 'is_dead') and self.is_dead:
            world.remove_entity(self)
            return
        
        # Call parent update
        super().update(world)
