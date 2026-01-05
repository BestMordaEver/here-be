from flask import Flask, render_template, request
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
