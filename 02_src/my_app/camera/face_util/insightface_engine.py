import math
import numpy as np
import cv2
from pathlib import Path
from insightface.app import FaceAnalysis

MODEL_ROOT = Path(__file__).resolve().parent.parent.parent / "vendor" / "insightface_models"

class InsightFaceEngine:
    """
    使用InsightFace进行人脸检测并提取特征向量
    """
    def __init__(self, model_name = "buffalo_l", det_size = (320, 320)):
        self.app = FaceAnalysis(
            root=str(MODEL_ROOT),
            name = model_name,
            providers = ["CPUExecutionProvider"],
            allowed_modules = ["detection", "recognition"]
        )

        self.app.prepare(ctx_id = -1, det_size = tuple(det_size))

    def detect_faces(self, bgr_frame):
        if bgr_frame is None:
            return []

        return self.app.get(bgr_frame)

    @staticmethod
    def _normalize_embedding(embedding):
        vector = np.asarray(embedding, dtype = np.float32).reshape(-1)

        norm = float(np.linalg.norm(vector))

        if norm <= 0:
            raise ValueError("顔特徴量のノルム0000")

        return (vector / norm).astype(np.float32)

    def _convert_face(self, face):
        return {
            "embedding": self._normalize_embedding(face.normed_embedding),
            "bbox": np.asarray(face.bbox,dtype = np.float32),
            "det_score": float(face.det_score),
            "kps": (None if getattr(face, "kps", None) is None else np.asarray(face.kps, dtype = np.float32)),
            "pose": getattr(face, "pose", None)
        }

    def extract_one(self, bgr_frame):
        """
        仅检测到一人时返回人脸信息🐸
        """

        faces = self.detect_faces(bgr_frame)

        if len(faces) != 1:
            return None, {"reason": f"face_count={len(faces)}"}

        face = faces[0]
        return face["embedding"], {
            key: value
            for key, value in face.items()
            if key != "embedding"
        }

    def extract_many(self, bgr_frame):
        """
        画像からすべての顔とその特徴ベクトルを返します。
        """
        results = [
            self._convert_face(face)
            for face in self.detect_faces(bgr_frame)
        ]

        # 大きく写っている顔から処理する
        results.sort(
            key=lambda item: (
                item["bbox"][2] - item["bbox"][0]
            ) * (
                item["bbox"][3] - item["bbox"][1]
            ),
            reverse=True,
        )

        return results


    def check_registration_quality(self, image, face_info, config):
        height, width = image.shape[:2]
        x1, y1, x2, y2 = map(int, face_info["bbox"])

        x1 = max(0, min(x1, width - 1))
        x2 = max(0, min(x2, width))
        y1 = max(0, min(y1, height - 1))
        y2 = max(0, min(y2, height))

        if x2 <= x1 or y2 <= y1:
            return False, {"reason": "顔領域が空です"}

        face_image = image[y1:y2, x1:x2]

        if face_image.size == 0:
            return False, {"reason": "顔領域が空です"}

        gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)

        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        brightness = float(np.mean(gray))
        det_score = float(face_info["det_score"])
        face_width = x2 - x1
        face_height = y2 - y1

        roll_deg = 0.0
        keypoints = face_info.get("kps")

        if keypoints is not None and len(keypoints) >= 2:
            left_eye = keypoints[0]
            right_eye = keypoints[1]

            roll_deg = math.degrees(
                math.atan2(
                    float(right_eye[1] - left_eye[1]),
                    float(right_eye[0] - left_eye[0]),
                )
            )

        errors = []

        if det_score < float(config["registration_min_det_score"]):
            errors.append("顔検出の信頼度低すぎ😱")

        if min(face_width, face_height) < int(config["registration_min_face_px"]):
            errors.append("顔をカメラへ近づけて😡")

        if blur_score < float(config["registration_min_blur"]):
            errors.append("画像がぼやけてる😡")

        if brightness < float(config["registration_min_brightness"]):
            errors.append("顔が暗すぎ😱")

        if brightness > float(config["registration_max_brightness"]):
            errors.append("顔が明るすぎ😱")

        if abs(roll_deg) > float(config.get("registration_max_roll_deg",18.0,)):
            errors.append("顔の傾きが大きすぎ😱")

        return not errors, {
            "reason": " / ".join(errors) if errors else "ok",
            "det_score": det_score,
            "blur_score": blur_score,
            "brightness": brightness,
            "face_width": face_width,
            "face_height": face_height,
            "roll_deg": roll_deg,
        }

    @staticmethod
    def cosine_similarity(a, b):
        return float(np.dot(a, b))