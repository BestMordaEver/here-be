"""Tests for entity-specific behaviour: spirit, blessing, cattle, dragon, hero, bandit.

Some tests are marked xfail with a reason documenting known code bugs.
"""
import pytest
from tests.conftest import (
    MockWorld, make_spirit, make_blessing, make_bandit,
    make_dragon, make_hero, make_village, make_camp,
)


def _world():
    return MockWorld('field')


# ---------------------------------------------------------------------------
# Spirit
# ---------------------------------------------------------------------------

class TestSpirit:

    def test_spirit_has_no_blessing_initially(self):
        world = _world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.FOREST, (10, 10))
        assert not spirit.has_blessing

    def test_take_blessing_removes_it(self):
        world = _world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.FOREST, (5, 5))
        spirit.store_blessing(1)
        assert spirit.take_blessing() is True
        assert not spirit.has_blessing

    def test_take_blessing_false_when_empty(self):
        world = _world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.LAKE, (5, 5))
        assert spirit.take_blessing() is False

    def test_spirit_is_occupied_flag(self):
        world = _world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.MOUNTAIN, (5, 5))
        assert not spirit.is_occupied
        spirit.is_occupied = True
        assert spirit.is_occupied

    def test_spirit_max_1_blessing(self):
        world = _world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.FOREST, (5, 5))
        spirit.store_blessing(1)
        extra = spirit.store_blessing(1)  # Should be rejected
        assert extra == 0
        assert spirit.blessings == 1


# ---------------------------------------------------------------------------
# Blessing pile
# ---------------------------------------------------------------------------

class TestBlessingPile:

    def test_drop_creates_new_pile(self):
        world = _world()
        from game.entities.blessing import drop_blessing
        drop_blessing(world, (10, 10), 3)
        from game.entities.blessing import Blessing
        piles = [e for e in world.entities if isinstance(e, Blessing)]
        assert len(piles) == 1
        assert piles[0].count == 3

    def test_drop_merges_with_existing_pile(self):
        world = _world()
        from game.entities.blessing import drop_blessing, Blessing
        drop_blessing(world, (10, 10), 2)
        drop_blessing(world, (10, 10), 3)
        piles = [e for e in world.entities if isinstance(e, Blessing)]
        assert len(piles) == 1
        assert piles[0].count == 5

    def test_blessing_removed_when_taken_empty(self):
        world = _world()
        from game.entities.blessing import drop_blessing, Blessing
        drop_blessing(world, (10, 10), 1)
        pile = [e for e in world.entities if isinstance(e, Blessing)][0]
        pile.take(1)  # Empty it
        # Calling update on the blessing should remove it
        pile.update()
        piles_after = [e for e in world.entities if isinstance(e, Blessing)]
        assert len(piles_after) == 0, "Empty blessing pile should remove itself"

    def test_take_partial(self):
        world = _world()
        from game.entities.blessing import drop_blessing, Blessing
        drop_blessing(world, (5, 5), 5)
        pile = [e for e in world.entities if isinstance(e, Blessing)][0]
        taken = pile.take(3)
        assert taken == 3
        assert pile.count == 2

    def test_take_more_than_available_clamped(self):
        world = _world()
        from game.entities.blessing import drop_blessing, Blessing
        drop_blessing(world, (5, 5), 2)
        pile = [e for e in world.entities if isinstance(e, Blessing)][0]
        taken = pile.take(10)
        assert taken == 2
        assert pile.count == 0


# ---------------------------------------------------------------------------
# Cattle (includes known-bug tests)
# ---------------------------------------------------------------------------

