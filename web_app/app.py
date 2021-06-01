import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g
import json

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

# Routes for HIMS node
@app.route("/hims/items")
def get_items():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("items")

    items = {}

    rows = table.scan()["Items"]
    for r in rows:
        items[r["id"]] = {
            "name": r["name"],
            "threshold": r["threshold"],
        }

    return jsonify(items)

@app.route("/hims/weights")
def get_weights():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("weights")

    weights = {}

    rows = table.scan()["Items"]
    for r in rows:
        if r["id"] not in weights:
            weights[r["id"]] = []

        weights[r["id"]].append({
            "weight": r["data"]["weight"],
            "timestamp": r["timestamp"]
        })

    return jsonify(weights)

@app.route("/hims/items/<nuid>", methods=["POST", "GET"])
def update_item(nuid):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("items")

    field = request.form["field"]
    value = request.form.get("value")

    try:
        print(field, value)
        # response = table.update_item(
            # Key={
                # "id": nuid
            # },
            # UpdateExpression="SET #f = :v",
            # ConditionExpression=Attr("id").eq(nuid),
            # ExpressionAttributeNames={
                # "#f": field
            # },
            # ExpressionAttributeValues={
                # ":v": value
            # },
            # ReturnValues="UPDATED_NEW"
        # )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return jsonify({ "msg": "Invalid Id" })

    return jsonify({ "msg": "Success" })

if __name__ == "__main__":
    # Load .env file for development
    load_dotenv()

    app.run(host="0.0.0.0", port=5000, debug=True)
