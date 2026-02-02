"""Bandit entity with day-based scheduling and encounter reactions."""
from enum import Enum
from random import random, choice
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from .base import Coordinates, Mobile, Thinking, Mortal, Settlement, Scheduled, ActionType, ScheduledAction, Aging

if TYPE_CHECKING:
    from game.world import World


# Bandit constants
ATTACK_RANGE = 8
MELEE_RANGE = 2
FOREST_SEARCH_RADIUS = 20
FEAR_RADIUS = 10           # Distance at which dragons/heroes are noticed
DAYS_WITHOUT_ROBBERY = 3   # Days without robbing before attacking villages
MAX_TRINKETS = 3           # Max blessings carried


class BanditBehavior(Enum):
    """Alternating daily behaviors."""
    LURKING = "lurking"     # Hide in forest, ambush caravans
    SEEKING = "seeking"     # Seek lairs, treasuries, ruins to pillage


class Bandit(Mortal, Mobile, Thinking, Scheduled, Aging):
    """Bandits that ambush caravans and pillage ruins."""
    
    LIFESPAN_DAYS = 50  # Bandit dies after this many days (same as heroes)

    def __init__(self, coordinates: Coordinates):
        Mobile.__init__(self, "#960000", 'Ω', coordinates, loiter=1)  # Bandits skip 1 cycle
        Thinking.__init__(self, intent="lurking")
        Scheduled.__init__(self)
        self.init_aging()
        
        self.behavior = BanditBehavior.LURKING
        self.trinkets = 0  # Stolen blessings (max 3)
        self.days_since_robbery = 0
        self.hiding_spot: Optional[Coordinates] = None
        self.fleeing_from = None  # Entity we're fleeing from
    
    def is_passable(self, coordinates: Coordinates, world: 'World') -> bool:
        """Bandits can move through fields and forests."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
            return False
        
        height = world.height_map[y][x]
        biome = world.get_biome_from_height(height)
        
        if biome not in ('field', 'forest'):
            return False
        
        # Can't move through settlements
        for entity in world.entities:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                return False
        
        return True
    
    def is_in_forest(self, world: 'World') -> bool:
        """Check if bandit is currently in a forest tile."""
        x, y = self.coordinates
        height = world.height_map[y][x]
        return world.get_biome_from_height(height) == 'forest'
    
    def find_nearby_forest(self, world: 'World') -> Optional[Coordinates]:
        """Find nearest forest tile to hide in."""
        best_distance = float('inf')
        best_coord = None
        
        for radius in range(1, FOREST_SEARCH_RADIUS):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    
                    x, y = self.coordinates[0] + dx, self.coordinates[1] + dy
                    if x < 0 or y < 0 or x >= world.WIDTH or y >= world.HEIGHT:
                        continue
                    
                    height = world.height_map[y][x]
                    if world.get_biome_from_height(height) == 'forest':
                        dist = (dx**2 + dy**2)**0.5
                        if dist < best_distance:
                            best_distance = dist
                            best_coord = (x, y)
            
            if best_coord:
                break
        
        return best_coord
    
    def on_old_age_death(self, world: 'World') -> None:
        """Clear trinkets before dying of old age so nothing drops."""
        self.trinkets = 0
    
    def die(self, world: 'World', reason: str) -> None:
        """Handle bandit death - drop trinkets as blessings."""
        # Drop trinkets (already 0 if old age via on_old_age_death)
        if self.trinkets > 0:
            from .blessing import drop_blessing
            drop_blessing(world, self.coordinates, self.trinkets)
            self.trinkets = 0
        
        super().die(world, reason)
    
    def on_dawn(self, world: 'World') -> None:
        """Dawn: age, check death, build schedule."""
        if self.process_aging(world):
            return
        
        self.build_schedule(world)
    
    def build_schedule(self, world: 'World') -> None:
        """Build daily schedule - alternate between lurking and seeking."""
        self.schedule = []
        self.current_action = None
        self.fleeing_from = None
        
        # Alternate behavior each day
        if self.behavior == BanditBehavior.LURKING:
            self.behavior = BanditBehavior.SEEKING
        else:
            self.behavior = BanditBehavior.LURKING
        
        self.days_since_robbery += 1
        
        if self.behavior == BanditBehavior.LURKING:
            self._schedule_lurking(world)
        else:
            self._schedule_seeking(world)
    
    def _schedule_lurking(self, world: 'World') -> None:
        """Schedule: hide in forest, wait to ambush caravans."""
        # Find a forest spot if not in one
        if not self.is_in_forest(world):
            forest = self.find_nearby_forest(world)
            if forest:
                self.hiding_spot = forest
                self.add_scheduled_action(7, ActionType.MOVE_TO, forest)
        
        # If desperate (3 days without robbery), attack village
        if self.days_since_robbery >= DAYS_WITHOUT_ROBBERY:
            village = self._find_nearby_village(world)
            if village:
                self.add_scheduled_action(14, ActionType.ATTACK, village)
                self.think("Hunger drives me to desperate measures.")
        else:
            # Otherwise just lurk and wait
            self.add_scheduled_action(10, ActionType.IDLE)
            self.add_scheduled_action(15, ActionType.WANDER)
        
        self.think("I shall wait in ambush today.")
    
    def _schedule_seeking(self, world: 'World') -> None:
        """Schedule: seek out lairs, treasuries, ruins to pillage."""
        # Look for pillage targets
        target = self._find_pillage_target(world)
        
        if target:
            self.add_scheduled_action(8, ActionType.MOVE_TO, target.coordinates)
            self.add_scheduled_action(12, ActionType.PILLAGE, target)
            self.think("Treasure awaits the bold.")
        else:
            # Wander looking for opportunities
            self.add_scheduled_action(9, ActionType.WANDER)
            self.add_scheduled_action(14, ActionType.WANDER)
            self.think("I seek fortune today.")
        
        # If desperate, attack village
        if self.days_since_robbery >= DAYS_WITHOUT_ROBBERY:
            village = self._find_nearby_village(world)
            if village:
                self.add_scheduled_action(16, ActionType.ATTACK, village)
    
    def _find_nearby_village(self, world: 'World') -> Optional[Any]:
        """Find a village to raid."""
        villages = []
        for entity in world.entities:
            if entity.__class__.__name__ == 'Village' and entity.is_alive:
                dist = self.get_distance(entity.coordinates)
                if dist <= 30:
                    villages.append((dist, entity))
        
        if villages:
            villages.sort(key=lambda x: x[0])
            return villages[0][1]
        return None
    
    def _find_pillage_target(self, world: 'World') -> Optional[Any]:
        """Find a treasury, ruin, or unguarded domain to pillage."""
        targets = []
        
        for entity in world.entities:
            # Treasury (dead dragon domain with treasure)
            if entity.__class__.__name__ == 'Domain':
                if hasattr(entity, 'is_treasury') and entity.is_treasury:
                    if hasattr(entity, 'treasure') and entity.treasure > 0:
                        targets.append(entity)
            
            # Ruins (dead settlement)
            if entity.__class__.__name__ in ('Village', 'City'):
                if entity.is_dead:
                    targets.append(entity)
        
        if targets:
            return choice(targets)
        return None
    
    def _find_nearby_caravan(self, world: 'World') -> Optional[Any]:
        """Find a nearby caravan to ambush."""
        for entity in world.entities:
            if entity.__class__.__name__ == 'Caravan' and entity.is_alive:
                if self.get_distance(entity.coordinates) <= ATTACK_RANGE:
                    return entity
        return None
    
    def on_hour(self, world: 'World', hour: int) -> None:
        """Process hourly updates."""
        if self.is_sleeping:
            return
        
        # If lurking in forest, check for caravans to ambush
        if self.behavior == BanditBehavior.LURKING and self.is_in_forest(world):
            caravan = self._find_nearby_caravan(world)
            if caravan:
                # Interrupt to attack
                attack = ScheduledAction(
                    hour=hour,
                    action_type=ActionType.ATTACK,
                    target=caravan,
                    priority=10
                )
                self.interrupt_for_encounter(attack)
                self.set_target_entity(caravan, world)
                self.think("A caravan! Perfect prey.")
                return
        
        # Check for scheduled action
        action = self.get_action_for_hour(hour)
        if action:
            self.start_action(action)
            self._execute_action_start(world, action)
    
    def _execute_action_start(self, world: 'World', action: ScheduledAction) -> None:
        """Start executing a scheduled action."""
        if action.action_type == ActionType.MOVE_TO:
            if isinstance(action.target, tuple):
                self.set_destination(action.target, world)
            elif hasattr(action.target, 'coordinates'):
                self.set_destination(action.target.coordinates, world)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.WANDER:
            # Pick random nearby location
            from random import randint
            x = self.coordinates[0] + randint(-15, 15)
            y = self.coordinates[1] + randint(-15, 15)
            x = max(0, min(world.WIDTH - 1, x))
            y = max(0, min(world.HEIGHT - 1, y))
            self.set_destination((x, y), world)
            
        elif action.action_type == ActionType.IDLE:
            self.complete_current_action()
            
        elif action.action_type == ActionType.ATTACK:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_target_entity(action.target, world)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.PILLAGE:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_destination(action.target.coordinates, world)
            else:
                self.complete_current_action()
    
    def on_arrival(self, world: 'World') -> None:
        """Called when arriving at destination."""
        if not self.current_action:
            return
        
        action = self.current_action
        
        if action.action_type == ActionType.ATTACK:
            self._execute_attack(world)
        elif action.action_type == ActionType.PILLAGE:
            self._execute_pillage(world)
        else:
            self.complete_current_action()
    
    def _execute_attack(self, world: 'World') -> None:
        """Execute an attack on target using combat resolution."""
        from game.world.combat import resolve_attack
        
        target = self.target_entity
        
        if not target or not target.is_alive:
            self.complete_current_action()
            return
        
        resolve_attack(self, target, world)
        self.complete_current_action()
    
    def _execute_pillage(self, world: 'World') -> None:
        """Pillage a treasury or ruins."""
        target = self.target_entity
        
        if not target:
            self.complete_current_action()
            return
        
        # Steal blessings/treasure
        if hasattr(target, 'treasure') and target.treasure > 0:
            take = min(MAX_TRINKETS - self.trinkets, target.treasure)
            self.trinkets += take
            target.treasure -= take
            self.days_since_robbery = 0
            self.think(f"Pillaged {take} blessings!")
        
        self.complete_current_action()
    
    def check_for_encounters(self, world: 'World') -> Optional[Mobile]:
        """Check for dragons (flee) or heroes (danger)."""
        nearby = self.get_nearby_entities(world, FEAR_RADIUS)
        
        for entity in nearby:
            # Fear dragons
            if entity.__class__.__name__ in ('Dragon', 'DragonBase'):
                return entity
            
            # Fear vengeful heroes
            if entity.__class__.__name__ == 'Hero':
                if hasattr(entity, 'mood') and entity.mood == 'vengeful':
                    return entity
        
        return None
    
    def react_to_encounter(self, world: 'World', other: 'Mobile') -> Optional[ScheduledAction]:
        """React to encounters - flee from dragons and heroes."""
        if other.__class__.__name__ in ('Dragon', 'DragonBase'):
            # Flee from dragon
            self.fleeing_from = other
            self.flee_from(other, world)
            self.think("A dragon! I must flee!")
            return ScheduledAction(
                hour=world.time.current_hour,
                action_type=ActionType.FLEE,
                target=None,
                priority=100
            )
        
        if other.__class__.__name__ == 'Hero':
            if hasattr(other, 'mood') and other.mood == 'vengeful':
                # Try to flee from vengeful hero
                self.fleeing_from = other
                self.flee_from(other, world)
                self.think("A vengeful hero! Run!")
                return ScheduledAction(
                    hour=world.time.current_hour,
                    action_type=ActionType.FLEE,
                    target=None,
                    priority=100
                )
        
        return None
    
    def update_movement(self, world: 'World') -> None:
        """Update movement and pick up any blessings at current location."""
        super().update_movement(world)
        
        # Try to pick up blessings at current location
        if self.trinkets < MAX_TRINKETS:
            self._try_pickup_blessings(world)
    
    def _try_pickup_blessings(self, world: 'World') -> None:
        """Pick up dropped blessings at current location as trinkets."""
        from .blessing import Blessing
        
        for entity in world.entities:
            if isinstance(entity, Blessing) and entity.coordinates == self.coordinates:
                can_take = MAX_TRINKETS - self.trinkets
                taken = entity.take(can_take)
                if taken > 0:
                    self.trinkets += taken
                    self.think(f"Found {taken} shiny trinket{'s' if taken > 1 else ''}!")
                break
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        data = super().serialize()
        data.update({
            "behavior": self.behavior.value,
            "trinkets": self.trinkets,
            "days_since_robbery": self.days_since_robbery,
            "schedule": self.get_schedule_summary(),
        })
        return data
