"""Scheduled entity mixin - for entities that plan their day."""
from dataclasses import dataclass, field
from enum import Enum
from random import randint, shuffle
from typing import Dict, Iterator, List, Optional, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World
    from game.world.time_system import GameTime
    from .mobile import Mobile


# Time key type alias for clarity
TimeKey = Tuple[int, int]  # (day, hour)

# Default timing constants (can be overridden per-entity)
DEFAULT_DUSK_HOUR = 20       # Default hour when entities wind down
DEFAULT_SLEEP_DURATION = 8   # Default hours of sleep


class ActionType(Enum):
    """Types of scheduled actions."""
    # Lifecycle
    WAKE = "wake"                 # Wake up and build schedule
    SLEEP = "sleep"               # Sleeping
    
    # Movement
    MOVE_TO = "move_to"           # Move to a location/entity
    RETURN_HOME = "return_home"   # Return to home/domain
    WANDER = "wander"             # Random movement
    FLEE = "flee"                 # Flee from threat
    
    # Combat/Interaction
    ATTACK = "attack"             # Attack a target
    PROTECT = "protect"           # Protect a target
    ESCORT = "escort"             # Escort a caravan
    
    # Dragon-specific
    FEED = "feed"                 # Seek food
    TEND = "tend"                 # Tend to a spirit
    HOARD = "hoard"               # Accumulate treasure
    
    # Hero-specific
    PATROL = "patrol"             # Patrol for threats
    REST = "rest"                 # Rest in settlement
    PILLAGE = "pillage"           # Pillage ruins/treasury
    
    # Settlement-specific
    TRADE = "trade"               # Trade at destination
    DELIVER = "deliver"           # Deliver goods
    SETTLE = "settle"             # Create a camp
    REPAIR = "repair"             # Restore settlement HP
    SPAWN_HERO = "spawn_hero"     # Spawn a hero from the settlement
    EXPAND = "expand"             # Send settler caravan to create camp
    
    # General
    IDLE = "idle"                 # Do nothing


@dataclass
class ScheduledAction:
    """An action scheduled for a specific time."""
    day: int                      # Day number
    hour: int                     # Hour (0-23)
    action_type: ActionType       # Type of action
    target: Any = None            # Target entity or coordinates
    
    @property
    def time_key(self) -> TimeKey:
        """Get the (day, hour) key for this action."""
        return (self.day, self.hour)
    
    def __str__(self) -> str:
        target_str = ""
        if self.target:
            if hasattr(self.target, 'name'):
                target_str = f" -> {self.target.name}"
            elif hasattr(self.target, 'coordinates'):
                target_str = f" -> {self.target.coordinates}"
            elif isinstance(self.target, tuple):
                target_str = f" -> {self.target}"
        return f"D{self.day} {self.hour:02d}:00 {self.action_type.value}{target_str}"