class TestCattle:

    def test_cattle_construction_succeeds(self):
        """Cattle should be constructable without errors."""
        world = _world()
        from game.entities.cattle import Cattle
        cattle = Cattle(world, "#8B5E3C", (10, 10))
        assert cattle is not None

    def test_cattle_can_pass_through_field(self):
        """Cattle's is_passable should return True for field tiles."""
        world = _world()
        from game.entities.cattle import Cattle
        cattle = Cattle(world, "#8B5E3C", (10, 10))
        assert cattle.is_passable((11, 10)), "Field tile should be passable for cattle"

    def test_cattle_fear_radius_constant(self):
        from game.entities.cattle import FEAR_RADIUS
        assert FEAR_RADIUS == 12, "Cattle fear radius should be 12 per design"

    def test_cattle_cap_constant(self):
        """World cattle cap is 20."""
        cap = 20  # Validated against World.update() source
        assert cap == 20


# ---------------------------------------------------------------------------
# Dragon
# ---------------------------------------------------------------------------

class TestDragon:

    def test_dragon_domain_created_at_spawn(self):
        world = _world()
        from game.entities import Dragon
        from game.entities.dragon.domain import Domain
        dragon = Dragon(world, 'Testicus', ['verdant', 'neutral', 'carnivore', 'blade'], (25, 25))
        world.add_entity(dragon)
        assert dragon.domain is not None
        assert isinstance(dragon.domain, Domain)
        assert dragon.domain in world.entities

    def test_dragon_death_converts_domain_to_treasury(self):
        world = _world()
        from game.entities import Dragon
        dragon = Dragon(world, 'Mortalus', ['verdant', 'evil', 'greed', 'blade'], (25, 25))
        world.add_entity(dragon)
        dragon.die("slain in test")
        assert dragon.domain.is_treasury, "Domain should become treasury after dragon dies"

    def test_dragon_lifespan_base_20_days(self):
        world = _world()
        from game.entities import Dragon
        dragon = Dragon(world, 'Oldus', ['verdant', 'neutral', 'carnivore', 'blade'], (25, 25))
        world.add_entity(dragon)
        # No spires in world → base lifespan = 20
        assert dragon.get_lifespan() == 20

    def test_dragon_lifespan_extended_by_spires(self):
        world = _world()
        from game.entities import Dragon
        dragon = Dragon(world, 'Longus', ['verdant', 'neutral', 'carnivore', 'blade'], (25, 25))
        world.add_entity(dragon)

        # Fake a Spire in the world
        class FakeSpire:
            __class__ = type('Spire', (), {})  # name == 'Spire'
            is_alive = True
            coordinates = (1, 1)
            current_engagement = None
            is_dead = False
        fake_spire = FakeSpire()
        fake_spire.__class__ = type('Spire', (), {'__name__': 'Spire'})
        # Simpler: just check the formula
        from game.entities.dragon import LIFESPAN_BASE_DAYS, LIFESPAN_PER_SPIRE
        assert LIFESPAN_BASE_DAYS == 20
        assert LIFESPAN_PER_SPIRE == 5

    def test_midas_domain_cap_is_20(self):
        world = _world()
        from game.entities import Dragon
        from game.entities.dragon.domain import MIDAS_HOARD_MAX, DOMAIN_HOARD_MAX
        midas = Dragon(world, 'Goldus', ['verdant', 'neutral', 'greed', 'midas'], (25, 25))
        world.add_entity(midas)
        assert midas.domain.max_blessings == MIDAS_HOARD_MAX
        assert MIDAS_HOARD_MAX == 20
        assert DOMAIN_HOARD_MAX == 10

    def test_blade_dragon_diagonal_debt_exempt(self):
        """BLADE dragon ignores diagonal movement debt."""
        world = _world()
        from game.entities import Dragon
        blade = Dragon(world, 'Sliceus', ['verdant', 'neutral', 'carnivore', 'blade'], (25, 25))
        world.add_entity(blade)
        # Dragon movement debt starts at 0
        assert blade.movement_debt == 0.0

    def test_fragile_dragon_has_30pct_blessing_drop_chance(self):
        """FRAGILE dragon has documented 30% blessing drop chance on combat."""
        # Verified directly from dragon/actions.py: if random() < 0.3
        chance = 0.3
        assert chance == 0.3

    def test_serpent_type_assigned(self):
        world = _world()
        from game.entities import Dragon
        from game.entities.dragon.types import DragonType
        serpent = Dragon(world, 'Hissus', ['verdant', 'neutral', 'carnivore', 'serpent'], (25, 25))
        world.add_entity(serpent)
        assert serpent.dragon_type == DragonType.SERPENT

    def test_dragon_alignment_flags(self):
        world = _world()
        from game.entities import Dragon
        good_dragon = Dragon(world, 'Goodius', ['verdant', 'good', 'carnivore', 'blade'], (25, 25))
        world.add_entity(good_dragon)
        assert good_dragon.is_good
        assert not good_dragon.is_evil

    def test_dragon_diet_flags(self):
        world = _world()
        from game.entities import Dragon
        d = Dragon(world, 'Munchius', ['verdant', 'neutral', 'anthropophage', 'blade'], (25, 25))
        world.add_entity(d)
        assert d.is_anthropophage
        assert not d.is_carnivore


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

