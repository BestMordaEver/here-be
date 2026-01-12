from typing import List
import random

class HeightMapGenerator:

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
    
    def generate_height_map(self, width=200, height=200) -> List[List[float]]:
        height_map = []
        scale = 0.09

        for y in range(height):
            height_map.append([])
            for x in range(width):
                noise = 0
                amplitude = 1
                frequency = 1
                max_value = 0

                for _ in range(4):
                    noise += self.noise(x * scale * frequency, y * scale * frequency) * amplitude
                    max_value += amplitude
                    amplitude *= 0.5
                    frequency *= 2

                height_map[y].append((noise / max_value + 1) / 2)

        iterations = 5
        for _ in range(iterations):
            smoothed = []
            for y in range(height):
                smoothed.append([])
                for x in range(width):
                    total = 0
                    count = 0

                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            ny = y + dy
                            nx = x + dx

                            if 0 <= ny < height and 0 <= nx < width:
                                total += height_map[ny][nx]
                                count += 1

                    smoothed[y].append(total / count)

            height_map = smoothed

        min_val = float('inf')
        max_val = float('-inf')

        for y in range(height):
            for x in range(width):
                val = height_map[y][x]
                if val < min_val:
                    min_val = val
                if val > max_val:
                    max_val = val

        range_val = max_val - min_val

        for y in range(height):
            for x in range(width):
                height_map[y][x] = (height_map[y][x] - min_val) / range_val

        return height_map