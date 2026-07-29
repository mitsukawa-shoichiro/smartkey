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

# 顔認証とICカード認証は同じ解除と自動ロックの処理を共有する
from my_app.service.utils.lock_control import request_unlock

# 複数の登録画像との距離とその平均を使って顔認識する
# from my_app.camera.face_util.face_stable import recognize_image_average

# ログの記入に使用
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

# cap_dictでIRカメラを識別するためのキーに使う
IR_CAMERA_KEY = "ir"

from my_app.camera.media_foundation_ir import MediaFoundationIRCamera

#endregion


class CaptureBuffer:
    """
    一時的にキャプチャした画像（フレーム）を保存するためのバッファクラス。
    このクラスは一時ディレクトリを作成し、その中で最新のキャプチャ画像を保存・取得する
    """
    # 一時ディレクトリを作成（prefix="facecap"）
    tempdir = tempfile.TemporaryDirectory(prefix="facecap")
    # 保存されたファイルパスを記録するリスト
    files = []

    @classmethod
    def save_frame(cls, frame, filename="shot.jpg"):
        """
        フレームを一時ディレクトリに保存する
        まず既存の一時ファイル情報をクリアして、その後新しいファイルを作成する

        Args:
        frame: OpenCVで取得した画像データ（NumPy 配列）
        filename: 保存するファイル名（デフォルトは "shot.jpg"）
        """
        # 保存先を作成する
        path = os.path.join(cls.tempdir.name, filename)
        # 画像を入力
        cv2.imwrite(path, frame)
        # ファイルパスを記録
        cls.files.append(path)

    @classmethod
    def clean_frame(cls):
        # 保存したファイルリストを空にする
        cls.files.clear()

    @classmethod
    def get_newest_shot(cls):
        """
        一時的なディレクトリで最新のキャプチャ画像ファイルのパスを返す

        Args:
            最新ファイルのパス。存在しない場合はNoneを返す
        """
        if len(cls.files) > 0:
            return CaptureBuffer.files[-1]
        else:
            return None


class CameraWorker:
    """
    バックグラウンドスレッド：カメラを起動 → プレビューを表示 → CAPTURE / STOP
    """
    isRegistering: bool = False # 現在のカメラ状態 True -> 登録 / False -> 認証

    FACE_UNLOCK_COOLDOWN_SEC = 6    # 同じ人が連続で解除するのを防ぐ待ち時間
    REQUIRED_MATCH_COUNT = 3        # 連続で認証成功した何フレーム後に通過を許可するか
    last_face_name = None           # 前回うまく解除した顔の名前
    last_face_timestamp = 0         # 最後に成功して解除した時間
    current_match_name = None       # 現在認証中の人物名
    current_match_count = 0         # 現在の連続認証成功回数

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

        logger.info("CameraWorker初期化")
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

        # 顔認識用のカメラをオンにする
        if not self.open_all_cameras():
            logger.error("カメラを起動できません")

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
        """
        顔認証スレッド本体


        """
        logger.info("カメラ起動！")
        released_for_register = False  # 認証 <=> 登録フラグ管理用、 登録の為のカメラ解放 -> True （None/True/False）
        capture_failure_count = 0
        loop_error_count = 0

        try:
            if not all(
                cap is not None and cap.isOpened()
                for cap in self.cap_dict.values()
            ):
                self.open_all_cameras()

            while not self.systemstop:  # 常に動作
                try:
                    if (
                        self._camera_reload_requested.is_set()
                        and not self.isRegistering
                    ):
                        self._apply_camera_config_reload()
                        released_for_register = False
                    # 状態遷移を検出
                    cycle_started = time.monotonic()
                    timg=time.time()

                    if self.isRegistering:
                        if released_for_register is not True:
                            # False -> True に遷移した瞬間だけ一度だけ実行
                            self.release_all_cameras()
                            self.latest_rgb_frame = None
                            self.latest_ir_frame = None
                            self.latest_rgb_timestamp = None
                            self.latest_ir_timestamp = None
                            self.face_authenticator._reset()
                            logger.info("登録モードのためカメラを一時解放しました")

                        released_for_register = True
                        logger.info("⏸️ 登録中のため認証処理を一時停止")
                        time.sleep(0.5)  # ポーリング間隔（短め）
                        continue
                    else:
                        if released_for_register is True:
                            # True -> False に遷移した瞬間だけ再オープン
                            if not self.open_all_cameras():
                                time.sleep(3.0)
                                continue

                            self.face_authenticator.reload_database_embeddings()

                            logger.info("登録完了。カメラを再オープンしました")

                        released_for_register = False

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

                    # ループ間隔の読み込みと読み込み失敗時のフォールバック
                    idle_interval = float( # 省エネ時間隔
                        face_auth_config.get("authentication_idle_interval_sec", 0.8))

                    active_interval = float( # 認証時間隔
                        face_auth_config.get("authentication_active_interval_sec", 0.35))

                    if self.last_auth_reason in ( # 省エネにすべき状態 -> 省エネ間隔
                        "no_face",
                        "cooldown",
                        "authenticated",
                        "no_frame"
                    ):
                        authentication_interval = idle_interval
                    else: # 顔を認識すべき状態 -> 認証間隔
                        authentication_interval = active_interval

                    elapsed = time.monotonic() - cycle_started
                    remaining = authentication_interval - elapsed

                    if remaining > 0:
                        time.sleep(remaining)

                    logger.debug("１サイクル終了、所要時間："+str(time.time()-timg)+"秒")

                except Exception:
                    # ループ継続用
                    loop_error_count += 1
                    logger.exception(
                        "認証サイクルで例外が発生しました（%d回連続）。次フレームへ継続します",
                        loop_error_count,
                    )
                    self.last_auth_reason = "loop_error"

                    # 認証状態は壊れている可能性があるのでリセットしておく
                    try:
                        self.face_authenticator._reset()
                    except Exception:
                        logger.exception("認証状態のリセットにも失敗しました")

                    # 例外が連発する＝カメラ等が壊れている可能性が高い。
                    # 一定回数を超えたらカメラを作り直してから続行する。
                    if loop_error_count >= 5:
                        logger.error("認証サイクルの例外が連続しました。カメラを再構築します")
                        try:
                            self.open_all_cameras()
                        except Exception:
                            logger.exception("カメラ再構築にも失敗しました")
                        loop_error_count = 0
                        time.sleep(3.0)
                    else:
                        time.sleep(0.5)

                    continue

        except KeyboardInterrupt:
            print("\n[INFO] ユーザー中断、プログラムを終了します。")
        except Exception:
            logger.exception("back_end_systemが予期していない例外で終了します")
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

        # OpenCVでRGBカメラを開く
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

        # Media Foundationを使ってIRカメラを直接開く
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

        self.__open_sesame(info.get("user_id"))
        return True



    def __open_sesame(self, user_id):
        # 解錠後、設定時間が経過すると自動的に再施錠されます！
        # TODO: request_unlockの引数にゆーざーIDを使用
        request_unlock(user_id)
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