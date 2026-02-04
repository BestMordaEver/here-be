"""Scheduled entity mixin - for entities that plan their day."""
from dataclasses import dataclass, field
from enum import Enum
from random import randint
from typing import List, Optional, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World
    from game.world.time_system import GameTime
    from .mobile import Mobile


# Active hours for scheduling (exclusive of dawn/dusk transition hours)
SCHEDULE_START_HOUR = 7   # First hour available for scheduled actions
SCHEDULE_END_HOUR = 19    # Last hour available (actions should complete before dusk)


@dataclass
class PlannedAction:
    """An action to be scheduled, before hour assignment."""
    action_type: 'ActionType'
    target: Any = None
    priority: int = 0
    metadata: dict = field(default_factory=dict)


class DayScheduler:
    """
    Helper class to spread actions across the active day with randomness.
    
    Usage:
        scheduler = DayScheduler()
        scheduler.add(ActionType.FEED)
        scheduler.add(ActionType.PATROL)
        scheduler.add(ActionType.REST)
        scheduled_actions = scheduler.build()  # Returns list of (hour, PlannedAction)
    """
    
    def __init__(
        self,
        start_hour: int = SCHEDULE_START_HOUR,
        end_hour: int = SCHEDULE_END_HOUR,
        randomness: int = 1,
    ):
        """
        Initialize the day scheduler.
        
        Args:
            start_hour: First hour available for scheduling (default 7)
            end_hour: Last hour available for scheduling (default 19)
            randomness: Maximum random hour offset (±randomness), default 1
        """
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.randomness = randomness
        self._actions: List[PlannedAction] = []
    
    def add(
        self,
        action_type: 'ActionType',
        target: Any = None,
        priority: int = 0,
        **metadata
    ) -> 'DayScheduler':
        """
        Add an action to be scheduled.
        
        Returns self for method chaining.
        """
        self._actions.append(PlannedAction(
            action_type=action_type,
            target=target,
            priority=priority,
            metadata=metadata
        ))
        return self
    
    def clear(self) -> 'DayScheduler':
        """Clear all pending actions."""
        self._actions = []
        return self
    
    def build(self) -> List[Tuple[int, PlannedAction]]:
        """
        Assign hours to all actions, spreading them evenly with randomness.
        
        Returns:
            List of (hour, PlannedAction) tuples, sorted by hour
        """
        if not self._actions:
            return []
        
        count = len(self._actions)
        available_hours = self.end_hour - self.start_hour + 1  # e.g., 7-19 = 13 hours
        
        result: List[Tuple[int, PlannedAction]] = []
        
        if count == 1:
            # Single action: place in middle of day with randomness
            base_hour = (self.start_hour + self.end_hour) // 2
            hour = self._apply_randomness(base_hour)
            result.append((hour, self._actions[0]))
        else:
            # Multiple actions: spread evenly
            # Calculate spacing between actions
            spacing = available_hours / count
            
            for i, action in enumerate(self._actions):
                # Base hour: start + (i + 0.5) * spacing to center actions in their slots
                base_hour = self.start_hour + int((i + 0.5) * spacing)
                hour = self._apply_randomness(base_hour)
                result.append((hour, action))
        
        # Sort by hour and resolve conflicts
        result.sort(key=lambda x: x[0])
        result = self._resolve_conflicts(result)
        
        return result
    
    def _apply_randomness(self, hour: int) -> int:
        """Apply random offset to an hour, clamping to valid range."""
        if self.randomness > 0:
            offset = randint(-self.randomness, self.randomness)
            hour += offset
        return max(self.start_hour, min(self.end_hour, hour))
    
    def _resolve_conflicts(
        self,
        scheduled: List[Tuple[int, PlannedAction]]
    ) -> List[Tuple[int, PlannedAction]]:
        """
        Resolve hour conflicts by shifting actions that land on the same hour.
        """
        if len(scheduled) <= 1:
            return scheduled
        
        result = [scheduled[0]]
        
        for i in range(1, len(scheduled)):
            hour, action = scheduled[i]
            prev_hour = result[-1][0]
            
            # If same hour as previous, try to shift forward
            if hour <= prev_hour:
                hour = prev_hour + 1
                # Clamp to end hour
                hour = min(hour, self.end_hour)
            
            result.append((hour, action))
        
        return result


class ActionType(Enum):
    """Types of scheduled actions."""
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
    TEND_SPIRIT = "tend_spirit"   # Tend to a spirit
    TEND_HOARD = "tend_hoard"     # Accumulate treasure
    CIRCLE = "circle"             # Circle around target
    
    # Hero-specific
    PATROL = "patrol"             # Patrol for threats
    REST = "rest"                 # Rest in settlement
    PILLAGE = "pillage"           # Pillage ruins/treasury
    
    # Settlement-specific
    TRADE = "trade"               # Trade at destination
    DELIVER = "deliver"           # Deliver goods
    SETTLE = "settle"             # Create a camp
    
    # General
    IDLE = "idle"                 # Do nothing
    SLEEP = "sleep"               # Sleeping (night)


