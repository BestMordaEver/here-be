from entities.base.mobile import Mobile
from entities.base.entity import Coordinates
import random


class Cattle(Mobile):
    
    def __init__(
        self,
        color: str,
        coordinates: Coordinates,
        life: int,
    ):
        super().__init__(color, 'Ɐ', coordinates, life, state="grazing", intent="foraging")
        self.loiter = 10
        self.path: list[Coordinates] = []  # Current path to follow
    
    def is_passable(self, coordinates: Coordinates, world) -> bool:
        """Check if a tile is passable (field or open area)."""
        
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
            return False  # Out of bounds
        
        height = world.height_map[y][x]
        
        return world.get_biome_from_height(height) == 'field'
    
    def choose_target(self, world) -> None:
        """Choose a target: near nearby settlement if within 10 units, else wander randomly."""
        # Check if there's a settlement within 10 units
        nearby_settlement = None
        for entity in world.entities if hasattr(world, 'entities') else []:
            if entity.__class__.__name__ == 'Settlement':
                distance = self.get_distance(entity.coordinates)
                if distance <= 10:
                    nearby_settlement = entity
                    break
        
        if nearby_settlement:
            # Stay within 5 units of settlement
            settlement_x, settlement_y = nearby_settlement.coordinates
            dx = random.randint(-5, 5)
            dy = random.randint(-5, 5)
            target = (settlement_x + dx, settlement_y + dy)
        else:
            # Wander randomly
            current_x, current_y = self.coordinates
            dx = random.randint(-10, 10)
            dy = random.randint(-10, 10)
            target = (current_x + dx, current_y + dy)
        
        self.set_target(target)
        self.path = self.find_path(target, world)
    
    def approach_target(self, world) -> None:
        """Move one step along the path to the target."""
        # Recalculate path if we don't have one
        if not self.path and self.target:
            self.path = self.find_path(self.target, world)
        
        # Move along the path
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
    
    def update(self, world) -> None:
        super().update(world)
