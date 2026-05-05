"""Tests for engagement resolution across all entity types.

Each test artificially constructs an engagement and calls resolve_engagement()
on the relevant participants, then asserts the expected outcome from the design.
"""
import pytest
from tests.conftest import MockWorld, make_spirit, make_blessing, make_bandit, make_dragon, make_hero, make_village, make_camp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_world():
    return MockWorld('field')


def _make_dragon_with_domain(world, properties=None, coords=(25, 25)):
    """Create a dragon; its Domain is auto-added to world via Dragon.__init__."""
    from game.entities import Dragon
    if properties is None:
        properties = ['verdant', 'neutral', 'carnivore', 'blade']
    dragon = Dragon(world, 'Testicus', properties, coords)
    world.add_entity(dragon)
    return dragon


def _make_caravan(world, home, coords=(10, 10)):
    from game.entities.caravan import Caravan, CaravanMission
    caravan = Caravan(
        world,
        coordinates=coords,
        home=home,
        destination=home,
        mission=CaravanMission.TRADE,
    )
    world.add_entity(caravan)
    return caravan


def _finish_hour(world):
    """Resolve all entity engagements once (simulates hour-end).
    
    Dragons resolve first so that party-kill logic sees living heroes.
    """
    entities = list(world.entities)
    # Dragons resolve first: their COMBAT resolver checks living_heroes >= PARTY_SIZE
    for entity in entities:
        if entity.__class__.__name__ == 'Dragon':
            entity.resolve_engagement()
    for entity in entities:
        if entity.__class__.__name__ != 'Dragon':
            entity.resolve_engagement()


# ---------------------------------------------------------------------------
# Spirit TENDING
# ---------------------------------------------------------------------------

class TestTending:

    def test_spirit_gains_blessing_when_tended(self):
        world = _mock_world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.FOREST, (10, 10))
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'carnivore', 'blade'], (10, 10))
        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.TENDING, spirit)
        _finish_hour(world)
        assert spirit.has_blessing, "Spirit should have a blessing after being tended"

    def test_spirit_already_blessed_not_re_tended(self):
        world = _mock_world()
        from game.entities.spirit import SpiritType
        from game.entities.base.engaging import EngagementType
        spirit = make_spirit(world, SpiritType.FOREST, (10, 10))
        spirit.store_blessing(1)  # Already has a blessing
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'carnivore', 'blade'], (10, 10))
        dragon.engage(EngagementType.TENDING, spirit)
        _finish_hour(world)
        # Spirit capacity is 1; count should remain 1
        assert spirit.blessings == 1

    def test_spirit_get_tended_returns_true_when_empty(self):
        world = _mock_world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.LAKE, (5, 5))
        assert spirit.get_tended() is True
        assert spirit.has_blessing

    def test_spirit_get_tended_returns_false_when_occupied(self):
        world = _mock_world()
        from game.entities.spirit import SpiritType
        spirit = make_spirit(world, SpiritType.LAKE, (5, 5))
        spirit.store_blessing(1)
        assert spirit.get_tended() is False

    def test_druid_dragon_tends_all_spirits_in_radius(self):
        """DRUID dragons tend every spirit within 8 tiles on TENDING engagement."""
        world = _mock_world()
        from game.entities.spirit import SpiritType
        from game.entities.base.engaging import EngagementType
        from game.entities import Dragon
        # Three spirits within 8 tiles; one outside
        s1 = make_spirit(world, SpiritType.FOREST, (10, 10))
        s2 = make_spirit(world, SpiritType.FOREST, (14, 14))  # ~5.6 tiles
        s3 = make_spirit(world, SpiritType.FOREST, (10, 17))  # 7 tiles
        s_far = make_spirit(world, SpiritType.FOREST, (10, 20))  # 10 tiles — outside radius

        druid = Dragon(world, 'Druidicus', ['verdant', 'neutral', 'carnivore', 'druid'], (10, 10))
        world.add_entity(druid)

        druid.engage(EngagementType.TENDING, s1)
        _finish_hour(world)

        assert s1.has_blessing, "Spirit 1 (engaged target) should be tended"
        assert s2.has_blessing, "Spirit 2 (within 8 tiles) should be tended by DRUID"
        assert s3.has_blessing, "Spirit 3 (within 8 tiles) should be tended by DRUID"
        assert not s_far.has_blessing, "Spirit beyond 8 tiles should NOT be tended"


# ---------------------------------------------------------------------------
# Dragon HOARDING
# ---------------------------------------------------------------------------

