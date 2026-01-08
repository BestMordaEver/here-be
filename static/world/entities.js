import { WIDTH, HEIGHT, CELL_WIDTH, CELL_HEIGHT, displayOptions } from './config.js';

// Canvas reference
let entityCanvas, entityCtx;

// Store entity data
export let entityMap = new Map();

// Animation tracking
let pulsePhase = 0;
let lastPulseTime = 0;

// Initialize entity canvas
export function initEntityCanvas() {
    entityCanvas = document.getElementById('entityCanvas');
    
    const canvasWidth = WIDTH * CELL_WIDTH;
    const canvasHeight = HEIGHT * CELL_HEIGHT;
    
    entityCanvas.width = canvasWidth;
    entityCanvas.height = canvasHeight;
    entityCtx = entityCanvas.getContext('2d');
    entityCtx.font = 'bold 14px "Roboto", monospace';
    
    return entityCanvas;
}

// Update pulse animation phase
function updatePulsePhase(timestamp) {
    const elapsed = timestamp - lastPulseTime;
    if (elapsed > 16) {
        pulsePhase = (timestamp / 2000) % 1;
        lastPulseTime = timestamp;
    }
}

// Calculate pulse effect
function getPulseEffect() {
    const t = Math.sin(pulsePhase * Math.PI * 2) * 0.5 + 0.5;
    const opacity = 0.95 + (1 - 0.95) * (1 - t);
    const scale = 1 + 0.015 * t;
    return { opacity, scale };
}

// Render entities
export function renderEntities(timestamp) {
    updatePulsePhase(timestamp);
    entityCtx.clearRect(0, 0, entityCanvas.width, entityCanvas.height);
    
    const pulse = getPulseEffect();
    
    entityMap.forEach((entity, key) => {
        const [x, y] = entity.coordinates;
        const px = x * CELL_WIDTH;
        const py = y * CELL_HEIGHT;
        
        if (!displayOptions.showEntities) return;
        
        entityCtx.save();
        
        // Apply rotation if entity has rotation property
        if (entity.rotation !== undefined) {
            const radians = (entity.rotation * Math.PI) / 180;
            entityCtx.translate(px + CELL_WIDTH / 2, py + CELL_HEIGHT / 2);
            entityCtx.rotate(radians);
            entityCtx.translate(-CELL_WIDTH / 2, -CELL_HEIGHT / 2);
        }
        
        if (displayOptions.entityAnimation) {
            entityCtx.globalAlpha = pulse.opacity;
            if (entity.rotation === undefined) {
                // Only apply pulse transform if not already transformed by rotation
                entityCtx.translate(px + CELL_WIDTH / 2, py + CELL_HEIGHT / 2);
            }
            entityCtx.scale(pulse.scale, pulse.scale);
            if (entity.rotation === undefined) {
                entityCtx.translate(-CELL_WIDTH / 2, -CELL_HEIGHT / 2);
            }
        }
        
        if (displayOptions.entityGlow) {
            entityCtx.shadowColor = 'rgba(255, 255, 255, 0.4)';
            entityCtx.shadowBlur = 2;
        }
        entityCtx.fillStyle = entity.color;
        entityCtx.fillText(entity.character, displayOptions.entityAnimation ? 0 : px + CELL_WIDTH * 0.5, displayOptions.entityAnimation ? CELL_HEIGHT : py + CELL_HEIGHT);
        
        if (displayOptions.entityGlow) {
            entityCtx.shadowColor = entity.color;
            entityCtx.shadowBlur = 1;
            entityCtx.fillText(entity.character, displayOptions.entityAnimation ? 0 : px + CELL_WIDTH * 0.5, displayOptions.entityAnimation ? CELL_HEIGHT : py + CELL_HEIGHT);
        }
        
        entityCtx.restore();
    });
}

// Fetch and update entities
export async function updateEntities() {
    const startTime = performance.now();
    try {
        const response = await fetch('/api/world');
        const data = await response.json();
        
        entityMap.clear();
        
        if (data.entities) {
            data.entities.forEach(entity => {
                if (entity.tiles && Array.isArray(entity.tiles)) {
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
