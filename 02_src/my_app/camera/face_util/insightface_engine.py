import numpy as np
from insightface.app import FaceAnalysis


class InsightFaceEngine:
    """
    使用InsightFace进行人脸检测并提取特征向量
    """
    def __init__(self, model_name="buffalo_l"):
        self.app = FaceAnalysis(
            name = model_name,
            providers = ["CPUExecutionProvider"],
        )

        self.app.prepare(ctx_id = -1, det_size = (640, 640))

    def extract_one(self, bgr_frame):
        """
        仅检测到一人时返回人脸信息🐸
        """
        faces = self.app.get(bgr_frame)

        if len(faces) != 1:
            return None, {"reason": f"face_count={len(faces)}"}
        
        face = faces[0]

        # 用于比较
        emb = np.asarray(face.normed_embedding, dtype=np.float32)

        return emb, {
            "bbox": face.bbox,
            "det_score": float(face.det_score),
            "pose": getattr(face, "pose", None),
        }
    
    @staticmethod
    def cosine_similarity(a, b):
        return float(np.dot(a, b))