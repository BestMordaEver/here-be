from flask import Flask, render_template, request, redirect
from endpoints import api_bp
from world import World
from entities.settlement import Settlement
from entities.caravan import Caravan
from entities.dragon import Dragon
from collections import defaultdict
import json
from datetime import datetime
#import firebase_admin
#from firebase_admin import credentials

#cred = credentials.Certificate("path/to/serviceAccountKey.json")
#firebase_admin.initialize_app(cred)


app = Flask(__name__)

world = World()
app.world = world  # Make world accessible to blueprints


def initialize_test_entities():
    """Create test entities for debugging entity movement."""
    # Create settlements in fields
    settlements = [
        Settlement("Millbrook", "#c0c0c0", "Ö", (50, 50), 100),
        Settlement("Greenvale", "#c0c0c0", "Ö", (80, 60), 100),
        Settlement("Riverside", "#c0c0c0", "Ö", (40, 90), 100),
        Settlement("Crossroads", "#c0c0c0", "Ö", (120, 70), 100),
    ]
    
    for settlement in settlements:
        world.add_entity(settlement)
    
    # Create caravans that move between settlements
    caravans = [
        Caravan((48, 50), "trade", settlements[0], settlements[1]),  # Millbrook <-> Greenvale
        Caravan((82, 62), "trade", settlements[1], settlements[2]),  # Greenvale <-> Riverside
        Caravan((42, 88), "trade", settlements[2], settlements[3]),  # Riverside <-> Crossroads
    ]
    
    # Set initial movement states
    for caravan in caravans:
        caravan.state = "moving"
    
    for caravan in caravans:
        world.add_entity(caravan)
    
    # Create dragons in mountains that chase caravans
    dragons = [
        Dragon("Emberfang", ["brute", "mountain"], (150, 40)),
        Dragon("Stormwing", ["blade", "mountain"], (160, 120)),
        Dragon("Ashbreather", ["serpent", "mountain"], (180, 80)),
    ]
    
    # Assign dragons to chase caravans in round trips
    dragons[0].target = caravans[0]
    dragons[1].target = caravans[1]
    dragons[2].target = caravans[2]
    
    for dragon in dragons:
        dragon.state = "moving"
    
    for dragon in dragons:
        world.add_entity(dragon)


# Initialize test entities
initialize_test_entities()

# Dictionary to store endpoint access statistics
endpoint_stats = defaultdict(int)

# Middleware to log endpoint access
@app.before_request
def log_endpoint_access():
    # Exclude static files
    if not request.path.startswith('/static/'):
        endpoint_stats[request.path] += 1


app.register_blueprint(api_bp)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/dragons")
def dragons():
    return render_template("dragons.html")


@app.get("/world")
def world_route():
    height_map = world.height_map
    return render_template("world.html", height_map=json.dumps(height_map))


@app.get("/endpoints")
def endpoints():
    # Convert defaultdict to regular dict and sort by access count
    sorted_stats = sorted(endpoint_stats.items(), key=lambda x: x[1], reverse=True)
    return render_template("endpoints.html", endpoint_stats=sorted_stats)


@app.get("/notes")
def notes():
    notes_data = [
        "The morning sun was particularly bright today.",
        "I wonder what secrets the old library holds.",
        "The dragon eggs have arrived safely.",
        "Must investigate the eastern tower.",
        "Something feels different in the air.",
    ]
    return render_template("notes.html", notes=notes_data)


@app.get("/names")
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


@app.get("/thoughts/<name>")
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
