"""Spirit base class - stationary entities with domain areas."""
from typing import TYPE_CHECKING, List, Tuple, Optional
from enum import Enum
from .base import Entity, Coordinates, Pockets
from .base.engaging import EngagementType, Engagement


if TYPE_CHECKING:
    from .dragon import Dragon
    from game.world import World


class SpiritType(Enum):
    FOREST = 'forest'
    LAKE = 'lake'
    MOUNTAIN = 'mountain'


class Spirit(Entity, Pockets):
    """Spirits are stationary entities representing natural domains. 
    Domain size is fixed by tileset. Tending by dragons creates blessings."""

    def __init__(
        self,
        world: 'World',
        type: SpiritType,
        coordinates: Coordinates,
        domain_tiles: List[Tuple[int, int]] = None,
    ):
        super().__init__(world, coordinates)
        Pockets.__init__(self, max_blessings=1)
        self.type = type    # forest, lake, mountain
        self.domain_tiles = domain_tiles if domain_tiles is not None else []
        self.is_occupied = False  # Whether a camp is on this spirit
    
    @property
    def has_blessing(self) -> bool:
        """Whether this spirit currently holds a blessing."""
        return self.has_blessings
    
    def get_tended(self) -> bool:
        """When tended by a dragon, create a blessing if none exists.
        Returns True if a blessing was created."""
        if not self.has_blessing:
            self.store_blessing(1)
            return True
        return False
    
    def take_blessing(self) -> bool:
        """Take the blessing from this spirit.
        Returns True if a blessing was taken."""
        if self.has_blessing:
            self.empty_blessings()
            return True
        return False
    
    def update(self) -> None:
        """Update spirit state during timestep."""
        pass  # Spirits are passive

    def resolve_engagement(self) -> Optional[Engagement]:
        """Spirits generate a blessing when tended by a dragon."""
        engagement = self.current_engagement
        self.current_engagement = None
        if not engagement:
            return engagement

        if engagement.engagement_type == EngagementType.TENDING:
            self.get_tended()

        return engagement
    
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
