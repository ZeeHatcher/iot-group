import boto3
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g
import json

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

# Routes for HIMS node
@app.route("/hims/weights")
def get_weights():
    return []

@app.route("/hims/<nuid>/threshold", methods=["POST"])
def update_item_threshold(nuid):
    return {}

if __name__ == "__main__":
    # Load .env file for development
    load_dotenv()

    app.run(host="0.0.0.0", port=5000, debug=True)
