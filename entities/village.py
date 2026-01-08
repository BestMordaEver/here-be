"""Village settlement."""
from entities.base.settlement import Settlement
from entities.base.entity import Coordinates
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from entities.city import City


class Village(Settlement):
    """3x3 village with fields, homes, and city square."""
    
    def __init__(self, name: str, coordinates: Coordinates):
        super().__init__(name, coordinates, life=500, settlement_type="village")
        
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
    
    def promote_to_city(self) -> 'City':
        """Promote this village to a city."""
        from entities.city import City
        city = City(self.name, self.coordinates)
        city.life = self.life
        return city
