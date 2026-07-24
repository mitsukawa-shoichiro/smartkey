
import threading
import cv2
import os
import tempfile
import time
import socket
import base64
import logging

logger = logging.getLogger(__name__)

HOST = '127.0.0.1'
PORT = 44444
def send_message(msg: str):
    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        ) as client:
            client.sendto(
                msg.encode("utf-8"),
                (HOST, PORT),
            )

        logger.debug("メッセージ送信成功: %s", msg)
        return True

    except Exception as ex:
        logger.warning("メッセージ送信失敗: %s", ex, exc_info=True)
        return False

def request_camera_config_reload(
    timeout: float = 10.0,
):
    """認証サービスへカメラ設定の再読み込みを依頼する"""
    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        ) as client:
            client.settimeout(timeout)

            client.sendto(
                b"reloadCameraConfig",
                (HOST, PORT),
            )

            data, _ = client.recvfrom(1024)

        response = data.decode(
            "utf-8",
            errors="replace",
        ).strip()

        parts = response.split(":", 2)

        if (
            len(parts) == 3
            and parts[0] == "reloadCameraConfig"
        ):
            return parts[1] == "ok", parts[2]

        return False, (
            f"認証サービスから不明な応答: {response}"
        )

    except socket.timeout:
        return False, (
            "認証サービスから応答がありません"
        )

    except Exception as ex:
        return False, str(ex)

def request_camera_release(
    timeout: float = 5.0,
):
    """認証サービスがカメラを解放するまで待つ"""
    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        ) as client:
            client.settimeout(timeout)

            client.sendto(
                b"startRegisteringAndWait",
                (HOST, PORT),
            )

            data, _ = client.recvfrom(1024)

        response = data.decode(
            "utf-8",
            errors="replace",
        ).strip()

        parts = response.split(":", 2)

        if (
            len(parts) == 3
            and parts[0] == "cameraRelease"
        ):
            return parts[1] == "ok", parts[2]

        return False, response

    except socket.timeout:
        return False, (
            "認証サービスから応答がありません"
        )

    except Exception as ex:
        return False, str(ex)

class CaptureBuffer:
    '''
    用于临时保存捕获图像（帧）的缓冲区类。
    该类会创建一个临时目录，并在其中保存和获取最新的捕获图像。
    '''
    # 一時ディレクトリを作成（prefix="facecap_"）
    tempdir = tempfile.TemporaryDirectory(prefix="facecap_")
    # 保存されたファイルパスを記録するリスト
    files = []

    @classmethod
    def save_frame(cls, frame, filename="shot.jpg"):
        '''
        将帧保存到临时目录中
        先清除已有的临时文件信息 然后创建新的文件

        Args:
            frame: 使用OpenCV获取的图像数据（NumPy 数组）
            filename: 保存文件名（默认值为"shot.jpg"）
        '''
        # 创建保存路径
        path = os.path.join(cls.tempdir.name, filename)

        if not cv2.imwrite(path, frame):
            raise OSError(f"画像保存できぬ {path}")

        # 记录文件路径
        cls.files.append(path)
        return path

    @classmethod
    def clean_frame(cls):
        # 保存ファイルリストをクリア
        cls.files.clear()

    @classmethod
    def get_newest_shot(cls):
        '''
        返回临时目录中最新捕获图像文件的路径
        返回值:
            最新文件的路径 若不存在, 则返回None
        '''
        if len(cls.files) > 0:
            return CaptureBuffer.files[-1]
        else:
            return None

