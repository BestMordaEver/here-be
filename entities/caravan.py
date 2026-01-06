from entities.base.mobile import Mobile
from entities.base.entity import Coordinates
from entities.base.thinking import Thinking
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from entities.settlement import Settlement
    from entities.spirit import Spirit


class Caravan(Mobile, Thinking):

    def __init__(
        self,
        coordinates: Coordinates,
        intent: str,  # "trade" or "exploit"
        home: "Settlement",
        target: "Settlement | Spirit",
    ):
        Mobile.__init__(self, "#2b1c00", '@', coordinates, 50, intent, target)
        Thinking.__init__(self)
        self.loiter = 4
        self.home = home  # Settlement to return to
        self.current_target = target  # Current destination
        self.path: list[Coordinates] = []  # Current path to follow
        self.idle_timer = 0  # Counter for idle time at target
        self.phase = "outbound"  # "outbound" (going to target) or "returning" (going home)
    
    def is_nearby_target(self, world) -> bool:
        """Check if caravan is nearby its current target."""
        if not self.current_target:
            return False
        
        distance = self.get_distance(self.current_target.coordinates)
        
        # For settlements: within 3 units
        if self.current_target.__class__.__name__ == 'Settlement':
            return distance <= 3
        
        # For spirits: within their domain
        if self.current_target.__class__.__name__ == 'Spirit':
            return distance <= self.current_target.domain_area
        
        return False
    
    def choose_target(self, world) -> None:
        """Choose next target based on phase."""
        if self.phase == "outbound":
            # We're going to the target, path will be calculated when we start moving
            pass
        elif self.phase == "returning":
            # Set target to home
            self.current_target = self.home
            self.path = self.find_path(self.home.coordinates, world)
    
    def approach_target(self, world) -> None:
        """Move one step along the path to the target."""
        # Recalculate path if we don't have one
        if not self.path and self.current_target:
            self.path = self.find_path(self.current_target.coordinates, world)
        
        # Move along the path
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
    
    def update(self, world) -> None:
        """Update caravan state."""
        # Set self.target for the Mobile class to use
        if self.current_target:
            self.target = self.current_target.coordinates
        
        if self.phase == "outbound":
            if self.is_nearby_target(world):
                # Reached target, start idle phase
                self.phase = "idle"
                self.idle_timer = 0
            else:
                # Continue moving to target
                if self.state == "moving":
                    if self.is_loitering():
                        self.loiter_counter += 1
                    else:
                        self.loiter_counter = 0
                        self.approach_target(world)
        
        elif self.phase == "idle":
            # Stay in place for 40 timesteps
            self.idle_timer += 1
            if self.idle_timer >= 40:
                # Idle complete, switch to returning phase
                self.phase = "returning"
                self.idle_timer = 0
                self.choose_target(world)
        
        elif self.phase == "returning":
            if self.is_nearby_target(world):
                # Reached home, caravan is collected
                self.state = "collected"
            else:
                # Continue moving home
                if self.state == "moving":
                    if self.is_loitering():
                        self.loiter_counter += 1
                    else:
                        self.loiter_counter = 0
                        self.approach_target(world)

    def serialize(self) -> Dict[str, Any]:
        """Serialize caravan to dictionary for JSON output."""
        data = super().serialize()
        data.update({
            "phase": self.phase,
            "home": list(self.home.coordinates) if self.home else None,
            "current_target": list(self.current_target.coordinates) if self.current_target else None,
        })
        return data