class TestHoarding:

    def test_hoarding_stores_one_blessing(self):
        world = _mock_world()
        from game.entities.base.engaging import EngagementType
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'carnivore', 'blade'], (25, 25))
        dragon.engage(EngagementType.HOARDING)
        _finish_hour(world)
        assert dragon.domain.blessings == 1

    def test_midas_hoarding_stores_two_blessings(self):
        world = _mock_world()
        from game.entities.base.engaging import EngagementType
        from game.entities import Dragon
        midas = Dragon(world, 'Midasius', ['verdant', 'neutral', 'greed', 'midas'], (25, 25))
        world.add_entity(midas)
        midas.engage(EngagementType.HOARDING)
        _finish_hour(world)
        assert midas.domain.blessings == 2

    def test_domain_hoard_caps_at_10(self):
        world = _mock_world()
        from game.entities.base.engaging import EngagementType
        from game.entities import Dragon
        dragon = Dragon(world, 'Greedhog', ['verdant', 'neutral', 'carnivore', 'blade'], (25, 25))
        world.add_entity(dragon)
        dragon.domain.blessings = 9
        dragon.engage(EngagementType.HOARDING)
        _finish_hour(world)
        assert dragon.domain.blessings == 10  # Filled to cap

        # A second hoard should NOT exceed cap
        dragon.engage(EngagementType.HOARDING)
        _finish_hour(world)
        assert dragon.domain.blessings == 10

    def test_midas_domain_caps_at_20(self):
        world = _mock_world()
        from game.entities.base.engaging import EngagementType
        from game.entities import Dragon
        midas = Dragon(world, 'Goldhog', ['verdant', 'neutral', 'greed', 'midas'], (25, 25))
        world.add_entity(midas)
        midas.domain.blessings = 20
        midas.engage(EngagementType.HOARDING)
        _finish_hour(world)
        assert midas.domain.blessings == 20  # Should NOT exceed 20


# ---------------------------------------------------------------------------
# Cattle FEEDING
# ---------------------------------------------------------------------------

class TestCattleFeeding:

    def test_cattle_die_from_feeding_engagement(self):
        world = _mock_world()
        from game.entities.cattle import Cattle
        from game.entities.base.engaging import EngagementType

        cattle = Cattle(world, "#8B5E3C", (10, 10))
        world.add_entity(cattle)

        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'carnivore', 'blade'], (10, 10))
        dragon.engage(EngagementType.FEEDING, cattle)
        _finish_hour(world)
        assert cattle.is_dead, "Cattle should die during a FEEDING engagement with a dragon"

    def test_cattle_survive_non_feeding_engagement(self):
        world = _mock_world()
        from game.entities.cattle import Cattle
        from game.entities.base.engaging import EngagementType

        cattle = Cattle(world, "#8B5E3C", (10, 10))
        world.add_entity(cattle)

        cattle.engage(EngagementType.RESTING)
        _finish_hour(world)
        assert cattle.is_alive, "Cattle should survive a RESTING engagement"


# ---------------------------------------------------------------------------
# Bandit ROBBERY
# ---------------------------------------------------------------------------

class TestRobbery:

    def test_bandit_takes_caravan_blessing(self):
        world = _mock_world()
        village = make_village(world, (25, 25))
        bandit = make_bandit(world, (10, 10))
        caravan = _make_caravan(world, village, (10, 10))
        caravan.blessing = True

        from game.entities.base.engaging import EngagementType
        bandit.engage(EngagementType.ROBBERY, caravan)
        _finish_hour(world)

        assert not caravan.blessing, "Caravan should lose its blessing after robbery"
        assert bandit.blessings == 1, "Bandit should gain 1 blessing"

    def test_bandit_resets_days_since_robbery(self):
        world = _mock_world()
        village = make_village(world, (25, 25))
        bandit = make_bandit(world, (10, 10))
        bandit.days_since_robbery = 5
        caravan = _make_caravan(world, village, (10, 10))
        caravan.blessing = True

        from game.entities.base.engaging import EngagementType
        bandit.engage(EngagementType.ROBBERY, caravan)
        _finish_hour(world)

        assert bandit.days_since_robbery == 0

    def test_wasteful_bandit_full_destroys_blessing(self):
        """If bandit is full (wasteful), it still takes the caravan's blessing but discards it."""
        world = _mock_world()
        village = make_village(world, (25, 25))
        bandit = make_bandit(world, (10, 10))
        bandit.blessings = 3  # Full (max is 3)
        caravan = _make_caravan(world, village, (10, 10))
        caravan.blessing = True

        from game.entities.base.engaging import EngagementType
        bandit.engage(EngagementType.ROBBERY, caravan)
        _finish_hour(world)

        assert not caravan.blessing, "Caravan loses blessing even when bandit is full"
        assert bandit.blessings == 3, "Full wasteful bandit does not accumulate more"
        assert bandit.days_since_robbery == 0, "days_since_robbery still resets"


