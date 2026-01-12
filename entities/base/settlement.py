"""Base settlement class for all settlement types."""
from entities.base.entity import Entity, Coordinates
from entities.base.expansion import ExpansionMixin
from entities.base.thinking import Thinking
from typing import Dict, Any, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from world import World


class Settlement(Entity, Thinking):
    """Base class for all settlement types."""
    
    def __init__(
        self,
        coordinates: Coordinates,
        life: int,
        color: str = "",
        character: str = "",
    ):
        Entity.__init__(self, color, character, coordinates, life)
        Thinking.__init__(self)
        
        # Resource storage
        self.resources = {
            'food': 0,
            'wood': 0,
            'ores': 0,
            'treasure': 0
        }
        
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return list of (coordinates, symbol, color) for all tiles in settlement."""
        raise NotImplementedError
    
    def occupies(self, coordinates: Coordinates) -> bool:
        """Check if this settlement occupies the given coordinates."""
        tiles = self.get_tiles()
        for tile_coords, _, _ in tiles:
            if tile_coords == coordinates:
                return True
        return False
    
    def die(self, world, reason) -> None:
        """Handle settlement death/depletion."""
        super().die(world, reason)
    
    def add_resource(self, resource_type: str, amount: int) -> int:
        """Add resources to storage. Returns amount actually added (capped by storage)."""
        if resource_type not in self.resources:
            return 0
        
        current = self.resources[resource_type]
        max_add = self.storage_capacity - current
        actual_add = min(amount, max_add)
        self.resources[resource_type] = current + actual_add
        return actual_add
    
    def remove_resource(self, resource_type: str, amount: int) -> int:
        """Remove resources from storage. Returns amount actually removed."""
        if resource_type not in self.resources:
            return 0
        
        current = self.resources[resource_type]
        actual_remove = min(amount, current)
        self.resources[resource_type] = current - actual_remove
        return actual_remove
    
    def generate_resources(self, world) -> None:
        """Generate resources based on settlement type. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement generate_resources()")
    
    def consume_resources(self) -> str:
        """Consume resources each cycle. Returns death reason if critical resources missing.
        Override in subclasses to define specific consumption needs."""
        raise NotImplementedError("Subclasses must implement consume_resources()")
    
    def update(self, world) -> None:
        # Generate resources each cycle
        self.generate_resources(world)
        # Consume resources each cycle
        self.consume_resources(world)
        
        if issubclass(type(self), ExpansionMixin) and self.is_alive:
            # Attempt settlement expansion
            self.expand_settlement(world)

    def serialize(self) -> Dict[str, Any]:
        """Serialize settlement to dictionary for JSON output."""
        data = super().serialize()
        data["tiles"] = self.get_tiles()
        data["debug_info"] = f"{self.name if hasattr(self, 'name') else 'Camp'} {self.coordinates} {self.resources}"
        return data
