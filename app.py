#import flask
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
# opencv
import cv2
import keras
import warnings
import time
import mediapipe as mp
import numpy as np
warnings.simplefilter(action='ignore', category=FutureWarning)


# buat instance flask
app = Flask(__name__, template_folder='./template')  # instantiate Flask


camera = cv2.VideoCapture(0)
model = keras.models.load_model("model/mobilenetV2_model2.h5")
background = None
accumulated_weight = 0.5
ROI_top = 100
ROI_bottom = 300
ROI_right = 150
ROI_left = 350
word_dict1 = {0: '1', 1: '2', 2: '3', 3: '4', 4: '5', 5: '6', 6: '7', 7: '8', 8: '9', 9: 'A', 10: 'B', 11: 'C', 12: 'D', 13: 'E', 14: 'F', 15: 'G', 16: 'H',
              17: 'I', 18: 'J', 19: 'K', 20: 'L', 21: 'M', 22: 'N', 23: 'O', 24: 'P', 25: 'Q', 26: 'R', 27: 'S', 28: 'T', 29: 'U', 30: 'V', 31: 'W', 32: 'X', 33: 'Y', 34: 'Z'}


@app.route('/')
def index():
    return render_template('index.html')


# def camera_max():
#     '''Returns int value of available camera devices connected to the host device'''
#     camera = 0
#     while True:
#         if (cv2.VideoCapture(camera).grab()):
#             camera = camera + 1
#         else:
#             cv2.destroyAllWindows()
#             return(max(0, int(camera-1)))


# cam_max = camera_max()

# cap = cv2.VideoCapture(cam_max, cv2.CAP_DSHOW)
# width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
# height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


# def mediapipe_detection(image, model):
#     # COLOR CONVERSION BGR 2 RGB
#     image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#     results = model.process(image)                 # Make prediction
#     # COLOR CONVERSION RGB 2 BGR
#     image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
#     return image, results


# def get_landmark_dist_test(results, x, y):
#     global width, height
#     hand_array = []
#     wrist_pos = results.multi_hand_landmarks[0].landmark[0]
#     for result in results.multi_hand_landmarks[0].landmark:
#         hand_array.append((result.x-wrist_pos.x) * (width/x))
#         hand_array.append((result.y-wrist_pos.y) * (height/y))
#     return(hand_array[2:])


# def start_model(frame):
#     global width, height
#     frame = cv2.resize(frame, (width, height))
#     image, results = mediapipe_detection(frame, model)
#     if results.multi_hand_landmarks[0].landmark:
#         hand_array = get_landmark_dist_test(results, width, height)
#         return hand_array
#     else:
#         return None

cam = cv2.VideoCapture(0)
num_frames = 0


def cal_accum_avg(frame, accumulated_weight):

    global background

    if background is None:
        background = frame.copy().astype("float")
        return None

    cv2.accumulateWeighted(frame, background, accumulated_weight)


def segment_hand(frame, threshold=25):
    global background

    diff = cv2.absdiff(background.astype("uint8"), frame)

    _, thresholded = cv2.threshold(diff, threshold, 255,
                                   cv2.THRESH_BINARY)

    # Fetching contours in the frame (These contours can be of handor any other object in foreground) …

    contours, hierarchy = cv2.findContours(
        thresholded.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # If length of contours list = 0, means we didn't get anycontours...
    if len(contours) == 0:
        return None
    else:
        # The largest external contour should be the hand
        hand_segment_max_cont = max(contours, key=cv2.contourArea)

        # Returning the hand segment(max contour) and thethresholded image of hand...
        return (thresholded, hand_segment_max_cont)


def start_model(frame):
    while True:
        ret, frame = cam.read()
        frame = cv2.flip(frame, 1)
        frame_copy = frame.copy()

        # ROI
        roi = frame[ROI_top:ROI_bottom, ROI_left:ROI_right]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        if num_frames < 70:
            cal_accum_avg(gray, accumulated_weight)

            cv2.putText(frame_copy, "FETCHING BACKGROUND...PLEASE WAIT",
                        (80, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

        else:
            hand = segment_hand(gray)
            if hand is not None:
                thresholded, hand_segment = hand

                # Drawing contours around hand segment
                cv2.drawContours(frame_copy, [hand_segment + (ROI_right,
                                                              ROI_top)], -1, (255, 0, 0), 1)
                cv2.imshow("Thresholded", thresholded)
                thresholded = cv2.resize(thresholded, (160, 160))
                thresholded = cv2.cvtColor(thresholded, cv2.COLOR_BGR2GRAY)
                thresholded = np.reshape(
                    thresholded, ((1, thresholded.shape[0], thresholded.shape[1], 3)))

                pred = model.predict(thresholded)
                cv2.putText(frame_copy, word_dict1[np.argmax(pred)],
                            (170, 45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # draw roi
        cv2.rectangle(frame_copy, (ROI_left, ROI_top),
                      (ROI_right, ROI_bottom), (255, 128, 0), 3)
        num_frames += 1

        # display frame
        cv2.putText(frame_copy, "DataFlair hand sign recognition_ _ _",
                    (50, 50), cv2.FONT_ITALIC, 0.5, (51, 255, 51), 1)
        cv2.imshow("Sign Detection", frame_copy)


def gen_frames():
    while True:
        success, frame = camera.read()  # read the camera frame
        if success:
            frame = start_model(frame)
        try:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            pass


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(debug=True)
