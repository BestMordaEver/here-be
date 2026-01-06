from typing import TYPE_CHECKING, Dict, Any
from entities.base.mobile import Mobile
from entities.base.entity import Coordinates
from entities.base.named import Named
from entities.base.thinking import Thinking


if TYPE_CHECKING:
    from entities.spirit import Spirit


class Dragon(Mobile, Named, Thinking):

    def __init__(
        self,
        name: str,
        properties: list[str],
        coordinates: Coordinates,
    ):
        if "serpent" in properties:
            char = '$'
            self.type = "serpent"
        elif "brute" in properties:
            char = "&"
            self.type = "brute"
        elif "blade" in properties:
            char = '%'
            self.type = "blade"
        
        if "aquatic" in properties:
            color = "#004080"
            self.domain = "aquatic"
        elif "mountain" in properties:
            color = "#808080"
            self.domain = "mountain"
        elif "verdant" in properties:
            color = "#008000"
            self.domain = "verdant"
        elif "flame" in properties:
            color = "#800000"
            self.domain = "flame"


        Mobile.__init__(self, color, char, coordinates, 500)
        Named.__init__(self, name)
        Thinking.__init__(self)
        self.loiter = 0
    
    def choose_target(self, world) -> None:
        pass
    
    def approach_target(self, world) -> None:
        """Approach target directly, moving one tile in the best direction."""
        if not self.target:
            self.state = "target lost"
            return
        
        # Handle both entity targets and coordinate targets
        if hasattr(self.target, 'coordinates'):
            target_coords = self.target.coordinates
        else:
            target_coords = self.target
        
        # Calculate direction to target
        dx = target_coords[0] - self.coordinates[0]
        dy = target_coords[1] - self.coordinates[1]
        
        # Clamp to -1, 0, 1 to get the direction
        dx = max(-1, min(1, dx))
        dy = max(-1, min(1, dy))
        
        # Only move if there's a direction
        if dx != 0 or dy != 0:
            new_x = self.coordinates[0] + dx
            new_y = self.coordinates[1] + dy
            self.move_to((new_x, new_y), self.type == "blade")
        else:
            self.state = "arrived"
    
    def update(self, world) -> None:
        if self.state == "moving":
            if self.is_loitering():
                self.increment_loiter()
            else:
                self.reset_loiter()
                self.approach_target(world)

    def serialize(self) -> Dict[str, Any]:
        """Serialize dragon to dictionary for JSON output."""
        data = super().serialize()
        data.update({
            "name": self.name,
            "type": self.type,
            "domain": self.domain,
        })
        return data
