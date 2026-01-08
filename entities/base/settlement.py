"""Base settlement class for all settlement types."""
from entities.base.entity import Entity, Coordinates
from entities.base.named import Named
from entities.base.thinking import Thinking
from typing import Dict, Any, List, Tuple


class Settlement(Entity, Named, Thinking):
    """Base class for all settlement types."""
    
    def __init__(
        self,
        name: str,
        coordinates: Coordinates,
        life: int,
        settlement_type: str,
    ):
        Entity.__init__(self, "#808080", "₼", coordinates, life)
        Named.__init__(self, name)
        Thinking.__init__(self)
        self.settlement_type = settlement_type
        
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
    
    def update(self, world) -> None:
        if self.life <= 0 and self.is_alive:
            self.die(world)

    def serialize(self) -> Dict[str, Any]:
        """Serialize settlement to dictionary for JSON output."""
        data = super().serialize()
        data["name"] = self.name
        data["settlement_type"] = self.settlement_type
        data["depleted"] = self.is_dead
        data["tiles"] = self.get_tiles()
        data["debug_info"] = f"{self.name} ({self.settlement_type}) at {self.coordinates}"
        return data
