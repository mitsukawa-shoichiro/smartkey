# 1. ライブラリのインポート
from os import name
from smartcard.Exceptions import NoCardException
from smartcard.System import readers

def scan_card():
    # 2. カードリーダーを取得
    reader_list = readers()
    register_reader = reader_list[0]
    # 3. カードリーダーをチェック
    print(f"カードリーダー1をチェック中: {register_reader}")
    try:
        # カードリーダーに接続
        connection = register_reader.createConnection()
        connection.connect()
            
        # カードを読み取り
        GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
        response, sw1, sw2 = connection.transmit(GET_IDM_APDU)
            
        # 読み取り成功の場合
        if sw1 == 0x90 and sw2 == 0x00:
            idm = ''.join(format(byte, '02X') for byte in response)
            print(f"登録用リーダー 1 でカードを検出、IDm:", idm)
            connection.disconnect()
            return idm  # カードIDを返す
        else:
            print(f"カードリーダー 1 でカードを検出できませんでした")
            connection.disconnect()
            return None

    except Exception as e:
        print(f"カードリーダー 1 でエラー:", e)
        return None

if __name__ == "__main__":
    scan_card()