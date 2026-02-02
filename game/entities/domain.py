"""Domain - a dragon's treasury and territory marker."""
from .base import Coordinates, Entity, Mortal
from typing import TYPE_CHECKING, Dict, Any, List, Tuple

if TYPE_CHECKING:
    from game.world import World
    from . import Dragon


# Domain constants
SCORCH_RADIUS = 10  # Radius of scorched earth effect
PILLAGE_TREASURE_AMOUNT = 50  # Treasure gained from pillaging


class Domain(Entity, Mortal):
    """A dragon's domain - their territory marker and treasury."""
    
    def __init__(self, coordinates: Coordinates, dragon: 'Dragon', is_scorched: bool = False):
        # Domain color matches dragon color
        super().__init__(dragon.color, "ʘ", coordinates)
        self.dragon = dragon
        self.is_scorched = is_scorched
        self.treasure = 0  # Accumulated treasure
        self.background_color = None  # Background color for scorched domains
        self.is_treasury = False  # Becomes true when dragon dies
        
        if is_scorched:
            # Scorched domains have a dark background
            self.background_color = "#1a0808"  # Dark red
    
    def get_tiles(self) -> List[Tuple[Coordinates, str, str]]:
        """Return tile for the domain."""
        if self.is_dead:
            # Dead domain shows as treasury that can be pillaged
            return [(self.coordinates, "¤", "#FFD700")]  # Gold treasury symbol
        
        tile = (self.coordinates, "ʘ", self.color)
        return [tile]
    
    def get_background_tiles(self) -> List[Tuple[Coordinates, str]]:
        """Return background tiles for scorched earth effect.
        Returns list of (coordinates, background_color) tuples.
        Only scorched domains affect terrain background.
        """
        if not self.is_scorched or self.is_dead:
            return []
        
        tiles = []
        cx, cy = self.coordinates
        
        # Create circle of scorched earth
        for dy in range(-SCORCH_RADIUS, SCORCH_RADIUS + 1):
            for dx in range(-SCORCH_RADIUS, SCORCH_RADIUS + 1):
                # Check if within circle (Euclidean distance)
                if dx * dx + dy * dy < SCORCH_RADIUS * SCORCH_RADIUS:
                    x, y = cx + dx, cy + dy
                    tiles.append(((x, y), self.background_color))
        
        return tiles
    
    def get_scorched_terrain_overlay(self, world: 'World') -> Dict[Coordinates, Tuple[str, str]]:
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
                    if x < 0 or y < 0 or x >= len(world.height_map[0]) or y >= len(world.height_map):
                        continue
                    
                    # Get biome and apply scorching effect
                    height = world.height_map[y][x]
                    biome = world.get_biome_from_height(height)
                    
                    if biome == 'water':
                        overlays[(x, y)] = ('ʬ', '#8B7355')  # Cracked bed, brown
                    elif biome == 'field':
                        overlays[(x, y)] = ('…', '#2F2F2F')  # Ash, dark gray
                    elif biome == 'forest':
                        overlays[(x, y)] = ('F', "#2E2E2E")  # Burnt, very dark
                    elif biome == 'mountain':
                        overlays[(x, y)] = ('Λ', '#505050')  # Darker mountain
        
        return overlays
    
    def occupies(self, coordinates: Coordinates) -> bool:
        """Check if domain occupies the given coordinates."""
        return self.coordinates == coordinates
    
    def can_be_pillaged(self, world: 'World') -> bool:
        """Check if domain can be pillaged (dragon dead or far away)."""
        if not self.dragon.is_alive:
            return True
        
        # Check if dragon is far enough away (>15 tiles)
        distance = self.dragon.get_distance(self.coordinates)
        return distance > 15
    
    def pillage(self, world: 'World') -> int:
        """Pillage the domain, removing scorched earth and returning treasure.
        Returns amount of treasure gained.
        """
        treasure_gained = self.treasure + PILLAGE_TREASURE_AMOUNT
        self.die(world, "pillaged")
        return treasure_gained
    
    def update(self, world: 'World') -> None:
        """Update domain state."""
        if self.is_dead:
            return
        
        # If dragon is dead, domain becomes a pillage-able treasury
        if not self.dragon.is_alive:
            self.is_treasury = True
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize domain to dictionary for JSON output."""
        data = super().serialize()
        data["dragon"] = self.dragon.name if self.dragon else "none"
        data["is_scorched"] = self.is_scorched
        data["treasure"] = self.treasure
        
        # Add background tiles for rendering
        data["background_tiles"] = self.get_background_tiles()
        
        # Add scorched terrain overlay for rendering (need world reference)
        # Will be populated by world serialization
        data["scorched_terrain_overlay"] = {}
        
        data["debug_info"] = f"Domain at {self.coordinates} for {self.dragon.name if self.dragon else 'none'}, treasure: {self.treasure}"
        return data
