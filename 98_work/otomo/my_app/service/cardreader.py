# reader_daemon.py
# from service import card_sys
import time
import json
import threading
from smartcard.System import readers
from smartcard.Exceptions import NoCardException
import time
import sys
import os
import logging
import socket



now = time.time()
HEARTBEAT_ERROR_GAP_S = 10

POLL = [0x00, 0xFF, 0xFF, 0x01, 0x00]    # FeliCaポーリング

heartbeatsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

state = "authenticating"

BASE_DIR = os.path.dirname(__file__) + "\\..\\config"
print(BASE_DIR)
config_path = os.path.join(BASE_DIR, "usb_settings.json")

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)

COUNT_READER = config["設置台数"]




# region logs
# logs ディレクトリのパスを sys.path に追加
LOGS_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..'))
if LOGS_PATH not in sys.path:
    sys.path.insert(0, LOGS_PATH)
# endregion

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import service.cardsystem as CardSys
from enum import Enum
class CardReaderState(Enum):
    REGISTERING = "registering"      # カード登録状態
    AUTHENTICATING = "authenticating"  # カード認証状態

class CardReader:   
    DEBUG=False

    state = "authenticating"
    reader_list = []

    systemError = False
    thread_card_check:threading.Thread=None


    SOCKET_HOST = '127.0.0.1'
    HEARTBEAT_PORT = 54321
    def __init__(self):
        self.systemError = False

    def ReadConfig(self):
        pass

    def get_reader(self):
        reader_list = readers()  # [(reader, serial), ...]
        systemError = False
        logging.info(f"カードリーダーの数: {len(reader_list)}")
        while True:
            if len(reader_list) >= COUNT_READER:
                logging.info("カードリーダーの数が設定台数と一致しましたのでカードの読み込みがスタートしました。")
                return reader_list

            if COUNT_READER > len(reader_list) and systemError:
                logging.error(
                    f"カードリーダーの数が不足しているためカードの読み込みがスタートしていません: {len(reader_list)} / {COUNT_READER}")
                systemError = True

            return None




    #region　カード認証機能
    def reader_loop(self):
        print(COUNT_READER)
        if not self.DEBUG:
            try:    
                reader_list = self.get_reader()
            except Exception as e:
                print(f"ERROR: カードリーダー異常: {e}")
                reader_list= []


        while True:
            if self.systemError:
                logging.info("システムエラー、カードリーダースレッド終了")
                break

            # 全てのカードリーダーをチェック
            # TODO 修正
            if not self.DEBUG:
                if len(reader_list) >0:
                    number=0
                    for reader in reader_list:
                        try:
                            # カードリーダーに接続
                            conn = reader.createConnection()
                            conn.connect()

                            # カードを読み取り
                            GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                            response, sw1, sw2 = conn.transmit(GET_IDM_APDU)

                            # 読み取り成功の場合
                            if [sw1, sw2] == [0x90, 0x00]:
                                idm = ''.join(format(byte, '02X') for byte in response)
                                if (state != "registering"):
                                    CardSys.receive_card(idm, number)
                                print(f"カードリーダー {number} でカードを検出、IDm:", idm)

                                conn.disconnect()
                                break  # カードを検出したら他のリーダーをチェックしない
                            else:
                                conn.disconnect()

                        except NoCardException:
                            conn.disconnect()
                        except Exception as e:
                            logging.error(f"カードリーダー {number} でエラー:", e)
                            continue
                        number+=1

                if (len(reader_list) < COUNT_READER) :
                    break   

            print(self.check_is_alive())
            time.sleep(1)  # CPU負荷軽減
            # break
    #endregion


    #region Thread Control

    def start_thread(self):
        # 通信
        print("Starting threads...")
        if  self.thread_card_check!=None and self.thread_card_check.is_alive():
            print("Thread already running.")
            return
        if self.thread_card_check==None:
            self.thread_card_check = threading.Thread(target=self.reader_loop)
            self.thread_card_check.start()
            logging.info("thread_card_check started.")

        self.systemError = False

    def stop_thread(self):
        print("Stopping thread...")
        self.systemError = True
        if self.thread_card_check:
            self.thread_card_check.join(timeout=2)
            print("thread_card_check stopped.")
        


    def check_is_alive(self):
        return self.thread_card_check.is_alive()


    #endregion


if __name__ == "__main__":
    cardreader=CardReader()
    cardreader.start_thread()