class CameraWorker_Front:
    instance = None

    def __init__(self):
        if CameraWorker_Front.instance is not None:
            return

        CameraWorker_Front.instance = self

        self.close_camera = True
        self.front_cap = None

        self._camera_thread = None
        self._thread_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._capture_lock = threading.Lock()
        self._camera_ready = threading.Event()

        self._latest_frame = None
        self._latest_frame_at = 0.0
        self._last_capture_at = 0.0
        self._camera_error = None

    @classmethod
    def get_instance(cls):
        if cls.instance is None:
            cls()
        return cls.instance

    def front_end_system(
        self,
        camera_index,
        show_window=False,
    ):
        self.stop_camera()

        try:
            camera_index = int(camera_index)
        except (TypeError, ValueError):
            self._camera_error = (
                f"無効なカメラインデックス: {camera_index}"
            )
            self._camera_ready.set()
            return

        with self._thread_lock:
            self.close_camera = False
            self._camera_error = None
            self._camera_ready.clear()
            self._latest_frame = None

            self._camera_thread = threading.Thread(
                target=self._front_preview,
                args=(camera_index, show_window),
                daemon=True,
            )
            self._camera_thread.start()

    def _front_preview(
        self,
        camera_index: int,
        show_window: bool,
    ):
        # 最初にDirectShowでカメラを開く
        cap = cv2.VideoCapture(
            camera_index,
            cv2.CAP_DSHOW,
        )
        camera_backend = "DirectShow"

        # DirectShowで開けない場合はMedia Foundationを試す
        if not cap.isOpened():
            cap.release()

            cap = cv2.VideoCapture(
                camera_index,
                cv2.CAP_MSMF,
            )
            camera_backend = "Media Foundation"

        self.front_cap = cap

        # どちらの方式でも開けなかった場合
        if not cap.isOpened():
            self._camera_error = (
                f"カメラ {camera_index} を"
                "DirectShow・Media Foundationの"
                "どちらでも開けませんでした"
            )
            self._camera_ready.set()
            cap.release()
            self.front_cap = None
            return

        logger.info("カメラ%sを%sで開きました", camera_index, camera_backend)

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 15)

        window_name = (
            f"Camera Preview - {camera_index}"
        )

        self._camera_ready.set()

        try:
            while not self.close_camera:
                ok, frame = cap.read()

                if not ok:
                    self._camera_error = (
                        "カメラ映像を取得できませんでした"
                    )
                    break

                captured_at = time.monotonic()

                with self._frame_lock:
                    self._latest_frame = frame.copy()
                    self._latest_frame_at = captured_at

                if show_window:
                    cv2.imshow(window_name, frame)
                    key = cv2.waitKey(1) & 0xFF

                    if key in (
                        27,
                        ord("q"),
                        ord("Q"),
                    ):
                        self.close_camera = True
                        break

                time.sleep(0.01)

        finally:
            cap.release()
            self.front_cap = None

            with self._frame_lock:
                self._latest_frame = None

            if show_window:
                try:
                    cv2.destroyWindow(window_name)
                except cv2.error:
                    pass

    def wait_until_ready(
        self,
        timeout: float = 4.0,
    ):
        self._camera_ready.wait(timeout)
        return self.is_camera_open()

    def is_camera_open(self):
        cap = self.front_cap
        return (
            cap is not None
            and cap.isOpened()
            and not self.close_camera
        )

    def get_camera_error(self):
        return self._camera_error

    def get_latest_frame(
        self,
        max_age_sec: float = 1.0,
    ):
        """スレッド共有中の最新フレームをコピーして返す"""
        now = time.monotonic()

        with self._frame_lock:
            if self._latest_frame is None:
                return None

            if (
                now - self._latest_frame_at
                > max_age_sec
            ):
                return None

            return self._latest_frame.copy()

    def get_preview_base64(
        self,
        max_width: int = 640,
        jpeg_quality: int = 75,
    ):
        with self._frame_lock:
            if self._latest_frame is None:
                return None

            frame = self._latest_frame.copy()

        height, width = frame.shape[:2]

        if width > max_width:
            scale = max_width / width
            frame = cv2.resize(
                frame,
                (
                    max_width,
                    int(height * scale),
                ),
                interpolation=cv2.INTER_AREA,
            )

        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                jpeg_quality,
            ],
        )

        if not ok:
            return None

        return base64.b64encode(
            encoded.tobytes()
        ).decode("ascii")

    def front_capture_photo(self):
        if not self.is_camera_open():
            logger.warning("フロントカメラが起動していません")
            return None

        with self._capture_lock:
            now = time.monotonic()

            if now - self._last_capture_at < 1.0:
                logger.debug("次の撮影まで1秒待ってください")
                return None

            with self._frame_lock:
                if self._latest_frame is None:
                    return None

                if now - self._latest_frame_at > 1.0:
                    logger.warning("カメラ画像が古すぎます")
                    return None

                frame = self._latest_frame.copy()

            filename = (
                f"capture_{time.time_ns()}.jpg"
            )

            path = CaptureBuffer.save_frame(
                frame,
                filename,
            )

            self._last_capture_at = now
            logger.info("撮影画像を保存しました: %s", path)
            return path

    def stop_camera(self):
        self.close_camera = True

        thread = self._camera_thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(timeout=1.5)

        cap = self.front_cap

        if cap is not None and cap.isOpened():
            cap.release()

        self.front_cap = None
        self._camera_thread = None

        with self._frame_lock:
            self._latest_frame = None

    #endregion
