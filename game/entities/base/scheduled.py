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
    RESTING = "resting"         # Solo - entity resting
    HOARDING = "hoarding"       # Solo - dragon tending hoard


@dataclass
class Engagement:
    """
    Represents an ongoing interaction that persists until hour-end or interruption.
    Resolution happens at on_hour_end().
    
    Engagements support arbitrary participants:
    - Solo activities (resting, hoarding) have one participant
    - Standard interactions (robbery, tending) have two
    - Group activities (combat with multiple heroes) can have many
    
    Participants can join/leave via the Scheduled mixin methods.
    """
    engagement_type: EngagementType
    started_by: 'Mobile'          # Who initiated the engagement
    started_hour: int             # Hour when engagement began
    participants: List['Mobile'] = field(default_factory=list)  # All involved entities
    location: Any = None          # Optional location (for pillaging ruins, etc.)
    can_be_interrupted: bool = True  # Some engagements may not be interruptible
    blocks_night: bool = False    # If True, participants delay sleep until disengaged
    
    def __post_init__(self):
        """Ensure started_by is in participants."""
        if self.started_by not in self.participants:
            self.participants.append(self.started_by)
    
    def __str__(self) -> str:
        participant_names = [getattr(p, 'name', str(p)) for p in self.participants]
        location_str = ""
        if self.location:
            loc_name = getattr(self.location, 'name', None) or str(getattr(self.location, 'coordinates', self.location))
            location_str = f" at {loc_name}"
        return f"{self.engagement_type.value} [{', '.join(participant_names)}]{location_str} (started {self.started_hour}:00)"
    
    def involves(self, entity: 'Mobile') -> bool:
        """Check if an entity is part of this engagement."""
        return entity in self.participants
    
    def add_participant(self, entity: 'Mobile') -> bool:
        """
        Add a participant to the engagement.
        
        Returns:
            True if added, False if already participating
        """
        if entity in self.participants:
            return False
        self.participants.append(entity)
        return True
    
    def remove_participant(self, entity: 'Mobile') -> bool:
        """
        Remove a participant from the engagement.
        
        Returns:
            True if removed, False if wasn't participating
        """
        if entity not in self.participants:
            return False
        self.participants.remove(entity)
        return True
    
    def is_solo(self) -> bool:
        """Check if this is a solo engagement (one participant)."""
        return len(self.participants) == 1
    
    def is_empty(self) -> bool:
        """Check if engagement has no participants left."""
        return len(self.participants) == 0
    
    def get_others(self, entity: 'Mobile') -> List['Mobile']:
        """Get all participants except the given entity."""
        return [p for p in self.participants if p is not entity]


