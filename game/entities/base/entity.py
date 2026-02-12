"""Base entity class for all game entities."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World

Coordinates = Tuple[int, int]

class EngagementType(Enum):
    """Types of engagements between entities."""
    COMBAT = "combat"           # Fighting between entities (dragon vs hero, hero vs bandit, etc.)
    ROBBERY = "robbery"         # Bandit robbing caravan/settlement
    TENDING = "tending"         # Dragon tending spirit
    TRADING = "trading"         # Caravan/hero trading at settlement
    FEEDING = "feeding"         # Dragon feeding
    PILLAGING = "pillaging"     # Looting ruins/treasury/domain
    RESTING = "resting"         # Entity resting
    HOARDING = "hoarding"       # Dragon tending hoard


@dataclass
class Engagement:
    """
    Represents an ongoing interaction that persists until hour-end or interruption.
    Resolution happens at on_hour_end().
    
    Engagements support arbitrary participants:
    - Solo activities (resting, hoarding) have one participant
    - Standard interactions (robbery, tending) have two
    - Group activities (combat with multiple heroes) can have many
    
    Engagement lifecycle:
    - Created by entity.engage(), stored in entity.current_engagement
    - During resolution/interruption, entities set current_engagement = None
    - Once all entity references are cleared, Python GC cleans up the engagement
    """
    engagement_type: EngagementType
    started_by: 'Entity'          # Who initiated the engagement
    started_hour: int             # Hour when engagement began
    participants: set['Entity'] = field(default_factory=set)
    location: Any = None          # Optional location (for pillaging ruins, etc.)
    
    def __post_init__(self):
        """Ensure started_by is in participants."""
        if self.started_by not in self.participants:
            self.participants.add(self.started_by)
    
    def __str__(self) -> str:
        participant_names = [getattr(p, 'name', str(p)) for p in self.participants]
        location_str = ""
        if self.location:
            loc_name = getattr(self.location, 'name', None) or str(getattr(self.location, 'coordinates', self.location))
            location_str = f" at {loc_name}"
        return f"{self.engagement_type.value} [{', '.join(participant_names)}]{location_str} (started {self.started_hour}:00)"
    
    def __contains__(self, entity: 'Entity') -> bool:
        """Check if an entity is part of this engagement. Enables 'entity in engagement' syntax."""
        return entity in self.participants
    
    def add_participant(self, entity: 'Entity') -> bool:
        """
        Add a participant to the engagement.
        
        Returns:
            True if added, False if already participating
        """
        if entity in self.participants:
            return False
        self.participants.add(entity)
        return True
    
    def remove_participant(self, entity: 'Entity') -> bool:
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
    
    def get_others(self, entity: 'Entity') -> List['Entity']:
        """Get all participants except the given entity."""
        return [p for p in self.participants if p is not entity]


class Entity:
    """Base class for all game entities. Entities have a position, alive/dead status and can engage in interactions."""
    
    def __init__(
        self,
        world: 'World',
        coordinates: Coordinates,
    ):
        self.world = world
        self.coordinates = coordinates
        
        self.is_alive = True
        self.is_dead = False

        self.current_engagement: Optional[Engagement] = None  # Active engagement if any
        
    def update(self) -> None:
        raise NotImplementedError("Subclasses must implement update()")
    
    # ==================== Positioning ====================

    def get_distance(self, destination: Coordinates) -> float:
        """Calculate Euclidean distance to destination."""

        x1, y1 = self.coordinates
        x2, y2 = destination
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def get_adjacent_tiles(self) -> list[Coordinates]:
        """Get all 8 adjacent tiles around current position."""

        x, y = self.coordinates
        adjacent = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    adjacent.append((x + dx, y + dy))
        return adjacent
    
    def get_surrounding_tiles(self, radius: int) -> list[Coordinates]:
        """Get all tiles within a radius around current position."""

        x, y = self.coordinates
        surrounding = []
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if dx != 0 or dy != 0:
                    surrounding.append((x + dx, y + dy))
        return surrounding
    
    def get_nearby_entities(self, radius: float, *types: str) -> List['Entity']:
        """Get all entities within a radius."""
        nearby = []
        for entity in self.world.entities:
            if entity is self:
                continue
            if not entity.is_alive:
                continue
            if self.get_distance(entity.coordinates) <= radius:
                if not types or entity.__class__.__name__ in types:
                    nearby.append(entity)
        return nearby
    
    # ==================== Engagement System ====================
    
    def resolve_engagement(self) -> Optional[Engagement]:
        """Resolve current engagement at hour-end. Override in subclasses for specific logic."""
        engagement = self.current_engagement
        self.current_engagement = None
        return engagement

    def engage(
        self,
        engagement_type: EngagementType,
        *others: 'Entity',
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
            if hasattr(other, 'current_engagement') and other.current_engagement is not None:
                # Join existing engagement
                return self.join_engagement(other.current_engagement)
        
        # Create new engagement
        engagement = Engagement(
            engagement_type=engagement_type,
            started_by=self,
            started_hour=getattr(self, 'world', None) and self.world.time.current_hour or 0,
            participants={self},  # Will be expanded in __post_init__ but we control it here
            location=location,
        )
        
        # Don't rely on __post_init__ since we set participants explicitly
        self.current_engagement = engagement
        
        # Add other participants
        for other in others:
            engagement.add_participant(other)
            if hasattr(other, 'current_engagement'):
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
    
    def is_engaged_with(self, entity: Any) -> bool:
        """Check if currently engaged with a specific entity."""
        if not self.current_engagement:
            return False
        return entity in self.current_engagement
    
    def is_engaged_in(self, engagement_type: EngagementType) -> bool:
        """Check if currently in a specific type of engagement."""
        if not self.current_engagement:
            return False
        return self.current_engagement.engagement_type == engagement_type
    
    def get_engagement_partners(self) -> List['Entity']:
        """Get other participants in current engagement."""
        if not self.current_engagement:
            return []
        return self.current_engagement.get_others(self)
    
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

    # ==================== Misc ====================

    def die(self, reason) -> None:
        """Handle entity death."""
        self.is_dead = True
        self.is_alive = False
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize entity to dictionary for JSON output."""
        raise NotImplementedError("Subclasses must implement serialize()")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(pos={self.coordinates})"