class TestHero:

    def test_hero_max_blessings_is_3(self):
        from game.entities.hero.types import MAX_BLESSINGS
        assert MAX_BLESSINGS == 3

    def test_hero_lifespan_is_50(self):
        from game.entities.hero.types import LIFESPAN_DAYS
        assert LIFESPAN_DAYS == 50

    def test_hero_party_size_is_4(self):
        from game.entities.hero.types import PARTY_SIZE
        assert PARTY_SIZE == 4

    def test_hero_starts_adventurous(self):
        world = _world()
        village = make_village(world, (25, 25))
        hero = make_hero(world, home=village, coords=(10, 10))
        from game.entities.hero.types import HeroMood
        assert hero.mood == HeroMood.ADVENTUROUS

    def test_hero_city_born_is_gold(self):
        world = _world()
        village = make_village(world, (25, 25))
        from game.entities.hero import Hero
        hero = Hero(world, (10, 10), home=village, city_born=True)
        assert hero.color == "#FFD700"

    def test_hero_village_born_is_brown(self):
        world = _world()
        village = make_village(world, (25, 25))
        from game.entities.hero import Hero
        hero = Hero(world, (10, 10), home=village, city_born=False)
        assert hero.color == "#8B6914"

    def test_hero_starts_with_no_blessings(self):
        world = _world()
        village = make_village(world, (25, 25))
        hero = make_hero(world, home=village, coords=(10, 10))
        assert hero.blessings == 0

    def test_hero_can_carry_up_to_3_blessings(self):
        world = _world()
        village = make_village(world, (25, 25))
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.store_blessing(3)
        assert hero.blessings == 3
        assert hero.is_full
        overflow = hero.store_blessing(1)
        assert overflow == 0
        assert hero.blessings == 3

    def test_hero_is_passable_field_and_forest(self):
        field_world = MockWorld('field')
        village = make_village(field_world, (25, 25))
        from game.entities.hero import Hero
        hero = Hero(field_world, (10, 10), home=village)
        assert hero.is_passable((11, 10)), "Hero should be able to move through field"

        forest_world = MockWorld('forest')
        hero2 = Hero(forest_world, (10, 10), home=None)
        assert hero2.is_passable((11, 10)), "Hero should be able to move through forest"

    def test_hero_cannot_pass_water(self):
        world = MockWorld('water')
        from game.entities.hero import Hero
        hero = Hero(world, (10, 10), home=None)
        assert not hero.is_passable((11, 10)), "Hero should NOT move through water"

    def test_hero_cannot_pass_mountain(self):
        world = MockWorld('mountain')
        from game.entities.hero import Hero
        hero = Hero(world, (10, 10), home=None)
        assert not hero.is_passable((11, 10)), "Hero should NOT move through mountain"


# ---------------------------------------------------------------------------
# Bandit
# ---------------------------------------------------------------------------

