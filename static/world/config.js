// World dimensions
export const WIDTH = 200;
export const HEIGHT = 200;

// Character cell size in pixels
export const CELL_WIDTH = 12;
export const CELL_HEIGHT = 12;

// Biome color mapping
export const BIOME_COLORS = {
    water: { fg: '#4da6ff', bg: '#161664' },
    field: { fg: '#6fcc50', bg: '#0d2d0d' },
    forest: { fg: '#1a5f1a', bg: '#0a1a0a' },
    mountain: { fg: '#ffffff', bg: '#2a2a2a' }
};

// Display options
export const displayOptions = {
    terrainChars: true,
    terrainBg: true,
    entityGlow: true,
    entityAnimation: true,
    showEntities: true
};
