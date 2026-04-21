"""Thinking mixin — thought memory, information exchange, and written logs.

Talkers (Settlement, Hero, Caravan) store a bounded set of thoughts in memory
and exchange them on encounter/arrival. Writers (City, Village, Dragon, Hero)
periodically render thoughts into a human-readable log visible to players.
"""
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .entity import Entity, Coordinates


# ---------------------------------------------------------------------------
# Memory system
# ---------------------------------------------------------------------------

class MemoryType(IntEnum):
    """Memory types in order of rising priority."""
    SAW_DRAGON = 1
    SAW_BANDIT = 2
    VILLAGE_HAS_BLESSING = 3
    ATTACKED_BY_BANDIT = 4
    SAW_DOMAIN = 5
    ATTACKED_BY_DRAGON = 6
    SAW_HERO_DIE = 7


@dataclass
class Memory:
    """A discrete piece of information an entity can remember and exchange.

    Attributes:
        type:       What happened (determines priority).
        subject:    The entity most relevant to the memory (dragon, bandit, hero…).
        location:   Where the memory was recorded.
        day:        Game-day the memory was created.
        source:     The original witness.
        remarked:   Whether a writer has already logged this memory.
    """
    type: MemoryType
    subject: Optional['Entity'] = None
    location: Optional['Coordinates'] = None
    day: int = 0
    source: Optional['Entity'] = None
    remarked: bool = False

    @property
    def priority(self) -> int:
        return int(self.type)

    def identity_key(self) -> tuple:
        """Key used for deduplication — same type + same subject = duplicate."""
        return (self.type, id(self.subject))


# Days after which a memory type expires and is automatically pruned.
# Types not listed here never expire.
MEMORY_STALENESS: dict[MemoryType, int] = {
    MemoryType.SAW_DRAGON: 3,
    MemoryType.SAW_BANDIT: 2,
    MemoryType.VILLAGE_HAS_BLESSING: 5,
    MemoryType.ATTACKED_BY_BANDIT: 5,
    MemoryType.SAW_DOMAIN: 10,
    MemoryType.ATTACKED_BY_DRAGON: 10,
    MemoryType.SAW_HERO_DIE: 10,
}


# ---------------------------------------------------------------------------
# Thinking mixin
# ---------------------------------------------------------------------------

class Thinking:
    """Mixin providing memory transport (talkers) and a written thought log (writers)."""

    def __init__(self, capacity: int = 0):
        # Memory — bounded priority queue
        self._memory_capacity: int = capacity
        self._memories: List[Memory] = []

        # Written log — append-only, for player display
        self.thoughts: List[str] = []

    # ------------------------------------------------------------------
    # Memory (talkers)
    # ------------------------------------------------------------------

    @property
    def is_talker(self) -> bool:
        return self._memory_capacity > 0

    @property
    def memories(self) -> List[Memory]:
        return list(self._memories)

    def add_memory(self, event: Memory) -> None:
        """Insert *event* into memory, evicting the lowest-priority entry if full.

        Duplicates (same type + subject) refresh the existing entry instead of
        consuming an additional slot.
        """
        if self._memory_capacity <= 0:
            return

        key = event.identity_key()

        # Dedup: refresh existing entry
        for i, existing in enumerate(self._memories):
            if existing.identity_key() == key:
                self._memories[i] = event
                return

        if len(self._memories) < self._memory_capacity:
            self._memories.append(event)
        else:
            # Evict lowest-priority event if new one beats it
            min_idx = min(range(len(self._memories)), key=lambda i: self._memories[i].priority)
            if event.priority > self._memories[min_idx].priority:
                self._memories[min_idx] = event

    def clear_memories_of_type(self, memory_type: MemoryType) -> None:
        """Remove all memories of a given type (staleness / consumption)."""
        self._memories = [e for e in self._memories if e.type != memory_type]

    def has_memory(self, memory_type: MemoryType, subject: 'Entity' = None) -> bool:
        """Check whether memory contains a matching memory."""
        for e in self._memories:
            if e.type == memory_type:
                if subject is None or e.subject is subject:
                    return True
        return False

    def highest_priority_memory(self) -> Optional[Memory]:
        """Return the highest-priority memory, or None."""
        if not self._memories:
            return None
        return max(self._memories, key=lambda e: e.priority)

    def prune_stale_memories(self, current_day: int) -> None:
        """Remove memories that have exceeded their staleness threshold."""
        self._memories = [
            e for e in self._memories
            if e.type not in MEMORY_STALENESS
            or (current_day - e.day) < MEMORY_STALENESS[e.type]
        ]

    # ------------------------------------------------------------------
    # Information exchange
    # ------------------------------------------------------------------

    def exchange_memories(self, other: 'Thinking') -> None:
        """Bidirectional memory exchange with *other*.

        Each side receives memories it doesn't already have, subject to its own
        capacity and priority eviction rules.
        """
        if not (self.is_talker and other.is_talker):
            return

        # Snapshot both sides before exchange to avoid feedback loops
        my_memories = list(self._memories)
        their_memories = list(other._memories)

        for memory in their_memories:
            self.add_memory(memory)
        for memory in my_memories:
            other.add_memory(memory)

    def inherit_top_memory(self, source: 'Thinking') -> None:
        """Copy the highest-priority memory from *source* into own memory.

        Used by caravans when departing a settlement.
        """
        top = source.highest_priority_memory()
        if top is not None:
            self.add_memory(top)

    # ------------------------------------------------------------------
    # Written thought log (writers)
    # ------------------------------------------------------------------

    def think(self, thought: str) -> None:
        """Append a rendered thought to the written thought log."""
        self.thoughts.append(thought)
