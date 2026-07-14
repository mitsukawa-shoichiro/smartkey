import cv2
import numpy as np


class LivenessGate:
    """
    确认是否为真实人脸
    """
    def __init__(self, ir_min_mean = 25, ir_min_face_mean = 35):
        self.ir_min_mean = ir_min_mean
        self.ir_min_face_mean = ir_min_face_mean

    def check_ir_response(self, ir_frame, bbox, rgb_shape):
        """
        确认在RGB图像中检测到的人脸位置是否存在IR响应
        """
        if ir_frame is None:
            return False, "ir_frame_missing"
        
        # 转换为灰度图像
        if len(ir_frame.shape) == 3:
            gray = cv2.cvtColor(ir_frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = ir_frame
        
        frame_mean = float(np.mean(gray))
        if frame_mean < self.ir_min_mean:
            return False, f"ir_too_dark = {frame_mean:.1f}"
        
        rgb_h, rgb_w = rgb_shape[:2]
        ir_h, ir_w = gray.shape[:2]

        # 当RGB和IR的分辨率不同时, 对坐标进行缩放
        scale_x = ir_w / rgb_w
        scale_y = ir_h / rgb_h

        x1, y1, x2, y2 = [float(value) for value in bbox]
        x1 = int(x1 * scale_x)
        x2 = int(x2 * scale_x)
        y1 = int(y1 * scale_y)
        y2 = int(y2 * scale_y)

        x1 = max(0, min(x1, ir_w - 1))
        x2 = max(0, min(x2, ir_w))
        y1 = max(0, min(y1, ir_h - 1))
        y2 = max(0, min(y2, ir_h))

        face_roi = gray[y1:y2, x1:x2]

        if face_roi.size == 0:
            return False, "empty_ir_face_roi"

        face_mean = float(np.mean(face_roi))
        face_std = float(np.std(face_roi))

        if face_mean < self.ir_min_face_mean:
            return False, f"face_ir_too_dark={face_mean:.1f}"

        # 通过辅助判定排除全黑或接近纯色的异常输入
        if face_std < 5.0:
            return False, f"face_ir_low_variance={face_std:.1f}"

        return True, "ir_response_ok"