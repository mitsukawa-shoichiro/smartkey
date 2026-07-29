import cv2
import numpy as np
import mediapipe as mp
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

LEFT_EYE  = [362, 385, 387, 263, 373, 380]#左目の位置を指定
RIGHT_EYE = [33,  160, 158, 133, 153, 144]#右目の位置を指定

EAR_THRESHOLD = 0.15 #どこまで閉じたら瞬きとするかの閾値
BLINK_REQUIRED = 2 #必要な瞬き回数
BLINK_FRAMES = 3 #目を閉じている時間の指定

"""
openのところにもともと登録してある顔の特徴量(エンコーディング済み)を入れておいてください(パスとかも変えないと動かないと思います)
カメラから画像をとってきて瞬きを二回連続で検知してから登録してある顔と似てるか判別してコンソールに出します。
瞬きの回数もコンソールにリアルタイムで出ます
瞬きの時間が長すぎると判断された場合はリセットがかかります
"""

def calculate_ear(landmarks, eye_indices, img_w, img_h):
    points = [(int(landmarks[i].x * img_w), int(landmarks[i].y * img_h)) for i in eye_indices]
    v1 = np.linalg.norm(np.array(points[1]) - np.array(points[5]))
    v2 = np.linalg.norm(np.array(points[2]) - np.array(points[4]))
    h  = np.linalg.norm(np.array(points[0]) - np.array(points[3]))
    if h == 0:
        return 0
    return (v1 + v2) / (2.0 * h)

class BlinkDetector:
    def __init__(self):
        self.blink_count = 0
        self.blink_frame_count = 0
        self.liveness_until = 0

        base_options = python.BaseOptions(
            model_asset_path = "face_landmarker.task"
        )
        options = vision.FaceLandmarkerOptions(
            base_options = base_options,
            num_faces = 1
        )
        self.landmarker = vision.FaceLandmarker.create_from_options(options)

        
    def detect(self,frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.landmarker.detect(mp_image)
    
        if result.face_landmarks:
            landmarks = result.face_landmarks[0]
            h, w, _ = frame.shape
            left_ear  = calculate_ear(landmarks, LEFT_EYE, w, h)
            right_ear = calculate_ear(landmarks, RIGHT_EYE, w, h)
            ear = (left_ear + right_ear) / 2.0

            if ear < EAR_THRESHOLD:
                self.blink_frame_count += 1
            elif self.blink_frame_count > 0 and self.blink_frame_count <= BLINK_FRAMES:
                self.blink_count += 1
                self.blink_frame_count = 0
                print(f"瞬き検出: {self.blink_count}回")
            
            elif self.blink_frame_count > BLINK_FRAMES:
                print("長時間検出のためリセット")
                self.blink_frame_count = 0
        if self.blink_count >= BLINK_REQUIRED:
            self.liveness_until = time.time() + 3
            self.blink_count = 0
            self.blink_frame_count = 0
        return time.time() < self.liveness_until