class Schedule:
    """
    Rolling schedule with (day, hour) keys.
    
    Manages a dictionary of scheduled actions indexed by time,
    with utilities for finding free slots, handling conflicts,
    and trimming past entries.
    """
    
    def __init__(self):
        self._actions: Dict[TimeKey, ScheduledAction] = {}
    
    def get(self, day: int, hour: int) -> Optional[ScheduledAction]:
        """Get action at specific time, or None."""
        return self._actions.get((day, hour))
    
    def has(self, day: int, hour: int) -> bool:
        """Check if a time slot is occupied."""
        return (day, hour) in self._actions
    
    def set(self, action: ScheduledAction) -> bool:
        """
        Set action at its scheduled time.
        Returns False if slot is already occupied.
        """
        key = action.time_key
        if key in self._actions:
            return False
        self._actions[key] = action
        return True
    
    def remove(self, day: int, hour: int) -> Optional[ScheduledAction]:
        """Remove and return action at specific time."""
        return self._actions.pop((day, hour), None)
    
    def find_free_slot(
        self,
        day: int,
        preferred_hour: int,
        anchor_hour: int,
        current_day: int,
        current_hour: int,
        direction: int = -1
    ) -> Optional[TimeKey]:
        """
        Find a free time slot, searching from preferred_hour.
        
        Args:
            day: Day to search
            preferred_hour: Ideal hour for the action
            anchor_hour: Dusk hour - prefer not to exceed (but will if necessary)
            current_day: Current game day
            current_hour: Current game hour
            direction: -1 = search backwards first, 1 = search forwards first
        
        Returns:
            (day, hour) tuple of free slot, or None if no slot available
        """
        # Can't schedule in the past
        if day < current_day or (day == current_day and preferred_hour <= current_hour):
            preferred_hour = current_hour + 1
            if preferred_hour >= 24:
                day += 1
                preferred_hour = 0
        
        # Try the preferred hour first
        if not self.has(day, preferred_hour):
            return (day, preferred_hour)
        
        # Search in preferred direction first (backwards toward start of day)
        if direction == -1:
            # Search backwards from preferred, but not into past
            min_hour = current_hour + 1 if day == current_day else 0
            for h in range(preferred_hour - 1, min_hour - 1, -1):
                if not self.has(day, h):
                    return (day, h)
            # Then search forwards toward anchor
            for h in range(preferred_hour + 1, anchor_hour + 1):
                if not self.has(day, h):
                    return (day, h)
            # Finally, overflow past anchor if needed
            for h in range(anchor_hour + 1, 24):
                if not self.has(day, h):
                    return (day, h)
        else:
            # Search forwards first
            for h in range(preferred_hour + 1, 24):
                if not self.has(day, h):
                    return (day, h)
            # Then backwards
            min_hour = current_hour + 1 if day == current_day else 0
            for h in range(preferred_hour - 1, min_hour - 1, -1):
                if not self.has(day, h):
                    return (day, h)
        
        # No slot found on this day - try next day
        for h in range(0, 24):
            if not self.has(day + 1, h):
                return (day + 1, h)
        
        return None
    
    def push_action(
        self,
        day: int,
        hour: int,
    ) -> bool:
        """
        Push the action at (day, hour) to the next available slot.
        Cascades if necessary.
        
        Returns True if successful, False if couldn't find space.
        """
        action = self.get(day, hour)
        if not action:
            return True  # Nothing to push
        
        # Find next free slot starting from hour + 1
        next_slot = None
        search_day = day
        search_hour = hour + 1
        
        while next_slot is None:
            if search_hour >= 24:
                search_day += 1
                search_hour = 0
            
            if not self.has(search_day, search_hour):
                next_slot = (search_day, search_hour)
            else:
                search_hour += 1
            
            # Safety: don't search more than 48 hours ahead
            if (search_day - day) * 24 + (search_hour - hour) > 48:
                return False
        
        # If the next slot has an action, cascade first
        if self.has(next_slot[0], next_slot[1]):
            if not self.push_action(next_slot[0], next_slot[1]):
                return False
        
        # Move the action
        self.remove(day, hour)
        action.day = next_slot[0]
        action.hour = next_slot[1]
        self._actions[next_slot] = action
        return True
    
    def trim_past(self, day: int, hour: int) -> int:
        """
        Remove all actions before the given time.
        Returns number of actions removed.
        """
        keys_to_remove = [k for k in self._actions if k < (day, hour)]
        for k in keys_to_remove:
            del self._actions[k]
        return len(keys_to_remove)
    
    def find_future_action(
        self,
        action_type: ActionType,
        day: int,
        hour: int
    ) -> Optional[ScheduledAction]:
        """Find an action of given type if it's scheduled in the future."""
        for (d, h), action in self._actions.items():
            if (d, h) > (day, hour) and action.action_type == action_type:
                return action
        return None
    
    def get_next_action(self, day: int, hour: int) -> Optional[ScheduledAction]:
        """Get the next scheduled action after the given time."""
        future_actions = [
            (k, v) for k, v in self._actions.items()
            if k > (day, hour)
        ]
        if not future_actions:
            return None
        future_actions.sort(key=lambda x: x[0])
        return future_actions[0][1]
    
    def iter_actions(self) -> Iterator[ScheduledAction]:
        """Iterate over all actions in chronological order."""
        for key in sorted(self._actions.keys()):
            yield self._actions[key]
    
    def __len__(self) -> int:
        return len(self._actions)
    
    def __contains__(self, key: TimeKey) -> bool:
        return key in self._actions


