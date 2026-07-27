import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort


APP_ROOT = Path(__file__).resolve().parent.parent
PAD_REPOSITORY = (
    APP_ROOT / "vendor" / "Silent-Face-Anti-Spoofing"
)
PAD_MODEL_DIRECTORY = (
    PAD_REPOSITORY / "resources" / "anti_spoof_models"
)


class PassivePad:
    def __init__(self, threshold=0.80):
        if not PAD_REPOSITORY.is_dir():
            raise FileNotFoundError(f"PADリポジトリないよ～ {PAD_REPOSITORY}")

        if not PAD_MODEL_DIRECTORY.is_dir():
            raise FileNotFoundError(f"PADモデルないよ～ {PAD_MODEL_DIRECTORY}")

        repository_path = str(PAD_REPOSITORY)

        if repository_path not in sys.path:
            sys.path.insert(0, repository_path)

        from src.generate_patches import CropImage
        from src.utility import parse_model_name

        self.cropper = CropImage()
        self.parse_model_name = parse_model_name
        self.threshold = float(threshold)

        self.model_paths = sorted(PAD_MODEL_DIRECTORY.glob("*.onnx"))

        if not self.model_paths:
            raise FileNotFoundError(f"PADモデルないよ～ {PAD_MODEL_DIRECTORY}")

        # ONNXモデルは起動時に一度だけ読み込まれます
        self.models = []

        for model_path in self.model_paths:
            # 元の関数は.pthファイル名を使うことを想定していたので、拡張子を.pthに戻しただけだよ
            pth_name = model_path.with_suffix(".pth").name
            input_height, input_width, _, scale = (self.parse_model_name(pth_name))

            session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])

            input_info = session.get_inputs()[0]
            output_info = session.get_outputs()[0]

            self.models.append({
                "path": model_path,
                "session": session,
                "input_name": input_info.name,
                "output_name": output_info.name,
                "input_height": input_height,
                "input_width": input_width,
                "scale": scale,
            })

    def check(self, bgr_frame, bbox):
        if bgr_frame is None:
            raise ValueError("RGBふれーむなしなし")

        x1, y1, x2, y2 = [int(value) for value in bbox]

        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        face_bbox = [x1, y1, width, height]

        prediction = np.zeros((1, 3), dtype=np.float32)

        for model in self.models:
            crop_parameters = {
                "org_img": bgr_frame,
                "bbox": face_bbox,
                "scale": model["scale"],
                "out_w": model["input_width"],
                "out_h": model["input_height"],
                "crop": model["scale"] is not None,
            }

            face_crop = self.cropper.crop(**crop_parameters)

            # 元のToTensorと同じで、BGR形式を保ったままfloat32に変換する
            input_tensor = np.ascontiguousarray(face_crop.transpose(2, 0, 1)[None, ...], dtype = np.float32)

            model_prediction = model["session"].run([model["output_name"]],{model["input_name"]: input_tensor},)[0]

            if model_prediction.shape != (1, 3):
                raise ValueError(f"PAD出力サイズがおかしい {model['path'].name}, {model_prediction.shape}")

            if not np.isfinite(model_prediction).all():
                raise ValueError(f"PAD出力に異常値 {model['path'].name}")

            prediction += model_prediction

        prediction /= len(self.models)

        predicted_label = int(np.argmax(prediction, axis=1)[0])
        live_score = float(prediction[0][1])

        is_live = (predicted_label == 1 and live_score >= self.threshold)

        return is_live, {
            "label": predicted_label,
            "live_score": live_score,
            "threshold": self.threshold,
            "model_count": len(self.models),
        }