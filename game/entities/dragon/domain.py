"""Domain - a dragon's treasury and territory marker."""
from typing import TYPE_CHECKING, Dict, Any, List, Optional, Tuple

from game.entities.base import Coordinates, Entity, Visible, Pockets
from game.world import Biome
from .types import DomainType

if TYPE_CHECKING:
    from game.world import World
    from . import Dragon


# Domain constants
SCORCH_RADIUS = 10  # Radius of scorched earth effect


class Domain(Entity, Visible, Pockets):
    """A dragon's domain - their territory marker and treasury."""

    # Valid spawn terrain by domain type
    VALID_SPAWN_TERRAIN = {
        DomainType.AQUATIC: [Biome.WATER],
        DomainType.MOUNTAIN: [Biome.MOUNTAIN],
        DomainType.VERDANT: [Biome.FIELD, Biome.FOREST],
        DomainType.SCORCHED: [Biome.FIELD, Biome.WATER, Biome.MOUNTAIN, Biome.FOREST],  # Scorched can spawn anywhere
    }
    
    @staticmethod
    def validate_spawn_location(world: 'World', coordinates: Coordinates, domain_type: DomainType) -> bool:
        """
        Validate that spawn coordinates match the domain type terrain.
        
        Args:
            world: The game world
            coordinates: Proposed spawn location
            domain_type: One of 'aquatic', 'mountain', 'verdant', 'scorched'
            
        Returns:
            True if location is valid for the domain type
        """
        x, y = coordinates
        if x < 0 or y < 0 or x >= world.WIDTH or y >= world.HEIGHT:
            return False
        
        height = world.height_map[y][x]
        biome = world.get_biome_from_height(height)
        
        valid_biomes = Domain.VALID_SPAWN_TERRAIN.get(domain_type, [])
        return biome in valid_biomes
    
    @staticmethod
    def find_valid_spawn_location(world: 'World', domain_type: DomainType, min_lair_distance: int = 30) -> Optional[Coordinates]:
        """
        Find a random valid spawn location for a dragon.
        
        Args:
            world: The game world
            domain_type: One of DomainType.AQUATIC, DomainType.MOUNTAIN, DomainType.VERDANT, DomainType.SCORCHED
            min_lair_distance: Minimum distance from other dragon lairs
            
        Returns:
            Valid coordinates, or None if no suitable location found
        """
        from random import sample
        
        valid_biomes = Domain.VALID_SPAWN_TERRAIN.get(domain_type, [])
        
        # Get all valid coordinates
        candidates = []
        for y in range(world.HEIGHT):
            for x in range(world.WIDTH):
                height = world.height_map[y][x]
                biome = world.get_biome_from_height(height)
                if biome in valid_biomes:
                    candidates.append((x, y))
        
        if not candidates:
            return None
        
        # Get existing lair locations
        lair_coords = []
        for entity in list(world.entities):
            if entity.__class__.__name__ == 'Domain' and entity.is_alive:
                lair_coords.append(entity.coordinates)
        
        # Try random candidates until we find one far enough from lairs
        for coords in sample(candidates, min(100, len(candidates))):
            far_enough = True
            for lair in lair_coords:
                dx = abs(coords[0] - lair[0])
                dy = abs(coords[1] - lair[1])
                if max(dx, dy) < min_lair_distance:
                    far_enough = False
                    break
            if far_enough:
                return coords
        
        # No location found far enough from lairs
        return None
    
    def __init__(self, world: 'World', coordinates: Coordinates, dragon: 'Dragon', is_scorched: bool = False):
        # Domain color matches dragon color
        super().__init__(world, coordinates)
        Visible.__init__(self)
        Pockets.__init__(self, max_blessings=-1)

        self.create_small("default", dragon.color, "ʘ")
        self.visual_state = "default"
        self.create_small("treasury", "#FFD700", "¤")  # Gold symbol for treasury state
        
        self.dragon = dragon
        self.is_scorched = is_scorched
        self.background_color = None  # Background color for scorched domains
        self.is_treasury = False  # Becomes true when dragon dies
        
        if is_scorched:
            # Scorched domains have a dark background
            self.background_color = "#1a0808"  # Dark red
    
    def occupies(self, coordinates: Coordinates) -> bool:
        """Check if domain occupies the given coordinates."""
        return self.coordinates == coordinates
    
    def can_be_pillaged(self) -> bool:
        """Check if domain can be pillaged (dragon dead or far away)."""
        if not self.dragon or not self.dragon.is_alive:
            return True
        
        # Check if dragon is far enough away (>15 tiles)
        distance = self.dragon.get_distance(self.coordinates)
        return distance > 15
    
    def pillage(self, amount: int = 3) -> int:
        """Pillage the domain, removing scorched earth and returning treasure.
        Returns amount of treasure gained.
        """
        taken = min(amount, self.blessings)
        if self.blessings == taken:
            self.die("pillaged")
        return taken
    
    def update(self) -> None:
        """Update domain state."""
        if self.is_dead:
            return
        
        # If dragon is dead, domain becomes a pillage-able treasury
        if self.dragon and not self.dragon.is_alive:
            self.is_treasury = True
            self.visual_state = "treasury"
            self.dragon = None
    
    def get_scorched_terrain_overlay(self) -> Dict[Coordinates, Tuple[str, str]]:
        """Get terrain overlays for scorched tiles.
        Returns dict mapping coordinates to (symbol, color) for terrain changes.
        Water→cracked bed (ʬ), grass→ash (…), forest→burnt (ɹ/ɺ), mountains lose snow.
        """
        if not self.is_scorched or self.is_dead:
            return {}
        
        overlays = {}
        cx, cy = self.coordinates
        
        for dy in range(-SCORCH_RADIUS, SCORCH_RADIUS + 1):
            for dx in range(-SCORCH_RADIUS, SCORCH_RADIUS + 1):
                # Check if within circle
                if dx * dx + dy * dy < SCORCH_RADIUS * SCORCH_RADIUS:
                    x, y = cx + dx, cy + dy
                    
                    # Check bounds
                    if x < 0 or y < 0 or x >= len(self.world.height_map[0]) or y >= len(self.world.height_map):
                        continue
                    
                    # Get biome and apply scorching effect
                    height = self.world.height_map[y][x]
                    biome = self.world.get_biome_from_height(height)
                    
                    if biome == Biome.WATER:
                        overlays[(x, y)] = ('ʬ', '#8B7355')  # Cracked bed, brown
                    elif biome == Biome.FIELD:
                        overlays[(x, y)] = ('…', '#2F2F2F')  # Ash, dark gray
                    elif biome == Biome.FOREST:
                        overlays[(x, y)] = ('F', "#2E2E2E")  # Burnt, very dark
                    elif biome == Biome.MOUNTAIN:
                        overlays[(x, y)] = ('Λ', '#505050')  # Darker mountain
        
        return overlays
    
    def get_visual(self):
        data = {"tiles": super().get_visual()}
        if self.is_scorched and not self.is_dead:
            # Add scorched earth background
            bg_tiles = []
            cx, cy = self.coordinates
            for dy in range(-SCORCH_RADIUS, SCORCH_RADIUS + 1):
                for dx in range(-SCORCH_RADIUS, SCORCH_RADIUS + 1):
                    if dx * dx + dy * dy < SCORCH_RADIUS * SCORCH_RADIUS:
                        x, y = cx + dx, cy + dy
                        bg_tiles.append(((x, y), self.background_color))
            data["background_tiles"] = bg_tiles
            data["scorched_terrain_overlay"] = {
                str(coords): [symbol, color]
                for coords, (symbol, color) in self.get_scorched_terrain_overlay().items()
            }

        return data

    def serialize(self) -> Dict[str, Any]:
        """Serialize domain for database storage."""
        return {
            "coordinates": self.coordinates,
            "dragon": self.dragon.name if self.dragon else None,
            "is_scorched": self.is_scorched,
            "blessings": self.blessings,
            "is_treasury": self.is_treasury,
            "is_alive": self.is_alive,
        }
