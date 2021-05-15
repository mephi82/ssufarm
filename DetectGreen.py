from picamera.array import PiRGBArray
from picamera import PiCamera
import os, time
import cv2
import numpy as np
import RPi.GPIO as GPIO
import smbus

import sys
import Adafruit_DHT

# def detect(img, cascade):
#     rects = cascade.detectMultiScale(img, scaleFactor=1.3, minNeighbors=4,minSize=(30,30),flags=cv2.CASCADE_SCALE_IMAGE)
#     if len(rects)==0:
#         return []
#     rects[:, 2:] += rects[:, :2]
#     return rects
# 
# def draw_rects(img, rects, color):
#     for x1, y1, x2, y2 in rects:
#         cv2.rectangle(img, (x1,y1), (x2,y2), color, 2)
# Lux sensor BH1750
I2C_CH = 1
BH_DEV_ADDR = 0x23
i2c = smbus.SMBus(I2C_CH)
CONT_H_RES = 0x10
ONETIME_H_RES = 0x20

 # initialize the camera and grab a reference to the raw camera capture
cv2_dir = os.path.dirname(os.path.abspath(cv2.__file__))
haar_model = os.path.join(cv2_dir, 'data/haarcascade_frontalface_default.xml')

camera = PiCamera()
camera.resolution = (1024, 768)
# camera.resolution = (1440, 1080)
camera.framerate = 32
rawCapture = PiRGBArray(camera, size=(1024, 768))
# rawCapture = PiRGBArray(camera, size=(1440, 1080))
font = cv2.FONT_HERSHEY_SIMPLEX

# cascade = cv2.CascadeClassifier(haar_model)
# allow the camera to warmup
time.sleep(0.1)

def writeOnImg(img, text, origin):
    cv2.putText(img, text, origin, font, 1, (255,255,0))

def senseDHT():
    humidity, temperature = Adafruit_DHT.read(Adafruit_DHT.DHT11, '4')
    if temperature is not None:
        return('Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(temperature, humidity))
    else:
        return('Fail to read DHT')
def senseBH1750():
    luxBytes = i2c.read_i2c_block_data(BH_DEV_ADDR, CONT_H_RES, 2)
    lux = int.from_bytes(luxBytes, byteorder = 'big')
    return('Light={0:0}  lux'.format(lux))

def rc_time(pin_to_circuit):
    count = 0
  
    #Output on the pin for 
    GPIO.setup(pin_to_circuit, GPIO.OUT)
    GPIO.output(pin_to_circuit, GPIO.LOW)
#     time.sleep(0.1)
    time.sleep(0.5)

    #Change the pin back to input
    GPIO.setup(pin_to_circuit, GPIO.IN)
  
    #Count until the pin goes high
    while (GPIO.input(pin_to_circuit) == GPIO.LOW):
        count += 1

    return count

def senseLight(pin_to_circuit):
    GPIO.setmode(GPIO.BOARD)
    return('Light={0:0.1f}'.format(rc_time(pin_to_circuit)))


def detectGreen(camera, rawCapture):
    camera.capture(rawCapture, format="bgr", use_video_port=True)
    img = rawCapture.array
#     cv2.imshow("Frame", img)
#     key = cv2.waitKey(1) & 0xFF
# 
#     # clear the stream in preparation for the next frame
#     rawCapture.truncate(0)
# 
#     # if the `q` key was pressed, break from the loop
#     if key == ord("q"):
#             break
# 
# 
# # for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
# # # grab the raw NumPy array representing the image, then initialize the timestamp
# # # and occupied/unoccupied text
# #         img = frame.array
        
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
#         gray = cv2.equalizeHist(gray)
    lower_green = np.array([25,52,10])
    upper_green = np.array([102,255,255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
#         green = cv2.bitwise_and(img, img, mask = mask)
    
    kernel = np.ones((5,5), 'int')
    dilated = cv2.dilate(mask, kernel)
    
    res = cv2.bitwise_and(img, img, mask = dilated)
    
    ret, threshold = cv2.threshold(cv2.cvtColor(res, cv2.COLOR_BGR2GRAY), 3,255,cv2.THRESH_BINARY)
    contours, hier = cv2.findContours(threshold, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
#         res = cv2.bitwise_and(frame, framecv2, mask = mask)
    maxArea = 5000
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > maxArea:
            cv2.drawContours(img, [cnt], 0, (0,255,0), 1)
            contpoly = cv2.approxPolyDP(cnt, 3, True)
            bbox = cv2.boundingRect(contpoly)
            
            cv2.putText(img, str(area), (bbox[0],bbox[1]), font, 1, (0,255,255))
            cv2.rectangle(img, (bbox[0],bbox[1]),(bbox[0]+bbox[2],bbox[1]+bbox[3]),(0,255,255),2)
            maxArea = area
    
    return(img)


while True:
    
    img = detectGreen(camera, rawCapture)
    writeOnImg(img, senseBH1750(), (50,50))
    time.sleep(0.5)
    writeOnImg(img, senseDHT(),(50,100))
    cv2.imshow("Frame", img)
    key = cv2.waitKey(1) & 0xFF

    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)

    # if the `q` key was pressed, break from the loop
    if key == ord("q"):
        break

cv2.destroyAllWindows()    
