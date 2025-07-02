# reader_daemon.py
import time, json, threading, queue, requests, hashlib
from smartcard.System import readers
from smartcard.Exceptions import NoCardException
from smartcard.util import toHexString
import time


POLL = [0x00, 0xFF, 0xFF, 0x01, 0x00]    # FeliCa polling
API  = "http://127.0.0.1:5000/api/users/add_user"   # バックエンドAPI
DEDUP_WINDOW = 2.0                       # 同一カード N 秒内無視
event_q = queue.Queue()
last_seen = {}                           # idm -> timestamp
sender_busy = False                      # senderの状態を追跡するフラグ変数

def sender():
    """非同期送信スレッド、ポーリングをブロックしない"""
    global sender_busy
    while True:
        idm = event_q.get()
        sender_busy = True  # sender作業開始をマーク
        print(f"カード処理開始: {idm}")
        
        user_name = input("ユーザー名を入力してください:")
        user_role = input("ユーザーロールを入力してください:")
        card_name = input("カード名を入力してください:")
        payload = {
            "name": user_name,
            "role": user_role,
            "card_id": idm,
            "card_name": card_name,
            "timestamp":int(time.time()) ,
            }
        print(f"カードID: {idm}")
        print(f"タイムスタンプ: {time.time()}")
        print(f"ユーザー名: {user_name}")
        print(f"ユーザーロール: {user_role}")
        print(f"カード名: {card_name}")
        print("上記データが正しいか確認してください...")

        try:
            requests.post(API, json=payload, timeout=2)
            print("データ送信成功！")
        except Exception as e:
            print("送信失敗:", e)
        
        sender_busy = False  # sender作業完了をマーク
        print("処理完了、新しいカードの監視を継続...")

def reader_loop():
    rdr = readers()[0]
    conn = rdr.createConnection()
    print("使用カードリーダー:", rdr)

    while True:
        # senderが作業中の場合は、カード読み取りを一時停止
        if sender_busy:
            time.sleep(3)  # 短時間待機
            continue
            
        try:
            conn.connect()
            GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = conn.transmit(GET_IDM_APDU)
            if [sw1, sw2] == [0x90, 0x00]:
                idm = ''.join(format(byte, '02X') for byte in response)
                now = time.time()
                if now - last_seen.get(idm, 0) > DEDUP_WINDOW:
                    last_seen[idm] = now
                    event_q.put(idm)
                    print("IDmをキャプチャ:", idm)
            conn.disconnect()
            time.sleep(0.05)             # CPU負荷軽減
        except NoCardException:
            time.sleep(0.05)
        except Exception as e:
            print("例外:", e); time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=sender, daemon=True).start()
    reader_loop()
