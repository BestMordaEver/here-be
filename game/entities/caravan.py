"""Caravan entity with schedule-based delivery."""
from enum import Enum
from typing import TYPE_CHECKING, Dict, Any, Optional

from .base import (
    Coordinates, Mobile, Thinking, Scheduled, Pockets,
    ActionType, ScheduledAction, EngagementType
)
from .settlement.settlement import Settlement

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


class Caravan(Mobile, Thinking, Scheduled, Pockets):
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
        Thinking.__init__(self)
        Scheduled.__init__(self)
        Pockets.__init__(self, max_blessings=1)
        
        self.home = home
        self.destination = destination
        self.mission = mission
        self.target_spirit = target_spirit  # Spirit coordinates for camp creation
        self.blessing = False  # Whether carrying a blessing
        self.returning = False  # Whether returning home after trade
        self.fleeing_from = None
        
        # Set initial destination
        if isinstance(destination, tuple):
            self.set_target(destination)
        else:
            self.set_target(destination.coordinates)
    
    def is_passable(self, coordinates: Coordinates) -> bool:
        """Caravans can only move through fields."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(self.world.height_map[0]) or y >= len(self.world.height_map):
            return False
        
        height = self.world.height_map[y][x]
        if self.world.get_biome_from_height(height) != 'field':
            return False
        
        # Can't move through settlements (except destination)
        for entity in self.world.get_entities_at(coordinates):
            if isinstance(entity, Settlement):
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
        self.fleeing_from = None

        if self.home and not self.home.is_alive:
            self.home = None
        
        # Resume movement if needed
        if self.destination and self.state != "moving":
            target = self.destination
            if not isinstance(target, tuple):
                target = target.coordinates
            self.set_target(target)
    
    def update_movement(self) -> None:
        """Process movement step."""
        # Check if destination still valid
        if not isinstance(self.destination, tuple) and not self.destination.is_alive:
            # Destination died, flee to nearest settlement
            self._flee_to_settlement()
            return
        
        # Normal movement
        super().update_movement()
        
        # Try to pick up a dropped blessing at current location (caravans carry only 1)
        if not self.blessing:
            from .blessing import Blessing
            for entity in self.world.get_entities_at(self.coordinates):
                if isinstance(entity, Blessing):
                    break
    
    def on_arrival(self) -> None:
        """Handle arrival at destination."""
        # Exchange events with destination settlement
        if not isinstance(self.destination, tuple) and hasattr(self.destination, 'is_talker') and self.destination.is_talker:
            self.exchange_memories(self.destination)

        if self.mission == CaravanMission.TRADE:
            if self.returning:
                self.think("Home at last.")
                self.die("success")
                return
            self.think("Trading news and goods.")
            self.returning = True
            if self.home and self.home.is_alive:
                self.destination = self.home
                self.set_target(self.home.coordinates)
                self.state = "moving"
            else:
                self.die("homeless")

        elif self.mission == CaravanMission.SETTLE_CAMP:
            from . import Camp
            spirit_coords = self.target_spirit.coordinates if self.target_spirit else self.coordinates
            camp = Camp(self.world, self.coordinates, spirit_coords, self.home)
            self.home.subsidiary_camps.append(camp)
            self.world.add_entity(camp)
            self.think("A new camp is established!")
            self.die("success")

        elif self.mission == CaravanMission.RETRIEVE_BLESSING:
            if self.returning:
                if self.blessing and self.home and self.home.is_alive:
                    self.home.store_blessing(1)
                    self.think("Delivered the blessing.")
                self.die("success")
                return
            if not isinstance(self.destination, tuple) and self.destination.has_blessings:
                self.destination.blessings -= 1
                self.blessing = True
                self.think("Acquired a blessing.")
            self.returning = True
            if self.home and self.home.is_alive:
                self.destination = self.home
                self.set_target(self.home.coordinates)
                self.state = "moving"
            else:
                self.die("homeless")

        elif self.mission == CaravanMission.DELIVER_BLESSING:
            if self.blessing and self.destination and not isinstance(self.destination, tuple):
                self.destination.store_blessing(1)
                self.blessing = False
                self.think("Blessing delivered!")
            self.die("success")
    
    def _flee_to_settlement(self) -> None:
        """Flee to nearest safe settlement."""
        closest: Optional[Settlement] = None
        closest_distance = float('inf')
        
        for entity in list(self.world.entities):
            if isinstance(entity, Settlement) and entity.is_alive:
                distance = self.get_distance(entity.coordinates)
                if distance < closest_distance:
                    closest_distance = distance
                    closest = entity
        
        if closest:
            self.destination = closest
            self.set_target(closest.coordinates)
            self.mission = CaravanMission.TRADE  # Just get to safety
            self.returning = True
            self.think("Must flee to safety!")
        else:
            self.die("no refuge")
    
    def check_for_encounters(self) -> Optional[Mobile]:
        """Check for threats. Caravans are passive - they notice but don't initiate."""
        # Exchange events with nearby talkers
        for entity in self.get_nearby_entities(FEAR_RADIUS):
            if hasattr(entity, 'is_talker') and entity.is_talker:
                self.exchange_memories(entity)

        nearby = self.get_nearby_entities(FEAR_RADIUS)
        
        for entity in nearby:
            # Only flee from dragons, bandits will engage us
            if entity.__class__.__name__ == 'Dragon' and entity.is_alive:
                from game.entities.base.thinking import Memory, MemoryType
                self.add_memory(Memory(
                    type=MemoryType.SAW_DRAGON,
                    subject=entity,
                    location=entity.coordinates,
                    day=self.world.time.current_day,
                    source=self,
                ))
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
                hour=self.world.time.current_hour,
                action_type=ActionType.FLEE
            )
        
        # Caravans don't react to bandits - they are passive targets
        # The bandit initiates robbery, heroes interrupt
        return None
    
    def die(self, reason: str) -> None:
        """Handle caravan death."""
        # Drop blessing if killed (not if mission completed successfully)
        if self.blessing and reason != "success":
            from .blessing import drop_blessing
            drop_blessing(self.world, self.coordinates, 1)
            self.blessing = False
        
        super().die(reason)
        
        # Remove from home's tracking
        if self.home:
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
        if isinstance(self.destination, tuple):
            dest_name = str(self.destination)
        else:
            dest_name = self.destination.name
        
        data.update({
            "home": self.home.name if self.home else "unknown",
            "destination": dest_name,
            "mission": self.mission.value,
            "blessing": self.blessing,
            "returning": self.returning,
        })
        return data
