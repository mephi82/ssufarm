import serial, sys
import json
from statistics import mean
import mariadb

if len(sys.argv) == 4:
    RACK, FLOOR, PIPE = sys.argv[1:4]
else:
    print('3 arguments required. Now:', sys.argv)
    sys.exit(1)

SAMPLING = 5

def emptyRecord():
    records = {'temp':[], 'ec':[], 'ph':[]}
    return(records)

def DBwrite_water(cursor, temperature, ph, ec):
    if ph is not None:
        cursor.execute("INSERT INTO `water.tab` (rack,floor,pipe,temperature,ph,ec) VALUES (?,?,?,?,?,?)",
                  (RACK,FLOOR,PIPE,temperature,ph,ec))
    else:
        cursor.execute("INSERT INTO `water.tab` (rack,floor,pipe,temperature,ec) VALUES (?,?,?,?,?)",
                  (RACK,FLOOR,PIPE,temperature,ec))

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

# Get Cursor
cur = conn.cursor()

T = serial.Serial('COM6',115200)
for _ in range(10):
    T.readline()
records = emptyRecord()
count = 0
while True:
    if count>SAMPLING:
        print("Writing DB")
        if len(records['ph'])>0:
            DBwrite_water(cur,mean(records['temp']), mean(records['ph']),mean(records['ec']))
        else:
            DBwrite_water(cur,mean(records['temp']), None,mean(records['ec']))
        count = 0        
        records = emptyRecord()
        conn.commit()

    output = T.readline().decode('ascii')
    if output.startswith('{'):
        data = json.loads(output)
        print(data)
        records['temp'].append(data['Temp'])
        try:
            records['ph'].append(data['pH'])
        except KeyError:
            pass
        records['ec'].append(data['EC'])
    count+=1
    # print(count)
    
