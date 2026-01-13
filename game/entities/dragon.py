from math import atan2, degrees
from random import randint, choice
from typing import TYPE_CHECKING, Dict, Any
from .base import Coordinates, Mobile, Named, Thinking, Mortal


if TYPE_CHECKING:
    from game.world import World
    from . import Domain


# Dragon constants
STARTING_LIFE = 500  # Dragon starting HP
LOITER_TIME = 0  # Dragons don't loiter (move every cycle)
MAX_AGE = 1000  # Dragon dies of old age after this many cycles
TREASURE_GENERATION_BASE = 1  # Base treasure per cycle
TREASURE_GENERATION_MIDAS = 3  # Midas treasure per cycle


class Dragon(Mortal, Mobile, Named, Thinking):

    def __init__(
        self,
        name: str,
        properties: list[str],
        coordinates: Coordinates,
    ):
        self.properties = properties

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
        elif "mountain" in properties:
            color = "#808080"
        elif "verdant" in properties:
            color = "#008000"
        elif "scorched" in properties:
            color = "#800000"


        Mobile.__init__(self, color, chars[0], coordinates, STARTING_LIFE)
        Named.__init__(self, name)
        Thinking.__init__(self)
        self.loiter = LOITER_TIME
        self.move_error = 0.0  # Track error for line approximation
        self.base_rotation = base_rotation
        self.rotation = base_rotation  # Current rotation angle in degrees
        
        # Store properties
        self.properties = properties
        self.is_scorched = "scorched" in properties
        self.is_carnivore = "carnivore" in properties
        self.is_herbivore = "herbivore" in properties
        self.is_greed = "greed" in properties
        self.is_anthropophage = "anthropophage" in properties
        self.is_good = "good" in properties
        self.is_evil = "evil" in properties
        self.is_territorial = "territorial" in properties
        
        # Dragon state
        self.age = 0  # Cycles alive
        self.domain_entity: 'Domain' = None  # Will be created when dragon is added to world
        self.food = 50  # Starting food
        self.current_want = "idle"  # Current desire/goal
        
        # Dragon state
        self.age = 0  # Cycles alive
        self.domain_entity: 'Domain' = None  # Will be created when dragon is added to world
        self.food = 50  # Starting food
        self.current_want = "idle"  # Current desire/goal
    
    def create_domain(self, world: 'World') -> None:
        """Create the dragon's domain at their spawn location."""
        if self.domain_entity is not None:
            return  # Already has domain
        
        from . import Domain
        self.domain_entity = Domain(self.coordinates, self, self.is_scorched)
        world.add_entity(self.domain_entity)
    
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
        # Create domain on first update if not exists
        if self.domain_entity is None:
            self.create_domain(world)
        
        # Age the dragon
        self.age += 1
        
        # Die of old age
        if self.age >= MAX_AGE:
            self.die(world, "old age")
            return
        
        # Generate treasure (domain accumulates it)
        if self.domain_entity and self.domain_entity.is_alive:
            if self.type == "midas":
                self.domain_entity.treasure += TREASURE_GENERATION_MIDAS
            else:
                self.domain_entity.treasure += TREASURE_GENERATION_BASE
        
        # Generate thoughts occasionally
        self.generate_thought(world)
        
        super().update(world)

        if self.state == "arrived":
            self.state = "moving"
            self.target = world.entities[randint(0, len(world.entities) - 1)]

    def serialize(self) -> Dict[str, Any]:
        """Serialize dragon to dictionary for JSON output."""
        data = super().serialize()
        data["name"] = self.name
        data["type"] = self.type
        data["age"] = self.age
        data["food"] = self.food
        data["rotation"] = self.rotation
        data["current_want"] = self.current_want
        data["debug_info"] = f"{self.name} {self.type} age {self.age}, want: {self.current_want}"
        return data
