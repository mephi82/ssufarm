#import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera
import os, time
import cv2

def detect(img, cascade):
    rects = cascade.detectMultiScale(img, scaleFactor=1.3, minNeighbors=4,minSize=(30,30),flags=cv2.CASCADE_SCALE_IMAGE)
    if len(rects)==0:
        return []
    rects[:, 2:] += rects[:, :2]
    return rects

def draw_rects(img, rects, color):
    for x1, y1, x2, y2 in rects:
        cv2.rectangle(img, (x1,y1), (x2,y2), color, 2)

 # initialize the camera and grab a reference to the raw camera capture
cv2_dir = os.path.dirname(os.path.abspath(cv2.__file__))
haar_model = os.path.join(cv2_dir, 'data/haarcascade_frontalface_default.xml')

camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 32
rawCapture = PiRGBArray(camera, size=(640, 480))
cascade = cv2.CascadeClassifier(haar_model)
# allow the camera to warmup
time.sleep(0.1)


# capture frames from the camera

for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
# grab the raw NumPy array representing the image, then initialize the timestamp
# and occupied/unoccupied text
        img = frame.array
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        rects = detect(gray, cascade)
        vis = img.copy()
        draw_rects(vis, rects, (0,255,0))
        # show the frame
        
        cv2.imshow("Frame", vis)
        key = cv2.waitKey(1) & 0xFF

        # clear the stream in preparation for the next frame
        rawCapture.truncate(0)

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
                break