"""Mobile entity base class - entities that can move and have states."""
from typing import Optional, Dict, Any
from entities.base.entity import Entity, Coordinates
from collections import deque

sqrt2 = 2 ** 0.5

class Mobile(Entity):

    def __init__(
        self,
        color: str,
        character: str,
        coordinates: Coordinates,
        life: int,
        intent="created",
        target=None
    ):
        super().__init__(color, character, coordinates, life)
        self.state = "created"
        self.intent = intent
        self.target: Optional[Coordinates] = target
        self.loiter = 0
        self.loiter_counter = 0
        self.movement_debt = 0.0  # Accumulated cost from diagonal movement
    
    def set_target(self, target: Coordinates) -> None:
        """Set a movement target."""
        self.target = target
        self.loiter_counter = 0
    
    def choose_target(self, world) -> None:
        """Choose a target based on entity-specific logic. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement choose_target()")
    
    def approach_target(self, world) -> None:
        """Move towards target. Override in subclasses for specific movement patterns."""
        raise NotImplementedError("Subclasses must implement approach_target()")
    
    def is_loitering(self) -> bool:
        """Check if entity is currently in loiter state."""
        return self.loiter_counter < self.loiter
    
    def increment_loiter(self) -> None:
        """Increment loiter counter."""
        self.loiter_counter += 1
    
    def reset_loiter(self) -> None:
        """Reset loiter counter."""
        self.loiter_counter = 0
    
    def get_distance(self, target: Coordinates) -> float:
        """Calculate Euclidean distance to target."""
        x1, y1 = self.coordinates
        x2, y2 = target
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def get_adjacent_tiles(self) -> list[Coordinates]:
        """Get all 8 adjacent tiles around current position."""
        x, y = self.coordinates
        adjacent = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    adjacent.append((x + dx, y + dy))
        return adjacent
    
    def get_surrounding_tiles(self, radius: int) -> list[Coordinates]:
        """Get all tiles within a radius around current position."""
        x, y = self.coordinates
        surrounding = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx != 0 or dy != 0:
                    surrounding.append((x + dx, y + dy))
        return surrounding
    
    def move_to(self, new_coordinates: Coordinates, forego_debt: bool = False) -> None:
        """Move to a new coordinate, applying movement debt if diagonal."""
        if not forego_debt:
            dx = abs(new_coordinates[0] - self.coordinates[0])
            dy = abs(new_coordinates[1] - self.coordinates[1])
        
            is_diagonal = dx > 0 and dy > 0
            
            if is_diagonal:
                self.movement_debt += (sqrt2 - 1.0)
            
            if self.movement_debt >= 1.0:
                self.loiter_counter -= self.loiter or 1
                self.movement_debt -= 1.0
        
        # Actually move
        self.coordinates = new_coordinates
    
    def get_movement_cost(self, target: Coordinates) -> float:
        """
        Calculate the cost of moving one step toward target.
        Cardinal movement costs 1.0, diagonal costs ~1.414.
        """
        dx = abs(target[0] - self.coordinates[0])
        dy = abs(target[1] - self.coordinates[1])
        
        if dx > 0 and dy > 0:
            return sqrt2  # Diagonal: sqrt(2) ≈ 1.414
        else:
            return 1.0  # Cardinal: straight line
    
    def is_passable(self, coordinates: Coordinates, world) -> bool:
        """Check if a tile is passable. Override in subclasses for terrain restrictions."""
        return True  # By default, all tiles are passable
    
    def find_path(self, target: Coordinates, world, max_search: int = 50) -> list[Coordinates]:
        """Find a path from current position to target using BFS, avoiding obstacles."""
        if not self.is_passable(target, world):
            return []  # Target is unreachable
        
        queue = deque([(self.coordinates, [self.coordinates])])
        visited = {self.coordinates}
        search_count = 0
        
        while queue and search_count < max_search:
            current, path = queue.popleft()
            search_count += 1
            
            # Check all 8 adjacent tiles
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    
                    neighbor = (current[0] + dx, current[1] + dy)
                    
                    if neighbor in visited or not self.is_passable(neighbor, world):
                        continue
                    
                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    
                    if neighbor == target:
                        return new_path[1:]  # Return path without current position
                    
                    queue.append((neighbor, new_path))
        
        return []  # No path found within search limit
    
    def update(self, world) -> None:
        if self.state == "moving":
            if self.is_loitering():
                self.increment_loiter()
            else:
                self.reset_loiter()
                self.approach_target(world)
            
            if self.coordinates == self.target:
                self.state = "arrived"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(state={self.state}, pos={self.coordinates})"

    def serialize(self) -> Dict[str, Any]:
        """Serialize mobile entity to dictionary for JSON output."""
        data = super().serialize()
        data.update({
            "state": self.state,
            "intent": self.intent,
            "target": list(self.target) if self.target else None,
        })
        return data
