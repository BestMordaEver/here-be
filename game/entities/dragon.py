"""Dragon entity with mood-based daily scheduling."""
from dataclasses import dataclass
from enum import Enum
from math import atan2, degrees
from random import randint, choice, random
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from .base import Coordinates, Mobile, Named, Thinking, Mortal, Scheduled, ActionType, ScheduledAction, ActionState, Aging

if TYPE_CHECKING:
    from game.world import World
    from . import Domain, Spirit


# Dragon constants
LIFESPAN_BASE_DAYS = 20  # Dragon dies after this many days
LIFESPAN_PER_SPIRE = 5   # Extra days per active spire

# Encounter radii
SCARE_RADIUS = 8         # Radius that scares bandits/cattle
PROTECTION_RADIUS = 10   # Radius for good dragons to protect humans
TERRITORIAL_RADIUS = 12  # Radius for territorial attacks

# Spirit tending
TEND_RADIUS_DRUID = 8    # Druids tend all spirits in this radius
TEND_RADIUS_NORMAL = 3   # Normal dragons tend single spirit


class DragonMood(Enum):
    """Dragon daily moods determining behavior."""
    DREARY = "dreary"       # Tends hoard, attacks if not good
    INSPIRED = "inspired"   # Tends hoard, travels to distant spirits
    PENSIVE = "pensive"     # Feeds once, tends nearby spirit
    HUNGRY = "hungry"       # Feeds twice, rests between (every 3 days)
    COVETOUS = "covetous"   # Attacks settlement, steals blessing


@dataclass
class DragonPronouns:
    """Pronoun set for a dragon."""
    subject: str = "it"      # he/she/they/it
    object: str = "it"       # him/her/them/it  
    possessive: str = "its"  # his/her/their/its
    
    @classmethod
    def from_string(cls, pronoun_str: str) -> 'DragonPronouns':
        """Parse pronouns from string like 'he/him/his'."""
        if not pronoun_str:
            return cls()
        parts = pronoun_str.split('/')
        if len(parts) >= 3:
            return cls(parts[0], parts[1], parts[2])
        return cls()