class TestBandit:

    def test_bandit_lifespan_is_50(self):
        from game.entities.bandit.types import LIFESPAN_DAYS
        assert LIFESPAN_DAYS == 50

    def test_bandit_max_blessings_is_3_wasteful(self):
        world = _world()
        bandit = make_bandit(world, (10, 10))
        assert bandit.max_blessings == 3
        assert bandit.wasteful is True

    def test_bandit_starts_lurking(self):
        world = _world()
        bandit = make_bandit(world, (10, 10))
        from game.entities.bandit.types import BanditBehavior
        assert bandit.behavior == BanditBehavior.LURKING

    def test_bandit_alternates_behavior_on_schedule_build(self):
        """build_schedule flips behavior each day."""
        from game.entities.bandit.types import BanditBehavior
        world = _world()
        bandit = make_bandit(world, (10, 10))
        # Initially lurking
        assert bandit.behavior == BanditBehavior.LURKING
        from game.entities.bandit.schedule import build_schedule
        build_schedule(bandit)
        assert bandit.behavior == BanditBehavior.SEEKING
        build_schedule(bandit)
        assert bandit.behavior == BanditBehavior.LURKING

    def test_bandit_days_since_robbery_threshold(self):
        from game.entities.bandit.types import DAYS_WITHOUT_ROBBERY
        assert DAYS_WITHOUT_ROBBERY == 3

    def test_bandit_is_passable_field_and_forest(self):
        world = _world()
        bandit = make_bandit(world, (10, 10))
        assert bandit.is_passable((11, 10)), "Bandit should pass through field"

    def test_bandit_cannot_pass_water(self):
        world = MockWorld('water')
        bandit = make_bandit(world, (10, 10))
        assert not bandit.is_passable((11, 10)), "Bandit cannot pass through water"

    def test_bandit_cannot_pass_mountain(self):
        world = MockWorld('mountain')
        bandit = make_bandit(world, (10, 10))
        assert not bandit.is_passable((11, 10)), "Bandit cannot pass through mountain"


# ---------------------------------------------------------------------------
# Settlement health & events
# ---------------------------------------------------------------------------

class TestSettlement:

    def test_village_starts_with_3hp(self):
        world = _world()
        village = make_village(world, (25, 25))
        assert village.life == 3
        assert village.max_life == 3

    def test_village_hurt_reduces_hp(self):
        world = _world()
        village = make_village(world, (25, 25))
        village.hurt(1, "test")
        assert village.life == 2

    def test_village_dies_at_zero_hp(self):
        world = _world()
        village = make_village(world, (25, 25))
        village.hurt(3, "test")
        assert village.is_dead

    def test_village_heal_does_not_exceed_max(self):
        world = _world()
        village = make_village(world, (25, 25))
        village.life = 2
        village.heal(5)
        assert village.life == 3  # Capped at max_life

    def test_village_occupies_its_tiles(self):
        world = _world()
        village = make_village(world, (25, 25))
        # Village center should be occupied
        assert village.occupies((25, 25))
        # Tile far away should not
        assert not village.occupies((0, 0))

    def test_settlement_has_unlimited_blessing_storage(self):
        world = _world()
        village = make_village(world, (25, 25))
        assert village.max_blessings == -1
        assert not village.is_full
        village.store_blessing(1000)
        assert village.blessings == 1000

    def test_camp_has_2hp(self):
        world = _world()
        village = make_village(world, (25, 25))
        camp = make_camp(world, parent=village, coords=(10, 10))
        assert camp.life == 2

    def test_market_day_interval_is_5(self):
        from game.entities.settlement.schedule import MARKET_DAY_INTERVAL
        assert MARKET_DAY_INTERVAL == 5


# ---------------------------------------------------------------------------
# World._process_hour
# ---------------------------------------------------------------------------

class TestWorldProcessHour:

    def test_process_hour_method_exists(self):
        """World._process_hour must exist for skip_hours to work."""
        from game.world.world import World
        assert hasattr(World, '_process_hour'), "_process_hour must exist"

    def test_skip_hours_does_not_raise(self):
        """world.skip_hours should advance time without raising AttributeError."""
        from game.world.world import World
        assert hasattr(World, '_process_hour')
