"""Visible entity mixin - for entities with visual representation."""
from dataclasses import dataclass
from typing import Tuple, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .entity import Coordinates

@dataclass
class VisualTile:
    """Represents a single tile of an entity's visual representation."""
    offset: Tuple[int, int]  # (dx, dy) from entity coordinates
    character: str            # Character to display
    color: str                # Color name or code

class Visible:
    """ Mixin for entities that have a visual representation in the game. """

    def __init__(self):
        self.states: Dict[str, list[VisualTile]] = {}
        self.visual_state: str = None

    """Create a visual state representation for a small entity."""
    def create_small(
        self,
        state_name: str,
        color: str,
        character: str,
    ):
        self.states[state_name] = [VisualTile((0,0), character, color)]
        
    """Create a visual state representation for a large entity."""
    def create_large(
        self,
        state_name: str,
        tiles: list,
    ):
        self.states[state_name] = [
            t if isinstance(t, VisualTile) else VisualTile(t[0], t[1], t[2])
            for t in tiles
        ]
    
    def get_visual(self) -> Dict[str, list[VisualTile]]:
        """Get visual representation based on current state."""
        return [(
            (tile.offset[0] + self.coordinates[0], tile.offset[1] + self.coordinates[1]),
            tile.character,
            tile.color
        ) for tile in self.states[self.visual_state]]
        