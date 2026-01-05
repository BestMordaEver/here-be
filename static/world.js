// Define world dimensions
const WIDTH = 200;
const HEIGHT = 200;

// Tile definitions
const TILES = {
    water: { chars: ['~', '≈'], css: 'water' },
    field: { chars: [".", ','], css: 'field' },
    forest: { chars: ['р', 'Р', 'ф', 'Ф'], css: 'forest' },
    mountain: { chars: ['^', 'А'], css: 'mountain' }
};

// Get biome type based on height
function getBiomeFromHeight(height) {
    if (height < 0.2) return 'water';
    if (height < 0.68) return 'field';
    if (height < 0.80) return 'forest';
    return 'mountain';
}

// Perlin noise implementation
class PerlinNoise {
    constructor(seed = 0) {
        this.permutation = [];
        this.p = [];
        this.initPermutation(seed);
    }
    
    initPermutation(seed) {
        for (let i = 0; i < 256; i++) {
            this.permutation[i] = i;
        }
        
        // Shuffle with seed
        const random = this.seededRandom(seed);
        for (let i = 255; i > 0; i--) {
            const j = Math.floor(random() * (i + 1));
            [this.permutation[i], this.permutation[j]] = [this.permutation[j], this.permutation[i]];
        }
        
        // Duplicate permutation for wrapped access
        this.p = [...this.permutation, ...this.permutation];
    }
    
    seededRandom(seed) {
        return () => {
            seed = (seed * 9301 + 49297) % 233280;
            return seed / 233280;
        };
    }
    
    fade(t) {
        return t * t * t * (t * (t * 6 - 15) + 10);
    }
    
    lerp(t, a, b) {
        return a + t * (b - a);
    }
    
    grad(hash, x, y) {
        const h = hash & 15;
        const u = h < 8 ? x : y;
        const v = h < 8 ? y : x;
        return ((h & 1) === 0 ? u : -u) + ((h & 2) === 0 ? v : -v);
    }
    
    noise(x, y) {
        const xi = Math.floor(x) & 255;
        const yi = Math.floor(y) & 255;
        
        const xf = x - Math.floor(x);
        const yf = y - Math.floor(y);
        
        const u = this.fade(xf);
        const v = this.fade(yf);
        
        const aa = this.p[this.p[xi] + yi];
        const ab = this.p[this.p[xi] + yi + 1];
        const ba = this.p[this.p[xi + 1] + yi];
        const bb = this.p[this.p[xi + 1] + yi + 1];
        
        const x1 = this.lerp(u, this.grad(aa, xf, yf), this.grad(ba, xf - 1, yf));
        const x2 = this.lerp(u, this.grad(ab, xf, yf - 1), this.grad(bb, xf - 1, yf - 1));
        
        return this.lerp(v, x1, x2);
    }
}

// Generate height map with Perlin noise
function generateHeightMap() {
    const perlin = new PerlinNoise(Math.random() * 1000);
    const heightMap = [];
    const scale = 0.1; // Controls feature size
    
    for (let y = 0; y < HEIGHT; y++) {
        heightMap[y] = [];
        for (let x = 0; x < WIDTH; x++) {
            // Multi-octave Perlin noise for more varied terrain
            let noise = 0;
            let amplitude = 1;
            let frequency = 1;
            let maxValue = 0;
            
            // 4 octaves of Perlin noise
            for (let i = 0; i < 4; i++) {
                noise += perlin.noise(x * scale * frequency, y * scale * frequency) * amplitude;
                maxValue += amplitude;
                amplitude *= 0.5;
                frequency *= 2;
            }
            
            // Normalize to roughly 0-1 range
            heightMap[y][x] = (noise / maxValue + 1) / 2;
        }
    }
    
    // ===== SMOOTHING =====
    let smoothed = [];
    const iterations = 5;
    
    for (let iter = 0; iter < iterations; iter++) {
        for (let y = 0; y < HEIGHT; y++) {
            smoothed[y] = [];
            for (let x = 0; x < WIDTH; x++) {
                let sum = 0;
                let count = 0;
                
                // Sample this tile and neighbors
                for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                        const ny = y + dy;
                        const nx = x + dx;
                        
                        if (ny >= 0 && ny < HEIGHT && nx >= 0 && nx < WIDTH) {
                            sum += heightMap[ny][nx];
                            count++;
                        }
                    }
                }
                
                smoothed[y][x] = sum / count;
            }
        }
    }
    
    // ===== NORMALIZATION =====
    let min = Infinity;
    let max = -Infinity;
    
    // Find min and max
    for (let y = 0; y < HEIGHT; y++) {
        for (let x = 0; x < WIDTH; x++) {
            const val = smoothed[y][x];
            if (val < min) min = val;
            if (val > max) max = val;
        }
    }
    
    const range = max - min;
    
    // Normalize to 0-1
    for (let y = 0; y < HEIGHT; y++) {
        for (let x = 0; x < WIDTH; x++) {
            smoothed[y][x] = (smoothed[y][x] - min) / range;
        }
    }
	
    return smoothed;
}

// Generate world based on height map
function generateWorld() {
    const heightMap = generateHeightMap();
    const world = [];
    
    // Log heightmap statistics for debugging
    let min = Infinity, max = -Infinity;
    let waterCount = 0, fieldCount = 0, forestCount = 0, mountainCount = 0;
    
    for (let y = 0; y < HEIGHT; y++) {
        for (let x = 0; x < WIDTH; x++) {
            const height = heightMap[y][x];
            if (height < min) min = height;
            if (height > max) max = height;
            
            const biome = getBiomeFromHeight(height);
            if (biome === 'water') waterCount++;
            else if (biome === 'field') fieldCount++;
            else if (biome === 'forest') forestCount++;
            else mountainCount++;
        }
    }
    
    console.log('=== Height Map Statistics ===');
    console.log(`Min height: ${min}`);
    console.log(`Max height: ${max}`);
    console.log(`Total tiles: ${WIDTH * HEIGHT}`);
    console.log(`Water: ${waterCount} (${(waterCount / (WIDTH * HEIGHT) * 100).toFixed(2)}%)`);
    console.log(`Fields: ${fieldCount} (${(fieldCount / (WIDTH * HEIGHT) * 100).toFixed(2)}%)`);
    console.log(`Forests: ${forestCount} (${(forestCount / (WIDTH * HEIGHT) * 100).toFixed(2)}%)`);
    console.log(`Mountains: ${mountainCount} (${(mountainCount / (WIDTH * HEIGHT) * 100).toFixed(2)}%)`);
    
    for (let y = 0; y < HEIGHT; y++) {
        let row = '';
        for (let x = 0; x < WIDTH; x++) {
            const height = heightMap[y][x];
            const biome = getBiomeFromHeight(height);
            const tile = TILES[biome];
            const char = tile.chars[Math.floor(Math.random() * tile.chars.length)];
            
            row += `<span class="${tile.css}">${char}</span>`;
        }
        world.push(row);
    }
    
    return world.join('\n');
}

// Render world
document.getElementById('worldMap').innerHTML = generateWorld();
