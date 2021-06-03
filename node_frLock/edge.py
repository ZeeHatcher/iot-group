from awscrt import auth, io, mqtt, http
from awsiot import mqtt_connection_builder
import boto3
from dotenv import load_dotenv
import json
import cv2
import numpy as np 
import pickle
from imutils.video import VideoStream
from flask import Flask, render_template, Response
from time import sleep
import threading
import time
import imutils
# import io
import os
from PIL import Image
import serial
from flask import jsonify
from uuid import uuid4

outputFrame = None
training = False
name = ""
distance = 0
lock = threading.Lock()
app = Flask(__name__)
device = '/dev/ttyUSB0'
arduino = serial.Serial(device,9600)
arduino.flush()
# start = time.time()

previous = ""

security = {
    'isTraining' : False,
    'name' : "",
    'access' : "Denied",
    'image': ""
}

securityChanges = False
lineT = ""
lineB = ""

vs = VideoStream(src=0).start()
time.sleep(2.0)

# @app.route("/")
# def facial():
#     return render_template("facial.html")

# @app.route("/add_face/<input_name>", methods=['POST'])
# def add_face(input_name):
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

# @app.route("/update", methods=['POST'])
# def update_webpage():
#     templateData = {
#         'isTraining' : training,   
#     }
#     return jsonify(templateData)

# @app.route("/facial")
def facial_recognition():
    global outputFrame,lock,training,name
    count = 1
    start = time.time()
    with open('labels','rb') as f:
        dict1 = pickle.load(f)
        f.close()
    
    faceCascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read("trainer.yml")
    while True:
        frame = vs.read()
        ori_frame = frame.copy()
        frame = imutils.resize(frame,width=640,height=480)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = faceCascade.detectMultiScale(gray, scaleFactor = 1.5, minNeighbors = 5)
        for (x, y, w, h) in faces:
            roiGray = gray[y:y+h, x:x+w]
            if not training:
#                 print("Detecting mode")
                id_, conf = recognizer.predict(roiGray)
                
                #Unlock if confidence is less than 70
                if conf <= 70:
                    keys = list(dict1.keys())
                    values = list(dict1.values())
                    position = values.index(id_)
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(frame, keys[position], (x, y), font, 1, (0, 255 ,0), 2,cv2.LINE_AA)
                    if distance <= 20:
                        securityChanges = True
                        lineT = "{} {}".format('Detected User:',keys[position])
                        lineB = "Permission Granted"                
                        security["isTraining"] = False
                        security["name"] = keys[position]
                        security["access"] = "Granted"
                        
                else:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
#                     print("Face not detected")
                    if distance <= 20:
                        lineT = 'Unauthorized User Detected'
                        lineB = "Permission Denied"
                        security["isTraining"] = False
                        security["name"] = "unknown"
                        security["access"] = "Denied"
            else:
                print("Training mode")
                lineT ='Training User: ' + name
                lineB = "Adding Permission"                
                security["isTraining"] = True
                security["name"] = name
                security["access"] = "Adding"
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
                if(name != ""):
                    user_images = './images/' + name
                    if not os.path.exists(user_images):
                        os.makedirs(user_images)
                    fileName = user_images + "/" + name + str(count) + ".jpg"
                    cv2.imwrite(fileName,roiGray)
                    count += 1
                    print("Detected ",str(count)," faces")
                    if(count >30):
                        (flag,encodedImage) = cv2.imencode(".jpeg",ori_frame)
                        fileName = str(int(time.time())) + ".jpg"
                        bucket.put_object(Key=fileName,Body=bytes(encodedImage))
                        security["image"] = "https://iot-bucket007.s3-ap-southeast-1.amazonaws.com/" + fileName
                        security["isTraining"] = False
                        security["name"] = name
                        security["access"] = "Added"
                        lineT = "User Added: " + name
                        lineB = "Added Permission to " + name
                        
                        topic = "frlock/face_recog/put"
                        payload = {
                            "isTraining": security["isTraining"],
                            "name": security["name"],
                            "access": security["access"],
                            "image" : security["image"]
                        }
                        publish_topic(topic,payload)
                        
                        train_recognizer()
                        with open('labels','rb') as f:
                            dict1 = pickle.load(f)
                            f.close()
                        recognizer = cv2.face.LBPHFaceRecognizer_create()
                        recognizer.read("trainer.yml")
                        training = False
                        start = time.time()
                        count = 1
            
            if time.time() - start > 10:
                (flag,encodedImage) = cv2.imencode(".jpeg",ori_frame)
                fileName = str(int(time.time())) + ".jpg"
                bucket.put_object(Key=fileName,Body=bytes(encodedImage))
                security["image"] = "https://iot-bucket007.s3-ap-southeast-1.amazonaws.com/" + fileName
                message = "{} ,{} \n".format(lineT,lineB)
                enc_message = message.encode("UTF-8")
                ser.write(enc_message)
                topic = "frlock/face_recog/put"
                payload = {
                    "isTraining": security["isTraining"],
                    "name": security["name"],
                    "access": security["access"],
                    "image" : security["image"]
                }
                publish_topic(topic,payload)
                start = time.time()
                
        with lock:
            outputFrame = frame.copy()

