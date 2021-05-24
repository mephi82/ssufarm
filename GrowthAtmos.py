from picamera.array import PiRGBArray
from picamera import PiCamera
import os, time, sys
import cv2
import numpy as np
import smbus
import Adafruit_DHT
import mariadb
import paramiko

host = '220.149.87.248'
transport = paramiko.transport.Transport(host,22)


DHT_GPIO, I2C_CH, BH_DEV_ADDR = (4,1,0x23)

if len(sys.argv) == 6:
    RACK, FLOOR, PIPE, POT = sys.argv[1:5]
else:
    print('5 arguments required. Now:', sys.argv)
    sys.exit(1)

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




# I2C_CH = 1
# BH_DEV_ADDR = 0x23
i2c = smbus.SMBus(I2C_CH)
CONT_H_RES = 0x10
ONETIME_H_RES = 0x20

camera = PiCamera()
camera.resolution = (1024, 768)
camera.framerate = 32
rawCapture = PiRGBArray(camera, size=(1024, 768))
font = cv2.FONT_HERSHEY_SIMPLEX

time.sleep(0.1)

def writeOnImg(img, text, origin):
    cv2.putText(img, text, origin, font, 1, (255,255,0))

def senseBH1750():
    luxBytes = i2c.read_i2c_block_data(BH_DEV_ADDR, CONT_H_RES, 2)
    lux = int.from_bytes(luxBytes, byteorder = 'big')
    return(lux)
#     return('Light={0:0}  lux'.format(lux))


def detectGreen(camera, rawCapture):
    camera.capture(rawCapture, format="bgr", use_video_port=True)
    img = rawCapture.array
        
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    lower_green = np.array([25,52,10])
    upper_green = np.array([102,255,255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    kernel = np.ones((5,5), 'int')
    dilated = cv2.dilate(mask, kernel)
    
    res = cv2.bitwise_and(img, img, mask = dilated)
    
    ret, threshold = cv2.threshold(cv2.cvtColor(res, cv2.COLOR_BGR2GRAY), 3,255,cv2.THRESH_BINARY)
    contours, hier = cv2.findContours(threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    maxArea = 5000
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > maxArea:
            cv2.drawContours(img, [cnt], 0, (0,255,0), 1)
            contpoly = cv2.approxPolyDP(cnt, 3, True)
            bbox = cv2.boundingRect(contpoly)
            (x, y), radius = cv2.minEnclosingCircle(contpoly)
            
            cv2.putText(img, "{0:0} width:{1:0} height:{2:0} rad:{3:0}".format(maxArea,bbox[2],bbox[3],radius), (bbox[0],bbox[1]), font, 1, (0,255,255))
            cv2.rectangle(img, (bbox[0],bbox[1]),(bbox[0]+bbox[2],bbox[1]+bbox[3]),(0,255,255),2)
            maxArea = area
    
    if maxArea>5000:
        return(img, maxArea, bbox[2], bbox[3], radius)
    else:
        return(img, None, None, None, None)


def DBwrite_atmos(cursor, brightness, temperature, humidity):
    if temperature is not None:
        cursor.execute("INSERT INTO `atmos.tab` (rack,floor,pipe,pot,brightness,temperature,humidity) VALUES (?,?,?,?,?,?,?)",
                  (RACK,FLOOR,PIPE,POT,brightness,temperature,humidity))
    else:
        cursor.execute("INSERT INTO `atmos.tab` (rack,floor,pipe,pot,brightness) VALUES (?,?,?,?,?)",
                  (RACK,FLOOR,PIPE,POT,brightness))


def DBwrite_growth(cursor, pixels, bx, by, radius):
    cursor.execute("INSERT INTO `growth.tab` (rack,floor,pipe,pot,pixels,bbx,bby,radius) VALUES (?,?,?,?,?,?,?,?)",
                  (RACK,FLOOR,PIPE,POT,pixels,bx,by,radius))

SAMPLING = 60
logcount = 1
capcount = 0
while True:
    
    img, pixels, bx, by, radius = detectGreen(camera, rawCapture)
    lux = senseBH1750()
    hum, temp = Adafruit_DHT.read(Adafruit_DHT.DHT11, DHT_GPIO)

    if sys.argv[5] == 'show':
        writeOnImg(img, 'Light={0:0} lux'.format(lux), (50,50))
        if temp is not None:
            writeOnImg(img, 'Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(temp, hum), (50,100))
        else:
            writeOnImg(img, "Failed to read", (50,100))        
        cv2.imshow("Frame"+' '.join(sys.argv), img)
    else:
        print(pixels, temp, hum)

    if capcount%3600==0:
        imgpath = '/images/'
        imgname = 'img_'+RACK+FLOOR+PIPE+POT+str(int(time.time()*1000.0))+'.jpg'
        cv2.imwrite(imgpath+imgname, img)
        print(imgpath+imgname)
        imgurl = '/web/livfarm/'+imgname
        try:
            transport.connect(username = 'hod', password = 'gkrrhkwkd0690')
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.put(imgpath+imgname, imgurl)
        finally:
            sftp.close()

        capcount = 0

    if logcount>SAMPLING:
        try:
            DBwrite_atmos(cur,lux, temp, hum)
            DBwrite_growth(cur,pixels,bx,by,radius)
        except:
            print(f"Error: {e}")
        if sys.argv[5] == 'show' or sys.argv[5] == 'commit':
            conn.commit()
        count = 0

    logcount+=1
    capcount+=1
        
    time.sleep(1)        
    key = cv2.waitKey(1) & 0xFF
    
    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)

    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break

conn.close()
cv2.destroyAllWindows()    
transport.close()