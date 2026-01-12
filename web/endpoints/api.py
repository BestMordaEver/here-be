from flask import Blueprint, jsonify, current_app
import time


api_bp = Blueprint("api", __name__)


@api_bp.get("/api/data")
def get_sample_data():
    return jsonify(
        {
            "data": [
                {"id": 1, "name": "Sample Item 1", "value": 100},
                {"id": 2, "name": "Sample Item 2", "value": 200},
                {"id": 3, "name": "Sample Item 3", "value": 300},
            ],
            "total": 3,
            "timestamp": "2024-01-01T00:00:00Z",
        }
    )


@api_bp.get("/api/items/<int:item_id>")
def get_item(item_id: int):
    return jsonify(
        {
            "item": {
                "id": item_id,
                "name": f"Sample Item {item_id}",
                "value": item_id * 100,
            },
            "timestamp": "2024-01-01T00:00:00Z",
        }
    )


@api_bp.get("/api/world")
def get_world():
    """Get current world state including all entities."""
    world = current_app.world
    
    # Force update check
    world.update()
    
    return jsonify({
        "entities": [entity.serialize() for entity in world.entities],
        "update_count": world.update_count,
        "timestamp": time.time(),
        "next_update_in": world.get_next_update_time(),
    })
