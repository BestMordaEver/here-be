"""Engaging mixin — engagement system for entity interactions.

Engagements represent ongoing interactions between entities (combat, robbery,
trading, etc.) that persist for a time period and resolve at hour-end.

The lifecycle:
    1. Entity calls engage() to start or join_engagement() to enter an existing one
    2. During the hour, entities can disengage() (flee, interrupt)
    3. At the end of the hour, resolve_engagement() is called — subclasses override for outcomes
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World


class EngagementType(Enum):
    """Types of engagements between entities."""
    COMBAT = "combat"           # Fighting between entities (dragon vs hero, hero vs bandit, etc.)
    ROBBERY = "robbery"         # Bandit robbing caravan
    TENDING = "tending"         # Dragon tending spirit
    TRADING = "trading"         # Caravan/hero trading at settlement
    FEEDING = "feeding"         # Dragon feeding
    PILLAGING = "pillaging"     # Looting ruins/treasury/domain
    RESTING = "resting"         # Entity resting
    HOARDING = "hoarding"       # Dragon tending hoard


@dataclass
class Engagement:
    """
    Represents an ongoing interaction that persists until hour-end.
    Resolution happens at the end of the hour.

    Engagements support arbitrary participants:
    - Solo activities (resting, hoarding) have one participant
    - Standard interactions (robbery, tending) have two
    - Group activities (combat with multiple heroes) can have many

    Engagement lifecycle:
    - Created by entity.engage(), stored in entity.current_engagement
    - During resolution, entities set current_engagement = None
    - Once all entity references are cleared, Python GC cleans up the engagement
    """
    engagement_type: EngagementType
    started_by: "Engaging"              # Who initiated the engagement
    started_hour: int                 # Hour when engagement began
    participants: Set["Engaging"] = field(default_factory=set)
    location: Any = None              # Optional location (for pillaging ruins, etc.)

    def __post_init__(self) -> None:
        """Ensure started_by is in participants."""
        if self.started_by not in self.participants:
            self.participants.add(self.started_by)

    def __str__(self) -> str:
        from .named import Named
        participant_names = [p.name if isinstance(p, Named) else str(p) for p in self.participants]
        location_str = ""
        if self.location:
            from .entity import Entity
            if isinstance(self.location, Named):
                loc_name = self.location.name
            elif isinstance(self.location, Entity):
                loc_name = str(self.location.coordinates)
            else:
                loc_name = str(self.location)
            location_str = f" at {loc_name}"
        return f"{self.engagement_type.value} [{', '.join(participant_names)}]{location_str} (started {self.started_hour}:00)"

    def __contains__(self, entity: "Engaging") -> bool:
        """Check if an entity is part of this engagement. Enables 'entity in engagement' syntax."""
        return entity in self.participants

    def add_participant(self, entity: "Engaging") -> bool:
        """
        Add a participant to the engagement.

        Returns:
            True if added, False if already participating
        """
        if entity in self.participants:
            return False
        self.participants.add(entity)
        return True

    def remove_participant(self, entity: "Engaging") -> bool:
        """
        Remove a participant from the engagement.

        Returns:
            True if removed, False if wasn't participating
        """
        if entity not in self.participants:
            return False
        self.participants.discard(entity)
        return True

    def is_solo(self) -> bool:
        """Check if this is a solo engagement (one participant)."""
        return len(self.participants) == 1

    def is_empty(self) -> bool:
        """Check if engagement has no participants left."""
        return len(self.participants) == 0

    def get_others(self, entity: "Engaging") -> List["Engaging"]:
        """Get all participants except the given entity."""
        return [p for p in self.participants if p is not entity]


class Engaging:
    """Mixin for entities that participate in engagements.

    Provides the full engagement API: starting, joining, leaving,
    querying, and resolving engagements at hour-end.
    """

    def __init__(self) -> None:
        self.current_engagement: Optional[Engagement] = None

    # ==================== Engagement System ====================

    def resolve_engagement(self) -> Optional[Engagement]:
        """Resolve current engagement at hour-end. Override in subclasses for specific logic.

        Default implementation clears the engagement and returns it so
        subclass overrides can inspect participants / type before cleanup.
        """
        engagement = self.current_engagement
        self.current_engagement = None
        return engagement

    def engage(
        self,
        engagement_type: EngagementType,
        *others: 'Engaging',
        location: Any = None,
    ) -> Engagement:
        """
        Start or join an engagement. Supports solo activities and multi-participant interactions.

        Current action is pushed onto the stack so it can be resumed after disengagement,
        even if there are nested engagements/interruptions.

        Args:
            engagement_type: Type of engagement (COMBAT, ROBBERY, RESTING, etc.)
            *others: Other entities to engage with (can be empty for solo activities)
            location: Optional location for place-based engagements (ruins, treasury)

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
        # Check if any of the others are already in an engagement we should join
        for other in others:
            if other.current_engagement is not None:
                # Join existing engagement
                return self.join_engagement(other.current_engagement)

        # Create new engagement
        engagement = Engagement(
            engagement_type=engagement_type,
            started_by=self,
            started_hour=self.world.time.current_hour if self.world else 0,
            participants={self},  # Will be expanded in __post_init__ but we control it here
            location=location,
        )

        # Don't rely on __post_init__ since we set participants explicitly
        self.current_engagement = engagement

        # Add other participants
        for other in others:
            engagement.add_participant(other)
            other.current_engagement = engagement

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
            self.disengage()

        engagement.add_participant(self)
        self.current_engagement = engagement

        return engagement

    def disengage(self) -> bool:
        """
        Leave current engagement. Called when interrupted or when entity chooses to leave.
        Removes self from participants and clears reference.
        To end the engagement, call resolve_engagement() instead.

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

        return True

    def is_engaged(self) -> bool:
        """Check if currently in an engagement."""
        return self.current_engagement is not None

    def is_engaged_with(self, entity: "Engaging") -> bool:
        """Check if currently engaged with a specific entity."""
        if not self.current_engagement:
            return False
        return entity in self.current_engagement

    def is_engaged_in(self, engagement_type: EngagementType) -> bool:
        """Check if currently in a specific type of engagement."""
        if not self.current_engagement:
            return False
        return self.current_engagement.engagement_type == engagement_type