class ActionState(Enum):
    """State of a scheduled action."""
    PENDING = "pending"           # Not yet started
    IN_PROGRESS = "in_progress"   # Currently executing
    COMPLETED = "completed"       # Finished successfully
    INTERRUPTED = "interrupted"   # Was interrupted by encounter
    CANCELLED = "cancelled"       # Was cancelled


@dataclass
class ScheduledAction:
    """An action scheduled for a specific hour."""
    hour: int                     # Hour to start (0-23)
    action_type: ActionType       # Type of action
    target: Any = None            # Target entity or coordinates
    state: ActionState = ActionState.PENDING
    priority: int = 0             # Higher = more important (for interruption decisions)
    metadata: dict = field(default_factory=dict)  # Additional action-specific data
    
    def __str__(self) -> str:
        target_str = ""
        if self.target:
            if hasattr(self.target, 'name'):
                target_str = f" -> {self.target.name}"
            elif hasattr(self.target, 'coordinates'):
                target_str = f" -> {self.target.coordinates}"
            elif isinstance(self.target, tuple):
                target_str = f" -> {self.target}"
        return f"{self.hour:02d}:00 {self.action_type.value}{target_str} [{self.state.value}]"
    
    def is_active(self) -> bool:
        """Check if action is currently active."""
        return self.state == ActionState.IN_PROGRESS
    
    def can_be_interrupted(self) -> bool:
        """Check if this action can be interrupted by encounters."""
        # Sleep and some critical actions can't be interrupted
        return self.action_type not in (ActionType.SLEEP,)


class EngagementType(Enum):
    """Types of engagements between entities."""
    COMBAT = "combat"           # Fighting - resolved by combat rules
    ROBBERY = "robbery"         # Bandit robbing caravan/settlement
    TENDING = "tending"         # Dragon tending spirit
    TRADING = "trading"         # Caravan trading at settlement
    FEEDING = "feeding"         # Dragon/predator feeding
    PROTECTING = "protecting"   # Hero protecting settlement/caravan
    PILLAGING = "pillaging"     # Looting ruins/treasury/domain


@dataclass
class Engagement:
    """
    Represents an ongoing interaction between entities that persists until
    hour-end or interruption. Resolution happens at on_hour_end().
    """
    engagement_type: EngagementType
    initiator: 'Mobile'           # Who started the engagement
    target: Any                   # Entity or location being engaged with
    started_hour: int             # Hour when engagement began
    can_be_interrupted: bool = True  # Some engagements (feeding?) may not be interruptible
    original_action: Optional[ScheduledAction] = None  # What initiator was doing before (for resume)
    
    def __str__(self) -> str:
        target_name = getattr(self.target, 'name', None) or str(getattr(self.target, 'coordinates', self.target))
        return f"{self.engagement_type.value} with {target_name} (started {self.started_hour}:00)"
    
    def involves(self, entity: 'Mobile') -> bool:
        """Check if an entity is part of this engagement."""
        return entity is self.initiator or entity is self.target


