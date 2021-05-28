from picamera.array import PiRGBArray
from picamera import PiCamera
import os, time, sys
import cv2
import numpy as np
import smbus
import Adafruit_DHT
import mariadb
import paramiko
from misc import trc_mean

host = '220.149.87.248'
transport = paramiko.transport.Transport(host,22)
transport.connect(username = 'hod', password = 'gkrrhkwkd0690')

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
camera.resolution = (672, 512)
camera.framerate = 32
camera.brightness = 60
camera.contrast = 10
camera.sharpness = 50
camera.image_effect = 'colorpoint'

# camera.exposure_mode = 'nightpreview'
rawCapture = PiRGBArray(camera, size=(672, 512))
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
            
            # cv2.putText(img, "{0:0}\nwidth:{1:0} height:{2:0}\nrad:{3:0}".format(maxArea,bbox[2],bbox[3],radius), (bbox[0],bbox[1]-50), font, 1, (0,255,255))
            cv2.putText(img, "{0:0}".format(area), (bbox[0],bbox[1]), font, 1, (0,255,255))
            cv2.rectangle(img, (bbox[0],bbox[1]),(bbox[0]+bbox[2],bbox[1]+bbox[3]),(0,255,255),2)
            maxArea = area
    
    if maxArea>5000:
        return(img, maxArea, bbox[2], bbox[3], radius)
    else:
        return(img, None, None, None, None)


def DBwrite_atmos(cursor, brightness, temperature, humidity):
    cursor.execute("INSERT INTO `atmos.tab` (rack,floor,pipe,pot,brightness,temperature,humidity) VALUES (?,?,?,?,?,?,?)",
                  (RACK,FLOOR,PIPE,POT,brightness,temperature,humidity))
    
def DBwrite_growth(cursor, pixels, bx, by, radius,imgname):
    cursor.execute("INSERT INTO `growth.tab` (rack,floor,pipe,pot,pixels,bbx,bby,radius,imgfile) VALUES (?,?,?,?,?,?,?,?,?)",
                  (RACK,FLOOR,PIPE,POT,pixels,bx,by,radius,imgname))

def emptyGrowth():
    record1 = {'pixels':[], 'bx':[], 'by':[], 'radius':[]}
    return(record1)

def emptyAtmos():
    record1 = {'brightness':[], 'temperature':[], 'humidity':[]}
    return(record1)
    

SAMPLING = 50
now = time.time()
logcount = now
capcount = now
recGrowth = emptyGrowth()
recAtmos = emptyAtmos()
doOnce = True
while True:
    
    img, pixels, bx, by, radius = detectGreen(camera, rawCapture)
    recGrowth['pixels'].append(pixels)
    recGrowth['bx'].append(bx)
    recGrowth['by'].append(by)
    recGrowth['radius'].append(radius)

    lux = senseBH1750()
    hum, temp = Adafruit_DHT.read(Adafruit_DHT.DHT11, DHT_GPIO)
    recAtmos['brightness'].append(lux)
    recAtmos['temperature'].append(temp)
    recAtmos['humidity'].append(hum)

    if sys.argv[5] == 'show':
        writeOnImg(img, 'Light={0:0} lux'.format(lux), (50,50))
        if temp is not None:
            writeOnImg(img, 'Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(temp, hum), (50,100))
        else:
            writeOnImg(img, "Failed to read", (50,100))        
        cv2.imshow("Frame"+' '.join(sys.argv), img)
    else:
        print(pixels, temp, hum)

    now = time.time()
    if (now-capcount)>3600 or doOnce:
        imgpath = r'/home/pi/ssufarm/images'
        imgname = 'img_'+RACK+FLOOR+PIPE+POT+'_'+str(int(now*1000.0))+'.jpg'
        os.chdir(imgpath)
        cv2.imwrite(imgname, img)
        print('Saving image:', imgpath+'/'+imgname)
        imgurl = '/web/livfarm/'+imgname
        try:
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.put(imgpath+'/'+imgname, imgurl)
        finally:
            sftp.close()

        capcount = now
        doOnce = False
    
    now = time.time()
    # print(logcount)
    if (now-logcount)>60:
        print("Writing DB", len(recAtmos['temperature']))
        try:
            DBwrite_atmos(cur,trc_mean(recAtmos['brightness']), trc_mean(recAtmos['temperature']), trc_mean(recAtmos['humidity']))
            DBwrite_growth(cur,trc_mean(recGrowth['pixels']),trc_mean(recGrowth['bx']),trc_mean(recGrowth['by']),trc_mean(recGrowth['radius']),imgname)
        except Exception as e:
            print(f"Error: {e}")
            print(trc_mean(recAtmos['brightness']), trc_mean(recAtmos['temperature']), trc_mean(recAtmos['humidity']))
            print(trc_mean(recGrowth['pixels']),trc_mean(recGrowth['bx']),trc_mean(recGrowth['by']),trc_mean(recGrowth['radius']),imgname)
        if sys.argv[5] == 'show' or sys.argv[5] == 'commit':
            conn.commit()
        logcount = now
        recGrowth = emptyGrowth()
        recAtmos = emptyAtmos()

        
    time.sleep(0.1)        
    key = cv2.waitKey(1) & 0xFF
    
    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)

    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break

conn.close()
cv2.destroyAllWindows()    
transport.close()