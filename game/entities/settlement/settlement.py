"""Base settlement class for all settlement types."""
from ..base.named import Named
from ..base.entity import Entity, Coordinates
from ..base.thinking import Thinking
from ..base.scheduled import Scheduled
from ..base.visible import Visible
from game.world.types import Biome
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World
    from game.entities import Caravan


class Settlement(Entity, Named, Thinking, Scheduled, Visible):
    """Base class for all settlement types. Includes health/life management."""
    
    def __init__(
        self,
        world: 'World',
        name: str,
        coordinates: Coordinates,
        life: int,
    ):
        Entity.__init__(self, world, coordinates)
        Named.__init__(self, name)
        Thinking.__init__(self)
        Scheduled.__init__(self)
        Visible.__init__(self)
        
        # Health system for settlements
        self.max_life = life
        self.life = life

        # Event tracking
        self.days_since_market = 0
        self.days_since_celebration = 0
        
        # Blessing system - only resource that matters
        self.blessings = 0
    
    def hurt(self, damage: int, source: str) -> None:
        """Inflict damage to the settlement."""
        self.life -= damage
        if self.life <= 0:
            self.die(source)
    
    def heal(self, amount: int) -> None:
        """Heal the settlement, not exceeding max life."""
        self.life = min(self.max_life, self.life + amount)
        
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
    
    def _is_field(self, coordinates: Coordinates) -> bool:
        """Check if a tile is passable field terrain for caravans."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= self.world.WIDTH or y >= self.world.HEIGHT:
            return False
        height = self.world.height_map[y][x]
        return self.world.get_biome_from_height(height) == Biome.FIELD

    def get_spawn_point(self, destination=None) -> Optional[Coordinates]:
        """Find a valid spawn point for an entity outside the settlement.
        Must be overridden by subclasses to define specific spawn logic based on settlement layout.
        """
        raise NotImplementedError

    def send_caravan(self, destination, mission, target_spirit=None) -> 'Caravan':
        """Unified method to create and send a caravan.
        Args:
            destination: Settlement or Coordinates to send caravan to
            mission: CaravanMission enum value
            target_spirit: Spirit for camp settlement missions
        Returns: The created Caravan entity
        """
        from game.entities import Caravan
        
        spawn = self.get_spawn_point(destination)
        if spawn is None:
            spawn = self.coordinates  # Last resort fallback
        
        caravan = Caravan(
            self.world,
            coordinates=spawn,
            home=self,
            destination=destination,
            mission=mission,
            target_spirit=target_spirit
        )
        
        self.world.add_entity(caravan)
        return caravan
    
    def update(self) -> None:
        pass

    def serialize(self) -> Dict[str, Any]:
        """Serialize settlement to dictionary for JSON output."""
        data = super().serialize()
        data["tiles"] = self.get_tiles()
        data["debug_info"] = f"{self.name} {self.coordinates} blessings={self.blessings}"
        return data
