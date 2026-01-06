"""Spirit base class - stationary entities with domain areas."""
from typing import TYPE_CHECKING
from entities.base.entity import Entity, Coordinates


if TYPE_CHECKING:
    from entities.dragon import Dragon


# Shared recovery rates for all spirits
NATURAL_RECOVERY_RATE = 1
TENDED_RECOVERY_RATE = 3


class Spirit(Entity):

    def __init__(
        self,
        type: str,
        coordinates: Coordinates,
        life: int,
        domain_area: int,
    ):
        super().__init__("", "", coordinates, life)
        self.type = type    # forest, water, mountain
        self.domain_area = domain_area
        self.max_life = life
        self.attending_dragons: list["Dragon"] = []
    
    def life_depletion_on_use(self, amount: int) -> None:
        """Deplete life when the spirit is used/exploited."""
        self.life = max(0, self.life - amount)
        self._update_domain_area()
    
    def natural_recovery(self) -> None:
        """Recover life naturally over time."""
        self.life = min(self.max_life, self.life + NATURAL_RECOVERY_RATE)
        self._update_domain_area()
    
    def get_tended(self) -> None:
        """Recover life when tended by a dragon."""
        self.life = min(self.max_life, self.life + TENDED_RECOVERY_RATE)
        self._update_domain_area()
    
    def _update_domain_area(self) -> None:
        """Update domain area based on current life (scales with life)."""
        if self.max_life > 0:
            self.domain_area = max(1, int(self.domain_area * (self.life / self.max_life)))
    
    def update(self, world) -> None:
        """Update spirit state during timestep."""
        for dragon in self.attending_dragons:
            self.recover_when_tended(dragon)
        
        if not self.attending_dragons:
            self.natural_recovery()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(life={self.life}/{self.max_life}, domain={self.domain_area})"
