import serial 
import MySQLdb
import time 
from flask import Flask, render_template

import paho.mqtt.client as paho
import os
import socket
import ssl
import random
import string
import json
from time import sleep
from random import uniform
 
connflag = False

device = '/dev/ttyACM0'
ser = serial.Serial(device, 9600, timeout=1)

# Dictionary of pins with name of pin and state ON/OFF 
pins = {
    3: {'name' : 'PIN 3', 'state' : 0}
}

valueDist = 0
valueLight = 0
preLight = 0

def on_connect(client, userdata, flags, rc):                # func for making connection
    global connflag
    print("Connected to AWS")
    connflag = True
    print("Connection returned result: " + str(rc) )
    client.subscribe("lightSensor")
 
def on_message(client, userdata, msg):                      # Func for Sending msg
    item = json.loads(msg.payload)
    if "state" in item:
        if(item['state'] == 1):
            ser.write(b"1") 
        else:
            ser.write(b"2")
    print(msg.topic+" "+str(msg.payload))
    
    
mqttc = paho.Client()                                       # mqttc object
mqttc.on_connect = on_connect                               # assign on_connect func
mqttc.on_message = on_message                               # assign on_message func

#### Change following parameters #### 
awshost = "ashixvhkiwhi7-ats.iot.ap-southeast-1.amazonaws.com"      # Endpoint
awsport = 8883                                              # Port no.   
clientId = "node_smartLight"                                     # Thing_Name
thingName = "node_smartLight"                                    # Thing_Name
caPath = "AmazonRootCA1.pem"                                      # Root_CA_Certificate_Name
certPath = "ac69e3dec7-certificate.pem.crt"                            # <Thing_Name>.cert.pem
keyPath = "ac69e3dec7-private.pem.key"                          # <Thing_Name>.private.key
     
mqttc.tls_set(caPath, certfile=certPath, keyfile=keyPath, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)  # pass parameters
 
mqttc.connect(awshost, awsport, keepalive=60)               # connect to aws server
 
mqttc.loop_start() 

while 1==1:
    sleep(3)
    
    preLight = valueLight
    line = ser.readline()
    print(line)
    valueDist = int(line[18:21])
    valueLight = int(line[24:27])
    state = int(line[30:31])
    print(valueDist)
    print(valueLight)
    print(line)
    
    if connflag == True:
        paylodmsg0="{"
        paylodmsg1="\"id\":\"light\""
        paylodmsg2 = ",\"distance\":"
        paylodmsg3 = ",\"light\":"
        paylodmsg4= ",\"state\":"
        paylodmsg5= "}"
        paylodmsg = "{} {} {} {} {} {} {} {} {}".format(paylodmsg0,paylodmsg1, paylodmsg2, valueDist,
                                                     paylodmsg3, valueLight, paylodmsg4, state, paylodmsg5)
        paylodmsg = json.dumps(paylodmsg) 
        paylodmsg_json = json.loads(paylodmsg)       
        mqttc.publish("node_smartLight", paylodmsg_json , qos=1)        # topic: temperature # Publishing Temperature values
        print("msg sent: node_smartLight" ) # Print sent temperature msg on console
        print(paylodmsg_json)

    else:
        print("waiting for connection...")