def publish_topic(topic,payload):
    print("Publishing...")
    print("\tTopic:", topic)
    print("\tPayload:", payload)
    publish_future, packet_id = mqtt_connection.publish(
        topic=topic,
        payload=json.dumps(payload),
        qos=mqtt.QoS.AT_LEAST_ONCE)
    publish_future.result()
    print("Published.")
    
def train_recognizer():
    faceCascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    
    base = os.path.dirname(os.path.abspath(__file__))
    images = os.path.join(base,"images")
    
    currentId = 1
    labelIds = {}
    yLabels = []
    xTrain = []
    
    for root, dirs, files in os.walk(images):
        print(root,dirs,files)
        for file in files:
            #print(file)
            if file.endswith("png") or file.endswith("jpg"):
                path = os.path.join(root,file)
                label = os.path.basename(root)
                print("label",label)
                
                if not label in labelIds:
                    labelIds[label] = currentId
                    print(labelIds)
                    currentId += 1
                    
                id_ = labelIds[label]
                lImage = Image.open(path).convert("L")
                image_arr = np.array(lImage, "uint8")
                faces = faceCascade.detectMultiScale(image_arr, scaleFactor=1.1, minNeighbors=5)
                
                for (x,y,w,h) in faces:
                    roi = image_arr[y:y+h,x:x+w]
                    xTrain.append(roi)
                    yLabels.append(id_)
                    
    with open("labels","wb") as f:
        pickle.dump(labelIds,f)
        f.close()
        
    recognizer.train(xTrain,np.array(yLabels))
    recognizer.write("trainer.yml")
    print(labelIds)
 

def generate():
    global outputFrame,lock
    while True:
        with lock:
            if outputFrame is None:
                print("No output frame")
                continue
            
            (flag,encodedImage) = cv2.imencode(".jpeg",outputFrame)
            
            if not flag:
                print("not flag")
                continue
        
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n'+ encodedImage.tobytes() + b'\r\n')

# @app.route("/video_feed")
# def video_feed():
#     return Response(generate(),mimetype = "multipart/x-mixed-replace; boundary=frame")
def loop():
    global distance
    
    # Do nothing if there is no incoming serial data
    while (ser.in_waiting == 0):
        pass

    # Extract data from serial input
    line = ser.readline().decode("UTF-8").strip()
    distance = int(line)
    topic = "frlock/ultrasonic/put"
    payload = {
        "distance": distance,
    }
    publish_topic(topic,payload)
    time.sleep(5)
    
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    global training,name
    print("Message received.")
    scr_stats = json.loads(payload)
    print("\tTopic:", topic)
    print("\tPayload:", scr_stats)

    training = scr_stats["isTraining"]
    name = scr_stats["name"]
 
        
if __name__ == "__main__":
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
        ser.flush()

        # Create connections with AWS services and resources
        dynamodb = boto3.resource("dynamodb")
        s3 = boto3.resource("s3")
        bucket = s3.Bucket("iot-bucket007")
        ultrasonicLogs = dynamodb.Table("ultrasonicSensor")

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
        
        #Subscribing to a topic
        subscribe_topic = "frlock/face_recog/update"

        print("Subscribing to topic '%s'..." % subscribe_topic, end=" ")
        subscribe_future, packet_id = mqtt_connection.subscribe(
            topic=subscribe_topic,
            qos=mqtt.QoS.AT_LEAST_ONCE,
            callback=on_message_received
        )
        subscribe_future.result()
        print("Subscribed.")
        
        t = threading.Thread(target=facial_recognition)
        t.daemon = True
        t.start()
        
        while True:
            loop()
                  
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt, terminating...")
        vs.stop()
        cv2.destroyAllWindows()

    except Exception as e:
        print(e)
        vs.stop()
        cv2.destroyAllWindows()
        
#     app.run(host="0.0.0.0", port=5000, debug=True, threaded=True, use_reloader=False)    