from math import atan2, degrees
from random import randint
from typing import TYPE_CHECKING, Dict, Any
from entities.base.mobile import Mobile
from entities.base.entity import Coordinates
from entities.base.named import Named
from entities.base.thinking import Thinking


if TYPE_CHECKING:
    from world import World



class Dragon(Mobile, Named, Thinking):

    def __init__(
        self,
        name: str,
        properties: list[str],
        coordinates: Coordinates,
    ):
        if "serpent" in properties:
            chars = ['Ȿ', 'Ɀ']
            self.type = "serpent"
            base_rotation = 270  # faces up
        elif "brute" in properties:
            chars = ['&', 'Ֆ']
            self.type = "brute"
            base_rotation = 270  # faces left up
        elif "blade" in properties:
            chars = ['%', '÷']
            self.type = "blade"
            base_rotation = 315  # faces right up
        elif "druid" in properties:
            chars = ['₷', '₻']
            self.type = "druid"
            base_rotation = 315  # faces right up
        elif "midas" in properties:
            chars = ['ꬸ', 'ꬷ']
            self.type = "midas"
            base_rotation = 270  # faces up
        
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


        Mobile.__init__(self, color, chars[0], coordinates, 500)
        Named.__init__(self, name)
        Thinking.__init__(self)
        self.loiter = 0
        self.move_error = 0.0  # Track error for line approximation
        self.base_rotation = base_rotation
        self.rotation = base_rotation  # Current rotation angle in degrees
    
    def choose_target(self, world) -> None:
        pass
    
    def approach_target(self, world) -> None:
        """Approach target using Bresenham-style line approximation for smooth movement."""
        if not self.target:
            self.state = "target lost"
            return
        
        # Handle both entity targets and coordinate targets
        if hasattr(self.target, 'coordinates'):
            target_coords = self.target.coordinates
        else:
            target_coords = self.target
        
        # Calculate full distance to target
        dx_full = target_coords[0] - self.coordinates[0]
        dy_full = target_coords[1] - self.coordinates[1]
        
        # If at target, we're done
        if dx_full == 0 and dy_full == 0:
            self.state = "arrived"
            return
        
        # Get absolute distances
        abs_dx = abs(dx_full)
        abs_dy = abs(dy_full)
        
        # Determine primary and secondary axes
        dx = 0
        dy = 0
        
        if abs_dx == 0:
            # Only vertical movement
            dy = 1 if dy_full > 0 else -1
        elif abs_dy == 0:
            # Only horizontal movement
            dx = 1 if dx_full > 0 else -1
        else:
            # Use error accumulation for line approximation
            # The idea: we accumulate the ratio and move diagonally when error allows
            ratio = abs_dy / abs_dx  # How much Y per X
            
            # Add the minor axis movement to error
            if abs_dx >= abs_dy:
                # X is primary axis (longer distance)
                dx = 1 if dx_full > 0 else -1
                self.move_error += ratio
                # If error >= 1, also move in Y direction (diagonal move)
                if self.move_error >= 1.0:
                    dy = 1 if dy_full > 0 else -1
                    self.move_error -= 1.0
            else:
                # Y is primary axis (longer distance)
                dy = 1 if dy_full > 0 else -1
                self.move_error += 1.0 / ratio
                # If error >= 1, also move in X direction (diagonal move)
                if self.move_error >= 1.0:
                    dx = 1 if dx_full > 0 else -1
                    self.move_error -= 1.0
        
        # Calculate movement heading (0° = right, 90° = down, 180° = left, 270° = up)
        if dx != 0 or dy != 0:
            heading = degrees(atan2(dy, dx))  # atan2 gives angle from positive x-axis
            # Calculate rotation needed to point from base direction to heading
            self.rotation = heading - self.base_rotation
        
        # Move
        self.move_to((self.coordinates[0] + dx, self.coordinates[1] + dy), self.type == "blade")
    
    def update(self, world: "World") -> None:
        
        super().update(world)

        if self.state == "arrived":
            self.state = "moving"
            self.target = world.entities[randint(0, len(world.entities) - 1)]

    def serialize(self) -> Dict[str, Any]:
        """Serialize dragon to dictionary for JSON output."""
        data = super().serialize()
        data["name"] = self.name
        data["type"] = self.type
        data["domain"] = self.domain
        data["rotation"] = self.rotation
        data["debug_info"] = f"{self.name} type {self.type} rotation {self.rotation:.1f}°"
        return data
