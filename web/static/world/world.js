import { initTerrainCanvases, renderTerrain, renderTerrainChars } from './terrain.js';
import { initEntityCanvas, renderEntities, updateEntities, entityMap } from './entities.js';
import { initUI } from './ui.js';

// Main animation loop
function animate(timestamp) {
    renderTerrainChars(timestamp, heightMap, entityMap);
    renderEntities(timestamp);
    requestAnimationFrame(animate);
}

// Initialize and start
const terrainCanvas = initTerrainCanvases();
initEntityCanvas();
initUI(terrainCanvas, heightMap);
renderTerrain(heightMap);
updateEntities();
requestAnimationFrame(animate);
setInterval(updateEntities, 1000);