class Dragon(Mortal, Mobile, Named, Thinking, Scheduled, Aging):
    """Base dragon class with mood-based scheduling."""

    def __init__(
        self,
        world: 'World',
        name: str,
        properties: List[str],
        coordinates: Coordinates,
        pronouns: str = None,
    ):
        # Determine dragon type from properties
        if 'serpent' in properties:
            self.dragon_type = 'serpent'
            char = 'Ȿ'
            base_rotation = 270
        elif 'blade' in properties:
            self.dragon_type = 'blade'
            char = '%'
            base_rotation = 315
        elif 'druid' in properties:
            self.dragon_type = 'druid'
            char = '₷'
            base_rotation = 315
        elif 'midas' in properties:
            self.dragon_type = 'midas'
            char = 'ꬸ'
            base_rotation = 270
        elif 'fragile' in properties:
            self.dragon_type = 'fragile'
            char = 'ϗ'
            base_rotation = 235
        elif 'brute' in properties:
            self.dragon_type = 'brute'
            char = 'Ȣ'
            base_rotation = 90
        
        # Determine domain from properties
        if 'aquatic' in properties:
            self.domain_type = 'aquatic'
            color = '#004080'
        elif 'mountain' in properties:
            self.domain_type = 'mountain'
            color = '#808080'
        elif 'verdant' in properties:
            self.domain_type = 'verdant'
            color = '#008000'
        elif 'scorched' in properties:
            self.domain_type = 'scorched'
            color = '#800000'

        # Initialize base classes
        Mobile.__init__(self, world, color, char, coordinates, loiter=0)  # Dragons move every cycle
        Named.__init__(self, name)
        Thinking.__init__(self)
        Scheduled.__init__(self)
        
        # Rotation for visual display
        self.base_rotation = base_rotation
        self.rotation = base_rotation
        self.move_error = 0.0  # For Bresenham-style movement
        
        # Properties
        self.properties = properties
        self.is_scorched = "scorched" in properties
        self.is_good = "good" in properties
        self.is_evil = "evil" in properties
        self.is_territorial = "territorial" in properties
        
        # Diet flags (used by schedule building)
        self.is_carnivore = "carnivore" in properties
        self.is_herbivore = "herbivore" in properties
        self.is_greed = "greed" in properties
        self.is_anthropophage = "anthropophage" in properties
        
        # Pronouns
        self.pronouns = DragonPronouns.from_string(pronouns)
        
        # State
        from . import Domain
        self.domain = Domain(world, self.coordinates, self, self.is_scorched)
        world.add_entity(self.domain)
        self.init_aging()
        self.mood = DragonMood.PENSIVE
        self.days_since_hungry = 0  # Track for hungry mood every 3 days
        self.blessings = 0  # Blessings in domain (midas can have up to 10)
        
        # Current action tracking
        self.current_target = None  # Entity or coordinates being approached
    
    def get_lifespan(self) -> int:
        """Calculate lifespan based on active spires."""
        spire_count = sum(1 for e in self.world.entities 
                         if e.__class__.__name__ == 'Spire' and e.is_alive)
        return LIFESPAN_BASE_DAYS + (LIFESPAN_PER_SPIRE * spire_count)
    
    def determine_mood(self) -> DragonMood:
        """Determine today's mood based on conditions."""
        # Hungry every 3 days (unless greed)
        if not self.is_greed and self.days_since_hungry >= 3:
            self.days_since_hungry = 0
            return DragonMood.HUNGRY
        
        # Greed dragons get covetous when they would be hungry
        if self.is_greed and self.days_since_hungry >= 3:
            self.days_since_hungry = 0
            if self.is_good:  # Good dragons become inspired instead
                return DragonMood.INSPIRED
            return DragonMood.COVETOUS
        
        # Covetous for evil dragons occasionally
        if self.is_evil and random() < 0.2:
            if not self.is_good:  # Good dragons become inspired instead
                return DragonMood.COVETOUS
            return DragonMood.INSPIRED
        
        # Random between dreary, inspired, pensive
        roll = random()
        if roll < 0.3:
            return DragonMood.DREARY
        elif roll < 0.6:
            return DragonMood.INSPIRED
        else:
            return DragonMood.PENSIVE
    
    def build_schedule(self) -> None:
        """Build the day's schedule based on mood."""
        self.schedule = []
        self.current_action = None
        
        # Ensure domain exists
        if self.domain is None:
            self.create_domain(self.world)
        
        self.mood = self.determine_mood()
        self.days_since_hungry += 1
        
        if self.mood == DragonMood.DREARY:
            self._schedule_dreary()
        elif self.mood == DragonMood.INSPIRED:
            self._schedule_inspired()
        elif self.mood == DragonMood.PENSIVE:
            self._schedule_pensive()
        elif self.mood == DragonMood.HUNGRY:
            self._schedule_hungry()
        elif self.mood == DragonMood.COVETOUS:
            self._schedule_covetous()
        
        # Always end day by returning home
        self.add_scheduled_action(19, ActionType.RETURN_HOME, self.domain)
        
        self.think(f"Today I feel {self.mood.value}.")
    
    def _schedule_dreary(self) -> None:
        """Dreary: tend hoard, attack if not good."""
        self.add_scheduled_action(8, ActionType.TEND_HOARD)
        if not self.is_good:
            target = self._find_human_target()
            if target:
                self.add_scheduled_action(12, ActionType.ATTACK, target)
        if self.is_evil:
            settlement = self._find_settlement_target()
            if settlement:
                self.add_scheduled_action(15, ActionType.ATTACK, settlement)
    
    def _schedule_inspired(self) -> None:
        """Inspired: tend hoard, visit distant spirits."""
        self.add_scheduled_action(8, ActionType.TEND_HOARD)
        spirits = self._find_distant_spirits(count=2)
        if len(spirits) >= 1:
            self.add_scheduled_action(10, ActionType.TEND_SPIRIT, spirits[0])
        if len(spirits) >= 2:
            self.add_scheduled_action(14, ActionType.TEND_SPIRIT, spirits[1])
    
    def _schedule_pensive(self) -> None:
        """Pensive: feed once, tend nearby spirit."""
        self.add_scheduled_action(9, ActionType.FEED)
        spirit = self._find_nearby_spirit()
        if spirit:
            self.add_scheduled_action(14, ActionType.TEND_SPIRIT, spirit)
    
    def _schedule_hungry(self) -> None:
        """Hungry: feed, rest, feed again."""
        if self.is_anthropophage:
            self.add_scheduled_action(8, ActionType.FEED)
            self.add_scheduled_action(14, ActionType.REST)
        else:
            self.add_scheduled_action(8, ActionType.FEED)
            self.add_scheduled_action(12, ActionType.REST)
            self.add_scheduled_action(16, ActionType.FEED)
        if self.is_evil:
            target = self._find_human_target()
            if target:
                for action in self.schedule:
                    if action.action_type == ActionType.REST:
                        action.action_type = ActionType.ATTACK
                        action.target = target
                        break
    
    def _schedule_covetous(self) -> None:
        """Covetous: attack settlement, steal blessing."""
        settlement = self._find_settlement_with_blessing()
        if not settlement:
            settlement = self._find_settlement_target()
        if settlement:
            self.add_scheduled_action(10, ActionType.ATTACK, settlement)
    
    def _find_human_target(self) -> Optional[Any]:
        """Find a human entity to attack."""
        humans = []
        for entity in self.world.entities:
            if entity.__class__.__name__ in ('Hero', 'Bandit', 'Caravan'):
                if entity.is_alive:
                    humans.append(entity)
        if humans:
            return choice(humans)
        return None
    
    def _find_settlement_target(self) -> Optional[Any]:
        """Find a settlement to attack."""
        settlements = []
        for entity in self.world.entities:
            if entity.__class__.__name__ in ('Village', 'City', 'Camp'):
                if entity.is_alive:
                    settlements.append(entity)
        if settlements:
            return choice(settlements)
        return None
    
    def _find_settlement_with_blessing(self) -> Optional[Any]:
        """Find a settlement that has blessings to steal."""
        settlements = []
        for entity in self.world.entities:
            if entity.__class__.__name__ in ('Village', 'City'):
                if entity.is_alive and hasattr(entity, 'blessings') and entity.blessings > 0:
                    settlements.append(entity)
        if settlements:
            return choice(settlements)
        return None
    
    def _find_nearby_spirit(self) -> Optional['Spirit']:
        """Find a spirit near the domain."""
        if not self.domain:
            return None
        
        spirits = []
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Spirit' and entity.is_alive:
                dist = self.domain.get_distance(entity.coordinates)
                if dist <= 30:  # Within reasonable range
                    spirits.append((dist, entity))
        
        if spirits:
            spirits.sort(key=lambda x: x[0])
            return spirits[0][1]
        return None
    
    def _find_distant_spirits(self, count: int = 2) -> List['Spirit']:
        """Find distant spirits to visit."""
        if not self.domain:
            return []
        
        spirits = []
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Spirit' and entity.is_alive:
                dist = self.domain.get_distance(entity.coordinates)
                if dist > 30:  # Far from domain
                    spirits.append((dist, entity))
        
        # Sort by distance, return furthest
        spirits.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in spirits[:count]]
    
    def on_hour(self, hour: int) -> None:
        """Process hourly updates."""
        if self.is_sleeping:
            return
        
        # Check for scheduled action
        action = self.get_action_for_hour(hour)
        if action:
            self.start_action(action)
            self._execute_action_start(action)
    
    def _execute_action_start(self, action: ScheduledAction) -> None:
        """Start executing a scheduled action."""
        if action.action_type == ActionType.TEND_HOARD:
            # Instant - generate blessing
            self.blessings += 1
            max_blessings = 10 if self.dragon_type == 'midas' else 5
            self.blessings = min(self.blessings, max_blessings)
            self.think("I tend to my hoard, feeling it grow.")
            self.complete_current_action()
            
        elif action.action_type == ActionType.FEED:
            # Find food based on diet and start moving toward it
            self._start_feeding()
            
        elif action.action_type == ActionType.TEND_SPIRIT:
            if action.target:
                self.set_target_entity(action.target, self.world)
                self.current_target = action.target
                self.think(f"I shall visit the spirit.")
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.ATTACK:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_target_entity(action.target, self.world)
                self.current_target = action.target
                self.think("Destruction awaits.")
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.RETURN_HOME:
            if self.domain:
                self.set_destination(self.domain.coordinates, self.world)
                self.think("Time to return to my domain.")
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.REST:
            self.think("I rest and gather my strength.")
            self.complete_current_action()
    
    def _start_feeding(self) -> None:
        """Start feeding behavior based on diet."""
        if self.is_greed:
            # Greed dragons don't feed - tend hoard instead
            self.blessings += 1
            self.think("Gold is my sustenance.")
            self.complete_current_action()
            return
        
        # Find appropriate food
        target = None
        
        if self.is_carnivore:
            target = self._find_cattle()
        elif self.is_herbivore:
            target = self._find_grazing_spot()
        elif self.is_anthropophage:
            target = self._find_human_target()
        
        if target:
            if isinstance(target, tuple):
                self.set_destination(target, self.world)
            else:
                self.set_target_entity(target, self.world)
            self.current_target = target
            self.think("Hunger drives me.")
        else:
            self.think("No prey to be found.")
            self.complete_current_action()
    
    def _find_cattle(self) -> Optional[Any]:
        """Find cattle to hunt."""
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Cattle' and entity.is_alive:
                if self.get_distance(entity.coordinates) <= 50:
                    return entity
        return None
    
    def _find_grazing_spot(self) -> Optional[Coordinates]:
        """Find a plains tile to graze."""
        for _ in range(20):
            x = randint(0, self.world.WIDTH - 1)
            y = randint(0, self.world.HEIGHT - 1)
            if self.world.get_biome_from_height(self.world.height_map[y][x]) == 'field':
                return (x, y)
        return None
    
    def update_movement(self) -> None:
        """Process movement using Bresenham-style approach."""
        if self.state != "moving" or not self.destination:
            return

        # Check diagonal debt (unless blade type ignores it)
        if self.dragon_type != 'blade' and self.should_skip_movement():
            return

        self._bresenham_move()
        
        # Check if arrived
        if self.coordinates == self.destination:
            self.state = "arrived"
            self._on_movement_complete()
    
    def _bresenham_move(self) -> None:
        """Move using Bresenham line algorithm for smooth movement."""
        target_coords = self.destination
        
        dx_full = target_coords[0] - self.coordinates[0]
        dy_full = target_coords[1] - self.coordinates[1]
        
        if dx_full == 0 and dy_full == 0:
            return
        
        abs_dx = abs(dx_full)
        abs_dy = abs(dy_full)
        
        dx = 0
        dy = 0
        
        if abs_dx == 0:
            dy = 1 if dy_full > 0 else -1
        elif abs_dy == 0:
            dx = 1 if dx_full > 0 else -1
        else:
            ratio = abs_dy / abs_dx
            
            if abs_dx >= abs_dy:
                dx = 1 if dx_full > 0 else -1
                self.move_error += ratio
                if self.move_error >= 1.0:
                    dy = 1 if dy_full > 0 else -1
                    self.move_error -= 1.0
            else:
                dy = 1 if dy_full > 0 else -1
                self.move_error += 1.0 / ratio
                if self.move_error >= 1.0:
                    dx = 1 if dx_full > 0 else -1
                    self.move_error -= 1.0
        
        # Update rotation for visual
        if dx != 0 or dy != 0:
            heading = degrees(atan2(dy, dx))
            self.rotation = heading - self.base_rotation
        
        # Move (blade type ignores diagonal debt)
        self.move_to(
            (self.coordinates[0] + dx, self.coordinates[1] + dy),
            forego_debt=self.dragon_type == 'blade'
        )
    
    def _on_movement_complete(self) -> None:
        """Called when movement to target completes."""
        if not self.current_action:
            return
        
        action = self.current_action
        
        if action.action_type == ActionType.FEED:
            self._complete_feeding()
        elif action.action_type == ActionType.TEND_SPIRIT:
            self._complete_tending()
        elif action.action_type == ActionType.ATTACK:
            self._complete_attack()
        elif action.action_type == ActionType.RETURN_HOME:
            self.complete_current_action()
    
    def _complete_feeding(self) -> None:
        """Complete a feeding action."""
        if self.current_target and hasattr(self.current_target, 'is_alive'):
            if self.current_target.is_alive:
                if self.is_carnivore or self.is_anthropophage:
                    # Kill the target
                    self.current_target.die(f"eaten by {self.name}")
                self.think("My hunger is sated.")
        
        self.complete_current_action()
        self.current_target = None
    
    def _complete_tending(self) -> None:
        """Complete tending a spirit. Druid type tends all spirits in range."""
        if self.dragon_type == 'druid':
            # Area tenders bless all spirits within radius
            count = 0
            for entity in self.world.entities:
                if entity.__class__.__name__ == 'Spirit' and entity.is_alive:
                    if self.get_distance(entity.coordinates) <= TEND_RADIUS_DRUID:
                        if not getattr(entity, 'has_blessing', False):
                            entity.has_blessing = True
                            count += 1
            if count > 0:
                self.think(f"I bless {count} spirits with my presence.")
            else:
                self.think("The spirits here already flourish.")
        else:
            # Normal dragons tend single spirit
            if self.current_target and self.current_target.__class__.__name__ == 'Spirit':
                if not getattr(self.current_target, 'has_blessing', False):
                    self.current_target.has_blessing = True
                    self.think("I bestow my blessing upon this spirit.")
        
        self.complete_current_action()
        self.current_target = None
    
    def _complete_attack(self) -> None:
        """Complete an attack action using combat resolution."""
        from game.world.combat import resolve_attack
        
        if self.current_target and hasattr(self.current_target, 'is_alive') and self.current_target.is_alive:
            resolve_attack(self, self.current_target, self.world)
        
        self.complete_current_action()
        self.current_target = None
    
    def check_for_encounters(self) -> Optional[Mobile]:
        """Check for entities that trigger encounters."""
        nearby = self.get_nearby_entities(self.world, SCARE_RADIUS)
        
        for entity in nearby:
            # Bandits flee from dragons
            if entity.__class__.__name__ == 'Bandit':
                return entity
            
            # Good dragons protect humans from threats
            if self.is_good:
                if entity.__class__.__name__ in ('Caravan', 'Hero'):
                    # Check if they're being threatened
                    for other in self.get_nearby_entities(self.world, PROTECTION_RADIUS):
                        if other.__class__.__name__ == 'Bandit':
                            return other  # Return the threat to deal with
        
        # Territorial dragons attack nearby humans
        if self.is_territorial and self.domain:
            if self.get_distance(self.domain.coordinates) <= TERRITORIAL_RADIUS:
                for entity in nearby:
                    if entity.__class__.__name__ in ('Hero', 'Caravan', 'Bandit'):
                        return entity
        
        return None
    
    def react_to_encounter(self, other: 'Mobile') -> Optional[ScheduledAction]:
        """React to an encountered entity."""
        # Scare bandits away
        if other.__class__.__name__ == 'Bandit':
            self.think("A bandit flees before me.")
            return None  # No action needed, bandit will flee
        
        # Good dragons protect
        if self.is_good and other.__class__.__name__ == 'Bandit':
            return ScheduledAction(
                hour=self.world.time.current_hour,
                action_type=ActionType.ATTACK,
                target=other,
                priority=10
            )
        
        # Territorial attack
        if self.is_territorial:
            if other.__class__.__name__ in ('Hero', 'Caravan'):
                return ScheduledAction(
                    hour=self.world.time.current_hour,
                    action_type=ActionType.ATTACK,
                    target=other,
                    priority=10
                )
        
        return None
    
    def on_dawn(self) -> None:
        """Dawn: age, check death, build schedule."""
        self.is_sleeping = False
        
        if self.process_aging():
            return
        
        self.build_schedule()
    
    def die(self, reason: str) -> None:
        """Handle dragon death - domain becomes treasury."""
        super().die(reason)
        
        if self.domain:
            self.domain.owner = None
            self.domain.is_treasury = True
            self.domain.treasure = self.blessings
    
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