"""Mixin for settlement expansion logic."""
from typing import Optional, List, Any, TYPE_CHECKING
from game.entities.spirit import Spirit, SpiritType


if TYPE_CHECKING:
    from game.entities.base import Coordinates
    from game.entities.settlement.settlement import Settlement


# Expansion constants
WOOD_EXTRACTION_RANGE = 6  # Max distance from forest spirit for camp
ORE_EXTRACTION_RANGE = 10  # Max distance from mountain spirit for camp
LAKE_EXTRACTION_RANGE = 10  # Max distance from lake spirit for camp


class Extractor:
    """Mixin providing resource extraction capabilities."""
    
    def __init__(self, *types: SpiritType):
        self.extraction_types = types  # Types of spirits this settlement can extract from
        
        self.nearby_spirits = []
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Spirit' and entity.type in self.extraction_types:
                distance = self.get_distance(entity.coordinates)
                if ((entity.type == SpiritType.FOREST and distance <= WOOD_EXTRACTION_RANGE) or
                    (entity.type == SpiritType.MOUNTAIN and distance <= ORE_EXTRACTION_RANGE) or
                    (entity.type == SpiritType.LAKE and distance <= LAKE_EXTRACTION_RANGE)):
                    self.nearby_spirits.append(entity)

    def has_wood_access(self) -> bool:
        """Check if there are any alive forest spirits nearby."""
        if self.nearby_spirits is None:
            return False
        return any(s.type == SpiritType.FOREST and s.is_alive for s in self.nearby_spirits)
    
    def has_ore_access(self) -> bool:
        """Check if there are any alive mountain spirits nearby."""
        if self.nearby_spirits is None:
            return False
        return any(s.type == SpiritType.MOUNTAIN and s.is_alive for s in self.nearby_spirits)
    
    def has_lake_access(self) -> bool:
        """Check if there are any alive lake spirits nearby."""
        if self.nearby_spirits is None:
            return False
        return any(s.type == SpiritType.LAKE and s.is_alive for s in self.nearby_spirits)
    
    def on_dawn(self) -> None:
        """Extract blessings from nearby spirits."""
        for spirit in self.nearby_spirits:
            if spirit.is_alive and spirit.has_blessing:
                spirit.take_blessing()
                self.blessings += 1
                return

