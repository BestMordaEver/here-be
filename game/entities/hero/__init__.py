"""Hero entity with mood-based daily scheduling."""

import random
from typing import TYPE_CHECKING, Dict, Any, List, Optional, Set

from game.entities.base import Coordinates, Mobile, Named, Thinking, Scheduled, Aging, Visible, Pockets
from game.entities.base.named import Pronouns
from game.world.types import Biome
from .types import HeroMood, LIFESPAN_DAYS, PARTY_SIZE, MAX_BLESSINGS, PATROL_RANGE, HERO_NAMES

if TYPE_CHECKING:
    from game.world import World
    from game.entities.settlement.settlement import Settlement


class Hero(Mobile, Visible, Named, Thinking, Scheduled, Aging, Pockets):
    """A hero that protects settlements and slays dragons."""

    def __init__(
        self,
        world: 'World',
        coordinates: Coordinates,
        home: 'Settlement',
        city_born: bool = True,
    ):
        # City heroes are gold, village heroes are brownish
        color = "#FFD700" if city_born else "#8B6914"

        Mobile.__init__(self, world, coordinates, loiter=1)  # Heroes skip 1 movement cycle
        Visible.__init__(self)
        Named.__init__(self, random.choice(HERO_NAMES), Pronouns.random())
        Thinking.__init__(self, capacity=3)
        Scheduled.__init__(self)
        Aging.__init__(self, lifespan=LIFESPAN_DAYS)
        Pockets.__init__(self, max_blessings=MAX_BLESSINGS)

        self.color = color
        self.char = "♦"
        self.create_small("default", color, "♦")
        self.visual_state = "default"

        # Home & origin
        self.home = home
        self.city_born = city_born

        # Mood / tiredness
        self.mood: HeroMood = HeroMood.ADVENTUROUS
        self.consecutive_active_days: int = 0
        self.is_permanently_tired: bool = False
        self.tired_today: bool = False  # Set by combat, cleared on build_schedule

        # Party management
        self.party: Optional[List['Hero']] = None
        self.party_leader: Optional['Hero'] = None

        # Memory
        self.known_domains: Set = set()               # Domain coordinates
        self.acquaintances: Set['Hero'] = set()        # Heroes we know
        self.days_domain_known: Dict = {}              # coords -> days since learned
        self.opportunistic_target: Optional[Any] = None  # Triggers opportunistic

    # ------------------------------------------------------------------
    # Terrain
    # ------------------------------------------------------------------

    def is_passable(self, coordinates: Coordinates) -> bool:
        """Heroes can move through fields and forests."""
        x, y = coordinates
        if x < 0 or y < 0 or x >= self.world.WIDTH or y >= self.world.HEIGHT:
            return False

        height = self.world.height_map[y][x]
        biome = self.world.get_biome_from_height(height)
        return biome in (Biome.FIELD, Biome.FOREST)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def prune_dead_refs(self) -> None:
        """Remove references to dead entities so they can be garbage collected."""
        if self.party_leader and not self.party_leader.is_alive:
            self.party_leader = None
        if self.party:
            self.party[:] = [h for h in self.party if h.is_alive]
            if len(self.party) <= 1:
                self.party = None
                self.party_leader = None
        if self.opportunistic_target and not self.opportunistic_target.is_alive:
            self.opportunistic_target = None

    def on_dawn(self) -> None:
        """Dawn: age, check death, build schedule."""
        self.prune_dead_refs()
        self.prune_stale_memories(self.world.time.current_day)
        if self.process_aging():
            return
        self.build_schedule()

    def get_lifespan(self) -> int:
        return LIFESPAN_DAYS

    def on_old_age_death(self) -> None:
        """Clear blessings before dying of old age so nothing drops."""
        self.empty_blessings()

    def die(self, reason: str) -> None:
        """Handle hero death - drop blessings, notify acquaintances, leave party."""
        # Drop carried blessings (already 0 if old age via on_old_age_death)
        dropped = self.empty_blessings()
        if dropped > 0:
            from game.entities.blessing import drop_blessing
            drop_blessing(self.world, self.coordinates, dropped)

        super().die(reason)

        # Broadcast SAW_HERO_DIE event to nearby talkers and home settlement
        from game.entities.base.thinking import Memory, MemoryType
        event = Memory(
            type=MemoryType.SAW_HERO_DIE,
            subject=self,
            location=self.coordinates,
            day=self.world.time.current_day,
            source=self,
        )
        for entity in self.get_nearby_entities(10):
            if hasattr(entity, 'is_talker') and entity.is_talker:
                entity.add_event(event)

        # Leave party
        if self.party:
            if self in self.party:
                self.party.remove(self)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self) -> Dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "coordinates": self.coordinates,
            "in_transit": self.in_transit,
            "name": self.name,
            "color": self.color,
            "character": self.char,
            "home": self.home.name if self.home else "none",
            "mood": self.mood.value,
            "age_days": self.age_days,
            "blessings": self.blessings,
            "in_party": self.party is not None,
            "is_leader": self.party_leader is self if self.party else False,
            "schedule": self.get_schedule_summary(),
        }


from .schedule import build_schedule
Hero.build_schedule = build_schedule

from .actions import start_action, on_movement_complete, on_hour, check_for_encounters, resolve_engagement
Hero.start_action = start_action
Hero.on_arrival = on_movement_complete
Hero.on_hour = on_hour
Hero.check_for_encounters = check_for_encounters
Hero.resolve_engagement = resolve_engagement

from .movement import update_movement
Hero.update_movement = update_movement

__all__ = ['Hero', 'HeroMood']