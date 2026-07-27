import cv2
import numpy as np


class LivenessGate:
    """
    本物の顔かどうか確認する
    """
    def __init__(self, config):
        self.ir_min_mean = float(config["ir_min_mean"])
        self.ir_min_face_mean = float(config["ir_min_face_mean"])
        self.ir_min_face_std = float(config.get("ir_min_face_std", 5.0))
        self.ir_min_abs_contrast = float(config.get("ir_min_abs_contrast", 2.0))
        self.background_padding_ratio = float(config.get("ir_background_padding_ratio", 0.25))

        homography = config.get("rgb_to_ir_homography_normalized")

        if homography is None:
            homography = np.eye(3, dtype=np.float32)

        self.homography = np.asarray(homography, dtype=np.float32)

        if self.homography.shape != (3, 3):
            raise ValueError("rgb_to_ir_homography_normalizedは3x3")

        if not np.isfinite(self.homography).all():
            raise ValueError("RGB・IR変換行列に異常値があり")

    def _map_bbox(self, bbox, rgb_shape, ir_shape):
        rgb_height, rgb_width = rgb_shape[:2]
        ir_height, ir_width = ir_shape[:2]

        x1, y1, x2, y2 = map(float, bbox)

        points = np.asarray(
            [
                [x1 / rgb_width, y1 / rgb_height],
                [x2 / rgb_width, y1 / rgb_height],
                [x2 / rgb_width, y2 / rgb_height],
                [x1 / rgb_width, y2 / rgb_height],
            ],
            dtype = np.float32,
        ).reshape(1, 4, 2)

        mapped = cv2.perspectiveTransform(
            points,
            self.homography,
        )[0]

        mapped[:, 0] *= ir_width
        mapped[:, 1] *= ir_height

        ir_x1 = int(np.floor(mapped[:, 0].min()))
        ir_y1 = int(np.floor(mapped[:, 1].min()))
        ir_x2 = int(np.ceil(mapped[:, 0].max()))
        ir_y2 = int(np.ceil(mapped[:, 1].max()))

        ir_x1 = max(0, min(ir_x1, ir_width - 1))
        ir_x2 = max(0, min(ir_x2, ir_width))
        ir_y1 = max(0, min(ir_y1, ir_height - 1))
        ir_y2 = max(0, min(ir_y2, ir_height))

        return ir_x1, ir_y1, ir_x2, ir_y2

    def _background_values(self, gray, bbox):
        x1, y1, x2, y2 = bbox
        height, width = gray.shape[:2]

        face_width = max(1, x2 - x1)
        face_height = max(1, y2 - y1)

        padding_x = max(2, int(face_width * self.background_padding_ratio))
        padding_y = max(2, int(face_height * self.background_padding_ratio))

        outer_x1 = max(0, x1 - padding_x)
        outer_y1 = max(0, y1 - padding_y)
        outer_x2 = min(width, x2 + padding_x)
        outer_y2 = min(height, y2 + padding_y)

        outer = gray[outer_y1:outer_y2, outer_x1:outer_x2]

        if outer.size == 0:
            return np.empty(0, dtype=np.uint8)

        mask = np.ones(outer.shape, dtype=bool)

        local_x1 = x1 - outer_x1
        local_y1 = y1 - outer_y1
        local_x2 = x2 - outer_x1
        local_y2 = y2 - outer_y1

        mask[local_y1:local_y2, local_x1:local_x2] = False

        return outer[mask]

    def check_ir_response(self, ir_frame, bbox, rgb_shape):
        """
        RGB画像で検出された顔の位置にIR反応があるかどうか確認する
        """
        if ir_frame is None:
            return False, {"reason": "ir_frame_missing"}

        if ir_frame.ndim == 3:
            gray = cv2.cvtColor(ir_frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = ir_frame

        frame_mean = float(np.mean(gray))

        if frame_mean < self.ir_min_mean:
            return False, {
                "reason": "ir_frame_too_dark",
                "frame_mean": frame_mean
            }

        mapped_bbox = self._map_bbox(bbox = bbox, rgb_shape = rgb_shape, ir_shape = gray.shape)

        x1, y1, x2, y2 = mapped_bbox

        if x2 <= x1 or y2 <= y1:
            return False, {
                "reason": "invalid_ir_face_bbox",
                "frame_mean": frame_mean,
                "mapped_bbox": mapped_bbox
            }

        face_roi = gray[y1:y2, x1:x2]

        if face_roi.size == 0:
            return False, {
                "reason": "empty_ir_face_roi",
                "frame_mean": frame_mean,
                "mapped_bbox": mapped_bbox
            }

        face_mean = float(np.mean(face_roi))
        face_std = float(np.std(face_roi))

        background_values = self._background_values(gray, mapped_bbox)

        if background_values.size > 0:
            background_mean = float(np.mean(background_values))
        else:
            background_mean = frame_mean

        absolute_contrast = abs(face_mean - background_mean)

        information = {
            "reason": "ir_response_ok",
            "frame_mean": frame_mean,
            "face_mean": face_mean,
            "face_std": face_std,
            "background_mean": background_mean,
            "absolute_contrast": absolute_contrast,
            "mapped_bbox": mapped_bbox
        }

        if face_mean < self.ir_min_face_mean:
            information["reason"] = "face_ir_too_dark"
            return False, information

        if face_std < self.ir_min_face_std:
            information["reason"] = "face_ir_low_variance"
            return False, information

        if absolute_contrast < self.ir_min_abs_contrast:
            information["reason"] = "face_ir_low_contrast"
            return False, information

        return True, information