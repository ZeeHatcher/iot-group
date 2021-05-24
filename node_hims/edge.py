import serial

threshold = 100

def loop():
    # Do nothing if there is no incoming serial data
    while (ser.in_waiting == 0):
        pass

    # Extract data from serial input
    line = ser.readline().decode("UTF-8").strip()

    tokens = line.split(":")
    nuid = tokens[0]
    weight = int(tokens[1])

    value = max(0, min(weight - threshold, 100))

    ser.write(bytes([value]))

    

if __name__ == "__main__":
    print("Running edge.py")

    ser = serial.Serial('/dev/ttyUSB0', 9600)

    while True:
        loop()
