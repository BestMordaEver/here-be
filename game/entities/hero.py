"""Hero - protector of settlements and slayer of dragons."""
from .base import Coordinates, Mobile, Thinking, Mortal, Settlement
from typing import TYPE_CHECKING, Dict, Any, List
import random

if TYPE_CHECKING:
    from game.world import World
    from . import City, Village, Dragon


# Hero constants
STARTING_LIFE = 100  # Hero starting HP
HEAL_RATE = 2  # HP healed per cycle in settlement
PATROL_RANGE = 15  # Range to look for threats
PROTECTION_RANGE = 10  # Range to rush to defend
ATTACK_DAMAGE = 15  # Damage dealt to enemies
ATTACK_COOLDOWN = 5  # Cycles between attacks
PARTY_SIZE_MIN = 3
PARTY_SIZE_MAX = 5
LOITER_TIME = 2  # Cycles between movements


class Hero(Mortal, Mobile, Thinking):
    """A hero that protects settlements and fights dragons."""
    
    def __init__(self, coordinates: Coordinates, home: 'City'):
        Mobile.__init__(self, "#FFD700", "♦", coordinates, life=STARTING_LIFE)  # Gold color
        Thinking.__init__(self, intent="patrolling")
        self.home = home
        self.loiter = LOITER_TIME
        self.path: List[Coordinates] = []
        self.last_attack_cycle = -999
        self.party: List['Hero'] = None  # Party for dragon hunting
        self.target_entity = None  # Current target (bandit, dragon, etc.)
    
    def is_passable(self, coordinates: Coordinates, world) -> bool:
        """Heroes can move through fields."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
            return False
        
        height = world.height_map[y][x]
        biome = world.get_biome_from_height(height)
        
        # Can move through fields and forests
        if biome not in ('field', 'forest'):
            return False
        
        return True
    
    def is_in_settlement(self, world) -> bool:
        """Check if hero is currently in a settlement."""
        for entity in world.entities:
            if isinstance(entity, Settlement) and entity.is_alive:
                if entity.occupies(self.coordinates):
                    return True
        return False
    
    def find_nearby_threat(self, world) -> tuple:
        """Find nearby threats (bandits attacking, caravans in danger).
        Returns (threat_entity, victim_entity) or (None, None)."""
        # Check for bandits near caravans or villages
        for entity in world.entities:
            if entity.__class__.__name__ == 'Bandit' and entity.is_alive:
                dist = self.get_distance(entity.coordinates)
                if dist <= PROTECTION_RANGE:
                    # Check if bandit is threatening something
                    for target in world.entities:
                        if target.__class__.__name__ in ('Caravan', 'Village') and target.is_alive:
                            if entity.get_distance(target.coordinates) <= 5:
                                return (entity, target)
        
        return (None, None)
    
    def find_dragon(self, world) -> 'Dragon':
        """Find a dragon to hunt (requires party)."""
        for entity in world.entities:
            if entity.__class__.__name__ == 'Dragon' and entity.is_alive:
                return entity
        return None
    
    def find_nearby_heroes(self, world) -> List['Hero']:
        """Find other heroes nearby for forming a party."""
        heroes = []
        for entity in world.entities:
            if entity.__class__.__name__ == 'Hero' and entity.is_alive and entity != self:
                if self.get_distance(entity.coordinates) <= PATROL_RANGE:
                    if entity.party is None:  # Not already in a party
                        heroes.append(entity)
        return heroes
    
    def form_party(self, world) -> bool:
        """Try to form a party for dragon hunting."""
        if self.party is not None:
            return True  # Already in a party
        
        nearby_heroes = self.find_nearby_heroes(world)
        
        # Need at least PARTY_SIZE_MIN - 1 other heroes (plus self)
        if len(nearby_heroes) >= PARTY_SIZE_MIN - 1:
            party_size = min(len(nearby_heroes) + 1, PARTY_SIZE_MAX)
            party = [self] + nearby_heroes[:party_size - 1]
            
            # Set party reference for all members
            for hero in party:
                hero.party = party
                hero.intent = "dragon hunting"
            
            return True
        
        return False
    
    def choose_target(self, world) -> None:
        """Decide what to do based on current situation."""
        # Priority 1: Respond to nearby threats
        threat, victim = self.find_nearby_threat(world)
        if threat:
            self.target_entity = threat
            self.destination = threat.coordinates
            self.intent = "protecting"
            self.path = self.find_path(threat.coordinates, world)
            self.state = "moving"
            return
        
        # Priority 2: Form party and hunt dragons
        dragon = self.find_dragon(world)
        if dragon and (self.party or self.form_party(world)):
            self.target_entity = dragon
            self.destination = dragon.coordinates
            self.intent = "dragon hunting"
            self.path = self.find_path(dragon.coordinates, world)
            self.state = "moving"
            return
        
        # Priority 3: Patrol near home city
        if self.home.is_alive:
            # Random patrol destination near home
            hx, hy = self.home.coordinates
            dx = random.randint(-PATROL_RANGE, PATROL_RANGE)
            dy = random.randint(-PATROL_RANGE, PATROL_RANGE)
            target = (hx + dx, hy + dy)
            
            if self.is_passable(target, world):
                self.destination = target
                self.intent = "patrolling"
                self.path = self.find_path(target, world)
                self.state = "moving"
                return
        
        # Default: stay put
        self.intent = "resting"
        self.state = "arrived"
    
    def approach_target(self, world) -> None:
        """Move towards current destination."""
        # Update path if target moved
        if self.target_entity and hasattr(self.target_entity, 'coordinates'):
            if self.target_entity.is_alive:
                self.destination = self.target_entity.coordinates
                self.path = self.find_path(self.destination, world)
        
        if not self.path and self.destination:
            self.path = self.find_path(self.destination, world)
        
        if self.path:
            next_step = self.path.pop(0)
            self.move_to(next_step)
    
    def attack(self, target, world) -> None:
        """Attack an enemy."""
        if hasattr(target, 'hurt'):
            target.hurt(world, ATTACK_DAMAGE, "hero attack")
            self.think(f"Strike! For the city!")
            self.last_attack_cycle = world.update_count
    
    def update(self, world: 'World') -> None:
        # Heal if in settlement
        if self.is_in_settlement(world):
            self.heal(HEAL_RATE)
        
        # Generate thoughts
        self.generate_thought(world)
        
        super().update(world)
        
        # Attack nearby enemies
        if world.update_count - self.last_attack_cycle >= ATTACK_COOLDOWN:
            # Check for adjacent enemies
            for entity in world.entities:
                if entity.__class__.__name__ in ('Bandit', 'Dragon') and entity.is_alive:
                    if self.get_distance(entity.coordinates) <= 2:
                        self.attack(entity, world)
                        break
        
        # Choose new action if needed
        if self.state in ("created", "arrived"):
            self.target_entity = None
            self.choose_target(world)
        
        # Disband party if dragon is dead
        if self.party and self.target_entity:
            if hasattr(self.target_entity, 'is_dead') and self.target_entity.is_dead:
                for hero in self.party:
                    hero.party = None
                    hero.target_entity = None
                    hero.intent = "patrolling"
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize hero to dictionary for JSON output."""
        data = super().serialize()
        data["home"] = self.home.name if self.home else "none"
        data["intent"] = self.intent
        data["in_party"] = self.party is not None
        data["debug_info"] = f"Hero at {self.coordinates} intent: {self.intent}, party: {len(self.party) if self.party else 0}"
        return data
