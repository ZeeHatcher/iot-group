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
    "id": None,
    "weight": None,
    "threshold": 0,
    "is_depleted": False
}
can_publish = False

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

    # Validation of payload data
    if "threshold" not in item:
        return

    state["threshold"] = item["threshold"]
    print("\tUpdated state:", state)

def get_threshold(nuid):
    response = items.get_item(Key={ "id": nuid })
    item = response["Item"] if "Item" in response else put_item(nuid)

    return int(item["threshold"])

def put_item(nuid):
    item = {
        "id": nuid,
        "threshold": 0
    }
    items.put_item(Item=item)

    return item

def publish_sensors_data():
    global can_publish

    t = threading.currentThread()
    while getattr(t, "is_run", True):
        if can_publish:
            # Disable publishing to prevent republishing of same data
            can_publish = False

            topic = "hims/{}/weight/put".format(state["id"])
            payload = {
                "weight": state["weight"],
                "is_depleted": state["is_depleted"]
            }

            print("Publishing...")
            print("\tTopic:", topic)
            print("\tPayload:", payload)
            publish_future, packet_id = mqtt_connection.publish(
                topic=topic,
                payload=json.dumps(payload),
                qos=mqtt.QoS.AT_LEAST_ONCE)
            publish_future.result()
            print("Published.")

        time.sleep(5)

def loop():
    global can_publish, subscribe_topic

    # Do nothing if there is no incoming serial data
    while (ser.in_waiting == 0):
        pass

    # Extract data from serial input
    line = ser.readline().decode("UTF-8").strip()
    tokens = line.split(":")

    # Update node state
    nuid = tokens[0]

    if state["id"] == None or state["id"] != nuid:
        if subscribe_topic != None:
            print("Unsubscribing from topic '%s'..." % subscribe_topic, end=" ")
            mqtt_connection.unsubscribe(subscribe_topic)
            print("Unsubscribed.")

        subscribe_topic = "hims/{}/threshold/update".format(nuid)

        print("Subscribing to topic '%s'..." % subscribe_topic, end=" ")
        subscribe_future, packet_id = mqtt_connection.subscribe(
            topic=subscribe_topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_message_received
        )
        subscribe_future.result()
        print("Subscribed.")

        # Get threshold for new item
        state["threshold"] = get_threshold(nuid)
        state["id"] = nuid

    state["weight"] = int(tokens[1])

    # Calculate "distance" of item weight from threshold and send to MCU
    value = max(0, min(state["weight"] - state["threshold"], 100))
    ser.write(bytes([value]))
    state["is_depleted"] = value <= 0

    # Reenable publishing because new sensors data was received
    can_publish = True



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
        items = dynamodb.Table("items")
        weights = dynamodb.Table("weights")

        # Start separate thread for uploading sensors data to cloud
        print("Starting publish thread...", end=" ")
        publish_thread = threading.Thread(target=publish_sensors_data)
        publish_thread.start()
        print("Started.")

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

        subscribe_topic = None

        while True:
            loop()

    except KeyboardInterrupt:
        exit("Caught KeyboardInterrupt, terminating...")

    except Exception as e:
        exit(e)
