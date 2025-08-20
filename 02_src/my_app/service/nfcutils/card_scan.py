# 1. ライブラリのインポート
from os import name
from smartcard.Exceptions import NoCardException
import json
import os
import pythoncom
from service.utils.usb_card_readers import get_readers

# USB設定ファイルのパスを指定
def load_config():
    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )

    CONFIG_PATH = os.path.normpath(
        os.path.join(base_dir,"config", "usb_settings.json")
    )

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def register_reader():
    config = load_config()
    reader_list = get_readers()
    
    if not reader_list:
        print("カードリーダーが見つかりませんでした")
        return None
    
    if len(reader_list) == 1:
        return reader_list[0]
    
    if len(reader_list) > 1:
        exit_id = config.get("出口")
        for r,s in reader_list:
            if exit_id in str(s):
                return r

register_readers = register_reader()

def scan_card():
    pythoncom.CoInitialize()  # COM初期化
    # 2. カードリーダーを取得
    if not register_readers:
        return None
    # 3. カードリーダーをチェック
    print(f"カードリーダー1をチェック中: {register_readers}")
    try:
        # カードリーダーに接続
        connection = register_readers.createConnection()
        connection.connect()
            
        # カードを読み取り
        GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(GET_IDM_APDU)
            
        # 読み取り成功の場合
        if sw1 == 0x90 and sw2 == 0x00:
            idm = ''.join(format(byte, '02X') for byte in response)
            print(f"登録用リーダーでカードを検出、IDm:", idm)
            connection.disconnect()
            return idm  # カードIDを返す
        else:
            print(f"登録用リーダーでカードを検出できませんでした")
            connection.disconnect()
            return None

    except Exception as e:
        print(f"登録用リーダーでエラーが発生しました:", e)
        return None

if __name__ == "__main__":
    scan_card()