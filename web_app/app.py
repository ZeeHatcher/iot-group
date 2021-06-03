from awscrt import auth, io, mqtt, http
from awsiot import mqtt_connection_builder
import boto3
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g, redirect, abort
import json
import os
from uuid import uuid4
import time

app = Flask(__name__)
can_publish = False

preLight = 0

pins = {
    3: {'name' : 'PIN 3', 'state' : 0}
}

def publish_to_topic(topic, payload):
     print("Publishing...")
     print("\tTopic:", topic)
     print("\tPayload:", payload)
     publish_future, packet_id = mqtt_connection.publish(
        topic=topic,
        payload=json.dumps(payload),
        qos=mqtt.QoS.AT_LEAST_ONCE)
     publish_future.result()
     print("Published.")

@app.route("/")
def index():
    return redirect("/autoblinds")

@app.route("/inventory")
def inventory():
    return render_template("inventory.html")

@app.route("/light")
def light():
    global preLight
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("lightSensor")

    response = table.query(Limit=1,
                           ScanIndexForward=False,
                           KeyConditionExpression=Key('id').eq('light'))

    response2 = table.query(ScanIndexForward=True,
                           KeyConditionExpression=Key('id').eq('light'))
    
    items = {}
    graph_items = {}

    rows = response["Items"]
    rows_graph = response2["Items"]
    
    time = 0
    
    for r in rows_graph:
        if(r['timestamp']/1000 >= (time+300)):
            time = (r['timestamp']/1000)
            
            if(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m') in graph_items and
               ((graph_items.get(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m')).get('valueDist') == 1) or
               (graph_items.get(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m')).get('state') == 1))):
                continue
            
            else:
                if(r["distance"] <= 600 and r["distance"] >= 300):
                    r['distance'] = 1
                else:
                    r['distance'] = 0
                
                graph_items[datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m')] = {
                    'valueDist' : r["distance"],
                    'valueLight' : r["light"],
                    'state' : r['state']
                }
                
                print(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m'),r['state'])
            
        else:
            continue
    
    for r in rows:
        pins[3]['state'] = r['state']
        items = {
            "pins" : pins,
            'valueDist' : r["distance"],
            'valueLight' : r["light"],
            'preLight' : preLight,
            'row_graph' : graph_items
        }
        preLight = r["light"]

    return render_template("light.html", **items)

@app.route("/autoblinds")
def autoblinds():
    return render_template("autoblinds.html")

@app.route("/<changePin>/<toggle>") 
def toggle_function(changePin, toggle):
     global preLight
     changePin = int(changePin)
     
     deviceName = pins[changePin]['name']
     
     if toggle == "on":
         if changePin == 3:
             payload = { "state": 1 }
             pins[changePin]['state'] = 1
             
     if toggle == "off":
         if changePin == 3:
             payload = { "state": 0 }
             pins[changePin]['state'] = 0
     
     dynamodb = boto3.resource('dynamodb')
     table = dynamodb.Table("lightSensor")

     response = table.query(Limit=1,
                           ScanIndexForward=False,
                           KeyConditionExpression=Key('id').eq('light'))

     response2 = table.query(ScanIndexForward=True,
                           KeyConditionExpression=Key('id').eq('light'))
    
     items = {}
     graph_items = {}

     rows = response["Items"]
     rows_graph = response2["Items"]
    
     time = 0
    
     for r in rows_graph:
        if(r['timestamp']/1000 >= (time+300)):
            time = (r['timestamp']/1000)
            
            if(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m') in graph_items and
               ((graph_items.get(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m')).get('valueDist') == 1) or
               (graph_items.get(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m')).get('state') == 1))):
                continue
            
            else:
                if(r["distance"] <= 600 and r["distance"] >= 300):
                    r['distance'] = 1
                else:
                    r['distance'] = 0
                
                graph_items[datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m')] = {
                    'valueDist' : r["distance"],
                    'valueLight' : r["light"],
                    'state' : r['state']
                }
                
                print(datetime.fromtimestamp(int(r['timestamp'])/1000).strftime('%Y-%m-%d %H:%m'),r['state'])
            
        else:
            continue
        
     for r in rows:
        items = {
            "pins" : pins,
            'valueDist' : r["distance"],
            'valueLight' : r["light"],
            'preLight' : preLight,
            'row_graph' : graph_items
        }
        preLight = r["light"]
     
     topic = 'lightSensor'
     publish_to_topic(topic, payload)
     
     return render_template('light.html', **items)

# Autoblind back-end functionality
@app.route("/autoblinds/autoblinds")
def get_autoblinds():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("autoblinds")

    autoblinds = {}

    rows = table.scan()["Items"]
    for r in rows:
        autoblinds[r["id"]] = {
            "mode": r["mode"],
            "motor_max_pos": int(r["motor_max_pos"]),
            "motor_min_pos": int(r["motor_min_pos"]),
            "location": r["location"]
        }

    return jsonify(autoblinds)

@app.route("/autoblinds/data")
def get_autoblinds_data():
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("autoblind_data")

    autoblinds = {}

    rows = table.scan()["Items"]
    for r in rows:
        if r["id"] not in autoblinds:
            autoblinds[r["id"]] = []

        autoblinds[r["id"]].append({
            "timestamp": int(r["timestamp"]),
            "light_exterior": int(r["data"]["light_exterior"]),
            "light_interior": int(r["data"]["light_interior"]),
            "mode": r["data"]["mode"],
            "motor_pos": int(r["data"]["motor_pos"]),
        })

    return jsonify(autoblinds)

@app.route("/autoblinds/<blind_id>", methods=["POST"])
def update_autoblind(blind_id):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("autoblinds")
    
    topic = "autoblinds/{}/set".format(blind_id)
    payload = {
        "motor_max_pos": request.form.get("motor_max_pos"),
        "motor_min_pos": request.form.get("motor_min_pos"),
        "motor_pos": request.form.get("motor_pos")
    }

    publish_to_topic(topic, payload)

    try:
        response = table.update_item(
            Key={
                "id": blind_id
            },
            UpdateExpression="SET #mx = :mx, #mn = :mn",
            ConditionExpression=Attr("id").eq(blind_id),
            ExpressionAttributeNames={
                "#mx": "motor_max_pos",
                "#mn": "motor_min_pos",
            },
            ExpressionAttributeValues={
                ":mx": request.form.get("motor_max_pos"),
                ":mn": request.form.get("motor_min_pos"),
            },
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return jsonify({ "status": 400, "message": "Invalid ID." })

    res = { "status": 200, "message": "Successfully updated autoblind." }

    return jsonify(res)

@app.route("/autoblinds/<blind_id>/mode", methods=["POST"])
def update_autoblind_mode(blind_id):
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("autoblinds")
    
    topic = "autoblinds/{}/set".format(blind_id)
    payload = {
        "mode": request.form.get("mode")
    }

    publish_to_topic(topic, payload)

    try:
        response = table.update_item(
            Key={
                "id": blind_id
            },
            UpdateExpression="SET #m = :m",
            ConditionExpression=Attr("id").eq(blind_id),
            ExpressionAttributeNames={
                "#m": "mode",
            },
            ExpressionAttributeValues={
                ":m": request.form.get("mode"),
            },
            ReturnValues="UPDATED_NEW"
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return jsonify({ "status": 400, "message": "Invalid ID." })

    res = { "status": 200, "message": "Successfully updated autoblind mode." }

    return jsonify(res)

# HIMS back-end functionality
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
    payload = { "threshold": value }

    publish_to_topic(topic, payload)

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
            "threshold": int(r["threshold"]),
            "log": [],
            "weight": None,
            "is_depleted": None
        }

    rows = table_weights.scan()["Items"]
    for r in rows:
        if r["id"] not in items:
            continue

        items[r["id"]]["log"].append({
            "weight": int(r["data"]["weight"]),
            "timestamp": int(r["timestamp"])
        })

        items[r["id"]]["weight"] = int(r["data"]["weight"])
        items[r["id"]]["is_depleted"] = r["data"]["is_depleted"]

    return jsonify(items)

#Security
@app.route("/security")
def security():
    return render_template("security.html")

@app.route("/add_face/<input_name>", methods=['POST'])
#Function for toggling training mode and call edge to detect new faces
def add_face(input_name):
    topic = "frlock/face_recog/update"
    payload = {
        "isTraining": True,
        "name": input_name
    }
    publish_to_topic(topic, payload)
    return "1"

@app.route("/update", methods=['POST'])
#Function for updating the website by checking if is in training mode or not
def update_webpage():
    dynamodb = boto3.resource("dynamodb")
    securityLogs = dynamodb.Table("securityLogs")
    ultrasonicLogs = dynamodb.Table("ultSensorLog")
#     response = securityLogs.scan()["Items"]  
    scrLogs = securityLogs.query(
        KeyConditionExpression = Key('id').eq('scrID'),
        Limit=1,
        ScanIndexForward=False)
#     print(response)
#     print(scrLogs)
    templateData = {}
    for r in scrLogs["Items"]:
        templateData["isTraining"] = r["securityLog"]["isTraining"]
        templateData["user"] = r["securityLog"]["name"]
        templateData["access"] = r["securityLog"]["access"]
        templateData["image"] = r["securityLog"]["image"]
        templateData["timestamp"] = int(r["timestamp"])
#         templateData = {
#             'isTraining' : r["securityLog"]["isTraining"]
#         }
        
    ultLogs = ultrasonicLogs.query(
        KeyConditionExpression = Key('id').eq('ultrasonicID'),
        Limit=1,
        ScanIndexForward=False)
    
    for a in ultLogs["Items"]:
        templateData["distance"] = int(a["ultrasonicLog"]["distance"])
        
    return jsonify(templateData)
    

@app.route("/video_feed")
def video_feed():
    return Response(generate(),mimetype = "multipart/x-mixed-replace; boundary=frame")
    
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
