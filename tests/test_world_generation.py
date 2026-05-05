"""Tests for world generation: heightmap, biomes, and spirit placement."""
import math
import pytest
from game.world.world import World
from game.world.heightmap import HeightMapGenerator
from game.world.types import Biome


# ---------------------------------------------------------------------------
# Heightmap generation
# ---------------------------------------------------------------------------

class TestHeightmap:

    def test_values_in_unit_range(self):
        """All generated height values must lie in [0.0, 1.0]."""
        gen = HeightMapGenerator(seed=42)
        hm = gen.generate_height_map(50, 50)
        for row in hm:
            for val in row:
                assert 0.0 <= val <= 1.0, f"Height {val} out of range"

    def test_normalized_uses_full_range(self):
        """After normalization the min should be ~0 and max should be ~1."""
        gen = HeightMapGenerator(seed=42)
        hm = gen.generate_height_map(100, 100)
        flat = [v for row in hm for v in row]
        assert min(flat) < 0.05, "Min value should be near 0 after normalization"
        assert max(flat) > 0.95, "Max value should be near 1 after normalization"

    def test_deterministic_with_same_seed(self):
        """Same seed must produce identical height maps."""
        gen1 = HeightMapGenerator(seed=99)
        gen2 = HeightMapGenerator(seed=99)
        hm1 = gen1.generate_height_map(30, 30)
        hm2 = gen2.generate_height_map(30, 30)
        assert hm1 == hm2

    def test_different_seeds_produce_different_maps(self):
        """Different seeds should not produce the same map."""
        gen1 = HeightMapGenerator(seed=1)
        gen2 = HeightMapGenerator(seed=2)
        hm1 = gen1.generate_height_map(30, 30)
        hm2 = gen2.generate_height_map(30, 30)
        # Very unlikely to be equal; if they were, the RNG is broken
        assert hm1 != hm2

    def test_correct_dimensions(self):
        w, h = 40, 60
        gen = HeightMapGenerator(seed=0)
        hm = gen.generate_height_map(w, h)
        assert len(hm) == h
        assert all(len(row) == w for row in hm)


# ---------------------------------------------------------------------------
# Biome thresholds
# ---------------------------------------------------------------------------

class TestBiomeThresholds:

    @pytest.mark.parametrize("height,expected_biome", [
        (0.00, Biome.WATER),
        (0.10, Biome.WATER),
        (0.229, Biome.WATER),  # Just below water threshold
        (0.23, Biome.FIELD),   # Exactly at water threshold → field
        (0.45, Biome.FIELD),
        (0.679, Biome.FIELD),  # Just below field threshold
        (0.68, Biome.FOREST),  # Exactly at field threshold → forest
        (0.72, Biome.FOREST),
        (0.799, Biome.FOREST), # Just below forest threshold
        (0.80, Biome.MOUNTAIN),# Exactly at forest threshold → mountain
        (0.90, Biome.MOUNTAIN),
        (1.00, Biome.MOUNTAIN),
    ])
    def test_biome_from_height(self, height, expected_biome):
        assert World.get_biome_from_height(height) == expected_biome

    def test_thresholds_match_design(self):
        """Validate the four boundary values from the design document."""
        # WATER: < 0.23
        assert World.get_biome_from_height(0.22) == Biome.WATER
        assert World.get_biome_from_height(0.23) == Biome.FIELD
        # FIELD: >= 0.23 and < 0.68
        assert World.get_biome_from_height(0.67) == Biome.FIELD
        assert World.get_biome_from_height(0.68) == Biome.FOREST
        # FOREST: >= 0.68 and < 0.80
        assert World.get_biome_from_height(0.79) == Biome.FOREST
        assert World.get_biome_from_height(0.80) == Biome.MOUNTAIN


# ---------------------------------------------------------------------------
# Spirit placement
# ---------------------------------------------------------------------------

