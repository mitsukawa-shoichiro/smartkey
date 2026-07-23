import json
import traceback
import sys
import time
import warnings
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


SRC_DIR = Path(__file__).resolve().parent
APP_DIR = SRC_DIR / "my_app"

sys.path.insert(0, str(SRC_DIR))

from my_app.camera.camera_config import load_rgb_camera_index
from my_app.camera.face_authenticator import FaceAuthenticator
from my_app.camera.media_foundation_ir import MediaFoundationIRCamera


CONFIG_PATH = APP_DIR / "config" / "face_auth.json"
FACE_DIR = APP_DIR / "db" / "FaceLib"

RGB_WINDOW = "SmartKey Full Authentication Debug - RGB"
IR_WINDOW = "SmartKey Full Authentication Debug - IR"

USE_DEBUG_IR_THRESHOLDS = False
DEBUG_IR_MIN_MEAN = 5.0
DEBUG_IR_MIN_FACE_MEAN = 8.0

warnings.filterwarnings(
    "ignore",
    message="`estimate` is deprecated.*",
    category=FutureWarning,
)


def load_font(size=18):
    for path in (
        Path(r"C:\Windows\Fonts\meiryo.ttc"),
        Path(r"C:\Windows\Fonts\msgothic.ttc"),
    ):
        if path.is_file():
            return ImageFont.truetype(
                str(path),
                size,
            )

    return ImageFont.load_default()


FONT = load_font()


def draw_panel(frame, lines):
    rgb_frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2RGB,
    )

    image = Image.fromarray(rgb_frame)
    draw = ImageDraw.Draw(image)

    line_height = 25
    panel_width = min(
        image.width - 16,
        1050,
    )
    panel_height = min(
        image.height - 16,
        16 + line_height * len(lines),
    )

    draw.rectangle(
        (
            8,
            8,
            8 + panel_width,
            8 + panel_height,
        ),
        fill=(15, 18, 22),
    )

    y = 14

    for text, color in lines:
        if y + line_height > panel_height:
            break

        draw.text(
            (18, y),
            text,
            font=FONT,
            fill=color,
        )
        y += line_height

    return cv2.cvtColor(
        np.asarray(image),
        cv2.COLOR_RGB2BGR,
    )


def resize_for_display(
    frame,
    max_width=1280,
    max_height=800,
):
    height, width = frame.shape[:2]

    scale = min(
        max_width / width,
        max_height / height,
        1.0,
    )

    if scale >= 1.0:
        return frame

    return cv2.resize(
        frame,
        (
            int(width * scale),
            int(height * scale),
        ),
        interpolation=cv2.INTER_AREA,
    )


def open_rgb_camera(camera_index):
    capture = cv2.VideoCapture(
        camera_index,
        cv2.CAP_DSHOW,
    )

    if not capture.isOpened():
        capture.release()

        capture = cv2.VideoCapture(
            camera_index,
            cv2.CAP_MSMF,
        )

    if not capture.isOpened():
        capture.release()
        raise RuntimeError(
            "RGBカメラを開けません: "
            f"index={camera_index}"
        )

    capture.set(
        cv2.CAP_PROP_BUFFERSIZE,
        1,
    )

    return capture


def result_color(reason):
    if reason == "authenticated":
        return (0, 200, 0)

    if reason == "need_more_frames":
        return (0, 220, 255)

    if reason == "cooldown":
        return (180, 180, 180)

    return (0, 0, 255)