@dataclass
class PlannedAction:
    """An action to be scheduled, before time assignment."""
    action_type: ActionType
    target: Any = None
    metadata: dict = field(default_factory=dict)


class DayPlanner:
    """
    Helper class to plan actions with dusk as anchor.
    
    Actions are placed working backwards from dusk, only overflowing
    past dusk if there's no room earlier in the day.
    
    commit() automatically schedules SLEEP at dusk and WAKE after sleep_duration.
    
    Usage:
        planner = entity.plan_day()
        planner.add(ActionType.FEED)
        planner.add(ActionType.PATROL)
        planner.add(ActionType.REST)
        planner.commit()  # Writes to schedule + schedules sleep/wake
    """
    
    def __init__(
        self,
        schedule: Schedule,
        day: int,
        dusk_hour: int,
        current_day: int,
        current_hour: int,
        sleep_duration: int = DEFAULT_SLEEP_DURATION,
        randomness: int = 1,
    ):
        self.schedule = schedule
        self.day = day
        self.dusk_hour = dusk_hour
        self.current_day = current_day
        self.current_hour = current_hour
        self.sleep_duration = sleep_duration
        self.randomness = randomness
        self._planned: List[PlannedAction] = []
    
    def add(
        self,
        action_type: ActionType,
        target: Any = None,
    ) -> 'DayPlanner':
        """Add an action to be scheduled. Returns self for chaining."""
        self._planned.append(PlannedAction(
            action_type=action_type,
            target=target
        ))
        return self
    
    def clear(self) -> 'DayPlanner':
        """Clear all pending actions."""
        self._planned = []
        return self
    
    def commit(self, randomize: bool = False) -> List[ScheduledAction]:
        """
        Assign times to all actions and write to schedule.
        
        Strategy:
        1. Calculate ideal hours spread evenly before dusk
        2. For each action, find nearest free slot (preferring backwards)
        3. If no room before dusk, overflow past it
        
        Returns list of created ScheduledActions.
        """
        if not self._planned:
            return []
        
        # Determine available window
        start_hour = self.current_hour + 1 if self.day == self.current_day else 0
        end_hour = self.dusk_hour
        available = end_hour - start_hour
        
        if available < 1:
            # No time before dusk - start from dusk
            start_hour = self.dusk_hour
            available = 24 - start_hour
        
        count = len(self._planned)
        spacing = max(1, available / count) if count > 0 else 1
        
        result: List[ScheduledAction] = []

        if randomize:
            # Shuffle the planned actions to add randomness to their order
            shuffle(self._planned)
        
        for i, planned in enumerate(self._planned):
            # Calculate preferred hour (spread evenly, anchor at dusk)
            # Place last action near dusk, work backwards
            reverse_i = count - 1 - i
            preferred = end_hour - int((reverse_i + 0.5) * spacing)
            
            # Apply randomness
            if self.randomness > 0:
                preferred += randint(-self.randomness, self.randomness)
            preferred = max(start_hour, min(end_hour, preferred))
            
            # Find actual free slot
            slot = self.schedule.find_free_slot(
                day=self.day,
                preferred_hour=preferred,
                anchor_hour=self.dusk_hour,
                current_day=self.current_day,
                current_hour=self.current_hour,
                direction=-1  # Prefer backwards
            )
            
            if slot is None:
                # Couldn't place action - this shouldn't happen often
                continue
            
            action = ScheduledAction(
                day=slot[0],
                hour=slot[1],
                action_type=planned.action_type,
                target=planned.target
            )
            
            self.schedule.set(action)
            result.append(action)
        
        self._planned = []
        
        # Schedule sleep/wake cycle - sleep after all actions are done
        # Find the last scheduled action's time
        last_action_time = (self.day, self.dusk_hour)  # Default to dusk
        if result:
            # Get the latest action we just scheduled
            last_action_time = max((a.day, a.hour) for a in result)
        
        # Sleep at the hour after last action
        sleep_day = last_action_time[0]
        sleep_hour = last_action_time[1] + 1
        
        # Handle hour overflow
        if sleep_hour >= 24:
            sleep_day += 1
            sleep_hour = 0
        
        # If sleep would be before dusk on the same day, push to dusk
        if (sleep_day, sleep_hour) < (self.day, self.dusk_hour):
            sleep_day = self.day
            sleep_hour = self.dusk_hour
        
        # Can't sleep in the past
        if (sleep_day, sleep_hour) <= (self.current_day, self.current_hour):
            sleep_day = self.current_day
            sleep_hour = self.current_hour + 1
            if sleep_hour >= 24:
                sleep_day += 1
                sleep_hour = 0
    
        self.schedule.set(ScheduledAction(
            day=sleep_day,
            hour=sleep_hour,
            action_type=ActionType.SLEEP
        ))
        
        # Schedule WAKE after sleep_duration
        wake_hour = (sleep_hour + self.sleep_duration) % 24
        wake_day = sleep_day + ((sleep_hour + self.sleep_duration) // 24)
        
        self.schedule.set(ScheduledAction(
            day=wake_day,
            hour=wake_hour,
            action_type=ActionType.WAKE
        ))


class Scheduled:
    """
    Mixin for entities that plan their activities using a rolling schedule.
    
    Key features:
    - Schedule is a dict keyed by (day, hour)
    - Dusk is the anchor - actions scheduled backwards from dusk
    - Sleep/wake cycle is entity-controlled (not world-triggered)
    - Configurable dusk_hour and sleep_duration per entity
    """
    
    # Override these in subclasses for different timing
    dusk_hour: int = DEFAULT_DUSK_HOUR
    sleep_duration: int = DEFAULT_SLEEP_DURATION
    
    def __init__(self):
        self.schedule: Schedule = Schedule()
        self.current_action: Optional[ScheduledAction] = None
    
    @property
    def world(self) -> 'World':
        """Access to world instance. Must be set by entity's __init__."""
        raise NotImplementedError("Subclass must provide world access")
    
    def _current_time(self) -> TimeKey:
        """Get current (day, hour) from world."""
        return (self.world.time.current_day, self.world.time.current_hour)
    
    def build_schedule(self) -> None:
        """
        Build the day's schedule. Called by WAKE action.
        Override in subclasses for entity-specific scheduling.
        
        Base implementation just schedules sleep/wake via an empty plan_day().
        Subclasses should call plan_day().add(...).commit() which handles sleep.
        """
        # Trim old entries
        day, hour = self._current_time()
        self.schedule.trim_past(day, hour)
        
        # Default: just schedule sleep/wake (subclasses override to add actions)
        self.plan_day().commit()
    
    def plan_day(self, randomness: int = 1) -> DayPlanner:
        """
        Get a DayPlanner for adding actions to today's schedule.
        
        commit() automatically schedules SLEEP at dusk and WAKE after sleep.
        
        Usage:
            planner = self.plan_day()
            planner.add(ActionType.FEED).add(ActionType.PATROL).add(ActionType.REST)
            planner.commit()  # Also schedules sleep/wake
        """
        day, hour = self._current_time()
        return DayPlanner(
            schedule=self.schedule,
            day=day,
            dusk_hour=self.dusk_hour,
            current_day=day,
            current_hour=hour,
            sleep_duration=self.sleep_duration,
            randomness=randomness
        )
    
    def schedule_action(
        self,
        action_type: ActionType,
        target: Any = None,
        preferred_hour: Optional[int] = None
    ) -> Optional[ScheduledAction]:
        """
        Schedule a single action, finding a free slot.
        
        Args:
            action_type: Type of action
            target: Target entity or coordinates
            preferred_hour: Ideal hour (defaults to middle of remaining day)
            **metadata: Additional data
        
        Returns:
            The created ScheduledAction, or None if couldn't schedule
        """
        day, hour = self._current_time()
        
        if preferred_hour is None:
            # Default to middle of remaining day before dusk
            remaining = self.dusk_hour - hour
            preferred_hour = hour + remaining // 2
        
        slot = self.schedule.find_free_slot(
            day=day,
            preferred_hour=preferred_hour,
            anchor_hour=self.dusk_hour,
            current_day=day,
            current_hour=hour
        )
        
        if slot is None:
            return None
        
        action = ScheduledAction(
            day=slot[0],
            hour=slot[1],
            action_type=action_type,
            target=target
        )
        self.schedule.set(action)
        return action
    
    def interrupt_current(self, reactive_action: ScheduledAction) -> None:
        """
        Interrupt current action to handle an encounter.
        
        The current action is pushed to next available hour (cascading if needed),
        and the reactive action takes its place.
        """
        day, hour = self._current_time()

        if self.current_action:
            interrupted_action = self.current_action
            
            # Push the interrupted action to next hour
            # First, find where it currently is and remove it
            old_key = self.current_action.time_key
            self.schedule.remove(old_key[0], old_key[1])
            
            # Find new slot for it (next hour, cascade if needed)
            new_slot = self.schedule.find_free_slot(
                day=day,
                preferred_hour=hour + 1,
                anchor_hour=self.dusk_hour,
                current_day=day,
                current_hour=hour,
                direction=1  # Search forwards
            )
            
            if new_slot:
                interrupted_action.day = new_slot[0]
                interrupted_action.hour = new_slot[1]
                self.schedule.set(interrupted_action)

        # Set the reactive action as current
        self.current_action = reactive_action
        
        # Also add reactive action to schedule for this hour
        reactive_action.day = day
        reactive_action.hour = hour
        # Don't add to schedule dict - it's immediate and won't conflict
    
    def start_action(self, action: ScheduledAction) -> None:
        """Begin executing an action."""
        self.current_action = action
        
        # Handle special action types
        if action.action_type == ActionType.WAKE:
            self._on_wake()
    
    def complete_current_action(self) -> None:
        """Mark the current action as completed."""
        if self.current_action:
            self.current_action = None
    
    def _on_wake(self) -> None:
        self.build_schedule()
    
    def _on_sleep(self) -> None:
        pass
    
    def on_hour(self, hour: int) -> None:
        """
        Called each hour by the world. Check for scheduled actions.
        Override in subclasses for custom hourly behavior, but call super().
        """
        day = self.world.time.current_day
        
        # Safety check: ensure we have a future WAKE action
        if not self.schedule.find_future_action(ActionType.WAKE, day, hour):
            # Also check if we're currently sleeping (wake scheduled for later)
            if not (self.current_action and self.current_action.action_type == ActionType.SLEEP):
                self._emergency_wake(day, hour)
        
        # Check for scheduled action this hour
        action = self.schedule.get(day, hour)
        if action:
            self.start_action(action)
    
    def _emergency_wake(self, day: int, hour: int) -> None:
        """Safety mechanism: force a wake action if none scheduled."""
        if hasattr(self, 'think'):
            self.think("Something stirs me to wakefulness.")
        
        # Create immediate wake action
        wake_action = ScheduledAction(
            day=day,
            hour=hour,
            action_type=ActionType.WAKE
        )
        self.start_action(wake_action)
    
    # -------------------------------------------------------------------------
    # Compatibility methods for migration from old API
    # -------------------------------------------------------------------------
    
    def schedule_actions(
        self,
        actions: List[Tuple[ActionType, Any]],
        randomness: int = 1,
    ) -> List[ScheduledAction]:
        """
        COMPATIBILITY: Schedule multiple actions spread across the day.
        
        Prefer using plan_day() for new code:
            self.plan_day().add(ActionType.X, target).add(...).commit()
        
        Args:
            actions: List of (ActionType, target) tuples
            randomness: Hour randomness (±randomness)
        
        Returns:
            List of created ScheduledActions
        """
        planner = self.plan_day(randomness=randomness)
        for action_type, target in actions:
            planner.add(action_type, target)
        return planner.commit()
    
    def check_for_encounters(self) -> None:
        """
        Check for nearby entities that trigger encounters.
        Override in subclasses for entity-specific encounter logic.
        """
        return
    
    def get_schedule_summary(self) -> List[str]:
        """Get a human-readable summary of the schedule."""
        return [str(action) for action in self.schedule.iter_actions()]
    
    def is_sleeping(self) -> bool:
        """Check if entity is currently sleeping."""
        return (
            self.current_action is not None 
            and self.current_action.action_type == ActionType.SLEEP
        )
