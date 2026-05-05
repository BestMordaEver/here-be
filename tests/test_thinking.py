"""Tests for the Thinking mixin — memory, staleness, and exchange.

Design spec (DESIGN.md § Memory System):
    SAW_DRAGON       priority 1  staleness 3 days
    ATTACKED_BY_DRAGON priority 6  staleness 5 days
    SAW_HERO_DIE     priority 7  staleness NEVER  ← DESIGN says never; CODE says 10 days
"""
import pytest
from game.entities.base.thinking import Thinking, Memory, MemoryType, MEMORY_STALENESS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeThinker(Thinking):
    def __init__(self, capacity: int = 3):
        Thinking.__init__(self, capacity=capacity)


def make_memory(memory_type: MemoryType, subject=None, day: int = 1) -> Memory:
    return Memory(type=memory_type, subject=subject, day=day)


# ---------------------------------------------------------------------------
# Basic memory storage
# ---------------------------------------------------------------------------

class TestMemoryStorage:

    def test_add_memory_within_capacity(self):
        t = FakeThinker(capacity=3)
        t.add_memory(make_memory(MemoryType.SAW_DRAGON))
        assert t.has_memory(MemoryType.SAW_DRAGON)

    def test_non_talker_ignores_memories(self):
        t = FakeThinker(capacity=0)
        t.add_memory(make_memory(MemoryType.SAW_DRAGON))
        assert not t.has_memory(MemoryType.SAW_DRAGON)

    def test_is_talker_respects_capacity(self):
        assert FakeThinker(capacity=0).is_talker is False
        assert FakeThinker(capacity=1).is_talker is True

    def test_evicts_lowest_priority_when_full(self):
        """When capacity is exceeded, the lowest-priority memory is dropped."""
        t = FakeThinker(capacity=2)
        low = make_memory(MemoryType.SAW_DRAGON)       # priority 1
        high = make_memory(MemoryType.SAW_HERO_DIE)    # priority 7
        mid = make_memory(MemoryType.ATTACKED_BY_DRAGON)  # priority 6
        t.add_memory(low)
        t.add_memory(high)
        # Adding mid should evict low (the lowest priority)
        t.add_memory(mid)
        assert not t.has_memory(MemoryType.SAW_DRAGON), "Lowest priority should be evicted"
        assert t.has_memory(MemoryType.SAW_HERO_DIE)
        assert t.has_memory(MemoryType.ATTACKED_BY_DRAGON)

    def test_higher_priority_replaces_lower_only(self):
        """Incoming memory does NOT replace a higher-priority existing memory."""
        t = FakeThinker(capacity=1)
        t.add_memory(make_memory(MemoryType.SAW_HERO_DIE))  # priority 7
        t.add_memory(make_memory(MemoryType.SAW_DRAGON))    # priority 1 — should be discarded
        assert t.has_memory(MemoryType.SAW_HERO_DIE)
        assert not t.has_memory(MemoryType.SAW_DRAGON)

    def test_deduplication_refreshes_existing_entry(self):
        """Adding the same type+subject again should replace the entry, not create duplicate."""
        t = FakeThinker(capacity=3)
        subject = object()
        t.add_memory(make_memory(MemoryType.SAW_DRAGON, subject=subject, day=1))
        t.add_memory(make_memory(MemoryType.SAW_DRAGON, subject=subject, day=5))
        # Should still be one memory, but updated
        dragon_memories = [m for m in t.memories if m.type == MemoryType.SAW_DRAGON]
        assert len(dragon_memories) == 1
        assert dragon_memories[0].day == 5  # Updated

    def test_different_subjects_same_type_are_separate(self):
        """Different subjects for the same memory type are distinct entries."""
        t = FakeThinker(capacity=3)
        s1, s2 = object(), object()
        t.add_memory(make_memory(MemoryType.SAW_DRAGON, subject=s1))
        t.add_memory(make_memory(MemoryType.SAW_DRAGON, subject=s2))
        dragon_memories = [m for m in t.memories if m.type == MemoryType.SAW_DRAGON]
        assert len(dragon_memories) == 2


# ---------------------------------------------------------------------------
# Priority ordering (matches design §Memory System)
# ---------------------------------------------------------------------------

class TestMemoryPriority:

    def test_saw_dragon_priority_is_1(self):
        assert MemoryType.SAW_DRAGON == 1

    def test_attacked_by_dragon_priority_is_6(self):
        assert MemoryType.ATTACKED_BY_DRAGON == 6

    def test_saw_hero_die_priority_is_7(self):
        assert MemoryType.SAW_HERO_DIE == 7

    def test_highest_priority_memory(self):
        t = FakeThinker(capacity=3)
        t.add_memory(make_memory(MemoryType.SAW_DRAGON))
        t.add_memory(make_memory(MemoryType.SAW_HERO_DIE))
        t.add_memory(make_memory(MemoryType.ATTACKED_BY_DRAGON))
        top = t.highest_priority_memory()
        assert top is not None
        assert top.type == MemoryType.SAW_HERO_DIE


