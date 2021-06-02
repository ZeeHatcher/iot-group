from awscrt import auth, io, mqtt, http
from awsiot import mqtt_connection_builder
import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g, redirect, abort
import json
import os
from uuid import uuid4

app = Flask(__name__)

@app.route("/")
def index():
    return redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/inventory")
def inventory():
    return render_template("inventory.html")

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

@app.route("/hims/items/<nuid>", methods=["POST"])
def update_item(nuid):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("items")

    field = request.form["field"]
    value = request.form.get("value")

    if field == "threshold":
        value = int(value)

    try:
        response = table.update_item(
            Key={
                "id": nuid
            },
            UpdateExpression="SET #f = :v",
            ConditionExpression=Attr("id").eq(nuid),
            ExpressionAttributeNames={
                "#f": field
            },
            ExpressionAttributeValues={
                ":v": value
            },
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return jsonify({ "status": 400, "message": "Invalid ID." })

    res = { "status": 200, "message": "Successfully updated item." }

    return jsonify(res)

@app.route("/hims/<nuid>/threshold/update", methods=["POST"])
def notify_threshold_update(nuid):
    value = int(request.form.get("value"))

    topic = "hims/{}/threshold/update".format(nuid)
    print(type(value))
    payload = { "threshold": value }

    print("Publishing...")
    print("\tTopic:", topic)
    print("\tPayload:", payload)
    publish_future, packet_id = mqtt_connection.publish(
        topic=topic,
        payload=json.dumps(payload),
        qos=mqtt.QoS.AT_LEAST_ONCE)
    publish_future.result()
    print("Published.")

    res = { "status": 200, "message": "Successfully published notification." }

    return jsonify(res)

@app.route("/hims/weights")
def get_weights():
    dynamodb = boto3.resource("dynamodb")
    table_items = dynamodb.Table("items")
    table_weights = dynamodb.Table("weights")

    items = {}

    rows = table_items.scan()["Items"]
    for r in rows:
        items[r["id"]] = {
            "name": r["name"],
            "threshold": r["threshold"],
            "log": [],
            "weight": None,
            "is_depleted": None
        }

    rows = table_weights.scan()["Items"]
    for r in rows:
        if r["id"] not in items:
            continue

        items[r["id"]]["log"].append({
            "weight": r["data"]["weight"],
            "timestamp": r["timestamp"]
        })

        items[r["id"]]["weight"] = r["data"]["weight"]
        items[r["id"]]["is_depleted"] = r["data"]["is_depleted"]

    return jsonify(items)

#Security
@app.route("/facial")
def facial():
    return render_template("facial.html")

@app.route("/add_face/<input_name>", methods=['POST'])
def add_face(input_name):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("securitylog")

    field = request.form["field"]
    value = request.form.get("value")
#     global training,name
#     training = True
#     name = input_name
# #     templateData = {
# #         "isTraining" : training,
# #     }
#     if(training):
#         return "1"
#     else:
#         return "0"
    
    

if __name__ == "__main__":
    # Load .env file for development
    load_dotenv()

    CLIENT_ID = os.environ.get("CLIENT_ID") or str(uuid4())
    THING_ENDPOINT = os.environ.get("THING_ENDPOINT")
    CERT_DIR = "./.certs/"
    CA_FILEPATH = CERT_DIR + os.environ.get("CA_FILE")
    CERT_FILEPATH = CERT_DIR + os.environ.get("CERT_FILE")
    PRIVATE_KEY_FILEPATH = CERT_DIR + os.environ.get("PRIVATE_KEY_FILE")

    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    # Initiate MQTT connection
    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=THING_ENDPOINT,
        cert_filepath=CERT_FILEPATH,
        pri_key_filepath=PRIVATE_KEY_FILEPATH,
        client_bootstrap=client_bootstrap,
        ca_filepath=CA_FILEPATH,
        client_id=CLIENT_ID,
        clean_session=False,
        keep_alive_secs=6)

    print("Connecting to %s with client ID %s..." % (THING_ENDPOINT, CLIENT_ID), end=" ")
    connect_future = mqtt_connection.connect()
    connect_future.result()
    print("Connected.")

    app.run(host="0.0.0.0", port=5000, debug=True)
