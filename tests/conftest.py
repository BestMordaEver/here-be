"""Shared fixtures for Here Be Dragons test suite."""
import pytest
from game.world.world import World
from game.world.types import Biome


# ---------------------------------------------------------------------------
# Minimal world mock
# ---------------------------------------------------------------------------

class MockTime:
    """Minimal time mock with mutable day/hour for testing."""
    def __init__(self, day: int = 1, hour: int = 7):
        self.current_day = day
        self.current_hour = hour


class MockWorld:
    """
    Lightweight world substitute for unit tests.

    The heightmap is a flat grid; all tiles default to a single height value
    so the caller controls which biome the world represents.  Spirit generation,
    settlement spawning and the real time-loop are all omitted.

    Default biome heights:
        water   → 0.10
        field   → 0.45   ← default
        forest  → 0.72
        mountain→ 0.88
    """
    WIDTH = 50
    HEIGHT = 50

    # Convenient height presets
    BIOME_HEIGHT = {
        'water':    0.10,
        'field':    0.45,
        'forest':   0.72,
        'mountain': 0.88,
    }

    def __init__(self, biome: str = 'field'):
        h = self.BIOME_HEIGHT[biome]
        self.height_map = [[h] * self.WIDTH for _ in range(self.HEIGHT)]
        self.entities: list = []
        self.time = MockTime()

    @staticmethod
    def get_biome_from_height(height: float) -> Biome:
        return World.get_biome_from_height(height)

    # --- entity management ---

    def add_entity(self, entity) -> None:
        if entity not in self.entities:
            self.entities.append(entity)

    def remove_entity(self, entity) -> None:
        if entity in self.entities:
            self.entities.remove(entity)

    # --- spatial queries (mirror World's real implementations) ---

    def get_entities_at(self, coordinates) -> list:
        from game.entities.settlement.settlement import Settlement
        result = []
        for e in list(self.entities):
            if isinstance(e, Settlement):
                if e.occupies(coordinates):
                    result.append(e)
            elif e.coordinates == coordinates:
                result.append(e)
        return result

    def get_entities_nearby(
        self,
        coordinates,
        radius: float,
        *types: str,
        exclude=None,
        alive_only: bool = True,
    ) -> list:
        result = []
        cx, cy = coordinates
        for e in list(self.entities):
            if exclude is not None and e is exclude:
                continue
            if alive_only and not e.is_alive:
                continue
            ex, ey = e.coordinates
            if ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5 <= radius:
                if not types or e.__class__.__name__ in types:
                    result.append(e)
        return result


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_world():
    """All-field MockWorld (day=1, hour=7)."""
    return MockWorld('field')


@pytest.fixture
def forest_world():
    """All-forest MockWorld."""
    return MockWorld('forest')


@pytest.fixture
def water_world():
    """All-water MockWorld."""
    return MockWorld('water')


@pytest.fixture
def mountain_world():
    """All-mountain MockWorld."""
    return MockWorld('mountain')


# ---------------------------------------------------------------------------
# Entity helper factories  (not pytest fixtures – call them directly)
# ---------------------------------------------------------------------------

def make_spirit(world, spirit_type=None, coords=(10, 10)):
    from game.entities.spirit import Spirit, SpiritType
    if spirit_type is None:
        spirit_type = SpiritType.FOREST
    spirit = Spirit(world, spirit_type, coords)
    world.add_entity(spirit)
    return spirit


def make_blessing(world, coords=(10, 10), count=1):
    from game.entities.blessing import Blessing
    b = Blessing(world, coords, count)
    world.add_entity(b)
    return b


def make_bandit(world, coords=(10, 10)):
    from game.entities.bandit import Bandit
    b = Bandit(world, coords)
    world.add_entity(b)
    return b


def make_dragon(world, properties=None, coords=(25, 25)):
    """Create a dragon.  properties defaults to a minimal non-anthropophage verdant dragon."""
    from game.entities import Dragon
    if properties is None:
        properties = ['verdant', 'neutral', 'carnivore', 'blade']
    dragon = Dragon(world, 'Testicus', properties, coords)
    world.add_entity(dragon)
    return dragon


def make_hero(world, home=None, coords=(10, 10)):
    from game.entities.hero import Hero
    hero = Hero(world, coords, home=home, city_born=True)
    world.add_entity(hero)
    return hero


def make_village(world, coords=(25, 25)):
    from game.entities.settlement.village import Village
    v = Village(world, 'Testburg', coords)
    world.add_entity(v)
    return v


def make_camp(world, parent, spirit_coords=(10, 10), coords=(10, 12)):
    from game.entities.settlement.camp import Camp
    from game.entities.spirit import SpiritType
    spirit = make_spirit(world, SpiritType.FOREST, spirit_coords)
    c = Camp(world, 'TestCamp', coords, spirit, parent)
    world.add_entity(c)
    return c
