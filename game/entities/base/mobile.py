"""Mobile entity base class - entities that can move and have states."""
from typing import Optional, List, TYPE_CHECKING
from .entity import Entity, Coordinates
import heapq

if TYPE_CHECKING:
    from game.world import World

sqrt2 = 2 ** 0.5

# Encounter detection radius
ENCOUNTER_RADIUS = 3.0


class Mobile(Entity):
    """Base class for entities that can move around the world."""

    def __init__(
        self,
        color: str,
        character: str,
        coordinates: Coordinates,
        destination=None,
        loiter: int = 0  # Update cycles to skip between moves (0 = fastest)
    ):
        super().__init__(color, character, coordinates)
        self.state = "created"
        self.destination: Optional[Coordinates] = destination
        self.target_entity = None  # The entity we're moving toward (if any)
        self.path: List[Coordinates] = []  # Current path to follow
        self.movement_debt = 0.0  # Accumulated cost from diagonal movement
        self.loiter = loiter  # Cycles to wait between moves
        self.loiter_counter = 0  # Current loiter countdown
    
    def set_destination(self, destination: Coordinates, world: 'World') -> bool:
        """
        Set a new destination and calculate path.
        
        Returns:
            True if a path was found, False otherwise
        """
        self.destination = destination
        self.target_entity = None
        self.path = self.find_path(destination, world)
        if self.path:
            self.state = "moving"
            return True
        return False
    
    def set_target_entity(self, target, world: 'World') -> bool:
        """
        Set an entity as the target and calculate path to it.
        
        Returns:
            True if a path was found, False otherwise
        """
        self.target_entity = target
        self.destination = target.coordinates
        self.path = self.find_path(target.coordinates, world)
        if self.path:
            self.state = "moving"
            return True
        return False
    
    def move_to(self, new_coordinates: Coordinates, forego_debt: bool = False) -> None:
        """Move to a new coordinate, applying movement debt if diagonal."""

        if not forego_debt:  # Blades ignore movement debt
            dx = abs(new_coordinates[0] - self.coordinates[0])
            dy = abs(new_coordinates[1] - self.coordinates[1])
        
            is_diagonal = dx > 0 and dy > 0
            
            if is_diagonal:
                self.movement_debt += (sqrt2 - 1.0)
        
        self.coordinates = new_coordinates
    
    def should_skip_movement(self) -> bool:
        """Check if this movement update should be skipped due to diagonal debt."""
        if self.movement_debt >= 1.0:
            self.movement_debt -= 1.0
            return True
        return False
    
    def is_passable(self, coordinates: Coordinates, world: 'World') -> bool:
        """Check if a tile is passable. Override in subclasses for terrain restrictions."""
        return True
    
    def find_path(self, destination: Coordinates, world: 'World', max_search: int = 5000) -> List[Coordinates]:
        """Find a path from current position to destination using A* pathfinding."""

        if not self.is_passable(destination, world):
            return []
        
        def heuristic(pos: Coordinates) -> float:
            """Euclidean distance heuristic."""
            dx = abs(pos[0] - destination[0])
            dy = abs(pos[1] - destination[1])
            return (dx**2 + dy**2)**0.5
        
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
    
    def update_movement(self, world: 'World') -> None:
        """
        Called every 10 seconds to process movement.
        Moves one step along the current path, respecting loiter delays.
        """
        if self.state != "moving" or not self.path:
            return
        
        # Check loiter (slower entities wait between moves)
        if self.loiter_counter > 0:
            self.loiter_counter -= 1
            return
        
        # Check diagonal debt
        if self.should_skip_movement():
            self.loiter_counter = self.loiter
            return
        
        # If tracking an entity, update destination if it moved
        if self.target_entity and hasattr(self.target_entity, 'coordinates'):
            if self.target_entity.coordinates != self.destination:
                self.destination = self.target_entity.coordinates
                # Recalculate path if target moved significantly
                if self.get_distance(self.destination) > 2:
                    self.path = self.find_path(self.destination, world)
        
        # Move along path
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
            
            # Reset loiter counter after moving
            self.loiter_counter = self.loiter
            
            # Check if arrived
            if self.coordinates == self.destination:
                self.state = "arrived"
                self.on_arrival(world)
            elif not self.path:
                # Path exhausted but not at destination - recalculate
                self.path = self.find_path(self.destination, world)
                if not self.path:
                    self.state = "stuck"
    
    def on_arrival(self, world: 'World') -> None:
        """Called when entity arrives at destination. Override in subclasses."""
        pass
    
    def check_for_encounters(self, world: 'World') -> Optional['Mobile']:
        """
        Check for nearby entities that should trigger an encounter.
        Override in subclasses for entity-specific encounter detection.
        
        Returns:
            An encountered entity, or None
        """
        # Default: no encounters
        return None
    
    def get_nearby_entities(self, world: 'World', radius: float = ENCOUNTER_RADIUS) -> List['Mobile']:
        """Get all mobile entities within encounter radius."""
        nearby = []
        for entity in world.entities:
            if entity is self:
                continue
            if not isinstance(entity, Mobile):
                continue
            if not entity.is_alive:
                continue
            if self.get_distance(entity.coordinates) <= radius:
                nearby.append(entity)
        return nearby
    
    def flee_from(self, threat, world: 'World') -> bool:
        """
        Start fleeing from a threat.
        
        Returns:
            True if a flee path was found
        """
        # Calculate direction away from threat
        tx, ty = threat.coordinates
        mx, my = self.coordinates
        
        # Move in opposite direction
        dx = mx - tx
        dy = my - ty
        
        # Normalize and extend
        dist = max(1, (dx**2 + dy**2)**0.5)
        flee_distance = 20  # Flee this far
        target_x = int(mx + (dx / dist) * flee_distance)
        target_y = int(my + (dy / dist) * flee_distance)
        
        # Clamp to world bounds
        target_x = max(0, min(world.WIDTH - 1, target_x))
        target_y = max(0, min(world.HEIGHT - 1, target_y))
        
        return self.set_destination((target_x, target_y), world)
    
    def stop_movement(self) -> None:
        """Stop current movement."""
        self.state = "idle"
        self.path = []
        self.destination = None
        self.target_entity = None
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(state={self.state}, pos={self.coordinates})"

