import serial 
import MySQLdb
import time 
from flask import Flask, render_template

device = '/dev/ttyACM0'
ser = serial.Serial(device, 9600, timeout=1)
app = Flask (__name__)

# Dictionary of pins with name of pin and state ON/OFF 
pins = {
    3: {'name' : 'PIN 3', 'state' : 0}
}

valueDist = 0
valueLight = 0
preLight = 0

# Main function when accessing the website 
@app.route("/") 
def index():
    global valueLight
    
    dbConn = MySQLdb.connect("localhost","pi","","assignment_db") or dle("Could not connect to database")
    print(dbConn)
    while(ser.in_waiting == 0):
        pass
    
    preLight = valueLight
    line = ser.readline()
    valueDist = int(line[18:21])
    valueLight = int(line[24:28])
    print(valueDist)
    print(valueLight)
    
    with dbConn:
        cursor = dbConn.cursor()
        cursor.execute("INSERT INTO tempLog (distance,light) VALUES (%s,%s)" %(valueDist,valueLight))
        dbConn.commit()
        cursor.close()
        
    if(valueLight <= 50):
        pins[3]['state'] = 1
    elif(valueLight > 50):
        pins[3]['state'] = 0
    
    if(valueDist <= 600 and valueDist >= 300):
        pins[3]['state'] = 1
            
        # This data will be sent to index.html (pin dictionary)
    templateData = {
        'pins' : pins,
        'valueDist' : valueDist,
        'valueLight' : valueLight,
        'preLight' : preLight
        }
    
    # Pass the template data into the template index.html and return it
    return render_template('assignment.html', **templateData) # Function to send simple commands

    
@app.route("/<action>")
def action(action):
     global valueLight
     preLight = valueLight
     if action == 'action1' :
         ser.write(b"1")
         pins[3]['state'] = 1
     if action == 'action2' :
         ser.write(b"2")
         pins[3]['state'] = 0

     # This data will be sent to index.html (pins dictionary)
     templateData = {
         'pins' : pins,
         'valueDist' : valueDist,
         'valueLight' : valueLight,
         'preLight' : preLight
         }
     return render_template('assignment.html', **templateData)
    
# Function with buttons that toggle (change on to off or off to on) depending on the status 
@app.route("/<changePin>/<toggle>") 
def toggle_function(changePin, toggle):
     global valueLight
     preLight = valueLight
     # Convert the pin from the URL into an integer
     changePin = int(changePin)
     # Get the device name for the pin being changed
     deviceName = pins[changePin]['name']
     # If the action part of the URL is "on", execute the code indented below:
     if toggle == "on":
         # Set the pin high:
         if changePin == 3:
             ser.write(b"1")
             pins[changePin]['state'] = 1
             # Save the status message to be passed into the template:
             message = "Turned " + deviceName + "on."
             # If the action part of the URL is "on", execute the code indented below:
     if toggle == "off":
     # Set the pin high:
         if changePin == 3:
             ser.write(b"2")
             pins[changePin]['state'] = 0
             # Save the status message to be passed into the template:
             message = "Turned " + deviceName + "off."
     
     # This data will be sent to index.html (pins dictionary)
     templateData = {
         'pins' : pins,
         'valueDist' : valueDist,
         'valueLight' : valueLight,
         'preLight' : preLight
         }
     # Pass the template data into the template index.html and return it
     return render_template('assignment.html', **templateData)

# Main function, set up serial bus, indicate port for the webserver, and start the service
if __name__ == "__main__" :
    ser.flush()
    app.run(host='0.0.0.0', port = 80, debug = True)