from flask import Flask, request
from endpoints import api_bp, endpoints_bp
from entities.dragon import Dragon
from world import World
from entities import Camp, Village, City
from collections import defaultdict
#import firebase_admin
#from firebase_admin import credentials

#cred = credentials.Certificate("path/to/serviceAccountKey.json")
#firebase_admin.initialize_app(cred)


app = Flask(__name__)

world = World()
app.world = world  # Make world accessible to blueprints

# Add some example settlements to demonstrate the new system
worker_camp = Camp("Mining Camp", (20, 20))
village = Village("Riverside", (30, 30))
city = City("Capital", (50, 50))

# Add a depleted village to show the depleted state
depleted_village = Village("Abandoned Hamlet", (70, 70))
depleted_village.life = 0
depleted_village.die(world, "hunger")

world.add_entity(worker_camp)
world.add_entity(village)
world.add_entity(city)
world.add_entity(depleted_village)

dragon1 = Dragon("Jielle", ["serpent", "aquatic"], (180, 180))
dragon2 = Dragon("Thrax", ["brute", "mountain"], (20, 200))
dragon3 = Dragon("Sylph", ["blade", "verdant"], (10, 30))
dragon4 = Dragon("Ember", ["druid", "flame"], (10, 50))
dragon5 = Dragon("Aurelia", ["midas", "mountain"], (25, 25))

dragon1.target = worker_camp
dragon2.target = worker_camp
dragon3.target = village
dragon4.target = village
dragon5.target = city

dragon1.state = "moving"
dragon2.state = "moving"
dragon3.state = "moving"
dragon4.state = "moving"
dragon5.state = "moving"

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
    if not request.path.startswith('/static/'):
        endpoint_stats[request.path] += 1


app.register_blueprint(api_bp)
app.register_blueprint(endpoints_bp)