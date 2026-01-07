from entities.base.mobile import Mobile
from entities.base.entity import Coordinates
from entities.base.thinking import Thinking
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from entities.settlement import Settlement


class Caravan(Mobile, Thinking):

    def __init__(
        self,
        coordinates: Coordinates,
        home: "Settlement",
        destination: "Settlement",
    ):
        Mobile.__init__(self, "#2b1c00", '@', coordinates, 50, destination)
        Thinking.__init__(self)
        self.loiter = 4
        self.home = home
        self.current_target: Coordinates = destination.coordinates
        self.path: list[Coordinates] = []

    def is_passable(self, coordinates, world):
        
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
            return False  # Out of bounds
        
        height = world.height_map[coordinates[1]][coordinates[0]]
        return world.get_biome_from_height(height) == 'field'
    
    def is_nearby_target(self, world) -> bool:
        """Check if caravan is nearby its current destination."""
        return self.get_distance(self.current_target) <= 2
    
    def approach_target(self, world) -> None:
        """Move one step along the path to the destination."""
        
        if not self.path and self.current_target:
            # Caravans don't know if their destination is alive
            self.path = self.find_path(self.current_target, world)
        
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
    
    def update(self, world) -> None:
        """Update caravan state."""

        # Movement processed by Mobile
        super().update(world)
        if self.is_nearby_target(world):
            self.state = "arrived"

        if self.state == "created":
            self.state = "moving"
            self.current_target = self.destination.coordinates
        elif self.state == "arrived":
            if self.destination == self.home:
                if self.destination.is_alive:
                    self.state = "collected"
                else:
                    self.state = "fleeing"  # Dead home, find new home
                
                    closest_settlement: Settlement = None
                    closest_distance = float('inf')

                    for entity in world.entities:
                        if isinstance(entity, Settlement) and entity != self.home and entity.is_alive:
                            distance = self.get_distance(entity.coordinates)
                            if distance < closest_distance:
                                closest_distance = distance
                                closest_settlement = entity

                    if closest_settlement:
                        self.current_target = closest_settlement.coordinates
            else:
                if self.destination.is_alive:
                    self.state = "idle"
                    self.loiter_counter = 40
                else:
                    # Destination is dead, return home
                    self.current_target = self.home.coordinates
                    self.state = "moving"

        elif self.state == "fleeing":
            self.life -= 1
            self.state = "moving"
            super().update(world)
            if self.state != "arrived":
                self.state = "fleeing"
        elif self.state == "idle":
            if self.loiter_counter > 0:
                self.loiter_counter -= 1
            else:
                self.state = "moving"
                self.current_target = self.home.coordinates

    def serialize(self) -> Dict[str, Any]:
        """Serialize caravan to dictionary for JSON output."""
        data = super().serialize()
        data["home"] = self.home.name
        data["destination"] = self.destination.name
        data["debug_info"] = f"Caravan at {self.coordinates} heading to {self.current_target} home: {self.home.name}, destination: {self.destination.name}, state {self.state}, loiter_counter {self.loiter_counter}, path {len(self.path)}"
        return data