# ---------------------------------------------------------------------------
# Settlement COMBAT
# ---------------------------------------------------------------------------

class TestSettlementCombat:

    def test_dragon_deals_1hp_damage_to_village(self):
        world = _mock_world()
        village = make_village(world, (25, 25))
        starting_life = village.life
        dragon = _make_dragon_with_domain(world, ['verdant', 'evil', 'greed', 'blade'], (25, 25))

        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.COMBAT, village)
        _finish_hour(world)

        assert village.life == starting_life - 1

    def test_hero_protects_settlement_from_dragon(self):
        """A hero joining the engagement blocks dragon damage (non-BLADE)."""
        world = _mock_world()
        village = make_village(world, (25, 25))
        starting_life = village.life
        # Non-blade dragon
        dragon = _make_dragon_with_domain(world, ['verdant', 'evil', 'greed', 'blade'], (25, 25))
        # Change to non-blade by using brute properties instead
        dragon2 = _make_dragon_with_domain(world, ['verdant', 'evil', 'greed', 'brute'], (24, 24))

        hero = make_hero(world, home=village, coords=(25, 25))

        from game.entities.base.engaging import EngagementType
        dragon2.engage(EngagementType.COMBAT, village)
        hero.join_engagement(village.current_engagement)

        _finish_hour(world)
        assert village.life == starting_life, "Hero should block damage from non-BLADE dragon"

    def test_blade_dragon_bypasses_hero_protection(self):
        """A BLADE dragon deals damage even when a hero is protecting."""
        world = _mock_world()
        village = make_village(world, (25, 25))
        starting_life = village.life
        dragon = _make_dragon_with_domain(world, ['verdant', 'evil', 'greed', 'blade'], (25, 25))
        hero = make_hero(world, home=village, coords=(25, 25))

        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.COMBAT, village)
        hero.join_engagement(village.current_engagement)

        _finish_hour(world)
        assert village.life < starting_life, "BLADE dragon should bypass hero protection"

    def test_brute_dragon_one_shots_camp(self):
        """BRUTE dragon destroys a camp in one hit regardless of HP."""
        world = _mock_world()
        village = make_village(world, (25, 25))
        camp = make_camp(world, parent=village, coords=(10, 10))
        from game.entities import Dragon
        brute = Dragon(world, 'Bruteicus', ['verdant', 'evil', 'greed', 'brute'], (10, 10))
        world.add_entity(brute)

        from game.entities.base.engaging import EngagementType
        brute.engage(EngagementType.COMBAT, camp)
        _finish_hour(world)

        assert camp.is_dead, "BRUTE dragon should one-shot a camp"

    def test_brute_dragon_reduces_village_to_1hp(self):
        """BRUTE dragon reduces village to 1 HP (doesn't one-shot)."""
        world = _mock_world()
        village = make_village(world, (25, 25))
        village.life = 3  # Ensure full HP
        from game.entities import Dragon
        brute = Dragon(world, 'Bruteicus2', ['verdant', 'evil', 'greed', 'brute'], (25, 25))
        world.add_entity(brute)

        from game.entities.base.engaging import EngagementType
        brute.engage(EngagementType.COMBAT, village)
        _finish_hour(world)

        assert village.life == 1, f"BRUTE should reduce village to 1 HP, got {village.life}"

    def test_village_dies_at_zero_hp(self):
        world = _mock_world()
        village = make_village(world, (25, 25))
        village.life = 1
        dragon = _make_dragon_with_domain(world, ['verdant', 'evil', 'greed', 'blade'], (25, 25))

        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.COMBAT, village)
        _finish_hour(world)

        assert village.is_dead


# ---------------------------------------------------------------------------
# Hero COMBAT
# ---------------------------------------------------------------------------

