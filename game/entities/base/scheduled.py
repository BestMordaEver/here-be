"""Scheduled entity mixin - for entities that plan their day."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World
    from game.world.time_system import GameTime


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


class Scheduled:
    """Mixin for entities that plan their daily activities."""
    
    def __init__(self):
        self.schedule: List[ScheduledAction] = []
        self.current_action: Optional[ScheduledAction] = None
        self._interrupted_action: Optional[ScheduledAction] = None  # Action we were doing before interruption
        self.is_sleeping = False
    
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
        """Add an action to the schedule."""
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
    
    def clear_schedule(self) -> None:
        """Clear all scheduled actions."""
        self.schedule = []
        self.current_action = None
        self._interrupted_action = None
    
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
