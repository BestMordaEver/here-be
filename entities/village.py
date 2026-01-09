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
    
    def generate_resources(self, world) -> None:
        """Generate food resources each cycle.
        - Base: 3 food
        - +3 food for each cattle within 10 tiles
        - +1 food for each water tile in a spirit's domain within 10 tiles
        """
        if self.is_dead:
            return
        
        food_generated = 3  # Base food generation
        
        x, y = self.coordinates
        
        # Check for cattle within 10 tiles (Manhattan distance)
        for entity in world.entities:
            if hasattr(entity, '__class__') and entity.__class__.__name__ == 'Cattle':
                ex, ey = entity.coordinates
                distance = abs(x - ex) + abs(y - ey)
                if distance <= 10:
                    food_generated += 3
        
        # Check for water tiles within spirit domains within 10 tiles
        for entity in world.entities:
            if hasattr(entity, '__class__') and entity.__class__.__name__ == 'Spirit':
                if entity.type == 'water' and hasattr(entity, 'domain_tiles'):
                    # Count water tiles in spirit domain that are within 10 tiles
                    for tile_x, tile_y in entity.domain_tiles:
                        distance = abs(x - tile_x) + abs(y - tile_y)
                        if distance <= 10:
                            food_generated += 1
        
        # Add generated food to storage (capped by capacity)
        self.add_resource('food', food_generated)
