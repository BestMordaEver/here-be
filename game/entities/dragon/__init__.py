"""Dragon entity with mood-based daily scheduling."""

from typing import TYPE_CHECKING, Dict, Any, List

from .types import DragonMood, DragonType, DomainType, DragonAlignment, DragonDiet
from game.entities.base import Coordinates, Mobile, Named, Aging, Thinking, Scheduled, Visible
from game.entities.base.named import Pronouns

if TYPE_CHECKING:
    from game.world import World


# Dragon constants
LIFESPAN_BASE_DAYS = 20  # Dragon dies after this many days
LIFESPAN_PER_SPIRE = 5   # Extra days per active spire


class Dragon(Mobile, Visible, Named, Thinking, Scheduled, Aging):
    """Base dragon class with mood-based scheduling."""
    
    def __init__(
        self,
        world: 'World',
        name: str,
        properties: List[str],
        coordinates: Coordinates,
        pronouns: str = None,
    ):
        # Initialize base classes
        Mobile.__init__(self, world, coordinates, loiter=0)  # Dragons move every cycle
        Visible.__init__(self)
        Named.__init__(self, name, Pronouns.from_string(pronouns))
        Thinking.__init__(self)
        Scheduled.__init__(self)
        Aging.__init__(self, lifespan=LIFESPAN_BASE_DAYS)  # Base lifespan, modified by spires

        # Determine dragon type from properties
        if 'serpent' in properties:
            self.dragon_type = DragonType.SERPENT
            char = 'Ȿ'
            base_rotation = 270
        elif 'blade' in properties:
            self.dragon_type = DragonType.BLADE
            char = '%'
            base_rotation = 315
        elif 'druid' in properties:
            self.dragon_type = DragonType.DRUID
            char = '₷'
            base_rotation = 315
        elif 'midas' in properties:
            self.dragon_type = DragonType.MIDAS
            char = 'ꬸ'
            base_rotation = 270
        elif 'fragile' in properties:
            self.dragon_type = DragonType.FRAGILE
            char = 'ϗ'
            base_rotation = 235
        elif 'brute' in properties:
            self.dragon_type = DragonType.BRUTE
            char = 'Ȣ'
            base_rotation = 90
        
        # Determine domain from properties
        if 'aquatic' in properties:
            self.domain_type = DomainType.AQUATIC
            color = '#004080'
        elif 'mountain' in properties:
            self.domain_type = DomainType.MOUNTAIN
            color = '#808080'
        elif 'verdant' in properties:
            self.domain_type = DomainType.VERDANT
            color = '#008000'
        elif 'scorched' in properties:
            self.domain_type = DomainType.SCORCHED
            color = '#800000'
        
        self.color = color
        self.char = char
        self.create_small("default", color, char)
        self.visual_state = "default"

        # Properties
        self.properties = properties
        self.is_scorched = "scorched" in properties
        self.is_good = "good" in properties
        self.is_evil = "evil" in properties
        self.is_territorial = "territorial" in properties
        
        # Diet flags
        self.is_carnivore = "carnivore" in properties
        self.is_herbivore = "herbivore" in properties
        self.is_greed = "greed" in properties
        self.is_anthropophage = "anthropophage" in properties
        self.is_hungry = False  # Only used by anthropophage

        # Rotation
        self.base_rotation = base_rotation
        self.rotation = base_rotation
        
        self.move_error = 0.0  # For Bresenham-style movement
        
        # State
        from .domain import Domain
        self.domain = Domain(world, self.coordinates, self, self.is_scorched)
        world.add_entity(self.domain)
        self.days_since_hungry: int = 0  # Track for hungry mood every 3 days
        self.mood: DragonMood = None           # Current mood
        
        # Circling state
        self.circle_angle = 0.0     # Current angle around target (radians)
    
    def on_dawn(self) -> None:
        """Dawn: age, check death, build schedule."""
        if self.process_aging():
            return
        
        self.build_schedule()
    
    def die(self, reason: str) -> None:
        """Handle dragon death - domain becomes treasury."""
        super().die(reason)

        if self.domain:
            self.domain.is_treasury = True
        
    def get_lifespan(self) -> int:
        """Calculate lifespan based on active spires."""
        spire_count = sum(1 for e in list(self.world.entities) 
                         if e.__class__.__name__ == 'Spire' and e.is_alive)
        return LIFESPAN_BASE_DAYS + (LIFESPAN_PER_SPIRE * spire_count)
    
    def find_path(self, destination, max_search = 5000):
        return True  # Dragons can move anywhere, so pathfinding always succeeds
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        data = {
            "coordinates": self.coordinates,
            "in_transit": self.in_transit,
            "name": self.name,
            "properties": self.properties,
            "mood": self.mood.value,
            "age_days": self.age_days,
            "rotation": self.rotation,
            "pronouns": f"{self.pronouns.subject}/{self.pronouns.object}/{self.pronouns.possessive}",
            "schedule": self.get_schedule_summary(),
        }
        return data


from .schedule import build_schedule
Dragon.build_schedule = build_schedule

from .movement import update_movement
Dragon.update_movement = update_movement

from .actions import start_action, check_for_encounters, resolve_engagement
Dragon.start_action = start_action
Dragon.check_for_encounters = check_for_encounters
Dragon.resolve_engagement = resolve_engagement

from .domain import Domain

__all__ = ['Dragon', 'DragonMood', 'DragonType', 'DomainType', 'DragonAlignment', 'DragonDiet', 'Domain']