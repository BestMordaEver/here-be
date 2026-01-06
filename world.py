import random
import time
from typing import List


class PerlinNoise:

    def __init__(self, seed=0):
        self.permutation = list(range(256))
        random.seed(seed)
        random.shuffle(self.permutation)
        self.p = self.permutation + self.permutation

    def fade(self, t):
        return t * t * t * (t * (t * 6 - 15) + 10)

    def lerp(self, t, a, b):
        return a + t * (b - a)

    def grad(self, hash_val, x, y):
        h = hash_val & 15
        u = x if h < 8 else y
        v = y if h < 8 else x
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise(self, x, y):
        xi = int(x) & 255
        yi = int(y) & 255

        xf = x - int(x)
        yf = y - int(y)

        u = self.fade(xf)
        v = self.fade(yf)

        aa = self.p[self.p[xi] + yi]
        ab = self.p[self.p[xi] + yi + 1]
        ba = self.p[self.p[xi + 1] + yi]
        bb = self.p[self.p[xi + 1] + yi + 1]

        x1 = self.lerp(u, self.grad(aa, xf, yf), self.grad(ba, xf - 1, yf))
        x2 = self.lerp(u, self.grad(ab, xf, yf - 1), self.grad(bb, xf - 1, yf - 1))

        return self.lerp(v, x1, x2)


class World:

    WIDTH = 200
    HEIGHT = 200
    
    THRESHOLDS = {
        'water': 0.23,
        'field': 0.68,
        'forest': 0.80,
    }

    def __init__(self, seed=None):
        if seed is None:
            seed = random.randint(0, 1000000)
        self.seed = seed
        self.height_map = self.generate_height_map()
        
        # Entity management
        self.entities: List = []
        self.update_interval = 10  # seconds
        self.last_update_time = time.time()
        self.update_count = 0

    def generate_height_map(self):
        perlin = PerlinNoise(self.seed)
        height_map = []
        scale = 0.09

        for y in range(self.HEIGHT):
            height_map.append([])
            for x in range(self.WIDTH):
                noise = 0
                amplitude = 1
                frequency = 1
                max_value = 0

                for _ in range(4):
                    noise += perlin.noise(x * scale * frequency, y * scale * frequency) * amplitude
                    max_value += amplitude
                    amplitude *= 0.5
                    frequency *= 2

                height_map[y].append((noise / max_value + 1) / 2)

        iterations = 5
        for _ in range(iterations):
            smoothed = []
            for y in range(self.HEIGHT):
                smoothed.append([])
                for x in range(self.WIDTH):
                    total = 0
                    count = 0

                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            ny = y + dy
                            nx = x + dx

                            if 0 <= ny < self.HEIGHT and 0 <= nx < self.WIDTH:
                                total += height_map[ny][nx]
                                count += 1

                    smoothed[y].append(total / count)

            height_map = smoothed

        min_val = float('inf')
        max_val = float('-inf')

        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                val = height_map[y][x]
                if val < min_val:
                    min_val = val
                if val > max_val:
                    max_val = val

        range_val = max_val - min_val

        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                height_map[y][x] = (height_map[y][x] - min_val) / range_val

        return height_map

    @staticmethod
    def get_biome_from_height(height):
        if height < World.THRESHOLDS['water']:
            return 'water'
        if height < World.THRESHOLDS['field']:
            return 'field'
        if height < World.THRESHOLDS['forest']:
            return 'forest'
        return 'mountain'

    def get_statistics(self):
        stats = {
            'water': 0,
            'field': 0,
            'forest': 0,
            'mountain': 0,
            'min_height': float('inf'),
            'max_height': float('-inf'),
        }

        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                height = self.height_map[y][x]
                stats['min_height'] = min(stats['min_height'], height)
                stats['max_height'] = max(stats['max_height'], height)

                biome = self.get_biome_from_height(height)
                stats[biome] += 1

        total = self.WIDTH * self.HEIGHT
        for biome in ['water', 'field', 'forest', 'mountain']:
            stats[f'{biome}_pct'] = (stats[biome] / total) * 100

        return stats

    def add_entity(self, entity) -> None:
        """Add an entity to the world."""
        self.entities.append(entity)
    
    def remove_entity(self, entity) -> None:
        """Remove an entity from the world."""
        if entity in self.entities:
            self.entities.remove(entity)
    
    def get_entities_at(self, coordinates):
        """Get all entities at a specific coordinate."""
        return [e for e in self.entities if e.coordinates == coordinates]
    
    def should_update(self) -> bool:
        """Check if enough time has passed for an update."""
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            return True
        return False
    
    def update(self) -> None:
        """Update all entities and advance game state."""
        if not self.should_update():
            return
        
        self.last_update_time = time.time()
        self.update_count += 1
        
        # Update all entities
        for entity in self.entities:
            entity.update(self)
    
    def get_next_update_time(self) -> float:
        """Get seconds until next update."""
        current_time = time.time()
        time_since_last = current_time - self.last_update_time
        return max(0, self.update_interval - time_since_last)
