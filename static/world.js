// Define world dimensions
const WIDTH = 200;
const HEIGHT = 200;

// Biome to CSS class mapping
const BIOME_CSS = {
    water: 'water',
    field: 'field',
    forest: 'forest',
    mountain: 'mountain'
};

// Store the rendered world as a 2D grid for entity overlay
let worldGrid = [];

// Get biome type based on height
function getBiomeFromHeight(height) {
    if (height < 0.23) return 'water';
    if (height < 0.68) return 'field';
    if (height < 0.80) return 'forest';
    return 'mountain';
}

// Check if a tile is adjacent to a specific biome
function isAdjacentTo(biome, heightMap, x, y) {
    for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue; // Skip self
            
            const ny = y + dy;
            const nx = x + dx;
            
            if (ny >= 0 && ny < HEIGHT && nx >= 0 && nx < WIDTH) {
                const neighborHeight = heightMap[ny][nx];
                const neighborBiome = getBiomeFromHeight(neighborHeight);
                if (neighborBiome === biome) {
                    return true;
                }
            }
        }
    }
    return false;
}

// Get contextual tile character based on biome and local height
function getContextualTile(biome, height, heightMap, x, y) {
    let char;
    
    if (biome === 'water') {
        // Deep water (height < 0.1) uses ≈, shallow water (0.1-0.2) uses ~
        if (height < 0.1) {
            char = '≈';
        } else {
            char = '~';
        }
    } else if (biome === 'mountain') {
        // Peaks use ^, slopes use А
        if (height > 0.89) {
            char = '^';
        } else {
            char = 'А';
        }
    } else if (biome === 'forest') {
        // Dense forest (lower heights) use р/Р, sparse forest (higher) use ф/Ф
        if (height < 0.72) {
            char = Math.random() < 0.5 ? 'р' : 'Р';
        } else {
            char = Math.random() < 0.5 ? 'ф' : 'Ф';
        }
    } else if (biome === 'field') {
        // Tall grass near forests and lakes
        if (isAdjacentTo('forest', heightMap, x, y)) {
            char = ';';
        } else {
            // Height gradient for regular fields
            if (height < 0.4) {
                char = '.';
            } else {
                char = ',';
            }
        }
    }
    
    return { char, cssClass: null };
}

// Generate world based on height map
function generateWorld(heightMapInput) {
    const heightMap = heightMapInput;
    const world = [];
    const HEIGHT = heightMap.length;
    const WIDTH = heightMap[0].length;
    
    // Initialize grid
    worldGrid = [];
    
    for (let y = 0; y < HEIGHT; y++) {
        worldGrid[y] = [];
        let row = '';
        for (let x = 0; x < WIDTH; x++) {
            const height = heightMap[y][x];
            const biome = getBiomeFromHeight(height);
            const tileData = getContextualTile(biome, height, heightMap, x, y);
            const cssClass = tileData.cssClass || BIOME_CSS[biome];
            const span = `<span class="terrain ${cssClass}" id="tile-${x}-${y}"><span class="char">${tileData.char}</span><span class="entity"></span></span>`;
            row += span + ' ';
            
            // Store reference to this tile
            worldGrid[y][x] = {
                x: x,
                y: y,
                biome: biome,
                height: height,
                element: null
            };
        }
        world.push(row);
    }
    
    return world.join('\n');
}

// Fetch and render entities on the world map
async function updateEntities() {
    try {
        const response = await fetch('/api/world');
        const data = await response.json();
        
        // Clear all entities first
        document.querySelectorAll('.entity').forEach(el => {
            el.textContent = '';
            el.style.color = '';
        });
        
        // Render each entity
        if (data.entities) {
            data.entities.forEach(entity => {
                const [x, y] = entity.coordinates;
                
                // Check bounds
                if (x >= 0 && x < WIDTH && y >= 0 && y < HEIGHT) {
                    const tile = document.getElementById(`tile-${x}-${y}`);
                    if (tile) {
                        const entitySpan = tile.querySelector('.entity');
                        entitySpan.textContent = entity.character;
                        entitySpan.style.color = entity.color;
                        
                        // Add title with entity info
                        let title = `${entity.type}: ${entity.life}/${entity.life}`;
                        if (entity.name) title = `${entity.name}: ${entity.life}`;
                        if (entity.state) title += ` [${entity.state}]`;
                        tile.title = title;
                    }
                }
            });
        }
        
        // Update next update time display
        const nextUpdate = data.next_update_in || 10;
        updateCountdown(nextUpdate);
        
    } catch (error) {
        console.error('Failed to fetch world data:', error);
    }
}

// Update countdown timer
function updateCountdown(secondsUntilUpdate) {
    const display = document.getElementById('update-countdown');
    if (display) {
        let remaining = secondsUntilUpdate;
        display.textContent = `Next update in: ${remaining.toFixed(1)}s`;
        
        // Update countdown every 100ms
        const interval = setInterval(() => {
            remaining -= 0.1;
            if (remaining <= 0) {
                clearInterval(interval);
                remaining = 10;
            }
            display.textContent = `Next update in: ${remaining.toFixed(1)}s`;
        }, 100);
        
        // Clear old interval after 10 seconds
        setTimeout(() => clearInterval(interval), 10000);
    }
}

// Initial render
document.getElementById('worldMap').innerHTML = generateWorld(heightMap);

// Auto-update entities every 10 seconds
updateEntities();
setInterval(updateEntities, 10000);
