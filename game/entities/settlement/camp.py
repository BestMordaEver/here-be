"""Worker camp settlement."""
from game.entities.base import Coordinates, Visible
from .settlement import Settlement
from typing import List, Tuple, TYPE_CHECKING

from game.entities.spirit import SpiritType
from .extractor import Extractor


if TYPE_CHECKING:
    from game.world import World
    from game.entities.spirit import Spirit

class Camp(Settlement, Extractor):
    """2x2 worker camp made of brown tents."""
    
    def __init__(
            self,
            world: 'World',
            name: str,
            coordinates: Coordinates,
            target_spirit: 'Spirit',
            home: 'Settlement'
        ):
        super().__init__(world, name, coordinates, life=2)
        Extractor.__init__(self, SpiritType.FOREST, SpiritType.MOUNTAIN, SpiritType.LAKE)
        
        self.target_spirit = target_spirit
        self.home = home
        self._last_blessing_day = -1

        self.create_large("default", [
            ((0,0), "Λ", "#8B4513"), ((0,1), "Λ", "#8B4513"),
            ((1,0), "Λ", "#8B4513"), ((1,1), "Λ", "#8B4513")
            ])
        self.visual_state = "default"

    def get_spawn_point(self, destination=None):
        """Spawn caravan on the adjacent tile closest to the destination."""
        x, y = self.coordinates
        # All tiles adjacent to the 2x2 footprint: (x,y)-(x+1,y+1)
        adjacent = [
            (x - 1, y - 1), (x, y - 1), (x + 1, y - 1), (x + 2, y - 1),  # top
            (x - 1, y), (x - 1, y + 1),                                     # left
            (x + 2, y), (x + 2, y + 1),                                     # right
            (x - 1, y + 2), (x, y + 2), (x + 1, y + 2), (x + 2, y + 2),  # bottom
        ]
        # Resolve destination coordinates
        if destination is not None:
            dest = destination.coordinates if not isinstance(destination, tuple) else destination
        else:
            dest = None

        passable = [c for c in adjacent if self._is_field(c)]
        if not passable:
            return None
        if dest is not None:
            passable.sort(key=lambda c: abs(c[0] - dest[0]) + abs(c[1] - dest[1]))
        return passable[0]
    
    def die(self, cause: str) -> None:
        """Handle camp death."""
        # Drop blessings
        if self.blessings > 0:
            from ..blessing import drop_blessing
            drop_blessing(self.world, self.coordinates, self.blessings)
            self.blessings = 0
        
        super().die(cause)
        
        # Free up the occupied spirit
        self.target_spirit.is_occupied = False
    
    def on_dawn(self) -> None:
        """Try to send blessings to parent, then extract from spirits."""
        if self.is_dead:
            return
        
        # Send blessing to parent settlement if we have one
        if self.blessings > 0 and self.home and self.home.is_alive:
            from ..caravan import Caravan, CaravanMission
            
            # Create caravan to deliver blessing
            caravan = Caravan(
                self.world,
                coordinates=self.coordinates,
                home=self.home,
                destination=self.home,
                mission=CaravanMission.DELIVER_BLESSING
            )
            caravan.blessing = True
            self.blessings -= 1
            self.world.add_entity(caravan)
        
        Extractor.on_dawn(self)  # Check for nearby spirits and get blessings
    
    def update(self) -> None:
        """Camps don't need regular updates beyond dawn."""
        pass