from .base import Coordinates, Mobile, Settlement, Mortal
import random


# Cattle constants
VILLAGE_ATTRACTION_RADIUS = 10  # Distance to check for villages
SETTLEMENT_MIN_DISTANCE = 3  # Minimum distance from settlement
SETTLEMENT_MAX_DISTANCE = 6  # Maximum distance from settlement
WANDER_RANGE = 10  # Random wander distance
LOITER_TIME = 10  # Cycles between movements
DESTINATION_ATTEMPTS = 10  # Attempts to find valid destination


class Cattle(Mortal, Mobile):
    
    def __init__(
        self,
        color: str,
        coordinates: Coordinates,
        life: int,
    ):
        super().__init__(color, 'ɤ', coordinates, life)
        self.state="grazing"
        self.loiter = LOITER_TIME
        self.path: list[Coordinates] = []  # Current path to follow
    
    def is_passable(self, coordinates: Coordinates, world) -> bool:
        """Check if a tile is passable (field or open area, not through settlements)."""
        
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
            return False  # Out of bounds
        
        height = world.height_map[y][x]
        
        if world.get_biome_from_height(height) != 'field':
            return False
        
        # Check if any settlement occupies this tile
        for entity in world.entities if hasattr(world, 'entities') else []:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                return False
        
        return True
    
    def choose_target(self, world) -> None:
        """Choose a destination: near nearby village if within attraction radius, else wander randomly."""
        # Check if there's a village within attraction radius
        nearby_settlement = None
        for entity in world.entities if hasattr(world, 'entities') else []:
            if entity.__class__.__name__ == 'Village':
                distance = self.get_distance(entity.coordinates)
                if distance <= VILLAGE_ATTRACTION_RADIUS:
                    nearby_settlement = entity
                    break
        
        # Try multiple times to find a valid destination
        for _ in range(DESTINATION_ATTEMPTS):
            if nearby_settlement:
                # Stay within min-max distance of settlement
                settlement_x, settlement_y = nearby_settlement.coordinates
                dx = random.randint(SETTLEMENT_MIN_DISTANCE, SETTLEMENT_MAX_DISTANCE) * random.choice([-1, 1])
                dy = random.randint(SETTLEMENT_MIN_DISTANCE, SETTLEMENT_MAX_DISTANCE) * random.choice([-1, 1])
                target = (settlement_x + dx, settlement_y + dy)
            else:
                # Wander randomly
                current_x, current_y = self.coordinates
                dx = random.randint(-WANDER_RANGE, WANDER_RANGE)
                dy = random.randint(-WANDER_RANGE, WANDER_RANGE)
                target = (current_x + dx, current_y + dy)
            
            if self.is_passable(target, world):
                self.destination = target
                self.path = self.find_path(target, world)
                self.state = "moving"
                return
        
        # Failed to find valid destination, stay put
        self.destination = None
        self.path = []
    
    def approach_target(self, world) -> None:
        """Move one step along the path to the destination."""
        # Recalculate path if we don't have one
        if not self.path and self.destination:
            self.path = self.find_path(self.destination, world)
        
        # Move along the path
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
    
    def update(self, world) -> None:
        super().update(world)
        
        # When arrived or just created, pick a new destination
        if self.state in ("arrived", "created"):
            self.choose_target(world)