class Scheduled:
    """Mixin for entities that plan their daily activities."""
    
    def __init__(self):
        self.schedule: List[ScheduledAction] = []
        self.current_action: Optional[ScheduledAction] = None
        self._interrupted_action: Optional[ScheduledAction] = None  # Action we were doing before interruption
        self.is_sleeping = False
        
        # Engagement system
        self.current_engagement: Optional[Engagement] = None  # Active engagement if any
    
    def build_schedule(self) -> None:
        """
        Build the day's schedule based on mood/intent.
        Override in subclasses for entity-specific scheduling.
        Called at dawn each day.
        """
        self.schedule = []
        self.current_action = None
        self._interrupted_action = None
    
    def add_scheduled_action(
        self,
        hour: int,
        action_type: ActionType,
        target: Any = None,
        priority: int = 0,
        **metadata
    ) -> ScheduledAction:
        """Add an action to the schedule at a specific hour."""
        action = ScheduledAction(
            hour=hour,
            action_type=action_type,
            target=target,
            priority=priority,
            metadata=metadata
        )
        self.schedule.append(action)
        # Keep schedule sorted by hour
        self.schedule.sort(key=lambda a: a.hour)
        return action
    
    def schedule_actions(
        self,
        actions: List[Tuple[ActionType, Any]],
        randomness: int = 1,
        start_hour: int = SCHEDULE_START_HOUR,
        end_hour: int = SCHEDULE_END_HOUR,
    ) -> List[ScheduledAction]:
        """
        Schedule multiple actions, spreading them evenly across the day with randomness.
        
        Args:
            actions: List of (ActionType, target) tuples to schedule.
                     Target can be None for actions that don't need one.
            randomness: Maximum random hour offset (±randomness), default 1
            start_hour: First hour available for scheduling (default 7)
            end_hour: Last hour available for scheduling (default 19)
        
        Returns:
            List of created ScheduledAction objects
        
        Example:
            self.schedule_actions([
                (ActionType.FEED, None),
                (ActionType.PATROL, None),
                (ActionType.REST, settlement),
            ])
            # Might produce: 8:00 FEED, 12:00 PATROL, 17:00 REST (with ±1 hour randomness)
        """
        scheduler = DayScheduler(
            start_hour=start_hour,
            end_hour=end_hour,
            randomness=randomness
        )
        
        for action_type, target in actions:
            scheduler.add(action_type, target)
        
        result = []
        for hour, planned in scheduler.build():
            action = self.add_scheduled_action(
                hour=hour,
                action_type=planned.action_type,
                target=planned.target,
                priority=planned.priority,
                **planned.metadata
            )
            result.append(action)
        
        return result
    
    def create_day_scheduler(
        self,
        randomness: int = 1,
        start_hour: int = SCHEDULE_START_HOUR,
        end_hour: int = SCHEDULE_END_HOUR,
    ) -> DayScheduler:
        """
        Create a DayScheduler for more complex scheduling needs.
        
        Use this when you need more control over the scheduling process,
        such as setting priorities or metadata for individual actions.
        
        Example:
            scheduler = self.create_day_scheduler(randomness=2)
            scheduler.add(ActionType.FEED, priority=10)
            scheduler.add(ActionType.ATTACK, target=dragon, priority=5)
            self.apply_scheduler(scheduler)
        """
        return DayScheduler(
            start_hour=start_hour,
            end_hour=end_hour,
            randomness=randomness
        )
    
    def apply_scheduler(self, scheduler: DayScheduler) -> List[ScheduledAction]:
        """
        Apply a DayScheduler's planned actions to this entity's schedule.
        
        Returns:
            List of created ScheduledAction objects
        """
        result = []
        for hour, planned in scheduler.build():
            action = self.add_scheduled_action(
                hour=hour,
                action_type=planned.action_type,
                target=planned.target,
                priority=planned.priority,
                **planned.metadata
            )
            result.append(action)
        return result
    
    def get_action_for_hour(self, hour: int) -> Optional[ScheduledAction]:
        """Get the scheduled action for a specific hour, if any."""
        for action in self.schedule:
            if action.hour == hour and action.state == ActionState.PENDING:
                return action
        return None
    
    def get_current_action(self) -> Optional[ScheduledAction]:
        """Get the currently active action."""
        return self.current_action
    
    def start_action(self, action: ScheduledAction) -> None:
        """Begin executing an action."""
        if self.current_action and self.current_action.state == ActionState.IN_PROGRESS:
            # Mark old action as interrupted if starting a new one
            self.current_action.state = ActionState.INTERRUPTED
        
        action.state = ActionState.IN_PROGRESS
        self.current_action = action
    
    def complete_current_action(self) -> None:
        """Mark the current action as completed."""
        if self.current_action:
            self.current_action.state = ActionState.COMPLETED
            self.current_action = None
    
    def interrupt_for_encounter(self, encounter_action: ScheduledAction) -> bool:
        """
        Interrupt current action for an encounter.
        
        Args:
            encounter_action: The reactive action to take (flee, attack, protect)
            
        Returns:
            True if interruption succeeded, False if current action can't be interrupted
        """
        if self.current_action and not self.current_action.can_be_interrupted():
            return False
        
        if self.current_action and self.current_action.state == ActionState.IN_PROGRESS:
            self.current_action.state = ActionState.INTERRUPTED
            self._interrupted_action = self.current_action
        
        self.current_action = encounter_action
        encounter_action.state = ActionState.IN_PROGRESS
        return True
    
    def resume_after_encounter(self) -> bool:
        """
        Try to resume the interrupted action after encounter resolves.
        
        Returns:
            True if there was an action to resume
        """
        if self._interrupted_action:
            self.current_action = self._interrupted_action
            self.current_action.state = ActionState.IN_PROGRESS
            self._interrupted_action = None
            return True
        return False
    
    # ==================== Engagement System ====================
    
    def engage(
        self,
        target: Any,
        engagement_type: EngagementType,
        can_be_interrupted: bool = True,
    ) -> Engagement:
        """
        Start an engagement with a target. Engagements persist until hour-end
        (when they resolve) or until interrupted by an encounter.
        
        Args:
            target: Entity or location to engage with
            engagement_type: Type of engagement (COMBAT, ROBBERY, etc.)
            can_be_interrupted: Whether this engagement can be broken by encounters
            
        Returns:
            The created Engagement
        """
        # Store current action in case we need to resume after interruption
        original = self.current_action if self.current_action else self._interrupted_action
        
        engagement = Engagement(
            engagement_type=engagement_type,
            initiator=self,
            target=target,
            started_hour=getattr(self, 'world', None) and self.world.time.current_hour or 0,
            can_be_interrupted=can_be_interrupted,
            original_action=original,
        )
        self.current_engagement = engagement
        
        # If target is also a Scheduled entity, make them aware of the engagement
        if hasattr(target, 'current_engagement') and target.current_engagement is None:
            target.current_engagement = engagement
        
        return engagement
    
    def disengage(self, reason: str = "") -> Optional[ScheduledAction]:
        """
        Break current engagement. Called when interrupted or when engagement
        is forcibly ended (e.g., target died).
        
        Args:
            reason: Why the engagement ended (for logging/thinking)
            
        Returns:
            The original action to potentially resume, or None
        """
        if not self.current_engagement:
            return None
        
        original_action = self.current_engagement.original_action
        target = self.current_engagement.target
        
        # Clear target's engagement reference if they were tracking this
        if hasattr(target, 'current_engagement'):
            if target.current_engagement is self.current_engagement:
                target.current_engagement = None
        
        self.current_engagement = None
        
        # Log the disengagement if entity can think
        if hasattr(self, 'think') and reason:
            self.think(reason)
        
        return original_action
    
    def is_engaged(self) -> bool:
        """Check if currently in an engagement."""
        return self.current_engagement is not None
    
    def is_engaged_with(self, entity: Any) -> bool:
        """Check if currently engaged with a specific entity."""
        if not self.current_engagement:
            return False
        return self.current_engagement.involves(entity)
    
    def try_resume_after_disengage(self) -> bool:
        """
        After disengaging, try to resume the original scheduled action.
        
        Returns:
            True if successfully resumed an action, False otherwise
        """
        original = self.disengage()
        if original and hasattr(original.target, 'is_alive'):
            # Check if original target is still valid
            if not original.target.is_alive:
                return False
        
        if original:
            original.state = ActionState.IN_PROGRESS
            self.current_action = original
            return True
        return False
    
    def on_hour_end(self, hour: int) -> None:
        """
        Called at the end of each hour. Resolve any active engagements.
        Override in subclasses for entity-specific resolution logic.
        
        Args:
            hour: The hour that just ended
        """
        # Default: just clear the engagement without resolution
        # Subclasses override to implement actual resolution
        if self.current_engagement:
            self.current_engagement = None
    
    # ==================== End Engagement System ====================

    def clear_schedule(self) -> None:
        """Clear all scheduled actions and engagements."""
        self.schedule = []
        self.current_action = None
        self._interrupted_action = None
        if self.current_engagement:
            self.disengage("Day ends.")
    
    def on_dawn(self) -> None:
        """Called at dawn - wake up and build schedule."""
        self.is_sleeping = False
        self.build_schedule()
    
    def on_dusk(self) -> None:
        """Called at dusk - prepare for night."""
        pass  # Override in subclasses (e.g., return home)
    
    def on_night(self) -> None:
        """Called when night begins - go to sleep."""
        self.is_sleeping = True
        self.clear_schedule()
        self.add_scheduled_action(
            hour=self.world.time.current_hour,
            action_type=ActionType.SLEEP,
            priority=100
        )
    
    def on_hour(self, hour: int) -> None:
        """
        Called each hour. Check for scheduled actions and execute.
        Override in subclasses for custom hourly behavior.
        """
        if self.is_sleeping:
            return
        
        # Check if there's an action scheduled for this hour
        action = self.get_action_for_hour(hour)
        if action:
            self.start_action(action)
    
    def check_for_encounters(self) -> Optional['Scheduled']:
        """
        Check for nearby entities that trigger encounters.
        Override in subclasses for entity-specific encounter logic.
        
        Returns:
            The encountered entity, or None
        """
        return None
    
    def react_to_encounter(self, other: 'Scheduled') -> Optional[ScheduledAction]:
        """
        Determine reaction to an encounter.
        Override in subclasses for entity-specific reactions.
        
        Args:
            other: The entity encountered
            
        Returns:
            A reactive ScheduledAction, or None if no reaction needed
        """
        return None
    
    def get_schedule_summary(self) -> List[str]:
        """Get a human-readable summary of the schedule."""
        return [str(action) for action in self.schedule]
