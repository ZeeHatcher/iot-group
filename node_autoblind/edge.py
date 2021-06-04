from awscrt import auth, io, mqtt, http
from awsiot import mqtt_connection_builder
import boto3
from dotenv import load_dotenv
import json
import os
import serial
import sys
import threading
import time
import traceback
from uuid import uuid4

state = {
    "light_interior": 0,
    "light_exterior": 0,
    "motor_pos": 0,
    "mode": "auto",
    "motor_max_pos": 4891,
    "motor_min_pos": 0
}

subscribe_topic = "autoblinds/node_autoblind/set"

# Function for gracefully quitting
def exit(msg_or_exception):
    if isinstance(msg_or_exception, Exception):
        print("Exiting due to exception.")
        traceback.print_exception(msg_or_exception.__class__, msg_or_exception, sys.exc_info()[2])
    else:
        print("Exiting:", msg_or_exception)

    print("Disconnecting MQTT connection...", end=" ")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected.")

    print("Stopping publish thread...", end=" ")
    publish_thread.is_run = False
    publish_thread.join()
    print("Stopped.")

    print("Terminated.")

def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Message received.")
    item = json.loads(payload)
    print("\tTopic:", topic)
    print("\tPayload:", item)
    
    if "mode" in item:
        state["mode"] = item["mode"]
    if "motor_max_pos" in item:
        state["motor_max_pos"] = int(item["motor_max_pos"])
    if "motor_min_pos" in item:
        state["motor_min_pos"] = int(item["motor_min_pos"])
    if "motor_pos" in item:
        state["motor_pos"] = int(item["motor_pos"])
        message = item["motor_pos"] + "," + state["mode"]
    else:
        message = "-1," + state["mode"]
    
    ser.write(message.encode())
    
def publish_sensors_data():
    t = threading.currentThread()
    while getattr(t, "is_run", True):   
        payload = {
            "light_interior": state["light_interior"],
            "light_exterior": state["light_exterior"],
            "mode": state["mode"],
            "motor_pos": state["motor_pos"]
        }

        print("Publishing...")
        print("\tTopic:", "autoblinds/node_autoblind/put")
        print("\tPayload:", payload)
        publish_future, packet_id = mqtt_connection.publish(
            topic="autoblinds/node_autoblind/put",
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_LEAST_ONCE)
        publish_future.result()
        print("Published.")

        time.sleep(10)
    
def loop():
    # Do nothing if there is no incoming serial data
    while (ser.in_waiting == 0):
        pass

    # Extract data from serial input
    line = ser.readline().decode("UTF-8").strip()
    values = line.split(",")

    state["light_interior"] = int(values[0])
    state["light_exterior"] = int(values[1])
    state["motor_pos"] = int(values[2])
    if (len(values) >= 4):
        if (values[3] == "a"):
            state["mode"] = "auto"
        elif (values[3] == "m"):
            state["mode"] = "manual"
    
    if state["mode"] == "auto":
        # Calculate the difference in light values
        light_diff = abs(state["light_interior"] - state["light_exterior"])
        
        if light_diff > 10:            
            if state["light_interior"] < state["light_exterior"]:
                new_motor_pos = state["motor_max_pos"] 
            else:
                new_motor_pos = state["motor_min_pos"]
                        
            # Update statea and arduino
            state["motor_pos"] = new_motor_pos
            
            message = str(state["motor_pos"]) + ",N"
            ser.write(message.encode())
        

if __name__ == "__main__":
    print("Running edge.py...")

    try:
        # Load environment variables in .env
        load_dotenv()

        CLIENT_ID = os.environ.get("CLIENT_ID") or str(uuid4())
        SERIAL_CONN = os.environ.get("SERIAL_CONN")
        THING_ENDPOINT = os.environ.get("THING_ENDPOINT")
        THING_NAME = os.environ.get("THING_NAME")

        CERT_DIR = "./.certs/"
        CA_FILEPATH = CERT_DIR + os.environ.get("CA_FILE")
        CERT_FILEPATH = CERT_DIR + os.environ.get("CERT_FILE")
        PRIVATE_KEY_FILEPATH = CERT_DIR + os.environ.get("PRIVATE_KEY_FILE")

        # Establish serial connectivity
        ser = serial.Serial(SERIAL_CONN, 9600)

        # Create connections with AWS services and resources
        dynamodb = boto3.resource("dynamodb")
        autoblind = dynamodb.Table("autoblind")
    
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
        
        print("Subscribing to topic '%s'..." % subscribe_topic, end=" ")
        subscribe_future, packet_id = mqtt_connection.subscribe(
            topic=subscribe_topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_message_received
        )
        subscribe_future.result()
        print("Subscribed.")
        
        # Start separate thread for uploading sensors data to cloud
        print("Starting publish thread...", end=" ")
        publish_thread = threading.Thread(target=publish_sensors_data)
        publish_thread.start()
        print("Started.")
        
        while True:
            loop()

    except KeyboardInterrupt:
        exit("Caught KeyboardInterrupt, terminating...")

    except Exception as e:
        exit(e)