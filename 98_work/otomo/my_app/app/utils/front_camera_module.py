
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
    一時的にキャプチャ画像（フレーム）を保存するためのバッファクラス。
    一時ディレクトリを作成し、そこに最新のキャプチャ画像を保存・取得する。
    '''
    # 一時ディレクトリを作成（prefix="facecap_"）
    tempdir = tempfile.TemporaryDirectory(prefix="facecap_")
    # 保存されたファイルパスを記録するリスト
    files = []

    @classmethod
    def save_frame(cls, frame, filename="shot.jpg"):
        '''
        フレームを一時ディレクトリに保存する。
        既存の一時ファイル情報をクリアしてから新しいファイルを作成する。
        Args:
            frame: OpenCVで取得した画像データ(numpy配列)
            filename: 保存ファイル名（デフォルトは "shot.jpg")
        '''
        # 保存先パスを作成
        path = os.path.join(cls.tempdir.name, filename)
        # 画像を書き込み
        cv2.imwrite(path, frame)
        # ファイルパスを記録
        cls.files.append(path)

    @classmethod
    def clean_frame(cls):
        # 保存ファイルリストをクリア
        cls.files.clear()

    @classmethod
    def get_newest_shot(cls):
        '''
        一時ディレクトリ内の最新のキャプチャ画像ファイルのパスを返す。 \\
        戻り値:
            最新のファイルパス。存在しない場合は None を返す。
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
        if self.front_cap is None:
            print("[エラー] フロントカメラが起動していません")
            return
        ok, frame = self.front_cap.read()
        if not ok:
            print("[エラー] フレームを取得できません")
            return
        timestamp = int(time.time())
        filename = f"capture_{timestamp}.jpg"
        CaptureBuffer.save_frame(frame, filename)
        print(f"[OK] 写真を保存しました: {filename}")

    #endregion
