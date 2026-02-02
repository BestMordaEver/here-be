"""Spirit base class - stationary entities with domain areas."""
from typing import TYPE_CHECKING, List, Tuple
from .base import Entity, Coordinates


if TYPE_CHECKING:
    from .dragon import Dragon


class Spirit(Entity):
    """Spirits are stationary entities representing natural domains. 
    Domain size is fixed by tileset. Tending by dragons creates blessings."""

    def __init__(
        self,
        type: str,
        coordinates: Coordinates,
        domain_tiles: List[Tuple[int, int]] = None,
    ):
        super().__init__("", "", coordinates)
        self.type = type    # forest, water, mountain
        self.domain_tiles = domain_tiles if domain_tiles is not None else []
        self.is_occupied = False  # Whether a camp is on this spirit
        self.has_blessing = False  # Spirits can store only one blessing
    
    def get_tended(self) -> bool:
        """When tended by a dragon, create a blessing if none exists.
        Returns True if a blessing was created."""
        if not self.has_blessing:
            self.has_blessing = True
            return True
        return False
    
    def take_blessing(self) -> bool:
        """Take the blessing from this spirit.
        Returns True if a blessing was taken."""
        if self.has_blessing:
            self.has_blessing = False
            return True
        return False
    
    def update(self, world) -> None:
        """Update spirit state during timestep."""
        pass  # Spirits are passive
    
    def serialize(self):
        """Serialize spirit to dictionary for JSON output."""
        base = super().serialize()
        base.update({
            "type": self.type,
            "domain_tiles": self.domain_tiles,
            "has_blessing": self.has_blessing,
            "debug_info": f"{self}"
        })
        return base
    
    def __repr__(self) -> str:
        return f"Spirit({self.type}, tiles={len(self.domain_tiles)}, blessing={self.has_blessing})"
