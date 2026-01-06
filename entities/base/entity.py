"""Base entity class for all game entities."""
from typing import Tuple, Dict, Any


Coordinates = Tuple[int, int]


class Entity:

    def __init__(
        self,
        color: str,
        character: str,
        coordinates: Coordinates,
        life: int,
    ):
        self.color = color
        self.character = character
        self.coordinates = coordinates
        self.life = life
    
    def update(self, world) -> None:
        raise NotImplementedError("Subclasses must implement update()")
    
    def die(self, world) -> None:
        raise NotImplementedError("Subclasses must implement die()")
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize entity to dictionary for JSON output."""
        return {
            "type": self.__class__.__name__,
            "color": self.color,
            "character": self.character,
            "coordinates": list(self.coordinates),
            "life": self.life,
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(life={self.life})"
