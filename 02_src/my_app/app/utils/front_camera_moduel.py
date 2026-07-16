
import threading
import cv2
import os
import tempfile
import time
import socket

HOST = '127.0.0.1'
PORT = 44444
def send_message(msg: str):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  
        client.sendto(msg.encode('utf-8'), (HOST, PORT))
        client.close()
        print(f"[OK] メッセージ送信成功: {msg}")
    except Exception as e:
        print(f"[WARN] メッセージ送信失敗: {e}")
        # 失敗しても続行

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
    __FRONT_END_CAMERA:threading.Thread = None
    instance:"CameraWorker_Front"=None
    #region front_end
    close_camera:bool=False
    front_cap:cv2.VideoCapture=None

    def __init__(self):
        if CameraWorker_Front.instance is None:
            CameraWorker_Front.instance = self

            self._frame_lock = threading.Lock()
            self._capture_lock = threading.Lock()
            self._latest_frame = None
            self._latest_frame_at = 0.0
            self._last_capture_at = 0.0

    def front_end_system(self,camera_index):
        if self.__FRONT_END_CAMERA is None or not self.__FRONT_END_CAMERA.is_alive():
            self.__FRONT_END_CAMERA = threading.Thread(target=self.__front_preview, args=(camera_index,), daemon=True)
            self.__FRONT_END_CAMERA.start()

    def __front_preview(self, camera_index:int):
        try:
            camera_index = int(camera_index)
        except (ValueError, TypeError):
            print(f"[エラー] 無効なカメラインデックス: {camera_index}")
            return
        self.front_cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        if not self.front_cap.isOpened():
            print(f"[エラー] カメラ {camera_index} を開けませんでした")
            return
        
        window_name = f"Camera Preview - {camera_index}"
        
        try:
            while not self.close_camera:
                ok, frame = self.front_cap.read()
                if not ok:
                    print("[エラー] フレームを取得できません")
                    break

                captured_at = time.monotonic()

                with self._frame_lock:
                    self._latest_frame = frame.copy()
                    self._latest_frame_at = captured_at

                cv2.imshow(window_name, frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q"), ord("Q")):
                    self.close_camera = True
                    break
        finally:
            # 必ずリソースを解放
            self.front_cap.release()
            cv2.destroyWindow(window_name)
            print(f"[INFO] カメラ {camera_index} を終了し、リソースを解放しました")

    def front_capture_photo(self):
        if self.front_cap is None or not self.front_cap.isOpened():
            print("フロントカメラが起動してない")
            return None

        with self._capture_lock:
            now = time.monotonic()

            if now - self._last_capture_at < 1.0:
                print("[INFO] 次の撮影まで1秒待ってください")
                return None

            with self._frame_lock:
                if self._latest_frame is None:
                    print("[エラー] 撮影可能なフレームがありません")
                    return None

                if now - self._latest_frame_at > 1.0:
                    print("[エラー] カメラ画像が古すぎます")
                    return None

                frame = self._latest_frame.copy()

            filename = f"capture_{time.time_ns()}.jpg"
            path = CaptureBuffer.save_frame(frame, filename)
            self._last_capture_at = now

            print(f"[OK] 保存完了 {path}")
            return path

    #endregion
