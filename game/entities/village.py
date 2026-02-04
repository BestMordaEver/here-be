"""Village settlement."""
from .base import Coordinates, Named, Settlement, ExpansionMixin, Ruins
from .base.settlement_events import SettlementEventsMixin
from typing import List, Tuple, TYPE_CHECKING


if TYPE_CHECKING:
    from . import City, Camp, Caravan
    from game.world import World


# Village constants
LAKE_BLESSING_RADIUS = 10  # Max distance to extract blessing from lake spirit

# Village init constants
STARTING_LIFE = 3  # Village starting HP


class Village(Settlement, ExpansionMixin, Named, SettlementEventsMixin, Ruins):
    """3x3 village with fields, homes, and city square."""
    
    RUINS_DURATION_DAYS = 50  # Days before ruins disappear
    
    def __init__(self, world: 'World', name: str, coordinates: Coordinates):
        super().__init__(world, coordinates, life=STARTING_LIFE)
        Named.__init__(self, name)
        SettlementEventsMixin.__init__(self)
        self.init_ruins()
        
        # Expansion tracking
        self.subsidiary_camps: List['Camp | Caravan'] = []
        
        # Lake spirit blessing tracking
        self._nearby_lake_spirits = None  # Cached list (lazy init)
        self._last_blessing_day = -1

    def on_dawn(self) -> None:
        """Handle dawn event - process daily settlement event and try to get blessing."""
        if self.process_ruins():
            return
        
        self.process_daily_event()
        
        # Try to extract a blessing from a nearby lake spirit (once per day)
        current_day = self.world.time.current_day
        if current_day != self._last_blessing_day:
            # Lazy init nearby lake spirits cache
            if self._nearby_lake_spirits is None:
                self._nearby_lake_spirits = []
                for entity in self.world.entities:
                    if entity.__class__.__name__ == 'Spirit' and entity.type == 'water':
                        if self.get_distance(entity.coordinates) <= LAKE_BLESSING_RADIUS:
                            self._nearby_lake_spirits.append(entity)
            
            # Try to get blessing from nearest lake spirit with one available
            for spirit in self._nearby_lake_spirits:
                if spirit.is_alive and spirit.has_blessing:
                    spirit.take_blessing()
                    self.blessings += 1
                    self._last_blessing_day = current_day
                    self.think(f"Received blessing from the lake spirit.")
                    break

    def get_max_camps(self) -> int:
        return 4  # Villages can have up to 4 camps (1 forest + 1 mountain + 2 any)

    def get_prioritized_resource(self) -> str:
        return 'forest'  # Villages prioritize forest camps

    def get_prioritized_resource_count(self) -> int:
        return 2
        
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return all 3x3 tiles for the village.
        Layout (coordinates at city square ¤):
        #⌂#
        ⌂¤⌂
        #₼#
        """
        x, y = self.coordinates  # City square position
        
        if self.is_dead:
            # Depleted village: loses fields (corners become empty), houses become dark grey
            return [
                # Corners (former fields) are now empty - no tiles
                ((x, y - 1), "⌂", "#505050"),  # Top home (dark grey)
                
                ((x - 1, y), "⌂", "#505050"),      # Middle left home
                ((x, y), "¤", "#808080"),  # City square (grey)
                ((x + 1, y), "⌂", "#505050"),  # Middle right home
                
                ((x, y + 1), "₼", "#808080"),  # Gate (grey)
            ]
        else:
            # Normal village
            return [
                ((x - 1, y - 1), "#", "#FFD700"),      # Top left field (yellow)
                ((x, y - 1), "⌂", "#8B4513"),  # Top home (brown)
                ((x + 1, y - 1), "#", "#FFD700"),  # Top right field
                
                ((x - 1, y), "⌂", "#8B4513"),      # Middle left home
                ((x, y), "¤", "#808080"),  # City square (grey)
                ((x + 1, y), "⌂", "#8B4513"),  # Middle right home
                
                ((x - 1, y + 1), "#", "#FFD700"),      # Bottom left field
                ((x, y + 1), "₼", "#808080"),  # Gate (grey)
                ((x + 1, y + 1), "#", "#FFD700"),  # Bottom right field
            ]
