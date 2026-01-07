from entities.base.entity import Entity, Coordinates
from entities.base.named import Named
from entities.base.thinking import Thinking
from typing import Dict, Any


class Settlement(Entity, Named, Thinking):

    def __init__(
        self,
        name: str,
        coordinates: Coordinates,
    ):
        Entity.__init__(self, "#4e2a00", "₼", coordinates, 1000)
        Named.__init__(self, name)
        Thinking.__init__(self)

    def update(self, world) -> None:
        pass

    def serialize(self) -> Dict[str, Any]:
        """Serialize settlement to dictionary for JSON output."""
        data = super().serialize()
        data["name"] = self.name
        data["debug_info"] = f"{self.name} at {self.coordinates}"
        return data
