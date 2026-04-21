"""Village settlement."""
from typing import List, Tuple, TYPE_CHECKING
from game.entities.base import Coordinates, Named
from game.entities.spirit import SpiritType
from .settlement import Settlement
from .ruins import Ruins
from .expansion import Expansion
from .extractor import Extractor


if TYPE_CHECKING:
    from .. import City, Camp, Caravan
    from game.world import World


# Village constants
LAKE_BLESSING_RADIUS = 10  # Max distance to extract blessing from lake spirit
RUINS_DURATION_DAYS = 50

# Village init constants
STARTING_LIFE = 3  # Village starting HP


class Village(Settlement, Expansion, Ruins):
    """3x3 village with fields, homes, and city square."""
    
    def __init__(self, world: 'World', name: str, coordinates: Coordinates):
        super().__init__(world, name, coordinates, life=STARTING_LIFE)
        Ruins.__init__(self, ruins_duration=RUINS_DURATION_DAYS)
        Extractor.__init__(self, SpiritType.LAKE)

        self.create_large("default", [
            ((-1,-1), "#", "#FFD700"),      # Top left field (yellow)
            ((0,-1), "⌂", "#8B4513"),  # Top home (brown)
            ((1,-1), "#", "#FFD700"),  # Top right field
            
            ((-1,0), "⌂", "#8B4513"),      # Middle left home
            ((0,0), "¤", "#808080"),  # City square (grey)
            ((1,0), "⌂", "#8B4513"),  # Middle right home
            
            ((-1,1), "#", "#FFD700"),      # Bottom left field
            ((0,1), "₼", "#808080"),  # Gate (grey)
            ((1,1), "#", "#FFD700"),  # Bottom right field
        ])

        self.visual_state = "default"

        self.create_large("ruins", [
            # Corners (former fields) are now empty - no tiles
            ((0,-1), "⌂", "#505050"),  # Top home (dark grey)
            
            ((-1,0), "⌂", "#505050"),      # Middle left home
            ((0,0), "¤", "#808080"),  # City square (grey)
            ((1,0), "⌂", "#505050"),  # Middle right home
            
            ((0,1), "₼", "#808080"),  # Gate (grey)
        ])

        self.is_village = True
        self.got_blessing_yesterday = False
        self.has_village_hero = False  # Track if village hero has been spawned
        self.subsidiary_camps: List['Camp | Caravan'] = []

    def get_max_camps(self) -> int:
        return 4  # Villages can have up to 4 camps (1 forest + 3 any). Lake camp is not counted against this limit.

    def get_prioritized_resource(self) -> SpiritType:
        return SpiritType.FOREST  # Villages prioritize forest camps

    def get_prioritized_resource_count(self) -> int:
        return 1

    def get_spawn_point(self, destination=None):
        """Spawn entity just outside the south gate (y+2 from center)."""
        x, y = self.coordinates
        # Prefer center gate exit, then left/right
        for dx in [0, -1, 1]:
            candidate = (x + dx, y + 2)
            if self._is_field(candidate):
                return candidate
        # Fallback: try one row further south
        for dx in range(-1, 2):
            candidate = (x + dx, y + 3)
            if self._is_field(candidate):
                return candidate
        return None
        
    def on_dawn(self) -> None:
        """Handle dawn event - build schedule and try to get blessing."""
        self.subsidiary_camps = [c for c in self.subsidiary_camps if c.is_alive]
        self.prune_stale_memories(self.world.time.current_day)

        if self.process_ruins():
            return
        
        self.build_schedule()
        
        Extractor.on_dawn(self)  # Check for nearby spirits and get blessings