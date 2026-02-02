"""Hero entity with mood-based daily scheduling."""
from enum import Enum
from random import random, choice, randint
from typing import TYPE_CHECKING, Dict, Any, List, Optional, Set

from .base import Coordinates, Mobile, Thinking, Mortal, Settlement, Scheduled, ActionType, ScheduledAction, Aging

if TYPE_CHECKING:
    from game.world import World
    from . import City, Village, Dragon, Caravan


# Hero constants
PROTECTION_RANGE = 10      # Range to rush to defend
PATROL_RANGE = 15          # Range to look for threats
MAX_BLESSINGS = 3          # Max blessings hero can carry
PARTY_SIZE = 4             # Heroes needed for dragon raid
TIRED_AFTER_DAYS = 48      # Hero becomes permanently tired
TIRED_THRESHOLD = 3        # Consecutive non-tired days before becoming tired


class HeroMood(Enum):
    """Hero daily moods."""
    MERCENARY = "mercenary"
    TIRED = "tired"
    ADVENTUROUS = "adventurous"
    OPPORTUNISTIC = "opportunistic"
    VENGEFUL = "vengeful"
    FOREBODING = "foreboding"
    SUBSERVIENT = "subservient"


class Hero(Mortal, Mobile, Thinking, Scheduled, Aging):
    """A hero that protects settlements and slays dragons."""
    
    LIFESPAN_DAYS = 50  # Hero dies after this many days
    
    def __init__(self, world: 'World', coordinates: Coordinates, home: 'City | Village', city_born: bool = True):
        # City heroes are gold, village heroes are brownish
        color = "#FFD700" if city_born else "#8B6914"
        
        Mobile.__init__(self, world, color, "♦", coordinates, loiter=1)  # Heroes skip 1 cycle
        Thinking.__init__(self, intent="patrolling")
        Scheduled.__init__(self)
        self.init_aging()
        
        self.home = home
        self.city_born = city_born
        self.mood = HeroMood.ADVENTUROUS
        self.consecutive_active_days = 0  # Days without being tired
        self.is_permanently_tired = False
        
        # Party management
        self.party: Optional[List['Hero']] = None
        self.party_leader: Optional['Hero'] = None
        
        # Inventory
        self.blessings = 0
        
        # Memory
        self.known_domains: Set = set()  # Domain locations
        self.acquaintances: Set['Hero'] = set()  # Heroes we know
        self.days_domain_known: Dict = {}  # domain -> days since learned
        self.dead_friend: Optional['Hero'] = None  # Friend who died (triggers vengeful)
    
    def is_passable(self, coordinates: Coordinates) -> bool:
        """Heroes can move through fields and forests."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(self.world.height_map[0]) or y >= len(self.world.height_map):
            return False
        
        height = self.world.height_map[y][x]
        biome = self.world.get_biome_from_height(height)
        
        return biome in ('field', 'forest')
    
    def is_in_settlement(self) -> bool:
        """Check if hero is currently in a settlement."""
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.is_alive:
                if entity.occupies(self.coordinates):
                    return True
        return False
    
    def get_current_settlement(self) -> Optional[Settlement]:
        """Get the settlement the hero is currently in."""
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.is_alive:
                if entity.occupies(self.coordinates):
                    return entity
        return None
    
    def determine_mood(self) -> HeroMood:
        """Determine today's mood based on conditions."""
        # Permanently tired after 48 days
        if self.is_permanently_tired or self.age_days >= TIRED_AFTER_DAYS:
            self.is_permanently_tired = True
            return HeroMood.TIRED
        
        # Following a party leader
        if self.party_leader and self.party_leader != self:
            return HeroMood.SUBSERVIENT
        
        # Leading a full party
        if self.party and len(self.party) >= PARTY_SIZE:
            return HeroMood.FOREBODING
        
        # Vengeful if friend died recently
        if self.dead_friend:
            self.dead_friend = None  # Clear after one day of vengeance
            return HeroMood.VENGEFUL
        
        # Opportunistic if domain known for 10+ days or sees ruins/treasury
        if self.days_domain_known:
            for domain, days in self.days_domain_known.items():
                if days >= 10:
                    return HeroMood.OPPORTUNISTIC
        
        # Check for ruins/treasury nearby
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Domain' and hasattr(entity, 'is_treasury') and entity.is_treasury:
                if self.get_distance(entity.coordinates) <= 30:
                    return HeroMood.OPPORTUNISTIC
        
        # Tired after 3 consecutive active days
        if self.consecutive_active_days >= TIRED_THRESHOLD:
            self.consecutive_active_days = 0
            return HeroMood.TIRED
        
        # Random between mercenary and adventurous
        if random() < 0.3:
            return HeroMood.MERCENARY
        else:
            return HeroMood.ADVENTUROUS
    
    def build_schedule(self) -> None:
        """Build the day's schedule based on mood."""
        self.schedule = []
        self.current_action = None
        
        self.mood = self.determine_mood()
        
        # Increment domain knowledge age
        for domain in list(self.days_domain_known.keys()):
            self.days_domain_known[domain] += 1
        
        if self.mood == HeroMood.MERCENARY:
            self._schedule_mercenary()
            self.consecutive_active_days += 1
        elif self.mood == HeroMood.TIRED:
            self._schedule_tired()
        elif self.mood == HeroMood.ADVENTUROUS:
            self._schedule_adventurous()
            self.consecutive_active_days += 1
        elif self.mood == HeroMood.OPPORTUNISTIC:
            self._schedule_opportunistic()
            self.consecutive_active_days += 1
        elif self.mood == HeroMood.VENGEFUL:
            self._schedule_vengeful()
            self.consecutive_active_days += 1
        elif self.mood == HeroMood.FOREBODING:
            self._schedule_foreboding()
            self.consecutive_active_days += 1
        elif self.mood == HeroMood.SUBSERVIENT:
            self._schedule_subservient()
            self.consecutive_active_days += 1
        
        self.think(f"Today I feel {self.mood.value}.")
    
    def _schedule_mercenary(self) -> None:
        """Escort a caravan."""
        caravan = self._find_caravan_to_escort()
        if caravan:
            self.schedule_actions([(ActionType.ESCORT, caravan)])
        else:
            self._schedule_adventurous()
    
    def _schedule_tired(self) -> None:
        """Rest and protect current settlement."""
        settlement = self.get_current_settlement()
        if settlement:
            self.schedule_actions([
                (ActionType.REST, None),
                (ActionType.PROTECT, settlement),
            ])
        elif self.home and self.home.is_alive:
            self.schedule_actions([
                (ActionType.MOVE_TO, self.home),
                (ActionType.REST, None),
            ])
    
    def _schedule_adventurous(self) -> None:
        """Travel to remote settlements, explore."""
        settlements = self._find_remote_settlements(count=2)
        actions = []
        for settlement in settlements:
            actions.append((ActionType.MOVE_TO, settlement))
        if random() < 0.3:
            actions.append((ActionType.PATROL, None))
        if actions:
            self.schedule_actions(actions)
    
    def _schedule_opportunistic(self) -> None:
        """Pillage ruins/treasury or rob unguarded domain."""
        target = self._find_pillage_target()
        if target:
            self.schedule_actions([
                (ActionType.MOVE_TO, target),
                (ActionType.PILLAGE, target),
            ])
        else:
            domain = self._find_unguarded_domain()
            if domain:
                self.schedule_actions([
                    (ActionType.MOVE_TO, domain),
                    (ActionType.PILLAGE, domain),
                ])
            else:
                self._schedule_adventurous()
    
    def _schedule_vengeful(self) -> None:
        """Hunt bandits."""
        self.schedule_actions([
            (ActionType.PATROL, None),
            (ActionType.PATROL, None),
            (ActionType.PATROL, None),
        ])
    
    def _schedule_foreboding(self) -> None:
        """Lead party to attack dragon domain."""
        if not self.party:
            self._schedule_adventurous()
            return
        domain = self._find_known_domain()
        if domain:
            self.schedule_actions([
                (ActionType.MOVE_TO, domain),
                (ActionType.ATTACK, domain),
            ])
        else:
            self._schedule_adventurous()
    
    def _schedule_subservient(self) -> None:
        """Follow the party leader."""
        if self.party_leader:
            self.schedule_actions([(ActionType.ESCORT, self.party_leader)])
        else:
            self.party = None
            self._schedule_adventurous()
    
    def _find_caravan_to_escort(self) -> Optional[Any]:
        """Find a caravan to escort."""
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Caravan' and entity.is_alive:
                if self.get_distance(entity.coordinates) <= 30:
                    return entity
        return None
    
    def _find_remote_settlements(self, count: int = 2) -> List[Settlement]:
        """Find distant settlements to visit."""
        settlements = []
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.is_alive:
                dist = self.get_distance(entity.coordinates)
                if dist > 20:  # Remote = more than 20 tiles away
                    settlements.append((dist, entity))
        
        settlements.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in settlements[:count]]
    
    def _find_pillage_target(self) -> Optional[Any]:
        """Find ruins or treasury to pillage."""
        for entity in self.world.entities:
            # Treasury
            if entity.__class__.__name__ == 'Domain':
                if hasattr(entity, 'is_treasury') and entity.is_treasury:
                    if hasattr(entity, 'treasure') and entity.treasure > 0:
                        return entity
            
            # Ruins
            if entity.__class__.__name__ in ('Village', 'City'):
                if entity.is_dead:
                    return entity
        
        return None
    
    def _find_unguarded_domain(self) -> Optional[Any]:
        """Find a domain whose dragon is away."""
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Domain' and entity.is_alive:
                if hasattr(entity, 'owner') and entity.owner:
                    dragon = entity.owner
                    # Check if dragon is far from domain
                    if dragon.get_distance(entity.coordinates) > 15:
                        return entity
        return None
    
    def _find_known_domain(self) -> Optional[Any]:
        """Find a domain we know about."""
        for domain in self.known_domains:
            for entity in self.world.entities:
                if entity.__class__.__name__ == 'Domain' and entity.is_alive:
                    if entity.coordinates == domain:
                        return entity
        return None
    
    def _find_nearby_heroes(self) -> List['Hero']:
        """Find other heroes nearby for party formation."""
        heroes = []
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Hero' and entity.is_alive and entity != self:
                if self.get_distance(entity.coordinates) <= PATROL_RANGE:
                    if not entity.party:  # Not already in a party
                        heroes.append(entity)
        return heroes
    
    def try_form_party(self) -> bool:
        """Try to form a dragon-hunting party."""
        if self.party:
            return True
        
        nearby = self._find_nearby_heroes()
        
        if len(nearby) >= PARTY_SIZE - 1:
            party = [self] + nearby[:PARTY_SIZE - 1]
            
            # Set up party
            self.party = party
            self.party_leader = self
            
            for hero in party[1:]:
                hero.party = party
                hero.party_leader = self
                hero.mood = HeroMood.SUBSERVIENT
                self.acquaintances.add(hero)
                hero.acquaintances.add(self)
            
            return True
        
        return False
    
    def disband_party(self) -> None:
        """Disband the party after raid."""
        if not self.party:
            return
        
        for hero in self.party:
            hero.party = None
            hero.party_leader = None
            hero.mood = HeroMood.TIRED
            hero.consecutive_active_days = 0
        
        self.party = None
        self.party_leader = None
    
    def on_hour(self, hour: int) -> None:
        """Process hourly updates."""
        if self.is_sleeping:
            return
        
        # Sell blessings if in city
        if self.blessings > 0:
            settlement = self.get_current_settlement()
            if settlement and settlement.__class__.__name__ == 'City':
                # Sell all blessings
                if hasattr(settlement, 'blessings'):
                    settlement.blessings += self.blessings
                self.blessings = 0
                self.think("Sold my treasures in the city.")
        
        # Try to form party if adventurous and see dragons
        if self.mood == HeroMood.ADVENTUROUS and not self.party:
            for entity in self.world.entities:
                if entity.__class__.__name__ in ('Dragon', 'DragonBase', 'Domain'):
                    if self.get_distance(entity.coordinates) <= PATROL_RANGE:
                        self.known_domains.add(entity.coordinates)
                        self.days_domain_known[entity.coordinates] = 0
        
        # Check for scheduled action
        action = self.get_action_for_hour(hour)
        if action:
            self.start_action(action)
            self._execute_action_start(action)
    
    def _execute_action_start(self, action: ScheduledAction) -> None:
        """Start executing a scheduled action."""
        if action.action_type == ActionType.MOVE_TO:
            if hasattr(action.target, 'coordinates'):
                self.set_destination(action.target.coordinates)
            elif isinstance(action.target, tuple):
                self.set_destination(action.target)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.REST:
            self.think("I rest my weary bones.")
            self.complete_current_action()
            
        elif action.action_type == ActionType.PATROL:
            # Pick random patrol location
            x = self.coordinates[0] + randint(-PATROL_RANGE, PATROL_RANGE)
            y = self.coordinates[1] + randint(-PATROL_RANGE, PATROL_RANGE)
            x = max(0, min(self.world.WIDTH - 1, x))
            y = max(0, min(self.world.HEIGHT - 1, y))
            self.set_destination((x, y))
            
        elif action.action_type == ActionType.ESCORT:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_target_entity(action.target)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.PROTECT:
            # Stay near target
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_destination(action.target.coordinates)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.PILLAGE:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_destination(action.target.coordinates)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.ATTACK:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_target_entity(action.target)
            else:
                self.complete_current_action()
    
    def on_arrival(self) -> None:
        """Called when arriving at destination."""
        if not self.current_action:
            return
        
        action = self.current_action
        
        if action.action_type == ActionType.PILLAGE:
            self._execute_pillage()
        elif action.action_type == ActionType.ATTACK:
            self._execute_attack()
        else:
            self.complete_current_action()
    
    def _execute_pillage(self) -> None:
        """Pillage ruins/treasury/domain."""
        target = self.target_entity
        
        if target and hasattr(target, 'treasure') and target.treasure > 0:
            take = min(MAX_BLESSINGS - self.blessings, target.treasure)
            self.blessings += take
            target.treasure -= take
            self.think(f"Claimed {take} blessings!")
        
        self.complete_current_action()
    
    def _execute_attack(self) -> None:
        """Attack a target (dragon domain or entity)."""
        from game.world.combat import resolve_attack
        
        target = self.target_entity
        
        if not target:
            self.complete_current_action()
            return
        
        # If attacking a domain, get the dragon
        if hasattr(target, 'owner') and target.owner and target.owner.is_alive:
            resolve_attack(self, target.owner, self.world)
        elif hasattr(target, 'owner') and (not target.owner or not target.owner.is_alive):
            # Dragon dead, pillage instead
            self._execute_pillage()
            return
        elif hasattr(target, 'is_alive') and target.is_alive:
            resolve_attack(self, target, self.world)
        
        self.complete_current_action()
    
    def check_for_encounters(self) -> Optional[Mobile]:
        """Check for threats to protect against."""
        nearby = self.get_nearby_entities(PROTECTION_RANGE)
        
        for entity in nearby:
            # Attack bandits (always if vengeful)
            if entity.__class__.__name__ == 'Bandit':
                if self.mood == HeroMood.VENGEFUL or random() < 0.7:
                    return entity
            
            # Protect caravans/settlements from bandits
            if entity.__class__.__name__ in ('Caravan', 'Village', 'Camp'):
                # Check if being attacked by bandit
                for other in self.get_nearby_entities(PROTECTION_RANGE):
                    if other.__class__.__name__ == 'Bandit':
                        return other
        
        return None
    
    def react_to_encounter(self, other: 'Mobile') -> Optional[ScheduledAction]:
        """React to an encountered entity."""
        if other.__class__.__name__ == 'Bandit':
            if self.mood == HeroMood.VENGEFUL:
                # Vengeful heroes kill bandits
                other.die("slain by vengeful hero")
                self.think("Vengeance is mine!")
                return None
            else:
                # Attack bandit
                return ScheduledAction(
                    hour=self.world.time.current_hour,
                    action_type=ActionType.ATTACK,
                    target=other,
                    priority=10
                )
        
        return None
    
    def on_old_age_death(self) -> None:
        """Clear blessings before dying of old age so nothing drops."""
        self.blessings = 0
    
    def on_dawn(self) -> None:
        """Dawn: age, check death, build schedule."""
        self.is_sleeping = False
        
        if self.process_aging():
            return
        
        self.build_schedule()
    
    def die(self, reason: str) -> None:
        """Handle hero death."""
        # Drop blessings (already 0 if old age via on_old_age_death)
        if self.blessings > 0:
            from .blessing import drop_blessing
            drop_blessing(self.world, self.coordinates, self.blessings)
            self.blessings = 0
        
        super().die(reason)
        
        # Notify acquaintances
        for friend in self.acquaintances:
            if friend.is_alive:
                friend.dead_friend = self
        
        # Leave party
        if self.party:
            self.party.remove(self)
    
    def update_movement(self) -> None:
        """Update movement and pick up any blessings at current location."""
        super().update_movement()
        
        # Try to pick up blessings at current location
        if self.blessings < MAX_BLESSINGS:
            self._try_pickup_blessings()
    
    def _try_pickup_blessings(self) -> None:
        """Pick up dropped blessings at current location."""
        from .blessing import Blessing
        
        for entity in self.world.entities:
            if isinstance(entity, Blessing) and entity.coordinates == self.coordinates:
                can_take = MAX_BLESSINGS - self.blessings
                taken = entity.take(can_take)
                if taken > 0:
                    self.blessings += taken
                    self.think(f"Found {taken} blessing{'s' if taken > 1 else ''}!")
                break
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        data = super().serialize()
        data.update({
            "home": self.home.name if self.home and hasattr(self.home, 'name') else "none",
            "mood": self.mood.value,
            "age_days": self.age_days,
            "blessings": self.blessings,
            "in_party": self.party is not None,
            "is_leader": self.party_leader == self if self.party else False,
            "schedule": self.get_schedule_summary(),
        })
        return data
