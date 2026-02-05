"""Dragon entity with mood-based daily scheduling."""

from .parser import parse_properties
from .movement import update_movement
from .schedule import build_schedule
from .actions import execute_action_start, check_for_encounters, react_to_encounter

from typing import TYPE_CHECKING, Dict, Any, List

from game.entities.base import Coordinates, Mobile, Named, Aging, Thinking, Mortal, Scheduled

if TYPE_CHECKING:
    from game.world import World


# Dragon constants
LIFESPAN_BASE_DAYS = 20  # Dragon dies after this many days
LIFESPAN_PER_SPIRE = 5   # Extra days per active spire


class Dragon(Mobile, Mortal, Named, Thinking, Scheduled, Aging):
    """Base dragon class with mood-based scheduling."""
    
    def __init__(
        self,
        world: 'World',
        name: str,
        properties: List[str],
        coordinates: Coordinates,
        pronouns: str = None,
    ):
        # Parse properties
        char, color = parse_properties(self, properties, pronouns)

        # Initialize base classes
        Mobile.__init__(self, world, color, char, coordinates, loiter=0)  # Dragons move every cycle
        Named.__init__(self, name)
        Thinking.__init__(self)
        Scheduled.__init__(self)
        Aging.__init__(self)
        
        self.move_error = 0.0  # For Bresenham-style movement
        
        # State
        from .. import Domain
        self.domain = Domain(world, self.coordinates, self, self.is_scorched)
        world.add_entity(self.domain)
        self.days_since_hungry = 0  # Track for hungry mood every 3 days
        
        # Current action tracking
        self.current_target = None  # Entity or coordinates being approached
        
        # Circling state
        self.circle_target = None   # Entity being circled
        self.circle_angle = 0.0     # Current angle around target (radians)
        self.circle_steps_done = 0  # Steps completed in current circle
    
    def on_dawn(self) -> None:
        """Dawn: age, check death, build schedule."""
        self.is_sleeping = False
        
        if self.process_aging():
            return
        
        self.build_schedule()

    def on_hour(self, hour: int) -> None:
        """Process hourly updates."""
        if self.is_sleeping:
            return
        
        # Check for scheduled action
        action = self.get_action_for_hour(hour)
        if action:
            self.start_action(action)
            execute_action_start(self, action)
    
    def on_hour_end(self, hour: int) -> None:
        """
        Resolve any active engagement at hour-end.
        Dragon combat outcomes are determined here.
        """
        if not self.current_engagement:
            return
        
        from game.world.combat import resolve_engagement
        
        # Resolve the engagement
        resolve_engagement(self.current_engagement)
        
        # Clear engagement and complete action
        self.current_engagement = None
        self.complete_current_action()
    
    def die(self, reason: str) -> None:
        """Handle dragon death - domain becomes treasury."""
        super().die(reason)
        
        if self.domain:
            self.domain.owner = None
            self.domain.is_treasury = True
            self.domain.treasure = self.blessings
        
    def get_lifespan(self) -> int:
        """Calculate lifespan based on active spires."""
        spire_count = sum(1 for e in self.world.entities 
                         if e.__class__.__name__ == 'Spire' and e.is_alive)
        return LIFESPAN_BASE_DAYS + (LIFESPAN_PER_SPIRE * spire_count)
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        data = super().serialize()
        data.update({
            "name": self.name,
            "dragon_type": self.dragon_type,
            "domain_type": self.domain_type,
            "mood": self.mood.value,
            "age_days": self.age_days,
            "blessings": self.blessings,
            "rotation": self.rotation,
            "pronouns": f"{self.pronouns.subject}/{self.pronouns.object}/{self.pronouns.possessive}",
            "schedule": self.get_schedule_summary(),
        })
        return data

Dragon.build_schedule = build_schedule
Dragon.update_movement = update_movement
Dragon.check_for_encounters = check_for_encounters
Dragon.react_to_encounter = react_to_encounter