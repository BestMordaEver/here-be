import json
from flask import Blueprint, current_app, render_template


endpoints_bp = Blueprint("endpoints", __name__)


@endpoints_bp.get("/")
def index():
    return render_template("index.html")


@endpoints_bp.get("/dragons")
def dragons():
    return render_template("dragons.html")


@endpoints_bp.get("/world")
def world_route():
    height_map = current_app.world.height_map
    return render_template("world.html", height_map=json.dumps(height_map))


@endpoints_bp.get("/endpoints")
def endpoints():
    # Convert defaultdict to regular dict and sort by access count
    sorted_stats = sorted(current_app.endpoint_stats.items(), key=lambda x: x[1], reverse=True)
    return render_template("endpoints.html", endpoint_stats=sorted_stats)


@endpoints_bp.get("/notes")
def notes():
    notes_data = [
        "The morning sun was particularly bright today.",
        "I wonder what secrets the old library holds.",
        "The dragon eggs have arrived safely.",
        "Must investigate the eastern tower.",
        "Something feels different in the air.",
    ]
    return render_template("notes.html", notes=notes_data)


@endpoints_bp.get("/names")
def names():
    names_data = [
        "Smaug",
        "Drogon",
        "Viserion",
        "Rhaegal",
        "Caraxes",
        "Meleys",
        "Sunfyre",
        "Syrax",
    ]
    return render_template("names.html", names=names_data)


@endpoints_bp.get("/thoughts/<name>")
def thoughts(name):
    thoughts_db = {
        "smaug": [
            "Gold gleams in the firelight.",
            "Thieves dare not enter my mountain.",
            "The taste of fear is exquisite.",
            "Even centuries pass like moments.",
        ],
        "drogon": [
            "Fire consumes everything in its path.",
            "Mother will return soon.",
            "The chains cannot hold me forever.",
            "Freedom tastes like ash and victory.",
        ],
        "caraxes": [
            "Blood runs through ancient veins.",
            "The rider calls, and I answer.",
            "Fire and rebellion stir in my heart.",
            "Loyalty to those who earn it.",
        ],
    }
    
    thoughts_data = thoughts_db.get(name.lower(), [f"No recorded thoughts for {name}"])
    return render_template("thoughts.html", name=name, thoughts=thoughts_data)
