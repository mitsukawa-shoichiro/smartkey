import re
import threading
import tempfile, cv2, os,random
import socket
import os
import cv2
import tempfile
import time

# import service.db_manager as repo
# import service.utils.sesame as sesame
from my_app.camera.face_authenticator import FaceAuthenticator

import my_app.logs.log_config_service
import logging

# 人脸识别和IC卡认证共用相同的解锁与自动上锁处理
from my_app.service.card_sys import request_unlock

# 通过与多张注册图像的距离及其平均值进行人脸识别
# from my_app.camera.face_util.face_stable import recognize_image_average

# 用于写入日志
logger = logging.getLogger(__name__)

#region ReadConfig
import json
from my_app.camera.camera_config import load_rgb_camera_index

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent   # service/face_recognition
ROOT_DIR = BASE_DIR.parent            # root/
DB_DIR = ROOT_DIR / "db" / "Facelib"         # root/db/Facelib
print("datapath is " + str(DB_DIR))

FACE_AUTH_CONFIG_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "face_auth.json"
)

with FACE_AUTH_CONFIG_PATH.open("r", encoding = "utf-8") as file:
    face_auth_config = json.load(file)

IR_DEVICE_ID_CONTAINS = str(
    face_auth_config["ir_device_id_contains"]
)

IR_STARTUP_TIMEOUT_SEC = float(
    face_auth_config.get("ir_startup_timeout_sec", 5.0)
)

# 用于在cap_dict中识别IR摄像头的键
IR_CAMERA_KEY = "ir"

from my_app.camera.media_foundation_ir import MediaFoundationIRCamera

#endregion


class CaptureBuffer:
    """
    用于临时保存捕获图像（帧）的缓冲区类
    该类会创建一个临时目录, 并在其中保存和获取最新的捕获图像
    """
    # 一時ディレクトリを作成（prefix="facecap_"）
    tempdir = tempfile.TemporaryDirectory(prefix="facecap_")
    # 保存されたファイルパスを記録するリスト
    files = []

    @classmethod
    def save_frame(cls, frame, filename="shot.jpg"):
        """
        将帧保存到临时目录中
        先清除已有的临时文件信息, 然后创建新的文件

        Args:
            frame: 使用 OpenCV 获取的图像数据（NumPy 数组）
            filename: 保存文件名（默认值为 "shot.jpg"）
        """
        # 创建保存路径
        path = os.path.join(cls.tempdir.name, filename)
        # 写入图像
        cv2.imwrite(path, frame)
        # 记录文件路径
        cls.files.append(path)

    @classmethod
    def clean_frame(cls):
        # 清空已保存的文件列表
        cls.files.clear()

    @classmethod
    def get_newest_shot(cls):
        """
        返回临时目录中最新捕获图像文件的路径

        返回值:
            最新文件的路径。若不存在, 则返回None
        """
        if len(cls.files) > 0:
            return CaptureBuffer.files[-1]
        else:
            return None


