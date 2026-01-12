"""Spirit base class - stationary entities with domain areas."""
from typing import TYPE_CHECKING, List, Tuple
from .base import Entity, Coordinates


if TYPE_CHECKING:
    from .dragon import Dragon


# Shared recovery rates for all spirits
NATURAL_RECOVERY_RATE = 1
TENDED_RECOVERY_RATE = 3


class Spirit(Entity):

    def __init__(
        self,
        type: str,
        coordinates: Coordinates,
        life: int,
        domain_tiles: List[Tuple[int, int]] = None,
    ):
        super().__init__("", "", coordinates, life)
        self.type = type    # forest, water, mountain
        self.max_life = life
        self.attending_dragons: list["Dragon"] = []
        self.domain_tiles = domain_tiles if domain_tiles is not None else []
        self.is_occupied = False
    
    def natural_recovery(self) -> None:
        """Recover life naturally over time."""
        self.life = min(self.max_life, self.life + NATURAL_RECOVERY_RATE)
    
    def get_tended(self) -> None:
        """Recover life when tended by a dragon."""
        self.life = min(self.max_life, self.life + TENDED_RECOVERY_RATE)
    
    def update(self, world) -> None:
        """Update spirit state during timestep."""
        for dragon in self.attending_dragons:
            self.recover_when_tended(dragon)
        
        if not self.attending_dragons:
            self.natural_recovery()
    
    def serialize(self):
        """Serialize spirit to dictionary for JSON output."""
        base = super().serialize()
        base.update({
            "domain_tiles": self.domain_tiles,
            "debug_info": f"{self}"
        })
        return base
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(life={self.life}/{self.max_life})"