# ---------------------------------------------------------------------------
# Staleness pruning
# ---------------------------------------------------------------------------

class TestStaleness:

    def test_saw_dragon_expires_after_3_days(self):
        t = FakeThinker(capacity=3)
        t.add_memory(make_memory(MemoryType.SAW_DRAGON, day=1))
        t.prune_stale_memories(current_day=4)  # 3 days elapsed
        assert not t.has_memory(MemoryType.SAW_DRAGON)

    def test_saw_dragon_survives_2_days(self):
        t = FakeThinker(capacity=3)
        t.add_memory(make_memory(MemoryType.SAW_DRAGON, day=1))
        t.prune_stale_memories(current_day=3)  # 2 days elapsed
        assert t.has_memory(MemoryType.SAW_DRAGON)

    def test_attacked_by_dragon_staleness_matches_design(self):
        """ATTACKED_BY_DRAGON staleness = 5 days."""
        assert MEMORY_STALENESS.get(MemoryType.ATTACKED_BY_DRAGON) == 5

    def test_saw_dragon_staleness_matches_design(self):
        """Design: SAW_DRAGON staleness = 3 days."""
        assert MEMORY_STALENESS.get(MemoryType.SAW_DRAGON) == 3, (
            "SAW_DRAGON staleness should be 3 days per design"
        )

    def test_saw_hero_die_expires_after_10_days(self):
        """SAW_HERO_DIE is forgettable: expires after 10 days."""
        assert MEMORY_STALENESS.get(MemoryType.SAW_HERO_DIE) == 10

    def test_saw_hero_die_survives_9_days(self):
        t = FakeThinker(capacity=3)
        t.add_memory(make_memory(MemoryType.SAW_HERO_DIE, day=1))
        t.prune_stale_memories(current_day=10)  # 9 days elapsed
        assert t.has_memory(MemoryType.SAW_HERO_DIE)

    def test_saw_hero_die_pruned_after_10_days(self):
        t = FakeThinker(capacity=3)
        t.add_memory(make_memory(MemoryType.SAW_HERO_DIE, day=1))
        t.prune_stale_memories(current_day=11)  # 10 days elapsed
        assert not t.has_memory(MemoryType.SAW_HERO_DIE)


# ---------------------------------------------------------------------------
# Memory exchange
# ---------------------------------------------------------------------------

class TestMemoryExchange:

    def test_bidirectional_exchange(self):
        a = FakeThinker(capacity=3)
        b = FakeThinker(capacity=3)
        a.add_memory(make_memory(MemoryType.SAW_DRAGON))
        b.add_memory(make_memory(MemoryType.SAW_HERO_DIE))
        a.exchange_memories(b)
        assert a.has_memory(MemoryType.SAW_HERO_DIE)
        assert b.has_memory(MemoryType.SAW_DRAGON)

    def test_exchange_with_non_talker_does_nothing(self):
        talker = FakeThinker(capacity=3)
        non_talker = FakeThinker(capacity=0)
        talker.add_memory(make_memory(MemoryType.SAW_DRAGON))
        talker.exchange_memories(non_talker)
        assert not non_talker.has_memory(MemoryType.SAW_DRAGON)

    def test_exchange_does_not_create_duplicates(self):
        a = FakeThinker(capacity=3)
        b = FakeThinker(capacity=3)
        m = make_memory(MemoryType.SAW_DRAGON)
        a.add_memory(m)
        b.add_memory(m)
        a.exchange_memories(b)
        dragon_count = sum(1 for mem in a.memories if mem.type == MemoryType.SAW_DRAGON)
        assert dragon_count == 1

    def test_inherit_top_memory(self):
        src = FakeThinker(capacity=3)
        src.add_memory(make_memory(MemoryType.SAW_DRAGON))
        src.add_memory(make_memory(MemoryType.SAW_HERO_DIE))
        dst = FakeThinker(capacity=3)
        dst.inherit_top_memory(src)
        # Only highest priority should be inherited
        assert dst.has_memory(MemoryType.SAW_HERO_DIE)
        dragon_count = sum(1 for m in dst.memories if m.type == MemoryType.SAW_DRAGON)
        assert dragon_count == 0

    def test_inherit_top_memory_from_empty_does_nothing(self):
        src = FakeThinker(capacity=3)
        dst = FakeThinker(capacity=3)
        dst.inherit_top_memory(src)
        assert len(dst.memories) == 0

    def test_think_appends_to_log(self):
        t = FakeThinker(capacity=3)
        t.think("Hello world")
        t.think("Goodbye world")
        assert t.thoughts == ["Hello world", "Goodbye world"]
