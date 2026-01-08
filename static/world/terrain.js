import { WIDTH, HEIGHT, CELL_WIDTH, CELL_HEIGHT, BIOME_COLORS, displayOptions } from './config.js';

// Canvas references
let terrainCanvas, terrainCtx;
let backgroundCanvas, backgroundCtx;
let terrainFrame0, terrainFrame0Ctx;
let terrainFrame1, terrainFrame1Ctx;

// Store static terrain data for animation
let terrainData = [];
let terrainAnimPhase = 0;

// Get biome type based on height
export function getBiomeFromHeight(height) {
    if (height < 0.23) return 'water';
    if (height < 0.68) return 'field';
    if (height < 0.80) return 'forest';
    return 'mountain';
}

// Check if a tile is adjacent to a specific biome
function isAdjacentTo(biome, heightMap, x, y) {
    for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            
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

// Get animated character based on animation phase
function getAnimatedChar(char, animPhase) {
    const shouldFlip = animPhase < 0.5;
    
    // Water characters flip horizontally
    if (char === '~' || char === '≈') {
        return { char, flip: shouldFlip, italic: false };
    }
    
    // Grass and tree characters toggle italic (preserve the actual character)
    if (char === ',' || char === ';' || char === 'р' || char === 'Р' || char === 'ф' || char === 'Ф') {
        return { char, flip: false, italic: shouldFlip };
    }
    
    // Other characters don't animate
    return { char, flip: false, italic: false };
}

// Initialize terrain canvases
export function initTerrainCanvases() {
    backgroundCanvas = document.getElementById('backgroundCanvas');
    terrainCanvas = document.getElementById('terrainCanvas');
    
    const canvasWidth = WIDTH * CELL_WIDTH;
    const canvasHeight = HEIGHT * CELL_HEIGHT;
    
    backgroundCanvas.width = canvasWidth;
    backgroundCanvas.height = canvasHeight;
    backgroundCtx = backgroundCanvas.getContext('2d');
    
    terrainCanvas.width = canvasWidth;
    terrainCanvas.height = canvasHeight;
    terrainCtx = terrainCanvas.getContext('2d');
    
    // Create offscreen canvases for prerendered animation frames
    terrainFrame0 = document.createElement('canvas');
    terrainFrame0.width = canvasWidth;
    terrainFrame0.height = canvasHeight;
    terrainFrame0Ctx = terrainFrame0.getContext('2d');
    
    terrainFrame1 = document.createElement('canvas');
    terrainFrame1.width = canvasWidth;
    terrainFrame1.height = canvasHeight;
    terrainFrame1Ctx = terrainFrame1.getContext('2d');
    
    // Set font
    terrainCtx.font = '12px "Roboto", monospace';
    terrainFrame0Ctx.font = '12px "Roboto", monospace';
    terrainFrame1Ctx.font = '12px "Roboto", monospace';
    
    return terrainCanvas;
}

// Prerender both animation frames
function prerenderTerrainFrames() {
    terrainFrame0Ctx.clearRect(0, 0, terrainFrame0.width, terrainFrame0.height);
    terrainFrame1Ctx.clearRect(0, 0, terrainFrame1.width, terrainFrame1.height);
    
    terrainData.forEach(tile => {
        const { x, y, char, biome } = tile;
        const px = x * CELL_WIDTH;
        const py = y * CELL_HEIGHT;
        const colors = BIOME_COLORS[biome];
        
        const frame0Anim = getAnimatedChar(char, 0);
        const frame1Anim = getAnimatedChar(char, 0.5);
        
        // Render frame 0
        terrainFrame0Ctx.fillStyle = colors.fg;
        if (frame0Anim.italic) {
            terrainFrame0Ctx.font = 'italic 12px "Roboto", monospace';
        } else {
            terrainFrame0Ctx.font = '12px "Roboto", monospace';
        }
        if (frame0Anim.flip) {
            terrainFrame0Ctx.save();
            terrainFrame0Ctx.translate(px + CELL_WIDTH, py);
            terrainFrame0Ctx.scale(-1, 1);
            terrainFrame0Ctx.fillText(frame0Anim.char, CELL_WIDTH * 0.25, CELL_HEIGHT * 0.75);
            terrainFrame0Ctx.restore();
        } else {
            terrainFrame0Ctx.fillText(frame0Anim.char, px + CELL_WIDTH * 0.25, py + CELL_HEIGHT * 0.75);
        }
        
        // Render frame 1
        terrainFrame1Ctx.fillStyle = colors.fg;
        if (frame1Anim.italic) {
            terrainFrame1Ctx.font = 'italic 12px "Roboto", monospace';
        } else {
            terrainFrame1Ctx.font = '12px "Roboto", monospace';
        }
        if (frame1Anim.flip) {
            terrainFrame1Ctx.save();
            terrainFrame1Ctx.translate(px + CELL_WIDTH, py);
            terrainFrame1Ctx.scale(-1, 1);
            terrainFrame1Ctx.fillText(frame1Anim.char, CELL_WIDTH * 0.25, CELL_HEIGHT * 0.75);
            terrainFrame1Ctx.restore();
        } else {
            terrainFrame1Ctx.fillText(frame1Anim.char, px + CELL_WIDTH * 0.25, py + CELL_HEIGHT * 0.75);
        }
    });
    
    console.log('Prerendered both terrain animation frames');
}

// Render static terrain
export function renderTerrain(heightMap) {
    const startTime = performance.now();
    
    if (terrainData.length === 0) {
        for (let y = 0; y < HEIGHT; y++) {
            for (let x = 0; x < WIDTH; x++) {
                const height = heightMap[y][x];
                const biome = getBiomeFromHeight(height);
                const char = getContextualTile(biome, height, heightMap, x, y);
                terrainData.push({ x, y, char, biome, height });
            }
        }
        prerenderTerrainFrames();
    }
    
    // Render backgrounds on background canvas
    backgroundCtx.clearRect(0, 0, backgroundCanvas.width, backgroundCanvas.height);
    
    if (displayOptions.terrainBg) {
        for (let y = 0; y < HEIGHT; y++) {
            for (let x = 0; x < WIDTH; x++) {
                const height = heightMap[y][x];
                const biome = getBiomeFromHeight(height);
                const colors = BIOME_COLORS[biome];
                
                const px = x * CELL_WIDTH;
                const py = y * CELL_HEIGHT;
                
                backgroundCtx.fillStyle = colors.bg;
                backgroundCtx.fillRect(px, py, CELL_WIDTH, CELL_HEIGHT);
            }
        }
    }
    
    const endTime = performance.now();
    console.log(`Terrain rendered in ${(endTime - startTime).toFixed(2)}ms`);
}

// Render animated terrain characters
export function renderTerrainChars(timestamp, heightMap, entityMap) {
    terrainAnimPhase = (timestamp / 1500) % 1;
    
    // Clear terrain canvas
    terrainCtx.clearRect(0, 0, terrainCanvas.width, terrainCanvas.height);
    
    // Draw terrain characters if enabled
    if (displayOptions.terrainChars) {
        const sourceFrame = terrainAnimPhase < 0.5 && displayOptions.entityAnimation ? terrainFrame0 : terrainFrame1;
        terrainCtx.drawImage(sourceFrame, 0, 0);
        
        // Clear terrain characters where entities are
        if (displayOptions.showEntities) {
            entityMap.forEach((entity, key) => {
                const [x, y] = entity.coordinates;
                const px = x * CELL_WIDTH;
                const py = y * CELL_HEIGHT;
                
                // Clear a slightly larger area to ensure complete coverage
                terrainCtx.clearRect(px - 1, py - 1, CELL_WIDTH + 2, CELL_HEIGHT + 2);
            });
        }
    }
}
