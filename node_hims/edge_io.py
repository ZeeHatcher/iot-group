import serial
import datetime
import MySQLdb

ser_in = serial.Serial('/dev/ttyUSB0', 9600)
ser_out = serial.Serial('/dev/ttyACM0', 9600)

if __name__ == "__main__":
    print("Running serial_into_db.py")

    # Connect to DB
    db = MySQLdb.connect("localhost", "pi", "", "hims_db") or die("Could not connect to database")

    ser_in.flush()

    while 1:

        while (ser_in.in_waiting == 0):
            pass

        # Extract data from serial input
        line = ser_in.readline()
        tokens = line.split(":")
        nuid = tokens[0]
        weight = int(tokens[1])
        is_begin_point = False
        delta = 0

        with db.cursor() as cur:
            # Compare recorded weight with previous weight to see if it is a new "begin point",
            cur.execute("SELECT weight FROM weights WHERE item_id = '%s' ORDER BY created_at DESC LIMIT 1" % nuid)
            prev = cur.fetchone()

            if (prev == None or weight > prev[0] + 2):
                is_begin_point = True

            # If not a "begin point", get the time difference between the current recording
            # and latest "begin point"
            if (not is_begin_point):
                cur.execute("SELECT created_at FROM weights WHERE item_id = '%s' AND is_begin_point = true ORDER BY created_at DESC LIMIT 1" % nuid)
                ref_point = cur.fetchone()
                time_delta = datetime.datetime.now() - ref_point[0]
                delta = time_delta.total_seconds()

            # Insert ID into DB, if it is new
            cur.execute("INSERT IGNORE INTO items (id, name) VALUES ('%s', '%s')" % (nuid, "Item Nil"))

            # Insert recorded weights
            cur.execute("INSERT INTO weights (item_id, weight, is_begin_point, delta) VALUES ('%s', %d, %s, %d)" % (nuid, weight, is_begin_point, delta))

            # Update status of item if weight passed threshold
            cur.execute("UPDATE items SET state = IF(%s < threshold, 0, 1) WHERE id = '%s'" % (weight, nuid))
            cur.close();

        db.commit()

        print("Insert into DB: (%s, %d)" % (nuid, weight))

        with db.cursor() as cur:
            cur.execute("SELECT name FROM items WHERE state = 0")

            depleted = [item[0] for item in cur.fetchall()]

            msg = ",".join(depleted) if len(depleted) > 0 else "-"
            ser_out.write(msg.encode())

            cur.close()
