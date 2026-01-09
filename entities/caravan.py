from entities.base.mobile import Mobile
from entities.base.entity import Coordinates
from entities.base.thinking import Thinking
from entities.base.settlement import Settlement
from typing import TYPE_CHECKING, Dict, Any


class Caravan(Mobile, Thinking):

    def __init__(
        self,
        coordinates: Coordinates,
        home: Settlement,
        destination: "Settlement | Coordinates",
        intent: str,
    ):
        Mobile.__init__(self, "#2b1c00", '@', coordinates, 50, destination)
        Thinking.__init__(self, intent)
        self.home = home
        self.loiter = 4
        self.current_target: Coordinates = destination.coordinates if hasattr(destination, "coordinates") else destination
        self.path: list[Coordinates] = []
    
    def die(self, world, reason):
        super().die(world)

    def is_passable(self, coordinates, world):
        """Check if a tile is passable (field, not through settlements)."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
            return False  # Out of bounds
        
        height = world.height_map[coordinates[1]][coordinates[0]]
        if world.get_biome_from_height(height) != 'field':
            return False
        
        for entity in world.entities if hasattr(world, 'entities') else []:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                return False
        
        return True
    
    def is_nearby_target(self, world) -> bool:
        """Check if caravan is nearby its current destination."""
        if self.intent.startswith("establish_camp"):
            # For camp establishment, need to be at exact location
            return self.coordinates == self.current_target
        elif self.intent == "trade":
            if self.destination.__class__.__name__ == "Camp":
                return self.get_distance(self.current_target) <= 2
            elif self.destination.__class__.__name__ == "Village":
                return self.get_distance(self.current_target) <= 3
            return self.get_distance(self.current_target) <= 5
        else:
            return self.coordinates == self.current_target
    
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
        if self.state == "moving" and self.is_nearby_target(world):
            self.state = "arrived"

        if self.state == "created":
            self.state = "moving"
            if isinstance(self.destination, tuple):
                self.current_target = self.destination
            else:
                self.current_target = self.destination.coordinates
        elif self.state == "arrived":
            # Handle camp establishment
            if self.intent.startswith("establish_camp"):
                # Parse the intent: "establish_camp:name:spirit_type"
                parts = self.intent.split(":")
                if len(parts) >= 2:
                    camp_name = parts[1]
                    
                    # Create the worker camp at current location
                    from entities import Camp
                    camp = Camp(camp_name, self.coordinates)
                    world.add_entity(camp)
                    
                    # Caravan completes its mission
                    self.die(world, "camp_established")
                    return
            
            # Original trading logic
            if hasattr(self.destination, 'is_alive') and self.destination.is_alive:
                self.state = "trading"
                self.loiter_counter = 40
            else:
                self.state = "fleeing"  # Dead target, flee
            
                closest_settlement: Settlement = None
                closest_distance = float('inf')

                for entity in world.entities:
                    if isinstance(entity, Settlement) and entity.is_alive:
                        distance = self.get_distance(entity.coordinates)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_settlement = entity

                if closest_settlement:
                    self.current_target = closest_settlement.coordinates

        elif self.state == "fleeing":
            self.life -= 1
            self.state = "moving"
            super().update(world)
            if self.state != "arrived":
                self.state = "fleeing"
        elif self.state == "trading":
            if self.loiter_counter > 0:
                self.loiter_counter -= 1
            else:
                self.die(world, "success")

    def serialize(self) -> Dict[str, Any]:
        """Serialize caravan to dictionary for JSON output."""
        data = super().serialize()
        data["home"] = self.home.name
        data["destination"] = self.destination.name if hasattr(self.destination, 'name') else self.destination
        data["debug_info"] = f"Caravan at {self.coordinates} heading to {self.current_target} home: {self.home.name}, destination: {self.destination}, state {self.state}, loiter_counter {self.loiter_counter}, path {len(self.path)}"
        return data