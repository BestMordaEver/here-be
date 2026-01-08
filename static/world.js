// Define world dimensions
const WIDTH = 200;
const HEIGHT = 200;

// Character cell size in pixels
const CELL_WIDTH = 9;
const CELL_HEIGHT = 14;

// Biome color mapping
const BIOME_COLORS = {
    water: { fg: '#4da6ff', bg: '#161664' },
    field: { fg: '#6fcc50', bg: '#0d2d0d' },
    forest: { fg: '#1a5f1a', bg: '#0a1a0a' },
    mountain: { fg: '#ffffff', bg: '#2a2a2a' }
};

// Canvas references
let terrainCanvas, terrainCtx;
let entityCanvas, entityCtx;

// Store entity data for hover detection
let entityMap = new Map(); // key: "x,y", value: entity data

// Animation frame tracking
let pulsePhase = 0;
let lastPulseTime = 0;

// Display options
const displayOptions = {
    terrainChars: true,
    terrainBg: true,
    entityGlow: true,
    entityAnimation: true,
    showEntities: true
};

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
    if (biome === 'water') {
        return height < 0.1 ? '≈' : '~';
    } else if (biome === 'mountain') {
        return height > 0.89 ? '^' : 'А';
    } else if (biome === 'forest') {
        if (height < 0.72) {
            return Math.random() < 0.5 ? 'р' : 'Р';
        } else {
            return Math.random() < 0.5 ? 'ф' : 'Ф';
        }
    } else if (biome === 'field') {
        if (isAdjacentTo('forest', heightMap, x, y)) {
            return ';';
        } else {
            return height < 0.4 ? '.' : ',';
        }
    }
    return ' ';
}

// Initialize canvases
function initializeCanvases() {
    terrainCanvas = document.getElementById('terrainCanvas');
    entityCanvas = document.getElementById('entityCanvas');
    
    const canvasWidth = WIDTH * CELL_WIDTH;
    const canvasHeight = HEIGHT * CELL_HEIGHT;
    
    // Set canvas dimensions
    terrainCanvas.width = canvasWidth;
    terrainCanvas.height = canvasHeight;
    entityCanvas.width = canvasWidth;
    entityCanvas.height = canvasHeight;
    
    terrainCtx = terrainCanvas.getContext('2d');
    entityCtx = entityCanvas.getContext('2d');
    
    // Set font for both canvases
    terrainCtx.font = '12px "Roboto", monospace';
    entityCtx.font = 'bold 14px "Roboto", monospace';
    
    // Add mouse move handler for tooltips
    terrainCanvas.addEventListener('mousemove', handleMouseMove);
    terrainCanvas.addEventListener('mouseleave', hideTooltip);
}

// Render static terrain (only called once)
function renderTerrain(heightMap) {
    const startTime = performance.now();
    
    for (let y = 0; y < HEIGHT; y++) {
        for (let x = 0; x < WIDTH; x++) {
            const height = heightMap[y][x];
            const biome = getBiomeFromHeight(height);
            const char = getContextualTile(biome, height, heightMap, x, y);
            const colors = BIOME_COLORS[biome];
            
            const px = x * CELL_WIDTH;
            const py = y * CELL_HEIGHT;
            
            // Draw background
            if (displayOptions.terrainBg) {
                terrainCtx.fillStyle = colors.bg;
                terrainCtx.fillRect(px, py, CELL_WIDTH, CELL_HEIGHT);
            } else {
                terrainCtx.clearRect(px, py, CELL_WIDTH, CELL_HEIGHT);
            }
            
            // Draw character
            if (displayOptions.terrainChars) {
                terrainCtx.fillStyle = colors.fg;
                terrainCtx.fillText(char, px + 1, py + 11);
            }
        }
    }
    
    const endTime = performance.now();
    console.log(`Terrain rendered in ${(endTime - startTime).toFixed(2)}ms`);
}

// Update pulse animation phase
function updatePulsePhase(timestamp) {
    const elapsed = timestamp - lastPulseTime;
    if (elapsed > 16) { // ~60fps
        pulsePhase = (timestamp / 2000) % 1; // 2 second cycle
        lastPulseTime = timestamp;
    }
}

// Calculate pulse scale and opacity
function getPulseEffect() {
    // Sine wave from 0 to 1 and back
    const t = Math.sin(pulsePhase * Math.PI * 2) * 0.5 + 0.5;
    const opacity = 0.95 + (1 - 0.95) * (1 - t);
    const scale = 1 + 0.015 * t;
    return { opacity, scale };
}