class Scheduled:
    """Mixin for entities that plan their daily activities."""
    
    def __init__(self):
        self.schedule: List[ScheduledAction] = []
        self.current_action: Optional[ScheduledAction] = None
        self._action_stack: List[ScheduledAction] = []  # Stack of interrupted actions for nested resume
        self.is_sleeping = False
        self._night_blocked = False  # If True, delay sleep until unblocked
        
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
        self._action_stack.clear()
    
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
        Interrupt current action for an encounter. Pushes current action onto
        the stack so it can be resumed later, even after nested interruptions.
        
        Args:
            encounter_action: The reactive action to take (flee, attack, protect)
            
        Returns:
            True if interruption succeeded, False if current action can't be interrupted
        """
        if self.current_action and not self.current_action.can_be_interrupted():
            return False
        
        if self.current_action and self.current_action.state == ActionState.IN_PROGRESS:
            self.current_action.state = ActionState.INTERRUPTED
            self._action_stack.append(self.current_action)
        
        self.current_action = encounter_action
        encounter_action.state = ActionState.IN_PROGRESS
        return True
    
    def resume_after_encounter(self) -> bool:
        """
        Try to resume the most recently interrupted action after encounter resolves.
        Pops from the action stack, supporting nested interruptions.
        
        Returns:
            True if there was an action to resume
        """
        if not self._action_stack:
            return False
        
        action = self._action_stack.pop()
        
        # Check if target is still valid
        if action.target and hasattr(action.target, 'is_alive'):
            if not action.target.is_alive:
                # Target died, try resuming the next action in stack
                return self.resume_after_encounter()
        
        action.state = ActionState.IN_PROGRESS
        self.current_action = action
        return True
    
    def push_current_action(self) -> None:
        """
        Push current action onto the stack without marking it interrupted.
        Use when temporarily switching to another action that will resolve quickly.
        """
        if self.current_action and self.current_action.state == ActionState.IN_PROGRESS:
            self._action_stack.append(self.current_action)
            self.current_action = None
    
    def peek_interrupted_action(self) -> Optional[ScheduledAction]:
        """
        View the most recently interrupted action without removing it from stack.
        
        Returns:
            The action that would be resumed, or None if stack is empty
        """
        return self._action_stack[-1] if self._action_stack else None
    
    def clear_action_stack(self) -> None:
        """Clear all interrupted actions from the stack."""
        self._action_stack.clear()
    
    # ==================== Engagement System ====================
    
    def engage(
        self,
        engagement_type: EngagementType,
        *others: 'Mobile',
        location: Any = None,
        can_be_interrupted: bool = True,
        blocks_night: bool = False,
    ) -> Engagement:
        """
        Start or join an engagement. Supports solo activities and multi-participant interactions.
        
        Current action is pushed onto the stack so it can be resumed after disengagement,
        even if there are nested engagements/interruptions.
        
        Args:
            engagement_type: Type of engagement (COMBAT, ROBBERY, RESTING, etc.)
            *others: Other entities to engage with (can be empty for solo activities)
            location: Optional location for place-based engagements (ruins, treasury)
            can_be_interrupted: Whether this engagement can be broken by encounters
            blocks_night: If True, participants delay sleep until disengaged
            
        Returns:
            The created or joined Engagement
            
        Examples:
            # Solo engagement (dragon hoarding)
            dragon.engage(EngagementType.HOARDING)
            
            # Two-participant engagement (robbery)
            bandit.engage(EngagementType.ROBBERY, caravan)
            
            # Multi-participant (hero joins ongoing combat)
            hero.join_engagement(ongoing_combat)
        """
        # Push current action onto stack for potential resume after disengagement
        self.push_current_action()
        
        # Check if any of the others are already in an engagement we should join
        for other in others:
            if hasattr(other, 'current_engagement') and other.current_engagement is not None:
                # Join existing engagement
                return self.join_engagement(other.current_engagement)
        
        # Create new engagement
        engagement = Engagement(
            engagement_type=engagement_type,
            started_by=self,
            started_hour=getattr(self, 'world', None) and self.world.time.current_hour or 0,
            participants=[self],  # Will be expanded in __post_init__ but we control it here
            location=location,
            can_be_interrupted=can_be_interrupted,
            blocks_night=blocks_night,
        )
        
        # Don't rely on __post_init__ since we set participants explicitly
        self.current_engagement = engagement
        
        if blocks_night:
            self._night_blocked = True
        
        # Add other participants
        for other in others:
            engagement.add_participant(other)
            if hasattr(other, 'current_engagement'):
                # Push their current action onto stack too
                if hasattr(other, 'push_current_action'):
                    other.push_current_action()
                other.current_engagement = engagement
                if blocks_night and hasattr(other, '_night_blocked'):
                    other._night_blocked = True
        
        return engagement
    
    def join_engagement(self, engagement: Engagement) -> Engagement:
        """
        Join an existing engagement as a participant.
        
        Args:
            engagement: The engagement to join
            
        Returns:
            The engagement (for chaining)
        """
        if self.current_engagement is engagement:
            return engagement  # Already in this engagement
        
        # Leave current engagement if any
        if self.current_engagement:
            self.disengage("Joining another engagement.")
        
        # Push current action onto stack for potential resume
        self.push_current_action()
        
        engagement.add_participant(self)
        self.current_engagement = engagement
        
        if engagement.blocks_night:
            self._night_blocked = True
        
        return engagement
    
    def disengage(self, reason: str = "") -> bool:
        """
        Leave current engagement. Called when interrupted, when engagement
        ends, or when entity chooses to leave.
        
        Args:
            reason: Why leaving the engagement (for logging/thinking)
            
        Returns:
            True if was engaged and successfully disengaged
        """
        if not self.current_engagement:
            return False
        
        engagement = self.current_engagement
        
        # Remove self from participants
        engagement.remove_participant(self)
        
        # Clear our engagement reference
        self.current_engagement = None
        self._night_blocked = False
        
        # Log the disengagement if entity can think
        if hasattr(self, 'think') and reason:
            self.think(reason)
        
        return True
    
    def disengage_and_resume(self, reason: str = "") -> bool:
        """
        Leave current engagement and try to resume the previous action.
        
        This is the typical flow when an engagement ends naturally - the entity
        should go back to what they were doing before (e.g., dragon resumes
        feeding after defending a city).
        
        Args:
            reason: Why leaving the engagement (for logging/thinking)
            
        Returns:
            True if successfully resumed a previous action
        """
        if not self.disengage(reason):
            return False
        
        return self.resume_after_encounter()
    
    def is_engaged(self) -> bool:
        """Check if currently in an engagement."""
        return self.current_engagement is not None
    
    def is_engaged_with(self, entity: Any) -> bool:
        """Check if currently engaged with a specific entity."""
        if not self.current_engagement:
            return False
        return self.current_engagement.involves(entity)
    
    def is_engaged_in(self, engagement_type: EngagementType) -> bool:
        """Check if currently in a specific type of engagement."""
        if not self.current_engagement:
            return False
        return self.current_engagement.engagement_type == engagement_type
    
    def get_engagement_partners(self) -> List['Mobile']:
        """Get other participants in current engagement."""
        if not self.current_engagement:
            return []
        return self.current_engagement.get_others(self)
    
    def try_resume_after_disengage(self) -> bool:
        """
        Disengage and try to resume the previous action.
        
        Deprecated: Use disengage_and_resume() instead.
        
        Returns:
            True if successfully resumed an action, False otherwise
        """
        return self.disengage_and_resume()
    
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
    
    # ==================== Night Blocking ====================
    
    def block_night(self, reason: str = "") -> None:
        """
        Prevent this entity from sleeping until unblocked.
        Use when critical situations require staying awake.
        
        Args:
            reason: Why night is blocked (for logging)
        """
        self._night_blocked = True
        if hasattr(self, 'think') and reason:
            self.think(reason)
    
    def unblock_night(self) -> None:
        """Allow this entity to sleep again."""
        self._night_blocked = False
    
    def is_night_blocked(self) -> bool:
        """Check if this entity is prevented from sleeping."""
        return self._night_blocked
    
    # ==================== End Engagement System ====================

    def clear_schedule(self) -> None:
        """Clear all scheduled actions and engagements."""
        self.schedule = []
        self.current_action = None
        self._action_stack.clear()
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
        """Called when night begins - go to sleep unless blocked."""
        if self._night_blocked:
            # Can't sleep yet - critical situation ongoing
            if hasattr(self, 'think'):
                self.think("Cannot rest while danger looms.")
            return
        
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
