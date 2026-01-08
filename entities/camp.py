"""Worker camp settlement."""
from entities.base.settlement import Settlement
from entities.base.entity import Coordinates
from typing import List, Tuple


class Camp(Settlement):
    """2x2 worker camp made of brown diamonds."""
    
    def __init__(self, name: str, coordinates: Coordinates):
        super().__init__(name, coordinates, life=200, settlement_type="worker_camp")
    
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return all 2x2 tiles for the worker camp."""
        if self.is_dead:
            return []  # Worker camp disappears when depleted
        
        x, y = self.coordinates
        tiles = []
        for dy in [0, 1]:
            for dx in [0, 1]:
                tiles.append(((x + dx, y + dy), "Λ", "#8B4513"))
        return tiles