// Render entities on entity canvas
function renderEntities(timestamp) {
    updatePulsePhase(timestamp);
    
    // Clear entity canvas
    entityCtx.clearRect(0, 0, entityCanvas.width, entityCanvas.height);
    
    const pulse = getPulseEffect();
    
    entityMap.forEach((entity, key) => {
        const [x, y] = entity.coordinates;
        const px = x * CELL_WIDTH;
        const py = y * CELL_HEIGHT;
        
        // Skip entity rendering if disabled - don't clear terrain
        if (!displayOptions.showEntities) return;
        
        // Clear the terrain character at this position (keeping background)
        terrainCtx.clearRect(px, py, CELL_WIDTH, CELL_HEIGHT);
        // Restore just the background color
        const height = heightMap[y][x];
        const biome = getBiomeFromHeight(height);
        const colors = BIOME_COLORS[biome];
        if (displayOptions.terrainBg) {
            terrainCtx.fillStyle = colors.bg;
            terrainCtx.fillRect(px, py, CELL_WIDTH, CELL_HEIGHT);
        }
        
        entityCtx.save();
        
        // Apply pulse transformation only if animation is enabled
        if (displayOptions.entityAnimation) {
            entityCtx.globalAlpha = pulse.opacity;
            entityCtx.translate(px + CELL_WIDTH / 2, py + CELL_HEIGHT / 2);
            entityCtx.scale(pulse.scale, pulse.scale);
            entityCtx.translate(-CELL_WIDTH / 2, -CELL_HEIGHT / 2);
        }
        
        // Draw entity with optional glow effect
        if (displayOptions.entityGlow) {
            entityCtx.shadowColor = 'rgba(255, 255, 255, 0.4)';
            entityCtx.shadowBlur = 2;
        }
        entityCtx.fillStyle = entity.color;
        entityCtx.fillText(entity.character, displayOptions.entityAnimation ? 0 : px + 1, displayOptions.entityAnimation ? 11 : py + 11);
        
        // Draw again for color glow
        if (displayOptions.entityGlow) {
            entityCtx.shadowColor = entity.color;
            entityCtx.shadowBlur = 1;
            entityCtx.fillText(entity.character, displayOptions.entityAnimation ? 0 : px + 1, displayOptions.entityAnimation ? 11 : py + 11);
        }
        
        entityCtx.restore();
    });
    
    // Continue animation
    requestAnimationFrame(renderEntities);
}

// Fetch and update entities
async function updateEntities() {
    const startTime = performance.now();
    try {
        const response = await fetch('/api/world');
        const data = await response.json();
        
        // Clear and rebuild entity map
        entityMap.clear();
        
        if (data.entities) {
            data.entities.forEach(entity => {
                // Check if entity has tiles (multi-tile entity like settlements)
                if (entity.tiles && Array.isArray(entity.tiles)) {
                    // Add each tile of the settlement
                    entity.tiles.forEach(tile => {
                        const [coords, symbol, color] = tile;
                        const [x, y] = coords;
                        if (x >= 0 && x < WIDTH && y >= 0 && y < HEIGHT) {
                            entityMap.set(`${x},${y}`, {
                                ...entity,
                                coordinates: coords,
                                character: symbol,
                                color: color
                            });
                        }
                    });
                } else {
                    // Regular single-tile entity
                    const [x, y] = entity.coordinates;
                    if (x >= 0 && x < WIDTH && y >= 0 && y < HEIGHT) {
                        entityMap.set(`${x},${y}`, entity);
                    }
                }
            });
        }
        
        const endTime = performance.now();
        console.log(`updateEntities completed in ${(endTime - startTime).toFixed(2)}ms (${entityMap.size} tiles)`);
        
    } catch (error) {
        console.error('Failed to fetch world data:', error);
    }
}

// Handle mouse movement for tooltips
function handleMouseMove(event) {
    const rect = terrainCanvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    
    const tileX = Math.floor(mouseX / CELL_WIDTH);
    const tileY = Math.floor(mouseY / CELL_HEIGHT);
    
    if (tileX >= 0 && tileX < WIDTH && tileY >= 0 && tileY < HEIGHT) {
        const key = `${tileX},${tileY}`;
        const entity = entityMap.get(key);
        
        if (entity) {
            showTooltip(event.clientX, event.clientY, entity);
        } else {
            hideTooltip();
        }
    } else {
        hideTooltip();
    }
}

// Show tooltip
function showTooltip(x, y, entity) {
    const tooltip = document.getElementById('tooltip');
    text = entity.debug_info
    
    
    tooltip.textContent = text;
    tooltip.style.display = 'block';
    tooltip.style.left = (x + 15) + 'px';
    tooltip.style.top = (y + 15) + 'px';
}

// Hide tooltip
function hideTooltip() {
    const tooltip = document.getElementById('tooltip');
    tooltip.style.display = 'none';
}

// Setup display option toggles
function setupDisplayToggles() {
    // Toggle menu visibility
    const menuToggle = document.getElementById('menuToggle');
    const menuContent = document.getElementById('menuContent');
    menuToggle.addEventListener('click', () => {
        const isHidden = menuContent.style.display === 'none';
        menuContent.style.display = isHidden ? 'block' : 'none';
        menuToggle.textContent = isHidden ? '▲' : '▼';
    });
    
    document.getElementById('toggleTerrainChars').addEventListener('change', (e) => {
        displayOptions.terrainChars = e.target.checked;
        renderTerrain(heightMap);
    });
    
    document.getElementById('toggleTerrainBg').addEventListener('change', (e) => {
        displayOptions.terrainBg = e.target.checked;
        renderTerrain(heightMap);
    });
    
    document.getElementById('toggleEntityGlow').addEventListener('change', (e) => {
        displayOptions.entityGlow = e.target.checked;
    });
    
    document.getElementById('toggleEntityAnimation').addEventListener('change', (e) => {
        displayOptions.entityAnimation = e.target.checked;
    });
    
    document.getElementById('toggleEntities').addEventListener('change', (e) => {
        displayOptions.showEntities = e.target.checked;
        // Re-render terrain to restore characters under entities when hiding them
        if (!e.target.checked) {
            renderTerrain(heightMap);
        }
    });
}

// Initialize and start
initializeCanvases();
setupDisplayToggles();
renderTerrain(heightMap);
updateEntities();
requestAnimationFrame(renderEntities);
setInterval(updateEntities, 1000);