# reader_daemon.py
import time, json, threading, queue, requests, hashlib
from smartcard.System import readers
from smartcard.Exceptions import NoCardException
from smartcard.util import toHexString
import time


POLL = [0x00, 0xFF, 0xFF, 0x01, 0x00]    # FeliCaポーリング
API  = "http://127.0.0.1:5000/api/users/check_card"   # バックエンドAPI
DEDUP_WINDOW = 5.0                       # 同じカードはN秒間無視
event_q = queue.Queue()


def sender():
    """非同期送信スレッド、ポーリングをブロックしない"""
    while True:
        idm = event_q.get()
        payload = {"card_id": idm,
                   "time": time.time()}
        try:
            print("送信成功")
            requests.post(API, json=payload, timeout=2)
        except Exception as e:
            print("送信失敗:", e)

def reader_loop():
    rdr = readers()[0]
    conn = rdr.createConnection()
    print("使用カードリーダー:", rdr)

    while True:
        try:
            conn.connect()
            GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = conn.transmit(GET_IDM_APDU)
            if [sw1, sw2] == [0x90, 0x00]:
                idm = ''.join(format(byte, '02X') for byte in response)
                event_q.put(idm)
                print("IDmをキャプチャ:", idm)
                time.sleep(DEDUP_WINDOW)  
            conn.disconnect()
            time.sleep(0.05)             # CPU負荷軽減
        except NoCardException:
            time.sleep(0.05)
        except Exception as e:
            print("例外:", e); time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=sender, daemon=True).start()
    reader_loop()
