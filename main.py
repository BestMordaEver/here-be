from flask import Flask, request
from endpoints import api_bp, endpoints_bp
from world import World
from collections import defaultdict
#import firebase_admin
#from firebase_admin import credentials

#cred = credentials.Certificate("path/to/serviceAccountKey.json")
#firebase_admin.initialize_app(cred)


app = Flask(__name__)

world = World()
app.world = world  # Make world accessible to blueprints
world.start_update_thread()

# Dictionary to store endpoint access statistics
endpoint_stats = defaultdict(int)
app.endpoint_stats = endpoint_stats

# Middleware to log endpoint access
@app.before_request
def log_endpoint_access():
    # Exclude static files
    if not request.path.startswith('/static/'):
        endpoint_stats[request.path] += 1


app.register_blueprint(api_bp)
app.register_blueprint(endpoints_bp)