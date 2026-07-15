import re
import time
import cv2
import numpy as np
from pathlib import Path

from my_app.camera.face_util.insightface_engine import InsightFaceEngine
from my_app.camera.liveness_gate import LivenessGate

import logging
from collections import deque

from my_app.camera.passive_pad import PassivePad

logger = logging.getLogger(__name__)

class FaceAuthenticator:
    """
    整合活体检测, 人脸识别和连续成功判定
    """
    def __init__(self, face_dir, config):
        self.engine = InsightFaceEngine()

        self.liveness = LivenessGate(
            ir_min_mean = config["ir_min_mean"],
            ir_min_face_mean = config["ir_min_face_mean"],
        )

        self.face_dir = Path(face_dir)
        self.similarity_threshold = config["similarity_threshold"]
        self.margin_threshold = config["margin_threshold"]
        self.required_success_frames = config["required_success_frames"]
        self.unlock_cooldown_sec = config["unlock_cooldown_sec"]

        self.passive_pad = PassivePad(threshold = config["pad_threshold"])
        self.pad_window_size = int(config["pad_window_size"])
        self.pad_required_passes = int(config["pad_required_passes"])
        
        if self.pad_required_passes > self.pad_window_size:
            raise ValueError(
                "pad_required_passes は pad_window_size以下！！"
            )
        
        self.pad_results = deque(maxlen = self.pad_window_size)

        self.current_name = None
        self.current_count = 0
        self.last_unlock_name = None
        self.last_unlock_at = 0

        # 从注册图像中提取每个人的特征向量
        self.known_embeddings = self.load_known_embeddings()
    
    def load_known_embeddings(self):
        """
        读取FaceLib中以 姓名_xxx.jpg 格式命名的图像
        """
        grouped_embeddings = {}

        self.face_dir.mkdir(parents = True, exist_ok = True)

        image_paths = []
        for pattern in ("*.jpg", "*.jpeg", "*.png"):
            image_paths.extend(self.face_dir.glob(pattern))

        for image_path in image_paths:
            # 去除末尾的 _001 等编号
            name = re.sub(r"_\d+$", "", image_path.stem)

            image = cv2.imread(str(image_path))
            if image is None:
                print(f"😾 登録画像よみこめない: {image_path}")
                continue

            embedding, info = self.engine.extract_one(image)
            if embedding is None:
                print(f"😾 登録画像から顔わからん: {image_path}, {info}")
                continue

            grouped_embeddings.setdefault(name, []).append(embedding)

        known_embeddings = []

        for name, embeddings in grouped_embeddings.items():
            # 对同一人的多张图像特征取平均值
            centroid = np.mean(np.stack(embeddings), axis = 0)
            norm = np.linalg.norm(centroid)

            if norm <= 0:
                continue

            centroid = (centroid / norm).astype(np.float32)

            known_embeddings.append({
                "name": name,
                "embedding": centroid,
                "image_count": len(embeddings)
            })

        print(f"顔の特徴量よんだ: {len(known_embeddings)}")
        return known_embeddings

    def authenticate(self, rgb_frame, ir_frame):
        """
        认证成功则返回姓名, 失败则返回None
        """
        embedding, face_info = self.engine.extract_one(rgb_frame)

        if embedding is None:
            self._reset()
            return None, face_info
        
        # RGB座標をIR画像用に変換
        ok, reason = self.liveness.check_ir_response(
            ir_frame = ir_frame,
            bbox = face_info["bbox"],
            rgb_shape = rgb_frame.shape
        )

        if not ok:
            self._reset()
            return None, {"reason": reason}
        
        name, score, margin = self._match(embedding)

        if name is None:
            self._reset()
            return None, {
                "reason": "not_matched",
                "score": score,
                "margin": margin,
            }
        
        try:
            is_live, pad_info = self.passive_pad.check(
                rgb_frame,
                face_info["bbox"]
            )
        except Exception:
            logger.exception("PADモデル推論むり")
            self._reset()
            return None, {
                "reason": "pad_error"
            }

        # 仅当同一人物连续认证成功时才通过
        if self.current_name == name:
            self.current_count += 1
        else:
            self.current_name = name
            self.current_count = 1
            self.pad_results.clear()

        self.pad_results.append(is_live)

        if len(self.pad_results) < self.pad_window_size:
            return None, {
                "reason": "need_more_frames",
                "name": name,
                "count": len(self.pad_results),
                "required": self.pad_window_size,
                "score": score,
                "pad_score": pad_info["live_score"]
            }
        
        pad_pass_count = sum(self.pad_results)

        if pad_pass_count < self.pad_required_passes:
            result = {
                "reason": "spoof_detected",
                "name": name,
                "pad_pass_count": pad_pass_count,
                "pad_required_passes": self.pad_required_passes,
                "pad_score": pad_info["live_score"]
            }

            self._reset()
            return None, result

        if self.current_count < self.required_success_frames:
            return None, {
                "reason": "need_more_frames",
                "name": name,
                "count": self.current_count,
                "required": self.required_success_frames,
                "score": score,
            }

        now = time.monotonic()

        # 防止同一人连续解锁
        if (
            self.last_unlock_name == name
            and now - self.last_unlock_at < self.unlock_cooldown_sec
        ):
            self._reset()
            return None, {"reason": "cooldown", "name": name}

        self.last_unlock_name = name
        self.last_unlock_at = now
        self._reset()

        return name, {
            "reason": "authenticated",
            "score": score,
            "margin": margin,
        }

    def _match(self, embedding):
        """
        与已注册的Embedding进行比较
        """
        if not self.known_embeddings:
            return None, 0.0, 0.0

        scores = [
            (
                item["name"],
                float(np.dot(embedding, item["embedding"]))
            )
            for item in self.known_embeddings
        ]

        scores.sort(key=lambda x: x[1], reverse=True)

        best_name, best_score = scores[0]
        second_score = scores[1][1] if len(scores) > 1 else 0.0
        margin = best_score - second_score

        if best_score < self.similarity_threshold:
            return None, best_score, margin

        if len(scores) > 1 and margin < self.margin_threshold:
            return None, best_score, margin

        return best_name, best_score, margin

    def _reset(self):
        self.current_name = None
        self.current_count = 0
        self.pad_results.clear()
