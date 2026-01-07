"""Mobile entity base class - entities that can move and have states."""
from typing import Optional
from entities.base.entity import Entity, Coordinates
import heapq

sqrt2 = 2 ** 0.5

class Mobile(Entity):

    def __init__(
        self,
        color: str,
        character: str,
        coordinates: Coordinates,
        life: int,
        destination=None
    ):
        super().__init__(color, character, coordinates, life)
        self.state = "created"
        self.destination: Optional[Coordinates] = destination
        self.loiter = 0
        self.loiter_counter = 0
        self.movement_debt = 0.0  # Accumulated cost from diagonal movement
    
    def choose_target(self, world) -> None:
        """Choose a destination based on entity-specific logic. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement choose_target()")
    
    def approach_target(self, world) -> None:
        """Move towards destination. Override in subclasses for specific movement patterns."""
        raise NotImplementedError("Subclasses must implement approach_target()")
    
    def get_distance(self, destination: Coordinates) -> float:
        """Calculate Euclidean distance to destination."""

        x1, y1 = self.coordinates
        x2, y2 = destination
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

        if not forego_debt: # Blades ignore movement debt
            dx = abs(new_coordinates[0] - self.coordinates[0])
            dy = abs(new_coordinates[1] - self.coordinates[1])
        
            is_diagonal = dx > 0 and dy > 0
            
            if is_diagonal:
                self.movement_debt += (sqrt2 - 1.0)
            
            if self.movement_debt >= 1.0:   # At least one, so dragons aren't exempt
                self.loiter_counter -= self.loiter or 1
                self.movement_debt -= 1.0
        
        self.coordinates = new_coordinates
    
    def is_passable(self, coordinates: Coordinates, world) -> bool:
        """Check if a tile is passable. Override in subclasses for terrain restrictions."""
        return True
    
    def find_path(self, destination: Coordinates, world, max_search: int = 5000) -> list[Coordinates]:
        """Find a path from current position to destination using A* pathfinding."""

        if not self.is_passable(destination, world):
            return []
        
        def heuristic(pos: Coordinates) -> float:
            """Euclidean distance heuristic."""
            dx = abs(pos[0] - destination[0])
            dy = abs(pos[1] - destination[1])
            # Use Chebyshev distance since we allow 8-directional movement
            return max(dx, dy)
        
        # Priority queue: (f_score, counter, current, path)
        # counter ensures stable sorting when f_scores are equal
        counter = 0
        start = self.coordinates
        heap = [(heuristic(start), counter, start, [start])]
        counter += 1
        
        # Track best cost to reach each position
        g_score = {start: 0}
        visited = set()
        search_count = 0
        
        while heap and search_count < max_search:
            f, _, current, path = heapq.heappop(heap)
            search_count += 1
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # Check if we reached destination
            if current == destination:
                return path[1:]  # Exclude starting position
            
            current_g = g_score[current]
            
            # Explore neighbors
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    
                    neighbor = (current[0] + dx, current[1] + dy)
                    
                    if neighbor in visited or not self.is_passable(neighbor, world):
                        continue
                    
                    # Cost: diagonal moves cost sqrt(2) ≈ 1.414, cardinal moves cost 1
                    is_diagonal = dx != 0 and dy != 0
                    move_cost = sqrt2 if is_diagonal else 1.0
                    tentative_g = current_g + move_cost
                    
                    # Only process if this is a better path
                    if neighbor not in g_score or tentative_g < g_score[neighbor]:
                        g_score[neighbor] = tentative_g
                        f_score = tentative_g + heuristic(neighbor)
                        new_path = path + [neighbor]
                        heapq.heappush(heap, (f_score, counter, neighbor, new_path))
                        counter += 1
        
        return []
    
    def update(self, world) -> None:
        if self.state == "moving":
            if self.loiter_counter < self.loiter:
                self.loiter_counter += 1
            else:
                self.loiter_counter = 0
                self.approach_target(world)
            
            if self.coordinates == self.destination:
                self.state = "arrived"
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(state={self.state}, pos={self.coordinates})"

