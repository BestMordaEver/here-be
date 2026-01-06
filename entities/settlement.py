from entities.base.entity import Entity, Coordinates
from entities.base.named import Named
from entities.base.thinking import Thinking
from typing import Dict, Any


class Settlement(Entity, Named, Thinking):

    def __init__(
        self,
        name: str,
        color: str,
        character: str,
        coordinates: Coordinates,
        life: int,
    ):
        Entity.__init__(self, color, character, coordinates, life)
        Named.__init__(self, name)
        Thinking.__init__(self)

    def update(self, world) -> None:
        pass

    def serialize(self) -> Dict[str, Any]:
        """Serialize settlement to dictionary for JSON output."""
        data = super().serialize()
        data["name"] = self.name
        return data
