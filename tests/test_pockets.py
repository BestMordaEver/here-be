"""Tests for the Pockets mixin — blessing storage and transfer."""
import pytest
from game.entities.base.pockets import Pockets


# ---------------------------------------------------------------------------
# Helpers: minimal Pockets holders
# ---------------------------------------------------------------------------

def make_pocket(max_blessings: int, wasteful: bool = False) -> Pockets:
    p = Pockets.__new__(Pockets)
    Pockets.__init__(p, max_blessings=max_blessings, wasteful=wasteful)
    return p


# ---------------------------------------------------------------------------
# Capacity queries
# ---------------------------------------------------------------------------

class TestCapacity:

    def test_zero_capacity_is_always_full(self):
        p = make_pocket(0)
        assert p.is_full

    def test_zero_capacity_available_space_is_zero(self):
        p = make_pocket(0)
        assert p.available_space() == 0

    def test_unlimited_capacity_never_full(self):
        p = make_pocket(-1)
        p.blessings = 9999
        assert not p.is_full

    def test_unlimited_capacity_available_space_is_minus_one(self):
        p = make_pocket(-1)
        assert p.available_space() == -1

    def test_fixed_capacity_full_when_at_max(self):
        p = make_pocket(3)
        p.blessings = 3
        assert p.is_full

    def test_fixed_capacity_available_space(self):
        p = make_pocket(3)
        p.blessings = 1
        assert p.available_space() == 2

    def test_can_store_zero_capacity_returns_false(self):
        p = make_pocket(0)
        assert not p.can_store()

    def test_can_store_unlimited_returns_true(self):
        p = make_pocket(-1)
        p.blessings = 9999
        assert p.can_store()

    def test_can_store_wasteful_always_returns_true(self):
        """Wasteful pockets always 'can store' even when full."""
        p = make_pocket(3, wasteful=True)
        p.blessings = 3
        assert p.can_store()

    def test_has_blessings_false_when_empty(self):
        p = make_pocket(3)
        assert not p.has_blessings

    def test_has_blessings_true_when_nonzero(self):
        p = make_pocket(3)
        p.blessings = 1
        assert p.has_blessings


# ---------------------------------------------------------------------------
# store_blessing
# ---------------------------------------------------------------------------

class TestStoreBlessings:

    def test_store_within_fixed_capacity(self):
        p = make_pocket(3)
        consumed = p.store_blessing(2)
        assert consumed == 2
        assert p.blessings == 2

    def test_store_rejected_when_zero_capacity(self):
        p = make_pocket(0)
        consumed = p.store_blessing(1)
        assert consumed == 0
        assert p.blessings == 0

    def test_store_clamped_at_capacity(self):
        p = make_pocket(3)
        p.blessings = 2
        consumed = p.store_blessing(5)  # Only 1 slot left
        assert consumed == 1
        assert p.blessings == 3

    def test_store_unlimited(self):
        p = make_pocket(-1)
        consumed = p.store_blessing(100)
        assert consumed == 100
        assert p.blessings == 100

    def test_wasteful_consumes_all_destroys_excess(self):
        """Wasteful pocket: consumed == amount offered, but only stores what fits."""
        p = make_pocket(3, wasteful=True)
        p.blessings = 3  # Already full
        consumed = p.store_blessing(2)
        assert consumed == 2          # Source loses 2
        assert p.blessings == 3       # But pocket didn't gain any (full)

    def test_wasteful_partially_full_stores_up_to_cap(self):
        p = make_pocket(3, wasteful=True)
        p.blessings = 1
        consumed = p.store_blessing(5)
        assert consumed == 5          # Source loses 5
        assert p.blessings == 3       # Pocket fills to cap, discards rest

    def test_store_zero_does_nothing(self):
        p = make_pocket(3)
        consumed = p.store_blessing(0)
        assert consumed == 0
        assert p.blessings == 0


# ---------------------------------------------------------------------------
# transfer_to / transfer_from / empty_blessings
# ---------------------------------------------------------------------------

class TestTransfer:

    def test_transfer_to_moves_blessings(self):
        src = make_pocket(5)
        src.blessings = 3
        dst = make_pocket(5)
        removed = src.transfer_to(dst, 2)
        assert removed == 2
        assert src.blessings == 1
        assert dst.blessings == 2

    def test_transfer_to_capped_by_source(self):
        src = make_pocket(5)
        src.blessings = 1
        dst = make_pocket(5)
        removed = src.transfer_to(dst, 10)
        assert removed == 1
        assert src.blessings == 0
        assert dst.blessings == 1

    def test_transfer_from_mirrors_transfer_to(self):
        src = make_pocket(-1)
        src.blessings = 5
        dst = make_pocket(3)
        removed = dst.transfer_from(src, 3)
        assert removed == 3
        assert src.blessings == 2
        assert dst.blessings == 3

    def test_empty_blessings(self):
        p = make_pocket(-1)
        p.blessings = 7
        taken = p.empty_blessings()
        assert taken == 7
        assert p.blessings == 0

    def test_transfer_to_full_destination_nothing_moves(self):
        src = make_pocket(5)
        src.blessings = 3
        dst = make_pocket(2)
        dst.blessings = 2   # Full
        removed = src.transfer_to(dst, 2)
        assert removed == 0
        assert src.blessings == 3
        assert dst.blessings == 2
