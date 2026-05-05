"""Tests for the Engaging mixin — engagement lifecycle."""
import pytest
from game.entities.base.engaging import Engaging, Engagement, EngagementType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeEngaging(Engaging):
    """Minimal entity with just the Engaging mixin for isolation testing."""
    def __init__(self, name='entity'):
        Engaging.__init__(self)
        self.world = None
        self.name = name


def make_entity(name='entity'):
    return FakeEngaging(name)


# ---------------------------------------------------------------------------
# Solo engagement
# ---------------------------------------------------------------------------

class TestSoloEngagement:

    def test_solo_engagement_is_created(self):
        e = make_entity()
        engagement = e.engage(EngagementType.RESTING)
        assert engagement is not None
        assert engagement.engagement_type == EngagementType.RESTING

    def test_solo_engagement_participant_is_self(self):
        e = make_entity()
        engagement = e.engage(EngagementType.RESTING)
        assert e in engagement.participants
        assert len(engagement.participants) == 1

    def test_solo_engagement_stored_on_entity(self):
        e = make_entity()
        engagement = e.engage(EngagementType.RESTING)
        assert e.current_engagement is engagement

    def test_solo_engagement_started_by(self):
        e = make_entity()
        engagement = e.engage(EngagementType.RESTING)
        assert engagement.started_by is e


# ---------------------------------------------------------------------------
# Two-participant engagement
# ---------------------------------------------------------------------------

class TestTwoParticipantEngagement:

    def test_two_participant_engagement(self):
        attacker = make_entity('attacker')
        target = make_entity('target')
        engagement = attacker.engage(EngagementType.COMBAT, target)
        assert attacker in engagement.participants
        assert target in engagement.participants
        assert len(engagement.participants) == 2

    def test_both_entities_reference_same_engagement(self):
        attacker = make_entity('attacker')
        target = make_entity('target')
        engagement = attacker.engage(EngagementType.COMBAT, target)
        assert attacker.current_engagement is engagement
        assert target.current_engagement is engagement

    def test_engage_joins_existing_when_target_already_engaged(self):
        """If the target is already in an engagement, engage() should join it."""
        a = make_entity('a')
        b = make_entity('b')
        c = make_entity('c')
        existing = a.engage(EngagementType.COMBAT, b)
        # c engages with b who is already in an engagement with a
        engagement = c.engage(EngagementType.COMBAT, b)
        assert engagement is existing
        assert c in existing.participants


# ---------------------------------------------------------------------------
# join_engagement
# ---------------------------------------------------------------------------

class TestJoinEngagement:

    def test_join_adds_participant(self):
        a = make_entity('a')
        b = make_entity('b')
        c = make_entity('c')
        engagement = a.engage(EngagementType.COMBAT, b)
        c.join_engagement(engagement)
        assert c in engagement.participants
        assert c.current_engagement is engagement

    def test_join_idempotent_if_already_participating(self):
        a = make_entity('a')
        b = make_entity('b')
        engagement = a.engage(EngagementType.COMBAT, b)
        initial_count = len(engagement.participants)
        a.join_engagement(engagement)  # a is already in it
        assert len(engagement.participants) == initial_count

    def test_cannot_switch_engagement(self):
        """An entity locked into an engagement cannot join a different one."""
        a = make_entity('a')
        b = make_entity('b')
        c = make_entity('c')
        d = make_entity('d')
        eng1 = a.engage(EngagementType.COMBAT, b)
        eng2 = c.engage(EngagementType.COMBAT, d)
        # Try to move b into eng2
        result = b.join_engagement(eng2)
        # b should still be in eng1
        assert result is eng1
        assert b.current_engagement is eng1
        assert b not in eng2.participants


# ---------------------------------------------------------------------------
# resolve_engagement
# ---------------------------------------------------------------------------

class TestResolveEngagement:

    def test_resolve_returns_engagement(self):
        e = make_entity()
        engagement = e.engage(EngagementType.RESTING)
        returned = e.resolve_engagement()
        assert returned is engagement

    def test_resolve_clears_current_engagement(self):
        e = make_entity()
        e.engage(EngagementType.RESTING)
        e.resolve_engagement()
        assert e.current_engagement is None

    def test_resolve_on_no_engagement_returns_none(self):
        e = make_entity()
        result = e.resolve_engagement()
        assert result is None


# ---------------------------------------------------------------------------
# Engagement query helpers
# ---------------------------------------------------------------------------

class TestEngagementQueries:

    def test_is_engaged_true_when_in_engagement(self):
        e = make_entity()
        e.engage(EngagementType.RESTING)
        assert e.is_engaged()

    def test_is_engaged_false_initially(self):
        e = make_entity()
        assert not e.is_engaged()

    def test_is_engaged_with(self):
        a = make_entity('a')
        b = make_entity('b')
        a.engage(EngagementType.COMBAT, b)
        assert a.is_engaged_with(b)
        assert b.is_engaged_with(a)

    def test_is_engaged_in_type(self):
        e = make_entity()
        e.engage(EngagementType.HOARDING)
        assert e.is_engaged_in(EngagementType.HOARDING)
        assert not e.is_engaged_in(EngagementType.RESTING)

    def test_get_others(self):
        a = make_entity('a')
        b = make_entity('b')
        c = make_entity('c')
        engagement = a.engage(EngagementType.COMBAT, b)
        c.join_engagement(engagement)
        others_of_a = engagement.get_others(a)
        assert b in others_of_a
        assert c in others_of_a
        assert a not in others_of_a

    def test_contains_operator(self):
        a = make_entity('a')
        b = make_entity('b')
        engagement = a.engage(EngagementType.COMBAT, b)
        assert a in engagement
        assert b in engagement

    def test_is_solo(self):
        e = make_entity()
        engagement = e.engage(EngagementType.RESTING)
        assert engagement.is_solo()

    def test_not_solo_with_two_participants(self):
        a = make_entity('a')
        b = make_entity('b')
        engagement = a.engage(EngagementType.COMBAT, b)
        assert not engagement.is_solo()