def main():
    with CONFIG_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        config = json.load(file)

    if USE_DEBUG_IR_THRESHOLDS:
        config["ir_min_mean"] = (
            DEBUG_IR_MIN_MEAN
        )
        config["ir_min_face_mean"] = (
            DEBUG_IR_MIN_FACE_MEAN
        )

    rgb_capture = None
    ir_capture = None

    try:
        print("=" * 60)
        print("フル顔認証デバッグ")
        print("このプログラムは絶対に解錠処理を呼びません")
        print("=" * 60)

        authenticator = FaceAuthenticator(
            face_dir=FACE_DIR,
            config=config,
        )

        print(
            "登録人数:",
            len(authenticator.user_names),
        )
        print(
            "登録テンプレート数:",
            len(authenticator.template_records),
        )

        rgb_capture = open_rgb_camera(
            load_rgb_camera_index()
        )

        ir_capture = MediaFoundationIRCamera(
            device_id_contains=str(
                config["ir_device_id_contains"]
            ),
            startup_timeout=float(
                config.get(
                    "ir_startup_timeout_sec",
                    5.0,
                )
            ),
            max_age_ms=float(
                config["max_frame_gap_ms"]
            ),
        )

        if not ir_capture.isOpened():
            raise RuntimeError(
                "IRカメラを開けません: "
                f"{ir_capture.last_error}"
            )

        print(
            "IRグループ:",
            ir_capture.group_name,
        )

        previous_time = time.perf_counter()
        fps = 0.0
        last_console_text = None

        while True:
            cycle_started = time.monotonic()
            rgb_grabbed = rgb_capture.grab()
            rgb_timestamp = time.monotonic()
            ir_grabbed = ir_capture.grab()

            if not rgb_grabbed or not ir_grabbed:
                time.sleep(0.05)
                continue

            rgb_ok, rgb_frame = (
                rgb_capture.retrieve()
            )

            (
                ir_ok,
                ir_frame,
                ir_timestamp,
            ) = ir_capture.retrieve_with_timestamp()

            if (
                not rgb_ok
                or not ir_ok
                or rgb_frame is None
                or ir_frame is None
                or ir_timestamp is None
            ):
                time.sleep(0.05)
                continue

            frame_gap_ms = abs(
                rgb_timestamp - ir_timestamp
            ) * 1000.0

            if frame_gap_ms > float(
                config["max_frame_gap_ms"]
            ):
                authenticated_name = None
                information = {
                    "reason": "frame_gap_too_large",
                    "face_count": 0,
                    "faces": [],
                    "frame_gap_ms": frame_gap_ms,
                }
            else:
                try:
                    (
                        authenticated_name,
                        information,
                    ) = authenticator.authenticate(
                        rgb_frame,
                        ir_frame,
                        rgb_timestamp=rgb_timestamp,
                        ir_timestamp=ir_timestamp,
                    )
                except Exception as error:
                    authenticated_name = None
                    information = {
                        "reason": (
                            "debug_exception: "
                            f"{type(error).__name__}: "
                            f"{error}"
                        ),
                        "face_count": 0,
                        "faces": [],
                        "frame_gap_ms": frame_gap_ms,
                    }

            reason = information.get(
                "reason",
                "unknown",
            )
            face_results = information.get(
                "faces",
                [],
            )

            current_time = time.perf_counter()
            elapsed = current_time - previous_time
            previous_time = current_time

            if elapsed > 0:
                current_fps = 1.0 / elapsed

                fps = (
                    current_fps
                    if fps == 0
                    else fps * 0.9
                    + current_fps * 0.1
                )

            if authenticated_name is not None:
                result_text = (
                    "最終判定: PASS "
                    f"{authenticated_name}"
                )
                result_text_color = (
                    100,
                    255,
                    140,
                )
            else:
                result_text = (
                    "最終判定: NG "
                    f"reason={reason}"
                )
                result_text_color = (
                    255,
                    130,
                    130,
                )

            lines = [
                (
                    result_text,
                    result_text_color,
                ),
                (
                    "同期時間="
                    f"{frame_gap_ms:.1f}ms  "
                    f"FPS={fps:.1f}  "
                    "検出顔="
                    f"{information.get('face_count', 0)}",
                    (180, 210, 255),
                ),
                (
                    "登録人数="
                    f"{len(authenticator.user_names)}  "
                    "テンプレート="
                    f"{len(authenticator.template_records)}",
                    (220, 220, 220),
                ),
                (
                    "顔閾値: "
                    f"score>={authenticator.similarity_threshold:.4f}  "
                    f"margin>={authenticator.margin_threshold:.4f}",
                    (220, 220, 220),
                ),
            ]

            rgb_display = rgb_frame.copy()

            if ir_frame.ndim == 2:
                ir_display = cv2.cvtColor(
                    ir_frame,
                    cv2.COLOR_GRAY2BGR,
                )
            else:
                ir_display = ir_frame.copy()

            for face_number, result in enumerate(
                face_results,
                start=1,
            ):
                face_reason = result.get(
                    "reason",
                    "unknown",
                )
                name = result.get("name")
                score = float(
                    result.get("score", 0.0)
                )
                margin = float(
                    result.get("margin", 0.0)
                )
                pad_score = result.get(
                    "pad_score"
                )

                line = (
                    f"顔{face_number}: "
                    f"{name or '未登録'} "
                    f"score={score:.4f} "
                    f"margin={margin:.4f} "
                    f"判定={face_reason}"
                )

                if pad_score is not None:
                    count = int(result.get("count", 0))
                    required = int(result.get("required", 0))
                    pad_pass_count = int(
                        result.get("pad_pass_count", 0)
                    )
                    pad_required = int(
                        result.get("pad_required_passes", 0)
                    )

                    lines.append((
                        f"  連続={count}/{required} "
                        f"PAD={float(pad_score):.4f} "
                        f"成功={pad_pass_count}/{pad_required}",
                        (220, 220, 220),
                    ))

                lines.append((
                    line,
                    (
                        100,
                        255,
                        140,
                    )
                    if face_reason
                    == "authenticated"
                    else (
                        255,
                        210,
                        120,
                    ),
                ))

                bbox = result.get("bbox")

                if bbox is not None:
                    x1, y1, x2, y2 = map(
                        int,
                        bbox,
                    )

                    cv2.rectangle(
                        rgb_display,
                        (x1, y1),
                        (x2, y2),
                        result_color(face_reason),
                        3,
                    )

                ir_information = result.get("ir")

                if isinstance(ir_information, str):
                    ir_information = {"reason": ir_information}

                if ir_information is not None and not isinstance(ir_information, dict):
                    ir_information = {}

                if ir_information is not None:
                    if isinstance(ir_information, str):
                        ir_information = {
                            "reason": ir_information,
                        }

                    if not isinstance(ir_information, dict):
                        ir_information = {}

                    lines.append((
                        "  IR: "
                        f"顔平均={ir_information.get('face_mean', 0.0):.1f} "
                        f"分散={ir_information.get('face_std', 0.0):.1f} "
                        f"差={ir_information.get('absolute_contrast', 0.0):.1f}",
                        (220, 220, 220),
                    ))

                    mapped_bbox = (
                        ir_information.get(
                            "mapped_bbox"
                        )
                    )

                    if mapped_bbox is not None:
                        (
                            ir_x1,
                            ir_y1,
                            ir_x2,
                            ir_y2,
                        ) = map(
                            int,
                            mapped_bbox,
                        )

                        cv2.rectangle(
                            ir_display,
                            (ir_x1, ir_y1),
                            (ir_x2, ir_y2),
                            (0, 255, 255),
                            2,
                        )

            rgb_display = draw_panel(
                rgb_display,
                lines,
            )

            cv2.imshow(
                RGB_WINDOW,
                resize_for_display(
                    rgb_display
                ),
            )

            cv2.imshow(
                IR_WINDOW,
                resize_for_display(
                    ir_display,
                    max_width=640,
                    max_height=480,
                ),
            )

            console_text = (
                f"name={authenticated_name} "
                f"reason={reason} "
                f"faces={len(face_results)} "
                f"gap={frame_gap_ms:.1f}ms"
            )

            if console_text != last_console_text:
                print(console_text)
                last_console_text = console_text

            key = cv2.waitKey(1) & 0xFF

            if key in (
                27,
                ord("q"),
                ord("Q"),
            ):
                break

            if key in (
                ord("r"),
                ord("R"),
            ):
                authenticator.reload_database_embeddings()

                print(
                    "特徴量を再読み込みしました:",
                    len(
                        authenticator.template_records
                    ),
                )

            if reason in (
                "no_face",
                "cooldown",
                "authenticated",
            ):
                authentication_interval = float(
                    config.get("authentication_idle_interval_sec", 0.8)
                )
            else:
                authentication_interval = float(
                    config.get("authentication_active_interval_sec", 0.35)
                )

            elapsed = time.monotonic() - cycle_started
            remaining = authentication_interval - elapsed

            if remaining > 0:
                time.sleep(remaining)

    finally:
        if rgb_capture is not None:
            rgb_capture.release()

        if ir_capture is not None:
            ir_capture.release()

        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        input(
            "\nエラーが発生しました。"
            "Enterキーで終了します..."
        )