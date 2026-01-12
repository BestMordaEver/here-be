from flask import Flask, request
from web.endpoints import api_bp, endpoints_bp
from game.entities.dragon import Dragon
from game.world import World
from collections import defaultdict
#import firebase_admin
#from firebase_admin import credentials

#cred = credentials.Certificate("path/to/serviceAccountKey.json")
#firebase_admin.initialize_app(cred)


app = Flask(__name__, template_folder='web/templates', static_folder='web/static')

world = World()
app.world = world  # Make world accessible to blueprints

dragon1 = Dragon("Jielle", ["serpent", "aquatic"], (180, 180))
dragon2 = Dragon("Thrax", ["brute", "mountain"], (20, 200))
dragon3 = Dragon("Sylph", ["blade", "verdant"], (10, 30))
dragon4 = Dragon("Ember", ["druid", "flame"], (10, 50))
dragon5 = Dragon("Aurelia", ["midas", "mountain"], (25, 25))

dragon1.state = "arrived"
dragon2.state = "arrived"
dragon3.state = "arrived"
dragon4.state = "arrived"
dragon5.state = "arrived"

world.add_entity(dragon1)
world.add_entity(dragon2)
world.add_entity(dragon3)
world.add_entity(dragon4)
world.add_entity(dragon5)

world.start_update_thread()

# Dictionary to store endpoint access statistics
endpoint_stats = defaultdict(int)
app.endpoint_stats = endpoint_stats

# Middleware to log endpoint access
@app.before_request
def log_endpoint_access():
    # Exclude static files
    if not (request.path.startswith('/static/') or request.path.startswith('/api/')):
        endpoint_stats[request.path] += 1


app.register_blueprint(api_bp)
app.register_blueprint(endpoints_bp)