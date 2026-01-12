import { WIDTH, HEIGHT, CELL_WIDTH, CELL_HEIGHT, displayOptions } from './config.js';
import { renderTerrain } from './terrain.js';
import { entityMap } from './entities.js';

let terrainCanvas;

// Initialize UI and event handlers
export function initUI(canvas, heightMap) {
    terrainCanvas = canvas;
    setupTooltips();
    setupDisplayToggles(heightMap);
}

// Setup tooltip handlers
function setupTooltips() {
    terrainCanvas.addEventListener('mousemove', handleMouseMove);
    terrainCanvas.addEventListener('mouseleave', hideTooltip);
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
    const text = entity.debug_info;
    
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
function setupDisplayToggles(heightMap) {
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
        if (!e.target.checked) {
            renderTerrain(heightMap);
        }
    });
}
