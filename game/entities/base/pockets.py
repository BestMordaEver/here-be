"""Pockets mixin — blessing storage and transfer system.

Provides a unified interface for entities that carry, store, or transfer
blessings.  The ``max_blessings`` parameter controls capacity:

    *  ``0``  — entity cannot store blessings (e.g. cattle, spirits)
    * ``-1``  — unlimited storage (e.g. settlements, dragon domains)
    *  ``N``  — fixed capacity of *N* blessings (e.g. heroes=3, bandits=3,
                caravans=1)

The ``wasteful`` flag models the bandit pattern: when storage is full the
entity still *accepts* incoming blessings (the source loses them) but the
excess is permanently destroyed rather than refused.
"""

class Pockets:
    """Mixin for entities that can store and transfer blessings.

    Call ``Pockets.__init__(self, max_blessings, wasteful)`` in the
    concrete entity's ``__init__`` to configure storage.
    """

    def __init__(self, max_blessings: int = 0, wasteful: bool = False) -> None:
        self.blessings: int = 0
        self.max_blessings: int = max_blessings
        self.wasteful: bool = wasteful

    # ==================== Capacity queries ====================

    @property
    def has_blessings(self) -> bool:
        """Whether this entity currently holds any blessings."""
        return self.blessings > 0

    @property
    def is_full(self) -> bool:
        """Whether blessing storage is at capacity.

        Entities with ``max_blessings=0`` are always considered full
        (they cannot store).  Unlimited (``-1``) entities are never full.
        """
        if self.max_blessings < 0:
            return False          # Unlimited
        if self.max_blessings == 0:
            return True           # Can't store at all
        return self.blessings >= self.max_blessings

    def available_space(self) -> int:
        """Number of additional blessings that can be stored.

        Returns ``-1`` for unlimited capacity.
        """
        if self.max_blessings < 0:
            return -1             # Unlimited
        return max(0, self.max_blessings - self.blessings)

    def can_store(self, count: int = 1) -> bool:
        """Check whether *count* blessings can be stored.

        Wasteful entities always 'can store' (they accept and destroy
        excess), so this returns ``True`` for them even when full.
        """
        if self.max_blessings == 0:
            return False
        if self.wasteful:
            return True
        if self.max_blessings < 0:
            return True           # Unlimited
        return self.blessings + count <= self.max_blessings

    # ==================== Storage operations ====================

    def store_blessing(self, count: int = 1) -> int:
        """Add blessings to storage.

        Returns the number of blessings *consumed* (removed from the
        source).  For non-wasteful entities this equals the number
        actually stored.  For wasteful entities the return value may
        exceed the number stored — the difference is permanently lost.

        Examples::

            hero.store_blessing(2)    # stores 2, returns 2
            bandit.store_blessing(2)  # full, stores 0, returns 2 (wasteful)
            cattle.store_blessing(1)  # max=0, stores 0, returns 0
        """
        if count <= 0 or self.max_blessings == 0:
            return 0

        if self.max_blessings < 0:
            # Unlimited storage
            self.blessings += count
            return count

        space = self.max_blessings - self.blessings
        stored = min(count, space)
        self.blessings += stored

        if self.wasteful:
            # Wasteful entities consume everything offered, even excess
            return count

        return stored

    def transfer_to(self, target: "Pockets", count: int = 1) -> int:
        """Transfer blessings from this entity to *target*.
        Returns the number of blessings removed from this entity.
        """
        available = min(count, self.blessings)
        if available <= 0:
            return 0

        consumed = target.store_blessing(available)
        self.blessings -= consumed
        return consumed
    
    def transfer_from(self, source: "Pockets", count: int = 1) -> int:
        """Transfer blessings from *source* to this entity.
        Returns the number of blessings removed from *source*.
        """
        return source.transfer_to(self, count)

    def empty_blessings(self) -> int:
        """Remove and return all stored blessings. Convenience wrapper."""
        taken = self.blessings
        self.blessings = 0
        return taken
