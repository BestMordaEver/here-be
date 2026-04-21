from flask import Blueprint, jsonify, current_app
import time


api_bp = Blueprint("api", __name__)


@api_bp.get("/api/render_world")
def get_world():
    """Get serialized world state for rendering."""
    world = current_app.world
    
    # Force update check
    world.update()
    
    # Serialize all entities
    serialized_entities = []
    for entity in list(world.entities):
        if not hasattr(entity, "get_visual"):
            continue

        data = entity.get_visual()
        if isinstance(data, list):
            data = {"tiles": data}
        serialized_entities.append(data)

    # Get current game time
    game_time = world.time.current_time
    
    return jsonify({
        "entities": serialized_entities,
        "game_day": game_time.day,
        "game_hour": game_time.hour,
        "timestamp": time.time(),
    })
