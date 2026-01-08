"""City settlement."""
from entities.base.settlement import Settlement
from entities.base.entity import Coordinates
from typing import List, Tuple


class City(Settlement):
    """5x5 city with walls, gates, buildings, and roads."""
    
    def __init__(self, name: str, coordinates: Coordinates):
        super().__init__(name, coordinates, life=1000, settlement_type="city")
        
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return all 5x5 tiles for the city.
        Layout (coordinates at city square Ѻ):
        #═══#
        ║ѦЋЋ║
        ║֏ѺЋ║
        ║Ҵ║Ҵ║
        #₸₳₸#
        """
        x, y = self.coordinates  # City square position
        
        if self.is_dead:
            # Depleted city: buildings grey, city square green, walls slightly green
            return [
                # Row 0
                ((x - 2, y - 2), "#", "#90A090"),          # Wall (slightly green)
                ((x - 1, y - 2), "═", "#90A090"),      # Wall
                ((x, y - 2), "═", "#90A090"),      # Wall
                ((x + 1, y - 2), "═", "#90A090"),      # Wall
                ((x + 2, y - 2), "#", "#90A090"),      # Wall
                
                # Row 1
                ((x - 2, y - 1), "║", "#90A090"),      # Wall
                ((x - 1, y - 1), "Ѧ", "#808080"),  # Building (grey)
                ((x, y - 1), "Ћ", "#808080"),  # Building
                ((x + 1, y - 1), "Ћ", "#808080"),  # Building
                ((x + 2, y - 1), "║", "#90A090"),  # Wall
                
                # Row 2
                ((x - 2, y), "║", "#90A090"),      # Wall
                ((x - 1, y), "֏", "#808080"),  # Building
                ((x, y), "Ѻ", "#228B22"),  # City square (green)
                ((x + 1, y), "Ћ", "#808080"),  # Building
                ((x + 2, y), "║", "#90A090"),  # Wall
                
                # Row 3
                ((x - 2, y + 1), "║", "#90A090"),      # Wall
                ((x - 1, y + 1), "Ҵ", "#808080"),  # Building
                ((x, y + 1), "║", "#345F12"),  # Main road (overgrown green)
                ((x + 1, y + 1), "Ҵ", "#808080"),  # Building
                ((x + 2, y + 1), "║", "#90A090"),  # Wall
                
                # Row 4
                ((x - 2, y + 2), "#", "#90A090"),      # Wall
                ((x - 1, y + 2), "₸", "#808080"),  # Gate (grey)
                ((x, y + 2), "₳", "#808080"),  # Gate
                ((x + 1, y + 2), "₸", "#808080"),  # Gate
                ((x + 2, y + 2), "#", "#90A090"),  # Wall
            ]
        else:
            # Normal city
            return [
                # Row 0
                ((x - 2, y - 2), "#", "#808080"),          # Wall (grey)
                ((x - 1, y - 2), "═", "#808080"),      # Wall
                ((x, y - 2), "═", "#808080"),      # Wall
                ((x + 1, y - 2), "═", "#808080"),      # Wall
                ((x + 2, y - 2), "#", "#808080"),      # Wall
                
                # Row 1
                ((x - 2, y - 1), "║", "#808080"),      # Wall
                ((x - 1, y - 1), "Ѧ", "#B22222"),  # Building (brick)
                ((x, y - 1), "Ћ", "#B22222"),  # Building
                ((x + 1, y - 1), "Ћ", "#B22222"),  # Building
                ((x + 2, y - 1), "║", "#808080"),  # Wall
                
                # Row 2
                ((x - 2, y), "║", "#808080"),      # Wall
                ((x - 1, y), "֏", "#B22222"),  # Building
                ((x, y), "Ѻ", "#808080"),  # City square (grey)
                ((x + 1, y), "Ћ", "#B22222"),  # Building
                ((x + 2, y), "║", "#808080"),  # Wall
                
                # Row 3
                ((x - 2, y + 1), "║", "#808080"),      # Wall
                ((x - 1, y + 1), "Ҵ", "#B22222"),  # Building
                ((x, y + 1), "║", "#8B4513"),  # Main road (grey)
                ((x + 1, y + 1), "Ҵ", "#B22222"),  # Building
                ((x + 2, y + 1), "║", "#808080"),  # Wall
                
                # Row 4
                ((x - 2, y + 2), "#", "#808080"),      # Wall
                ((x - 1, y + 2), "₸", "#808080"),  # Gate (grey)
                ((x, y + 2), "₳", "#808080"),  # Gate
                ((x + 1, y + 2), "₸", "#808080"),  # Gate
                ((x + 2, y + 2), "#", "#808080"),  # Wall
            ]
