import re
import threading
import tempfile, cv2, os,random
import socket
import os
import cv2
import tempfile
import time

import service.db_manager as db
import service.utils.sesame as sesami
import camera.face_util as face_util

import my_app.logs.log_config_service
import logging

# 顔認証とICカード認証で同じ開錠・自動施錠の処理つかっちゃう
from my_app.service.cardsystem import request_unlock

# 複数登録画像との距離・平均値で顔認証するよう
from my_app.camera.face_util.face_stable import recognize_image_average

#region ReadConfig
import json
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..',  'config', 'camera_settings.json'))
print(CONFIG_PATH)
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)
    indoor_index=int(config_list["devices"]["入口"]["index"])
    outdoor_index=int(config_list["devices"]["出口"]["index"])

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent   # service/face_recognition
ROOT_DIR = BASE_DIR.parent            # root/
DB_DIR = ROOT_DIR / "db" / "Facelib"         # root/db/Facelib
print("datapath is " + str(DB_DIR))

#endregion


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


class CameraWorker:
    """バックグラウンドスレッド：カメラ起動 -> プレビュー表示 -> CAPTURE/STOP"""
    isRegisting: bool = False

    FACE_UNLOCK_COOLDOWN_SEC = 6    # 同じ顔で連続開錠しないための待ち時間
    REQUIRED_MATCH_COUNT = 3        # 何フレーム連続で成功したらとおすか
    last_face_name = None           # 最後に開錠した顔のなまえ
    last_face_timestamp = 0         # 最後に開錠したじかん
    current_match_name = None       # 今やってる人物名
    current_match_count = 0         # 今の成功回数

    __BACK_END_CAMERA:threading.Thread = None
    __SOCKET_THREAD:threading.Thread = None

    cap_dict: dict[int, cv2.VideoCapture] = {}

    instance:"CameraWorker"=None

    systemstop:bool=False

    def __init__(self):
        if CameraWorker.instance is None:
            print("CameraWorker初期化")
            CameraWorker.instance = self

            if self.__SOCKET_THREAD is None:
                self.__SOCKET_THREAD = threading.Thread(target=self.socket_receiver, daemon=True)
                self.__SOCKET_THREAD.start()

            cap_indoor=cv2.VideoCapture(indoor_index, cv2.CAP_DSHOW)
            self.cap_dict[indoor_index]=(cap_indoor)
            print("入口を追加")
            if outdoor_index!=indoor_index:
                print("出口を追加")
                cap_outdoor=cv2.VideoCapture(outdoor_index, cv2.CAP_DSHOW)
                self.cap_dict[outdoor_index]=(cap_outdoor)

    def stop(self):
        self.systemstop=True

    def back_end_system(self):
        print("カメラ起動！")
        was_registing = None  # 直前の状態を記録（None/True/False）
        try:
            while not self.systemstop:  # 常に動作
                # 状態遷移を検出
                timg=time.time()
                if self.isRegisting:
                    if was_registing is not True:
                        # False -> True に遷移した瞬間だけ一度だけ実行
                        self.release_all_cameras()
                        print("[INFO] 登録モードのためカメラを一時解放しました")
                    was_registing = True
                    print("⏸️ 登録中のため認証処理を一時停止")
                    time.sleep(0.5)  # ポーリング間隔（短め）
                    continue
                else:
                    if was_registing is True:
                        # True -> False に遷移した瞬間だけ再オープン
                        self.open_all_cameras()
                        print("[INFO] 登録完了。カメラを再オープンしました")
                    was_registing = False

                # 通常フロー（認証）
                CaptureBuffer.clean_frame()
                for i, cap in self.cap_dict.items():
                    ok, frame = cap.read()
                    if ok:
                        CaptureBuffer.save_frame(frame, f"camera_{i}.jpg")
                    print("写真を保存"+str(i))

                # 認証
                self.__Authentication()
                # 成功でも失敗でもまつ
                time.sleep(0.5)

                logging.info("１サイクル終了、所要時間："+str(time.time()-timg)+"秒")

        except KeyboardInterrupt:
            print("\n[INFO] ユーザー中断、プログラムを終了します。")
        finally:
            print("\nバックシステム終了")
            cv2.destroyAllWindows()

    def release_all_cameras(self):
        if self.cap_dict:
            for i, cap in self.cap_dict.items():
                cap.release()
                print(f"[INFO] カメラ {i} のリソースを解放しました。")

    def open_all_cameras(self):
        for i in self.cap_dict.keys():
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            self.cap_dict[i] = cap
            print(f"[INFO] カメラ {i} を開きました。")



    def __Authentication(self):
        for file_path in CaptureBuffer.files:
            # 1枚一致ではなく、登録画像との距離・平均値で認証する
            name_roma, info = recognize_image_average(file_path, DB_DIR)

            # 今回のフレームで認証できなかったら次の画像にいく
            if name_roma is None:
                continue

            # 同じ人物が連続で認証されたか確認するよ
            if self.current_match_name == name_roma:
                self.current_match_count += 1
            else:
                self.current_match_name = name_roma
                self.current_match_count = 1

            # 判定状況をログとして見えるようにするよ
            print(
                f"認証候補: {name_roma} "
                f"{self.current_match_count}/{self.REQUIRED_MATCH_COUNT} "
                f"best={info['best_distance']:.4f} "
                f"avg={info['avg_nearest_distance']:.4f} "
                f"hits={info['registered_match_count']}/{info['required_registered_matches']}"
            )

            # 必要回数連続で成功するまではあけない
            if self.current_match_count < self.REQUIRED_MATCH_COUNT:
                return False

            # 次の判定用に連続カウントリセット
            self.current_match_name = None
            self.current_match_count = 0

            now = time.time()

            # 同じ顔で、前回の開錠から指定秒数以内なら開錠しない
            if (
                self.last_face_name == name_roma
                and now - self.last_face_timestamp < self.FACE_UNLOCK_COOLDOWN_SEC
            ):
                print(f"開錠スキップ: {name_roma}")
                return True

            # 開錠した顔とじかん記録
            self.last_face_name = name_roma
            self.last_face_timestamp = now

            # どのカメラで認証されたかを表示
            match = re.search(r"camera_(\d+)\.jpg", file_path)
            if match:
                index = int(match.group(1))
                print("撮影されたカメラのindexは" + str(index))

            # あける
            self.__open_sesami()
            return True

        # どのカメラ画像でも一致しなかった場合は連続成功をリセット
        self.current_match_name = None
        self.current_match_count = 0
        return False



    def __open_sesami(self):
        # 開錠 -> 一定時間後の自動施錠も予約！！！！！！
        request_unlock()
        print("認証成功")


    #region socket
    HOST = '127.0.0.1'
    PORT = 44444

    def socket_receiver(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.HOST, self.PORT))
            print(f"🟢 UDPポート {self.PORT} を監視中...")
        except OSError as e:
            print(f"⚠️ ポートバインドエラー: {e}")
            print(f"ポート {self.PORT} は既に使用されている可能性があります")
            return

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                recv_msg = data.decode('utf-8').strip()
                print(f"📩 {addr} からのメッセージを受信：{recv_msg}")

                if recv_msg == "startRegisting":
                    self.isRegisting = True
                    print("✅ 現在の状態：登録中")
                elif recv_msg == "finishRegisting":
                    self.isRegisting = False
                    print("❎ 現在の状態：未登録")
                else:
                    print(f"⚠️ 不明なメッセージ：{recv_msg}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"❌ 受信エラー: {e}")
                break

    #endregion


