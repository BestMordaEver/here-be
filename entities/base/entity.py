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
        self.is_alive = True
        self.is_dead = False
    
    def update(self, world) -> None:
        raise NotImplementedError("Subclasses must implement update()")
    
    def hurt(self, damage: int) -> None:
        self.life -= damage
        if self.life <= 0:
            self.die()
    
    def heal(self, amount: int) -> None:
        self.life += amount

    def die(self, world) -> None:
        self.is_dead = True
        self.is_alive = False
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize entity to dictionary for JSON output."""
        return {
            "color": self.color,
            "character": self.character,
            "coordinates": list(self.coordinates),
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(life={self.life})"
