import serial, sys, time
import json

import mariadb
from misc import trc_mean

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
                      (RACK,FLOOR,pipe,trc_mean(record['temp']),trc_mean(record['ph']),trc_mean(record['ec']),trc_mean(record['fr'])))
        else:
            cursor.execute("INSERT INTO `water.tab` (rack,floor,pipe,temperature,ec,flowrate) VALUES (?,?,?,?,?,?)",
                      (RACK,FLOOR,pipe,trc_mean(record['temp']),trc_mean(record['ec']),trc_mean(record['fr'])))
        conn.commit()
    except:
        conn = getConnDB()
        
    return(conn)

def getConnDB():
    conn= None
    try:
        conn = mariadb.connect(
            user="farmer",
            password="!SSUfarm0690",
            host="220.149.87.248",
            port=3307,
            database="livfarm"

        )
    except mariadb.Error as e:
        print(f"Error connecting to MariaDB Platform: {e}")
        sys.exit(1)
    return(conn)


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
        data['EC2'] = data['EC2'] - 1.0
        data = {'Temp':24.3, 'EC1':2.080, 'EC2':0.657, 'Flow1':64, 'Flow2':64, 'pH1':6.21, 'pH2':7.34}

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
    