class TestHeroCombat:

    def test_solo_hero_vs_dragon_becomes_tired(self):
        """Solo hero fighting a dragon should become tired (unless VENGEFUL)."""
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (25, 25))
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.mood = HeroMood.ADVENTUROUS
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'greed', 'brute'], (10, 10))

        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.COMBAT, hero)
        _finish_hour(world)

        assert hero.tired_today or not hero.is_alive, (
            "Solo hero vs dragon should be tired or dead"
        )

    def test_vengeful_hero_vs_dragon_not_auto_tired(self):
        """VENGEFUL hero fighting dragon should NOT become tired."""
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (25, 25))
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.mood = HeroMood.VENGEFUL
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'greed', 'brute'], (10, 10))

        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.COMBAT, hero)
        _finish_hour(world)

        assert not hero.tired_today, "VENGEFUL hero should not become tired from dragon combat"

    def test_tired_hero_vs_blade_dragon_dies(self):
        """A TIRED hero always dies fighting a BLADE dragon."""
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (25, 25))
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.mood = HeroMood.TIRED
        hero.tired_today = True
        blade = _make_dragon_with_domain(world, ['verdant', 'neutral', 'greed', 'blade'], (10, 10))

        from game.entities.base.engaging import EngagementType
        blade.engage(EngagementType.COMBAT, hero)
        _finish_hour(world)

        assert hero.is_dead, "TIRED hero vs BLADE dragon should die"

    def test_tired_hero_outside_settlement_dies(self):
        """TIRED hero with no nearby settlement dies against any dragon."""
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (45, 45))  # Far away
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.mood = HeroMood.TIRED
        hero.tired_today = True
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'greed', 'brute'], (10, 10))

        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.COMBAT, hero)
        _finish_hour(world)

        assert hero.is_dead, "TIRED hero away from settlement should die vs dragon"

    def test_full_party_kills_dragon(self):
        """4 heroes in a party kill the dragon."""
        from game.entities.hero.types import HeroMood, PARTY_SIZE
        world = _mock_world()
        village = make_village(world, (25, 25))
        heroes = [make_hero(world, home=village, coords=(10, 10)) for _ in range(PARTY_SIZE)]
        # Set up party
        for h in heroes:
            h.party = heroes
            h.party_leader = heroes[0]
            h.mood = HeroMood.FOREBODING

        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'greed', 'brute'], (10, 10))

        from game.entities.base.engaging import EngagementType
        dragon.engage(EngagementType.COMBAT, heroes[0])
        for h in heroes[1:]:
            h.join_engagement(heroes[0].current_engagement)
        _finish_hour(world)

        assert dragon.is_dead, "Dragon should die against a full party of 4 heroes"

    def test_blade_dragon_party_causes_2_casualties(self):
        """BLADE dragon vs 4-hero party: dragon dies, first 2 heroes die."""
        from game.entities.hero.types import HeroMood, PARTY_SIZE
        from game.entities import Dragon
        world = _mock_world()
        village = make_village(world, (25, 25))
        heroes = [make_hero(world, home=village, coords=(10, 10)) for _ in range(PARTY_SIZE)]
        for h in heroes:
            h.party = heroes
            h.party_leader = heroes[0]
            h.mood = HeroMood.FOREBODING

        blade = Dragon(world, 'Bladix', ['verdant', 'evil', 'greed', 'blade'], (10, 10))
        world.add_entity(blade)

        from game.entities.base.engaging import EngagementType
        blade.engage(EngagementType.COMBAT, heroes[0])
        for h in heroes[1:]:
            h.join_engagement(heroes[0].current_engagement)
        _finish_hour(world)

        assert blade.is_dead, "Dragon should die"
        sorted_by_id = sorted(heroes, key=id)
        dead = [h for h in sorted_by_id[:2] if h.is_dead]
        alive = [h for h in sorted_by_id[2:] if h.is_alive]
        assert len(dead) == 2, f"First 2 heroes by id should die, got {[h.is_dead for h in sorted_by_id]}"
        assert len(alive) == 2, "Last 2 heroes should survive"

    def test_nonblade_dragon_party_causes_1_casualty(self):
        """Non-BLADE dragon vs 4-hero party: dragon dies, first 1 hero dies."""
        from game.entities.hero.types import HeroMood, PARTY_SIZE
        from game.entities import Dragon
        world = _mock_world()
        village = make_village(world, (25, 25))
        heroes = [make_hero(world, home=village, coords=(10, 10)) for _ in range(PARTY_SIZE)]
        for h in heroes:
            h.party = heroes
            h.party_leader = heroes[0]
            h.mood = HeroMood.FOREBODING

        brute = Dragon(world, 'Brutix', ['verdant', 'evil', 'greed', 'brute'], (10, 10))
        world.add_entity(brute)

        from game.entities.base.engaging import EngagementType
        brute.engage(EngagementType.COMBAT, heroes[0])
        for h in heroes[1:]:
            h.join_engagement(heroes[0].current_engagement)
        _finish_hour(world)

        assert brute.is_dead, "Dragon should die"
        sorted_by_id = sorted(heroes, key=id)
        assert sorted_by_id[0].is_dead, "First hero by id should die"
        for h in sorted_by_id[1:]:
            assert h.is_alive, "Heroes 2-4 should survive against non-BLADE"


