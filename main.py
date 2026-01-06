from flask import Flask, render_template, request, redirect
from endpoints import api_bp
from collections import defaultdict
import json
from datetime import datetime
#import firebase_admin
#from firebase_admin import credentials

#cred = credentials.Certificate("path/to/serviceAccountKey.json")
#firebase_admin.initialize_app(cred)


app = Flask(__name__)


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
def world():
    return render_template("world.html")


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
