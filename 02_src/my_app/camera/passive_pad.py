import sys
from pathlib import Path

import numpy as np

APP_ROOT = Path(__file__).resolve().parent.parent
PAD_REPOSITORY = (
    APP_ROOT / "vendor" / "Silent-Face-Anti-Spoofing"
)
PAD_MODEL_DIRECTORY = (
    PAD_REPOSITORY / "resources" / "anti_spoof_models"
)


class PassivePad:
    def __init__(self, threshold = 0.80):
        if not PAD_REPOSITORY.is_dir():
            raise FileNotFoundError(
                f"PADリポジトリないよ～ {PAD_REPOSITORY}"
            )
        
        if not PAD_MODEL_DIRECTORY.is_dir():
            raise FileNotFoundError(
                f"PADモデルないよ～ {PAD_MODEL_DIRECTORY}"
            )
        
        repository_path = str(PAD_REPOSITORY)

        if repository_path not in sys.path:
            sys.path.insert(0, repository_path)

        from src.anti_spoof_predict import AntiSpoofPredict
        from src.generate_patches import CropImage
        from src.utility import parse_model_name

        self.predictor = AntiSpoofPredict(device_id = 0)
        self.cropper = CropImage()
        self.parse_model_name = parse_model_name
        self.threshold = float(threshold)

        self.model_paths = sorted(
            PAD_MODEL_DIRECTORY.glob("*.pth")
        )

        if not self.model_paths:
            raise FileNotFoundError(
                f"PADモデルないよ～ {PAD_MODEL_DIRECTORY}"
            )
        
    def check(self, bgr_frame, bbox):
        if bgr_frame is None:
            raise ValueError("RGBふれーむなしなし")
        
        x1, y1, x2, y2 = [int(value) for value in bbox]

        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        face_bbox = [x1, y1, width, height]

        prediction = np.zeros((1, 3), dtype = np.float32)

        for model_path in self.model_paths:
            input_height, input_width, _, scale = (
                self.parse_model_name(model_path.name)
            )

            crop_parameters = {
                "org_img": bgr_frame,
                "bbox": face_bbox,
                "scale": scale,
                "out_w": input_width,
                "out_h": input_height,
                "crop": True
            }

            if scale is None:
                crop_parameters["crop"] = False

            face_crop = self.cropper.crop(**crop_parameters)

            prediction += self.predictor.predict(
                face_crop,
                str(model_path)
            )

        prediction /= len(self.model_paths)

        predicted_label = int(np.argmax(prediction))
        live_score = float(prediction[0][1])

        is_live = (
            predicted_label == 1
            and live_score >= self.threshold
        )

        return is_live, {
            "label": predicted_label,
            "live_score": live_score,
            "threshold": self.threshold
        }