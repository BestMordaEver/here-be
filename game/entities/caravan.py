from .base import Coordinates, Mobile, Thinking, Settlement, Mortal
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from game.world import World
    from . import Village, City


CAMP_TRADE_DISTANCE = 2
VILLAGE_TRADE_DISTANCE = 3
CITY_TRADE_DISTANCE = 5


class Caravan(Mortal, Mobile, Thinking):

    def __init__(
        self,
        coordinates: Coordinates,
        home: 'Village | City',
        destination: "Settlement | Coordinates",
        intent: str,
    ):
        Mobile.__init__(self, "#2b1c00", '@', coordinates, 50, destination)
        Thinking.__init__(self, intent)
        self.home = home
        self.loiter = 4
        self.current_target: Coordinates = destination.coordinates if hasattr(destination, "coordinates") else destination
        self.path: list[Coordinates] = []
    
    def die(self, world : 'World', reason):
        super().die(world, reason)

        if self in self.home.subsidiary_camps:
            self.home.subsidiary_camps.remove(self)
        if self.home.__class__.__name__ == "City" and self in self.home.subsidiary_villages:
            self.home.subsidiary_villages.remove(self)
        if "(" in self.intent:
            coordinates = tuple(int(c) for c in self.intent.split("(")[1].split(")")[0].split(", "))
            entities = world.get_entities_at(coordinates)
            for entity in entities:
                if entity.__class__.__name__ == 'Spirit':
                    entity.is_occupied = False

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
    
    def is_nearby_target(self) -> bool:
        """Check if caravan is nearby its current destination."""
        if self.intent.startswith("settle"):
            # For settlement intents, require exact match
            return self.coordinates == self.current_target
        elif self.intent == "trade":
            if self.destination.__class__.__name__ == "Camp":
                return self.get_distance(self.current_target) <= CAMP_TRADE_DISTANCE
            elif self.destination.__class__.__name__ == "Village":
                return self.get_distance(self.current_target) <= VILLAGE_TRADE_DISTANCE
            return self.get_distance(self.current_target) <= CITY_TRADE_DISTANCE
    
    def approach_target(self, world) -> None:
        """Move one step along the path to the destination."""
        
        if not self.path and self.current_target:
            self.path = self.find_path(self.current_target, world)
        
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
    
    def update(self, world) -> None:
        """Update caravan state."""

        # Movement processed by Mobile
        super().update(world)
        if self.state == "moving" and self.is_nearby_target():
            self.state = "arrived"

        if self.state == "created":
            self.state = "moving"
            if isinstance(self.destination, tuple):
                self.current_target = self.destination
            else:
                self.current_target = self.destination.coordinates
        elif self.state == "arrived":
            # Handle settlement
            if self.intent.startswith("settle"):
                if 'village' in self.intent:
                    from . import Village
                    from game.world import generate_village_name
                    
                    village = Village(generate_village_name(), self.coordinates)
                    world.add_entity(village)
                    
                    # Caravan completes its mission
                    self.die(world, "success")
                    return
                
                else:
                    from . import Camp

                    camp = Camp(self.coordinates)
                    world.add_entity(camp)
                    
                    # Caravan completes its mission
                    self.die(world, "success")
                    return
            
            # Trade handling
            elif self.destination.is_alive:
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