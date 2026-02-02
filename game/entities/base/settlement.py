"""Base settlement class for all settlement types."""
from .entity import Entity, Coordinates
from .thinking import Thinking
from typing import Dict, Any, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World
    from game.entities import Caravan


class Settlement(Entity, Thinking):
    """Base class for all settlement types. Includes health/life management."""
    
    def __init__(
        self,
        world: 'World',
        coordinates: Coordinates,
        life: int,
        color: str = "",
        character: str = "",
    ):
        Entity.__init__(self, world, color, character, coordinates)
        Thinking.__init__(self)
        
        # Health system for settlements
        self.max_life = life
        self.life = life
        
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
    
    def die(self, reason) -> None:
        """Handle settlement death/depletion."""
        super().die(reason)
    
    def send_caravan(self, destination, mission, target_spirit=None) -> 'Caravan':
        """Unified method to create and send a caravan.
        Args:
            destination: Settlement or Coordinates to send caravan to
            mission: CaravanMission enum value
            target_spirit: Spirit for camp settlement missions
        Returns: The created Caravan entity
        """
        from game.entities import Caravan
        from game.entities.caravan import CaravanMission
        
        # Create caravan at settlement's southern gate
        caravan = Caravan(
            world,
            coordinates=(self.coordinates[0], self.coordinates[1] + 2),
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
        data["debug_info"] = f"{self.name if hasattr(self, 'name') else 'Camp'} {self.coordinates} blessings={self.blessings}"
        return data