class CameraWorker:
    """
    后台线程：启动摄像头 → 显示预览 → CAPTURE / STOP
    """
    isRegistering: bool = False

    FACE_UNLOCK_COOLDOWN_SEC = 6    # 防止同一人连续解锁的等待时间
    REQUIRED_MATCH_COUNT = 3        # 连续认证成功多少帧后才允许通过
    last_face_name = None           # 上一次成功解锁的人脸姓名
    last_face_timestamp = 0         # 上一次成功解锁的时间
    current_match_name = None       # 当前正在认证的人物姓名
    current_match_count = 0         # 当前连续认证成功次数

    __BACK_END_CAMERA:threading.Thread = None
    __SOCKET_THREAD:threading.Thread = None

    cap_dict: dict[int, cv2.VideoCapture] = {}

    instance:"CameraWorker" = None

    systemstop:bool = False

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        print("CameraWorker初期化")
        CameraWorker.instance = self
        # self.blink_detector = BlinkDetector()

        self.face_authenticator = FaceAuthenticator(face_dir = DB_DIR, config = face_auth_config)

        self.latest_rgb_frame = None
        self.latest_ir_frame = None
        self.latest_rgb_timestamp = None
        self.latest_ir_timestamp = None
        self.last_auth_reason = "no_face"
        self.cap_dict = {}
        self.systemstop = False
        self.isRegistering = False
        self.rgb_camera_index = (load_rgb_camera_index())

        self._camera_reload_requested = (threading.Event())
        self._camera_reload_done = (threading.Event())
        self._camera_reload_lock = (threading.Lock())
        self._camera_reload_result = (False, "まだ実行されていません")

        # 打开用于人脸识别的摄像头
        if not self.open_all_cameras():
            logger.error("カメラひらけん")

        if self.__SOCKET_THREAD is None:
            self.__SOCKET_THREAD = threading.Thread(target=self.socket_receiver, daemon=True)
            self.__SOCKET_THREAD.start()

        self._initialized = True

    def stop(self):
        self.systemstop=True

    def request_camera_config_reload(
        self,
        timeout=8.0,
    ):
        """バックエンド処理へ設定再読み込みを依頼する"""
        with self._camera_reload_lock:
            if self._camera_reload_requested.is_set():
                return False, "再読み込み処理中です"

            self._camera_reload_done.clear()
            self._camera_reload_requested.set()

        completed = self._camera_reload_done.wait(
            timeout
        )

        if not completed:
            return False, (
                "カメラ設定の反映がタイムアウトしました"
            )

        with self._camera_reload_lock:
            return self._camera_reload_result


    def _apply_camera_config_reload(self):
        """認証スレッド上で設定を読み直してカメラを開き直す"""
        old_index = self.rgb_camera_index

        try:
            new_index = load_rgb_camera_index()

            self.rgb_camera_index = new_index

            self.latest_rgb_frame = None
            self.latest_ir_frame = None
            self.latest_rgb_timestamp = None
            self.latest_ir_timestamp = None
            self.last_auth_reason = "no_frame"

            self.face_authenticator._reset()

            if not self.open_all_cameras():
                self.rgb_camera_index = old_index

                self.open_all_cameras()

                raise RuntimeError(
                    f"カメラindex {new_index}を"
                    "開けませんでした"
                )

            result = (
                True,
                f"カメラindex {new_index}を反映しました",
            )

            logger.info(result[1])

        except Exception as ex:
            logger.exception(
                "カメラ設定の即時反映に失敗しました"
            )
            result = (False, str(ex))

        with self._camera_reload_lock:
            self._camera_reload_result = result
            self._camera_reload_requested.clear()
            self._camera_reload_done.set()

    def back_end_system(self):
        logger.info("カメラ起動！")
        was_registering = None  # 记录上一次的状态（None/True/False）
        capture_failure_count = 0

        try:
            if not all(
                cap is not None and cap.isOpened()
                for cap in self.cap_dict.values()
            ):
                self.open_all_cameras()

            while not self.systemstop:  # 常に動作
                if (
                    self._camera_reload_requested.is_set()
                    and not self.isRegistering
                ):
                    self._apply_camera_config_reload()
                    was_registering = False
                # 状態遷移を検出
                cycle_started = time.monotonic()
                timg=time.time()

                if self.isRegistering:
                    if was_registering is not True:
                        # False -> True に遷移した瞬間だけ一度だけ実行
                        self.release_all_cameras()
                        self.latest_rgb_frame = None
                        self.latest_ir_frame = None
                        self.latest_rgb_timestamp = None
                        self.latest_ir_timestamp = None
                        self.face_authenticator._reset()
                        logger.info("登録モードのためカメラを一時解放しました")

                    was_registering = True
                    print("登録中のため認証処理を一時停止")
                    time.sleep(0.5)  # ポーリング間隔（短め）
                    continue
                else:
                    if was_registering is True:
                        # True -> False に遷移した瞬間だけ再オープン
                        if not self.open_all_cameras():
                            time.sleep(3.0)
                            continue

                        self.face_authenticator.reload_database_embeddings()

                        logger.info("登録完了。カメラを再オープンしました")

                    was_registering = False

                # 通常フロー（認証）
                rgb_cap = self.cap_dict.get(self.rgb_camera_index)
                ir_cap = self.cap_dict.get(IR_CAMERA_KEY)

                if (
                    rgb_cap is None
                    or ir_cap is None
                    or not rgb_cap.isOpened()
                    or not ir_cap.isOpened()
                ):
                    capture_failure_count += 1

                    if capture_failure_count >= 5:
                        self.open_all_cameras()
                        capture_failure_count = 0

                    time.sleep(0.5)
                    continue

                rgb_grabbed = rgb_cap.grab()
                rgb_timestamp = time.monotonic()

                ir_grabbed = ir_cap.grab()

                if not rgb_grabbed or not ir_grabbed:
                    capture_failure_count += 1

                    if capture_failure_count >= 5:
                        self.open_all_cameras()
                        capture_failure_count = 0

                    time.sleep(0.5)
                    continue

                rgb_ok, rgb_frame = rgb_cap.retrieve()

                (
                    ir_ok,
                    ir_frame,
                    ir_timestamp,
                ) = ir_cap.retrieve_with_timestamp()

                if (
                    not rgb_ok
                    or not ir_ok
                    or rgb_frame is None
                    or ir_frame is None
                    or ir_timestamp is None
                ):
                    capture_failure_count += 1

                    if capture_failure_count >= 5:
                        self.open_all_cameras()
                        capture_failure_count = 0

                    time.sleep(0.5)
                    continue

                frame_gap_ms = abs(
                    rgb_timestamp - ir_timestamp
                ) * 1000.0

                if frame_gap_ms > float(
                    face_auth_config["max_frame_gap_ms"]
                ):
                    logger.debug("RGB・IRフレーム差が大きいため破棄 %.1fms", frame_gap_ms)
                    time.sleep(0.01)
                    continue

                capture_failure_count = 0

                self.latest_rgb_frame = rgb_frame
                self.latest_ir_frame = ir_frame
                self.latest_rgb_timestamp = rgb_timestamp
                self.latest_ir_timestamp = ir_timestamp

                # 認証
                self.__Authentication()

                # 成功でも失敗でもまつ
                idle_interval = float(
                    face_auth_config.get("authentication_idle_interval_sec", 0.8))

                active_interval = float(
                    face_auth_config.get("authentication_active_interval_sec", 0.35))

                if self.last_auth_reason in (
                    "no_face",
                    "cooldown",
                    "authenticated",
                    "no_frame"
                ):
                    authentication_interval = idle_interval
                else:
                    authentication_interval = active_interval

                elapsed = time.monotonic() - cycle_started
                remaining = authentication_interval - elapsed

                if remaining > 0:
                    time.sleep(remaining)

                logger.info("１サイクル終了、所要時間："+str(time.time()-timg)+"秒")

        except KeyboardInterrupt:
            print("\n[INFO] ユーザー中断、プログラムを終了します")
        finally:
            self.latest_rgb_frame = None
            self.latest_ir_frame = None
            self.latest_rgb_timestamp = None
            self.latest_ir_timestamp = None
            self.last_auth_reason = "no_face"
            self.release_all_cameras()
            print("\nバックシステム終了")
            cv2.destroyAllWindows()

    def release_all_cameras(self):
        if self.cap_dict:
            for camera_key, cap in self.cap_dict.items():
                if cap is not None:
                    cap.release()
                    print(f"[INFO] カメラ {camera_key} のリソースを解ほうう！！！")

        self.cap_dict = {}

    def open_all_cameras(self):
        self.release_all_cameras()

        # 使用OpenCV打开RGB摄像头
        rgb_cap = cv2.VideoCapture(
            self.rgb_camera_index,
            cv2.CAP_DSHOW,
        )

        if not rgb_cap.isOpened():
            rgb_cap.release()
            rgb_cap = cv2.VideoCapture(
                self.rgb_camera_index,
                cv2.CAP_MSMF,
            )

        if not rgb_cap.isOpened():
            rgb_cap.release()
            self.cap_dict = {self.rgb_camera_index: None, IR_CAMERA_KEY: None}
            logger.error("RGBカメラひらけん index=%s", self.rgb_camera_index)
            return False

        rgb_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # 使用Media Foundation直接打开IR摄像头
        ir_cap = MediaFoundationIRCamera(
            device_id_contains=IR_DEVICE_ID_CONTAINS,
            startup_timeout=IR_STARTUP_TIMEOUT_SEC,
            max_age_ms=float(
                face_auth_config.get("max_frame_gap_ms", 150)
            ),
        )

        if not ir_cap.isOpened():
            error = ir_cap.last_error
            ir_cap.release()
            rgb_cap.release()

            self.cap_dict = {
                self.rgb_camera_index: None,
                IR_CAMERA_KEY: None,
            }

            logger.error(
                "IRカメラをひらけん %s", error)
            return False

        self.cap_dict = {
            self.rgb_camera_index: rgb_cap,
            IR_CAMERA_KEY: ir_cap,
        }

        print(f"[INFO] RGBカメラ {self.rgb_camera_index} ぱかっ")
        print("[INFO] IRカメラをMedia Foundationでひらく")
        print(f"[INFO] IRグループ {ir_cap.group_name}")

        return True

    def __Authentication(self):
        """
        RGBとIRを用いた顔認識
        """
        rgb_frame = self.latest_rgb_frame
        ir_frame = self.latest_ir_frame

        if rgb_frame is None or ir_frame is None:
            self.last_auth_reason = "no_frame"
            return False

        name, info = (
            self.face_authenticator.authenticate(
                rgb_frame,
                ir_frame,
                rgb_timestamp=self.latest_rgb_timestamp,
                ir_timestamp=self.latest_ir_timestamp
            )
        )

        reason = info.get("reason", "unknown")
        self.last_auth_reason = reason

        if name is None:
            if reason == "need_more_frames":
                print(
                    f"認証候補: {info.get('name')} "
                    f"{info.get('count', 0)}/"
                    f"{info.get('required', 0)} "
                    f"score={info.get('score', 0.0):.4f} "
                    f"PAD={info.get('pad_score', 0.0):.4f}"
                )

            elif reason not in ("cooldown", "no_face"):
                print(f"顔があかんわ {reason} faces={info.get('face_count', 0)}")

            return False

        self.last_auth_reason = "authenticated"

        logger.info(
            "びじゅいいじゃん "
            "user_id=%s name=%s "
            "score=%.4f margin=%.4f faces=%s",
            info.get("user_id"),
            name,
            info.get("score", 0.0),
            info.get("margin", 0.0),
            info.get("face_count", 0)
        )

        self.__open_sesame()
        return True





    def __Authentication_old(self):
        for file_path in CaptureBuffer.files:
            # 不以单张图像是否匹配作为判断, 而是根据与多张注册图像的距离及其平均值进行认证
            name_roma, info = recognize_image_average(file_path, DB_DIR)

            # 如果当前帧认证失败, 则处理下一帧图像
            if name_roma is None:
                continue

            # 确认是否为同一人连续认证成功
            if self.current_match_name == name_roma:
                self.current_match_count += 1
            else:
                self.current_match_name = name_roma
                self.current_match_count = 1

            # 将判定状态输出到日志中, 以便查看
            print(
                f"認証候補: {name_roma} "
                f"{self.current_match_count}/{self.REQUIRED_MATCH_COUNT} "
                f"best={info['best_distance']:.4f} "
                f"avg={info['avg_nearest_distance']:.4f} "
                f"hits={info['registered_match_count']}/{info['required_registered_matches']}"
            )

            # 在连续成功达到规定次数之前不解锁
            if self.current_match_count < self.REQUIRED_MATCH_COUNT:
                return False

            # 重置连续认证计数, 以便进行下一次判定
            self.current_match_name = None
            self.current_match_count = 0

            now = time.time()

            # 如果是同一张脸, 并且距离上次解锁未超过指定秒数, 则不执行解锁
            if (
                self.last_face_name == name_roma
                and now - self.last_face_timestamp < self.FACE_UNLOCK_COOLDOWN_SEC
            ):
                print(f"開錠スキップ: {name_roma}")
                return True

            # 记录成功解锁的人脸姓名和解锁时间
            self.last_face_name = name_roma
            self.last_face_timestamp = now

            # 显示通过哪个摄像头完成了认证
            match = re.search(r"camera_(\d+)\.jpg", file_path)
            if match:
                index = int(match.group(1))
                print("撮影されたカメラのindexは" + str(index))

            # 解锁
            self.__open_sesame()
            return True

        # どのカメラ画像でも照合に成功しなかった場合、連続成功回数はリセットされます。
        self.current_match_name = None
        self.current_match_count = 0
        return False



    def __open_sesame(self):
        # 解錠後、設定時間が経過すると自動的に再施錠されます！
        # TODO: request_unlockの引数にゆーざーIDを使用
        request_unlock()
        print("認証成功")


    #region socket
    HOST = '127.0.0.1'
    PORT = 44444

    def socket_receiver(self):
        sock = None

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.bind((self.HOST, self.PORT))
            print(f"UDPポート {self.PORT} を監視中...")
        except OSError as e:
            print(f"ポートバインドエラー: {e}")
            print(f"ポート {self.PORT} は既に使用されている可能性があります")

            if sock is not None:
                sock.close()

            return

        try:
            while not self.systemstop:
                try:
                    data, addr = sock.recvfrom(1024)
                    recv_msg = data.decode('utf-8').strip()
                    print(f"{addr} からのメッセージを受信：{recv_msg}")

                    if recv_msg == "startRegistering":
                        self.isRegistering = True

                    elif recv_msg == "startRegisteringAndWait":
                        self.isRegistering = True

                        deadline = time.monotonic() + 5.0

                        while time.monotonic() < deadline:
                            cameras_open = any(
                                cap is not None
                                and cap.isOpened()
                                for cap in self.cap_dict.values()
                            )

                            if not cameras_open:
                                break

                            time.sleep(0.05)

                        cameras_open = any(
                            cap is not None
                            and cap.isOpened()
                            for cap in self.cap_dict.values()
                        )

                        if cameras_open:
                            self.isRegistering = False
                            status = "error"
                            message = "カメラを解放できませんでした"
                        else:
                            status = "ok"
                            message = "カメラを解放しました"

                        sock.sendto(
                            (
                                f"cameraRelease:"
                                f"{status}:"
                                f"{message}"
                            ).encode("utf-8"),
                            addr,
                        )

                    elif recv_msg == "finishRegistering":
                        self.isRegistering = False

                    elif recv_msg == "reloadCameraConfig":
                        # UDPの到着順に関係なく登録モードを解除する
                        self.isRegistering = False

                        success, message = (
                            self.request_camera_config_reload()
                        )

                        status = (
                            "ok"
                            if success
                            else "error"
                        )

                        sock.sendto(
                            (
                                f"reloadCameraConfig:"
                                f"{status}:"
                                f"{message}"
                            ).encode("utf-8"),
                            addr,
                        )

                    else:
                        print(
                            f"不明なメッセージ: {recv_msg}"
                        )
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"受信エラー: {e}")
                    break
        finally:
            sock.close()

    #endregion