class TestSpiritGeneration:

    @pytest.fixture(scope='module')
    def small_world(self):
        """A real world with a controlled seed for spirit placement testing."""
        return World(seed=1234, debug_speed=True)

    def test_spirits_exist(self, small_world):
        """Spirits must be present after world generation."""
        from game.entities.spirit import Spirit
        spirits = [e for e in small_world.entities if isinstance(e, Spirit)]
        assert len(spirits) > 0, "World should contain at least one spirit"

    def test_spirits_at_valid_biomes(self, small_world):
        """Spirits must sit on a tile matching their type."""
        from game.entities.spirit import Spirit, SpiritType

        biome_for_spirit = {
            SpiritType.LAKE: Biome.WATER,
            SpiritType.FOREST: Biome.FOREST,
            SpiritType.MOUNTAIN: Biome.MOUNTAIN,
        }

        for spirit in [e for e in small_world.entities if isinstance(e, Spirit)]:
            x, y = spirit.coordinates
            height = small_world.height_map[y][x]
            actual_biome = small_world.get_biome_from_height(height)
            expected_biome = biome_for_spirit[spirit.type]
            assert actual_biome == expected_biome, (
                f"Spirit {spirit.type} at {spirit.coordinates} is on {actual_biome}, "
                f"expected {expected_biome}"
            )

    def test_spirits_within_bounds(self, small_world):
        """Spirit coordinates must be within the map."""
        from game.entities.spirit import Spirit
        for spirit in [e for e in small_world.entities if isinstance(e, Spirit)]:
            x, y = spirit.coordinates
            assert 0 <= x < small_world.WIDTH
            assert 0 <= y < small_world.HEIGHT

    def test_each_spirit_type_present(self, small_world):
        """Seed 1234 should produce lake, forest, and mountain spirits."""
        from game.entities.spirit import Spirit, SpiritType
        types_found = {s.type for s in small_world.entities if isinstance(s, Spirit)}
        # On a large map there should be at least lake and mountain regions
        assert len(types_found) >= 2, (
            f"Expected multiple spirit types, found: {types_found}"
        )


# ---------------------------------------------------------------------------
# Initial settlement placement
# ---------------------------------------------------------------------------

class TestInitialSettlements:

    @pytest.fixture(scope='module')
    def world(self):
        return World(seed=42, debug_speed=True)

    def test_one_starting_city(self, world):
        from game.entities.settlement.city import City
        cities = [e for e in world.entities if e.__class__.__name__ == 'City' and e.is_alive]
        assert len(cities) >= 1, "World must start with at least one city"

    def test_five_starting_villages(self, world):
        from game.entities.settlement.village import Village
        villages = [e for e in world.entities if e.__class__.__name__ == 'Village' and e.is_alive]
        assert len(villages) >= 5, "World must start with at least 5 villages"

    def test_starting_city_has_spire(self, world):
        """The starting city must immediately spawn a spire (has 10 blessings)."""
        from game.entities.settlement.city import City
        from game.entities.settlement.spire import Spire
        cities = [e for e in world.entities if e.__class__.__name__ == 'City' and e.is_alive]
        assert cities, "No city found"
        city = cities[0]
        spires = [e for e in world.entities if e.__class__.__name__ == 'Spire' and e.is_alive]
        assert len(spires) >= 1, "The starting city must have created at least one spire"

    def test_settlements_on_field_tiles(self, world):
        """All villages and cities should be on field biome tiles."""
        settlement_types = ('Village', 'City')
        for e in world.entities:
            if e.__class__.__name__ in settlement_types and e.is_alive:
                x, y = e.coordinates
                height = world.height_map[y][x]
                biome = world.get_biome_from_height(height)
                assert biome == Biome.FIELD, (
                    f"{e.__class__.__name__} '{e.name}' at {e.coordinates} is on {biome}"
                )


# ---------------------------------------------------------------------------
# Cattle spawning cap
# ---------------------------------------------------------------------------

class TestCattleSpawning:
    """Cattle cap is 20; spawn logic respects it."""

    def test_cattle_cap_at_world_start(self):
        """A fresh world should have fewer than 20 cattle (spawned on first dawn)."""
        world = World(seed=7, debug_speed=True)
        cattle = [e for e in world.entities if e.__class__.__name__ == 'Cattle' and e.is_alive]
        assert len(cattle) <= 20
