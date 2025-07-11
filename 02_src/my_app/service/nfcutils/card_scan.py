# 1. ライブラリのインポート
from os import name
from smartcard.Exceptions import NoCardException
from smartcard.System import readers


def scan_card():
    # 2. カードリーダーを取得
    reader_list = readers()
    print("利用可能なカードリーダー:", reader_list)
    
    # 3. 全てのカードリーダーをチェック
    for i, reader in enumerate(reader_list):
        print(f"カードリーダー {i+1} をチェック中: {reader}")
        try:
            # カードリーダーに接続
            connection = reader.createConnection()
            connection.connect()
            
            # カードを読み取り
            GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            response, sw1, sw2 = connection.transmit(GET_IDM_APDU)
            
            # 読み取り成功の場合
            if sw1 == 0x90 and sw2 == 0x00:
                idm = response
                idm_hex = ''.join(format(byte, '02X') for byte in idm)
                print(f"カードリーダー {i+1} でカードを検出、IDm:", idm_hex)
                connection.disconnect()
                return idm_hex
            else:
                print(f"カードリーダー {i+1} でカードを検出できませんでした")
                connection.disconnect()
                
        except Exception as e:
            print(f"カードリーダー {i+1} でエラー:", e)
            continue
    
    print("全てのカードリーダーでカードを検出できませんでした")
    return None

if __name__ == "__main__":
    scan_card()