from flask import Flask, render_template
from endpoints import api_bp
#import firebase_admin
#from firebase_admin import credentials

#cred = credentials.Certificate("path/to/serviceAccountKey.json")
#firebase_admin.initialize_app(cred)


app = Flask(__name__)


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
