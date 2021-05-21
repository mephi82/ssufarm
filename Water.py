import serial, sys, time
import json
from statistics import mean
import mariadb

if len(sys.argv) == 6:
    RACK, FLOOR, PIPE1, PIPE2, PORT = sys.argv[1:6]
else:
    print('6 arguments required. Now:', sys.argv)
    sys.exit(1)

SAMPLING = 60

def emptyRecords():
    record1 = {'temp':[], 'ec':[], 'ph':[], 'fr':[]}
    return(record1)

def DBwrite_water(conn, pipe, record):
    cursor = conn.cursor()
    try:
        if len(record['ph'])>0:
            cursor.execute("INSERT INTO `water.tab` (rack,floor,pipe,temperature,ph,ec,flowrate) VALUES (?,?,?,?,?,?,?)",
                      (RACK,FLOOR,pipe,mean(record['temp']),ph,mean(record['ec']),mean(record['fr'])))
        else:
            cursor.execute("INSERT INTO `water.tab` (rack,floor,pipe,temperature,ec,flowrate) VALUES (?,?,?,?,?,?)",
                      (RACK,FLOOR,pipe,mean(record['temp']),mean(record['ec']),mean(record['fr'])))
        conn.commit()
    except:
        conn = getConnDB()
        
    return(conn)

def getConnDB():
    conn= None
    try:
        conn = mariadb.connect(
            user="root",
            password="!Gkrrhkwkd0690",
            host="220.149.87.248",
            port=3307,
            database="livfarm"

        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)
    return(conn);


# Get Cursor
conn = getConnDB()


T = serial.Serial(PORT,115200)
for _ in range(10):
    T.readline()
record1= emptyRecords()
record2= emptyRecords()
count1 = 0
count2 = SAMPLING*(-0.5)
while True:
    if count1>SAMPLING:
        print("Writing DB for PIPE1")
        conn = DBwrite_water(conn, PIPE1, record1)
        record1=emptyRecords()
        count1 = 1
    if count2>SAMPLING:
        print("Writing DB for PIPE2")
        conn = DBwrite_water(conn, PIPE2, record2)
        record2=emptyRecords()
        count2 = 1
        
        

    output = T.readline().decode('ascii')
    print(output.strip())
    if output.startswith('{'):
        data = json.loads(output)
        
        record1['temp'].append(data['Temp'])
        record2['temp'].append(data['Temp'])
        try:
            record1['ph'].append(data['pH1'])
        except KeyError:
            pass
        try:
            record2['ph'].append(data['pH2'])
        except KeyError:
            pass        
        record1['ec'].append(data['EC1'])
        record2['ec'].append(data['EC2'])
        record1['fr'].append(data['Flow1'])
        record2['fr'].append(data['Flow2'])
    count1+=1
    count2+=1
    # print(count)
    
