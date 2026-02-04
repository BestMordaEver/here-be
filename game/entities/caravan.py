"""Caravan entity with schedule-based delivery."""
from enum import Enum
from typing import TYPE_CHECKING, Dict, Any, Optional

from .base import (
    Coordinates, Mobile, Thinking, Settlement, Mortal, Scheduled, 
    ActionType, ScheduledAction, EngagementType
)

if TYPE_CHECKING:
    from game.world import World
    from . import Village, City, Camp, Spirit


# Caravan constants
ARRIVAL_DISTANCE = 2   # Distance to consider "arrived"
FEAR_RADIUS = 8        # Distance to notice threats


class CaravanMission(Enum):
    """Types of caravan missions."""
    TRADE = "trade"           # Exchange gossip at settlement
    SETTLE_CAMP = "settle_camp"  # Create a worker camp
    RETRIEVE_BLESSING = "retrieve_blessing"  # Buy blessing from village
    DELIVER_BLESSING = "deliver_blessing"  # Deliver blessing to parent settlement


class Caravan(Mortal, Mobile, Thinking, Scheduled):
    """A caravan that travels between settlements."""

    def __init__(
        self,
        world: 'World',
        coordinates: Coordinates,
        home: 'Village | City',
        destination: 'Settlement | Coordinates',
        mission: CaravanMission,
        target_spirit: 'Spirit' = None,  # For settle_camp mission
    ):
        Mobile.__init__(self, world, "#2b1c00", '@', coordinates, loiter=4)  # Caravans skip 4 cycles
        Thinking.__init__(self, intent=mission.value)
        Scheduled.__init__(self)
        
        self.home = home
        self.destination = destination
        self.mission = mission
        self.target_spirit = target_spirit  # Spirit coordinates for camp creation
        self.blessing = False  # Whether carrying a blessing
        self.returning = False  # Whether returning home after trade
        self.fleeing_from = None
        
        # Set initial destination
        if hasattr(destination, 'coordinates'):
            self.set_destination(destination.coordinates)
        elif isinstance(destination, tuple):
            self.set_destination(destination)
    
    def is_passable(self, coordinates: Coordinates) -> bool:
        """Caravans can only move through fields."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(self.world.height_map[0]) or y >= len(self.world.height_map):
            return False
        
        height = self.world.height_map[y][x]
        if self.world.get_biome_from_height(height) != 'field':
            return False
        
        # Can't move through settlements (except destination)
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                # Allow moving to destination settlement
                if entity == self.destination:
                    continue
                return False
        
        return True
    
    def build_schedule(self) -> None:
        """Caravans are mission-driven, not day-scheduled."""
        # Caravans don't use the normal scheduling system
        # They just continue their mission
        self.schedule = []
        self.current_action = None
        
        # Resume movement if needed
        if self.destination and self.state != "moving":
            target = self.destination
            if hasattr(target, 'coordinates'):
                target = target.coordinates
            self.set_destination(target)
    
    def on_hour(self, hour: int) -> None:
        """Caravans don't have hourly schedules."""
        pass
    
    def update_movement(self) -> None:
        """Process movement step."""
        # Check if destination still valid
        if hasattr(self.destination, 'is_alive') and not self.destination.is_alive:
            # Destination died, flee to nearest settlement
            self._flee_to_settlement()
            return
        
        # Normal movement
        super().update_movement()
        
        # Try to pick up a blessing if we don't have one
        if not self.blessing:
            self._try_pickup_blessing()
    
    def _try_pickup_blessing(self) -> None:
        """Pick up a dropped blessing at current location (caravans carry only 1)."""
        from .blessing import Blessing
        
        for entity in self.world.entities:
            if isinstance(entity, Blessing) and entity.coordinates == self.coordinates:
                taken = entity.take(1)
                if taken > 0:
                    self.blessing = True
                    self.think("Found a blessing on the road!")
                break
    
    def on_arrival(self) -> None:
        """Handle arrival at destination."""
        if self.mission == CaravanMission.TRADE:
            self._complete_trade()
        elif self.mission == CaravanMission.SETTLE_CAMP:
            self._complete_settle_camp()
        elif self.mission == CaravanMission.RETRIEVE_BLESSING:
            self._complete_retrieve_blessing()
        elif self.mission == CaravanMission.DELIVER_BLESSING:
            self._complete_deliver_blessing()
    
    def _complete_trade(self) -> None:
        """Complete a trade mission."""
        if self.returning:
            # Arrived home, mission complete
            self.think("Home at last.")
            self.die("success")
            return
        
        # Exchange gossip (placeholder for future implementation)
        self.think("Trading news and goods.")
        
        # Start return journey
        self.returning = True
        if self.home and self.home.is_alive:
            self.destination = self.home
            self.set_destination(self.home.coordinates)
            self.state = "moving"
        else:
            # Home is gone, wander
            self.die("homeless")
    
    def _complete_settle_camp(self) -> None:
        """Create a camp at destination."""
        from . import Camp
        
        spirit_coords = self.target_spirit.coordinates if self.target_spirit else self.coordinates
        
        camp = Camp(self.world, self.coordinates, spirit_coords, self.home)
        
        # Track camp in home's subsidiary list
        if hasattr(self.home, 'subsidiary_camps'):
            self.home.subsidiary_camps.append(camp)
        
        self.world.add_entity(camp)
        self.think("A new camp is established!")
        self.die("success")
    
    def _complete_retrieve_blessing(self) -> None:
        """Retrieve blessing from village and return home."""
        if self.returning:
            # Deliver blessing to home
            if self.blessing and self.home and self.home.is_alive:
                if hasattr(self.home, 'blessings'):
                    self.home.blessings += 1
                self.think("Delivered the blessing.")
            self.die("success")
            return
        
        # Get blessing from destination
        if hasattr(self.destination, 'blessings') and self.destination.blessings > 0:
            self.destination.blessings -= 1
            self.blessing = True
            self.think("Acquired a blessing.")
        
        # Return home
        self.returning = True
        if self.home and self.home.is_alive:
            self.destination = self.home
            self.set_destination(self.home.coordinates)
            self.state = "moving"
        else:
            self.die("homeless")
    
    def _complete_deliver_blessing(self) -> None:
        """Deliver blessing to parent settlement."""
        if self.blessing and self.destination and hasattr(self.destination, 'blessings'):
            self.destination.blessings += 1
            self.blessing = False
            self.think("Blessing delivered!")
        
        self.die("success")
    
    def _flee_to_settlement(self) -> None:
        """Flee to nearest safe settlement."""
        closest: Optional[Settlement] = None
        closest_distance = float('inf')
        
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.is_alive:
                distance = self.get_distance(entity.coordinates)
                if distance < closest_distance:
                    closest_distance = distance
                    closest = entity
        
        if closest:
            self.destination = closest
            self.set_destination(closest.coordinates)
            self.mission = CaravanMission.TRADE  # Just get to safety
            self.returning = True
            self.think("Must flee to safety!")
        else:
            self.die("no refuge")
    
    def check_for_encounters(self) -> Optional[Mobile]:
        """Check for threats. Caravans are passive - they notice but don't initiate."""
        nearby = self.get_nearby_entities(FEAR_RADIUS)
        
        for entity in nearby:
            # Only flee from dragons, bandits will engage us
            if entity.__class__.__name__ == 'Dragon' and entity.is_alive:
                return entity
        
        return None
    
    def react_to_encounter(self, other: 'Mobile') -> Optional[ScheduledAction]:
        """React to threats by fleeing from dragons."""
        if other.__class__.__name__ == 'Dragon':
            # If we're being robbed, the robbery is interrupted by dragon fear
            if self.is_engaged():
                # The bandit will disengage due to their own fear check
                pass
            
            self.fleeing_from = other
            self._flee_to_settlement()
            self.think("A dragon! We must flee!")
            return ScheduledAction(
                hour=self.world.time.current_hour if hasattr(self.world, 'time') else 0,
                action_type=ActionType.FLEE,
                priority=100
            )
        
        # Caravans don't react to bandits - they are passive targets
        # The bandit initiates robbery, heroes interrupt
        return None
    
    def on_hour_end(self, hour: int) -> None:
        """
        Resolve any engagement at hour-end.
        For caravans, this is usually being the target of robbery.
        """
        if not self.current_engagement:
            return
        
        # If we're being robbed, the bandit's on_hour_end handles resolution
        # We just need to clear our engagement state
        self.current_engagement = None
        
        # Continue our mission if still alive
        if self.is_alive and self.destination:
            if hasattr(self.destination, 'coordinates'):
                self.set_destination(self.destination.coordinates)
            self.think("We continue our journey.")
    
    def die(self, reason: str) -> None:
        """Handle caravan death."""
        # Drop blessing if killed (not if mission completed successfully)
        if self.blessing and reason != "success":
            from .blessing import drop_blessing
            drop_blessing(self.world, self.coordinates, 1)
            self.blessing = False
        
        super().die(reason)
        
        # Remove from home's tracking
        if self.home and hasattr(self.home, 'subsidiary_camps'):
            if self in self.home.subsidiary_camps:
                self.home.subsidiary_camps.remove(self)
        
        # Free up target spirit if settling failed
        if self.mission == CaravanMission.SETTLE_CAMP and reason != "success":
            if self.target_spirit:
                self.target_spirit.is_occupied = False
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        data = super().serialize()
        dest_name = "unknown"
        if hasattr(self.destination, 'name'):
            dest_name = self.destination.name
        elif isinstance(self.destination, tuple):
            dest_name = str(self.destination)
        
        data.update({
            "home": self.home.name if self.home and hasattr(self.home, 'name') else "unknown",
            "destination": dest_name,
            "mission": self.mission.value,
            "blessing": self.blessing,
            "returning": self.returning,
        })
        return data
