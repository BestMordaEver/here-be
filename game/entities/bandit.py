"""Bandit entity with day-based scheduling and encounter reactions."""
from enum import Enum
from random import random, choice
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from .base import (
    Coordinates, Mobile, Mortal, Settlement, Scheduled, 
    ActionType, ScheduledAction, Aging, EngagementType
)

if TYPE_CHECKING:
    from game.world import World


# Bandit constants
ATTACK_RANGE = 8
MELEE_RANGE = 2
FOREST_SEARCH_RADIUS = 20
FEAR_RADIUS = 10           # Distance at which dragons/heroes are noticed
DAYS_WITHOUT_ROBBERY = 3   # Days without robbing before attacking villages
MAX_BLESSINGS = 3          # Max blessings carried


class BanditBehavior(Enum):
    """Alternating daily behaviors."""
    LURKING = "lurking"     # Hide in forest, ambush caravans
    SEEKING = "seeking"     # Seek lairs, treasuries, ruins to pillage


class Bandit(Mortal, Mobile, Scheduled, Aging):
    """Bandits that ambush caravans and pillage ruins."""
    
    LIFESPAN_DAYS = 50  # Bandit dies after this many days (same as heroes)

    def __init__(self, world: 'World', coordinates: Coordinates):
        Mobile.__init__(self, world, "#960000", 'Ω', coordinates, loiter=1)  # Bandits skip 1 cycle
        Scheduled.__init__(self)
        self.init_aging()
        
        self.behavior = BanditBehavior.LURKING
        self.blessings = 0  # Stolen blessings (max 3)
        self.days_since_robbery = 0
        self.hiding_spot: Optional[Coordinates] = None
        self.fleeing_from = None  # Entity we're fleeing from
    
    def is_passable(self, coordinates: Coordinates) -> bool:
        """Bandits can move through fields and forests."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= len(self.world.height_map[0]) or y >= len(self.world.height_map):
            return False
        
        height = self.world.height_map[y][x]
        biome = self.world.get_biome_from_height(height)
        
        if biome not in ('field', 'forest'):
            return False
        
        # Can't move through settlements
        for entity in self.world.entities:
            if isinstance(entity, Settlement) and entity.occupies(coordinates):
                return False
        
        return True
    
    def is_in_forest(self) -> bool:
        """Check if bandit is currently in a forest tile."""
        x, y = self.coordinates
        height = self.world.height_map[y][x]
        return self.world.get_biome_from_height(height) == 'forest'
    
    def find_nearby_forest(self) -> Optional[Coordinates]:
        """Find nearest forest tile to hide in."""
        best_distance = float('inf')
        best_coord = None
        
        for radius in range(1, FOREST_SEARCH_RADIUS):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    
                    x, y = self.coordinates[0] + dx, self.coordinates[1] + dy
                    if x < 0 or y < 0 or x >= self.world.WIDTH or y >= self.world.HEIGHT:
                        continue
                    
                    height = self.world.height_map[y][x]
                    if self.world.get_biome_from_height(height) == 'forest':
                        dist = (dx**2 + dy**2)**0.5
                        if dist < best_distance:
                            best_distance = dist
                            best_coord = (x, y)
            
            if best_coord:
                break
        
        return best_coord
    
    def on_old_age_death(self) -> None:
        """Clear blessings before dying of old age so nothing drops."""
        self.blessings = 0
    
    def die(self, reason: str) -> None:
        """Handle bandit death - drop blessings."""
        # Drop blessings (already 0 if old age via on_old_age_death)
        if self.blessings > 0:
            from .blessing import drop_blessing
            drop_blessing(self.world, self.coordinates, self.blessings)
            self.blessings = 0
        
        super().die(reason)
    
    def on_dawn(self) -> None:
        """Dawn: age, check death, build schedule."""
        if self.process_aging():
            return
        
        self.build_schedule()
    
    def build_schedule(self) -> None:
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
            self._schedule_lurking()
        else:
            self._schedule_seeking()
    
    def _schedule_lurking(self) -> None:
        """Schedule: hide in forest, wait to ambush caravans."""
        actions = []
        
        # Find a forest spot if not in one
        if not self.is_in_forest():
            forest = self.find_nearby_forest()
            if forest:
                self.hiding_spot = forest
                actions.append((ActionType.MOVE_TO, forest))
        
        # If desperate (3 days without robbery), attack village
        if self.days_since_robbery >= DAYS_WITHOUT_ROBBERY:
            village = self._find_nearby_village()
            if village:
                actions.append((ActionType.ATTACK, village))
        else:
            # Otherwise just lurk and wait
            actions.append((ActionType.IDLE, None))
            actions.append((ActionType.WANDER, None))
        
        if actions:
            self.schedule_actions(actions)
    
    def _schedule_seeking(self) -> None:
        """Schedule: seek out lairs, treasuries, ruins to pillage."""
        actions = []
        
        # Look for pillage targets
        target = self._find_pillage_target()
        
        if target:
            actions.append((ActionType.MOVE_TO, target.coordinates))
            actions.append((ActionType.PILLAGE, target))
        else:
            # Wander looking for opportunities
            actions.append((ActionType.WANDER, None))
            actions.append((ActionType.WANDER, None))
        
        # If desperate, attack village
        if self.days_since_robbery >= DAYS_WITHOUT_ROBBERY:
            village = self._find_nearby_village()
            if village:
                actions.append((ActionType.ATTACK, village))
        
        self.schedule_actions(actions)
    
    def _find_nearby_village(self) -> Optional[Any]:
        """Find a village to raid."""
        villages = []
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Village' and entity.is_alive:
                dist = self.get_distance(entity.coordinates)
                if dist <= 30:
                    villages.append((dist, entity))
        
        if villages:
            villages.sort(key=lambda x: x[0])
            return villages[0][1]
        return None
    
    def _find_pillage_target(self) -> Optional[Any]:
        """Find a treasury, ruin, or unguarded domain to pillage."""
        targets = []
        
        for entity in self.world.entities:
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
    
    def _find_nearby_caravan(self) -> Optional[Any]:
        """Find a nearby caravan to ambush."""
        for entity in self.world.entities:
            if entity.__class__.__name__ == 'Caravan' and entity.is_alive:
                if self.get_distance(entity.coordinates) <= ATTACK_RANGE:
                    return entity
        return None
    
    def on_hour(self, hour: int) -> None:
        """Process hourly updates."""
        if self.is_sleeping:
            return
        
        # If lurking in forest, check for caravans to ambush
        if self.behavior == BanditBehavior.LURKING and self.is_in_forest():
            caravan = self._find_nearby_caravan()
            if caravan:
                # Interrupt to attack
                attack = ScheduledAction(
                    hour=hour,
                    action_type=ActionType.ATTACK,
                    target=caravan,
                    priority=10
                )
                self.interrupt_for_encounter(attack)
                self.set_target_entity(caravan)
                return
        
        # Check for scheduled action
        action = self.get_action_for_hour(hour)
        if action:
            self.start_action(action)
            self._execute_action_start(action)
    
    def _execute_action_start(self, action: ScheduledAction) -> None:
        """Start executing a scheduled action."""
        if action.action_type == ActionType.MOVE_TO:
            if isinstance(action.target, tuple):
                self.set_destination(action.target)
            elif hasattr(action.target, 'coordinates'):
                self.set_destination(action.target.coordinates)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.WANDER:
            # Pick random nearby location
            from random import randint
            x = self.coordinates[0] + randint(-15, 15)
            y = self.coordinates[1] + randint(-15, 15)
            x = max(0, min(self.world.WIDTH - 1, x))
            y = max(0, min(self.world.HEIGHT - 1, y))
            self.set_destination((x, y))
            
        elif action.action_type == ActionType.IDLE:
            self.complete_current_action()
            
        elif action.action_type == ActionType.ATTACK:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_target_entity(action.target)
            else:
                self.complete_current_action()
                
        elif action.action_type == ActionType.PILLAGE:
            if action.target and hasattr(action.target, 'coordinates'):
                self.set_destination(action.target.coordinates)
            else:
                self.complete_current_action()
    
    def on_arrival(self) -> None:
        """Called when arriving at destination."""
        if not self.current_action:
            return
        
        action = self.current_action
        
        if action.action_type == ActionType.ATTACK:
            self._execute_attack()
        elif action.action_type == ActionType.PILLAGE:
            self._execute_pillage()
        else:
            self.complete_current_action()
    
    def _execute_attack(self) -> None:
        """
        Initiate engagement with target. Resolution happens at hour-end.
        For caravans: robbery. For settlements: raid. For heroes: combat.
        """
        from game.world.combat import initiate_robbery, initiate_combat
        
        target = self.target_entity
        
        if not target or not target.is_alive:
            self.complete_current_action()
            return
        
        target_type = target.__class__.__name__
        
        if target_type == 'Caravan':
            # Initiate robbery - doesn't check for heroes, that's an interrupt
            initiate_robbery(self, target, self.world)
        elif target_type in ('Village', 'City'):
            # Raid settlement - also via robbery engagement
            initiate_robbery(self, target, self.world)
        elif target_type == 'Hero':
            # Engage hero in combat - we don't know their mood yet!
            initiate_combat(self, target, self.world)
        else:
            # Fallback to legacy instant resolution
            from game.world.combat import resolve_attack
            resolve_attack(self, target, self.world)
            self.complete_current_action()
    
    def _execute_pillage(self) -> None:
        """Pillage a treasury or ruins using engagement system."""
        from game.world.combat import initiate_pillage
        
        target = self.target_entity
        
        if not target:
            self.complete_current_action()
            return
        
        # Check if target can be pillaged
        can_pillage = False
        if hasattr(target, 'can_be_pillaged') and target.can_be_pillaged():
            can_pillage = True
        elif hasattr(target, 'ruin_blessings') and target.ruin_blessings > 0:
            can_pillage = True
        elif hasattr(target, 'treasure') and target.treasure > 0:
            can_pillage = True
        
        if can_pillage:
            initiate_pillage(self, target, self.world)
            # Don't complete action - engagement resolves at hour-end
        else:
            self.think("Nothing left to take.")
            self.complete_current_action()
    
    def check_for_encounters(self) -> Optional[Mobile]:
        """Check for dragons (flee). Heroes don't scare bandits - bandits don't know their mood."""
        nearby = self.get_nearby_entities(self.world, FEAR_RADIUS)
        
        for entity in nearby:
            # Fear dragons
            if entity.__class__.__name__ == 'Dragon':
                return entity
            
            # Note: Bandits do NOT flee from heroes preemptively.
            # They don't know the hero's mood until combat resolves.
        
        return None
    
    def react_to_encounter(self, other: 'Mobile') -> Optional[ScheduledAction]:
        """React to encounters - flee from dragons only."""
        if other.__class__.__name__ == 'Dragon':
            # Flee from dragon - disengage from any current engagement
            if self.is_engaged():
                self.disengage("A dragon! I must flee!")
            
            self.fleeing_from = other
            self.flee_from(other)
            return ScheduledAction(
                hour=self.world.time.current_hour,
                action_type=ActionType.FLEE,
                target=None,
                priority=100
            )
        
        # Bandits don't flee from heroes - they don't know the mood
        return None
    
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
                break
    
    def on_hour_end(self, hour: int) -> None:
        """
        Resolve any active engagement at hour-end.
        This is where robbery/combat outcomes are determined.
        """
        if not self.current_engagement:
            return
        
        from game.world.combat import resolve_engagement
        
        # Resolve the engagement
        resolve_engagement(self.current_engagement, self.world)
        
        # Clear engagement and complete action
        self.current_engagement = None
        self.complete_current_action()
        
        # Try to resume previous action if we were interrupted into this engagement
        if self._interrupted_action:
            if hasattr(self._interrupted_action.target, 'is_alive'):
                if self._interrupted_action.target.is_alive:
                    self.resume_after_encounter()

    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        data = super().serialize()
        data.update({
            "behavior": self.behavior.value,
            "blessings": self.blessings,
            "days_since_robbery": self.days_since_robbery,
            "schedule": self.get_schedule_summary(),
        })
        return data
