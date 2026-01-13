import { initTerrainCanvases, renderTerrain, renderTerrainChars } from './terrain.js';
import { initEntityCanvas, renderEntities, updateEntities, entityMap, domainBackgrounds, scorchedOverlays } from './entities.js';
import { initUI } from './ui.js';

// Main animation loop
function animate(timestamp) {
    renderTerrainChars(timestamp, heightMap, entityMap, scorchedOverlays);
    renderEntities(timestamp);
    requestAnimationFrame(animate);
}

// Re-render terrain backgrounds when entities update (for domain backgrounds)
async function updateAndRender() {
    await updateEntities();
    renderTerrain(heightMap, domainBackgrounds);
}

// Initialize and start
const terrainCanvas = initTerrainCanvases();
initEntityCanvas();
initUI(terrainCanvas, heightMap);
renderTerrain(heightMap);
updateEntities();
requestAnimationFrame(animate);
setInterval(updateAndRender, 1000);