# ---------------------------------------------------------------------------
# Bandit COMBAT
# ---------------------------------------------------------------------------

class TestBanditCombat:

    def test_vengeful_hero_kills_bandit(self):
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (25, 25))
        bandit = make_bandit(world, (10, 10))
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.mood = HeroMood.VENGEFUL

        from game.entities.base.engaging import EngagementType
        bandit.engage(EngagementType.COMBAT, village)
        hero.join_engagement(village.current_engagement)
        _finish_hour(world)

        assert bandit.is_dead, "Bandit should die when VENGEFUL hero is in the engagement"

    def test_non_vengeful_hero_does_not_kill_bandit(self):
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (25, 25))
        bandit = make_bandit(world, (10, 10))
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.mood = HeroMood.ADVENTUROUS  # Not vengeful

        from game.entities.base.engaging import EngagementType
        bandit.engage(EngagementType.COMBAT, village)
        hero.join_engagement(village.current_engagement)
        _finish_hour(world)

        # Village should be protected (hero present), bandit lives
        assert bandit.is_alive, "Non-vengeful hero does not kill the bandit"

    def test_bandit_steals_from_settlement_when_winning(self):
        """Bandit outnumbering protectors takes blessings from settlement."""
        world = _mock_world()
        village = make_village(world, (25, 25))
        village.blessings = 3
        bandit = make_bandit(world, (25, 25))

        from game.entities.base.engaging import EngagementType
        bandit.engage(EngagementType.COMBAT, village)
        _finish_hour(world)

        # Bandit wins (no protectors), should have taken blessings
        assert bandit.blessings > 0, "Bandit should steal blessings from unprotected settlement"
        assert village.blessings < 3, "Settlement should lose blessings"


# ---------------------------------------------------------------------------
# Hero/Bandit PILLAGING
# ---------------------------------------------------------------------------

class TestPillaging:

    def test_hero_pillages_dragon_domain(self):
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (25, 25))
        hero = make_hero(world, home=village, coords=(10, 10))
        hero.mood = HeroMood.OPPORTUNISTIC

        # Create a dragon domain that is now a treasury (dragon dead)
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'greed', 'blade'], (10, 10))
        dragon.domain.blessings = 5
        dragon.domain.is_treasury = True  # Dragon has died
        dragon.domain.dragon = None

        from game.entities.base.engaging import EngagementType
        hero.engage(EngagementType.PILLAGING, dragon.domain)
        _finish_hour(world)

        assert hero.blessings > 0, "Hero should have claimed blessings from domain treasury"

    def test_bandit_pillages_domain(self):
        world = _mock_world()
        bandit = make_bandit(world, (10, 10))
        dragon = _make_dragon_with_domain(world, ['verdant', 'neutral', 'greed', 'blade'], (10, 10))
        dragon.domain.blessings = 5
        dragon.domain.is_treasury = True
        dragon.domain.dragon = None

        from game.entities.base.engaging import EngagementType
        bandit.engage(EngagementType.PILLAGING, dragon.domain)
        _finish_hour(world)

        assert bandit.blessings > 0, "Bandit should have claimed blessings from treasury"

    def test_hero_pillages_ruins(self):
        """Hero pillages a dead settlement's remaining blessings."""
        from game.entities.hero.types import HeroMood
        world = _mock_world()
        village = make_village(world, (25, 25))
        village.blessings = 3
        village.is_alive = False
        village.is_dead = True  # Ruins: can_be_pillaged() requires is_dead=True

        hero = make_hero(world, home=None, coords=(25, 25))
        hero.mood = HeroMood.OPPORTUNISTIC

        from game.entities.base.engaging import EngagementType
        hero.engage(EngagementType.PILLAGING, village)
        _finish_hour(world)

        assert hero.blessings > 0 or village.blessings < 3, (
            "Hero should claim blessings from ruins"
        )
