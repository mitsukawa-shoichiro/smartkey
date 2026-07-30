# 1. ライブラリのインポート
from os import name
from smartcard.Exceptions import NoCardException
import json
import os
import pythoncom
from my_app.service.utils.usb_card_readers import resolve_readers
import logging

logger = logging.getLogger(__name__)  # logに書き込む用

# USB設定ファイルのパスを指定


#超危険、グローバル変数を塗り替えさせるな!!!!!!
def load_config():
    base_dir = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )

    CONFIG_PATH = os.path.normpath(
        os.path.join(base_dir, "config", "usb_settings.json")
    )

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)



def register_reader():
    config = load_config()
    reader_list = resolve_readers()

    if not reader_list:
        logger.info("カードリーダーが見つかりませんでした")
        return None

    if len(reader_list) == 1:
        r,s = reader_list[0]
        return r

    if len(reader_list) > 1:
        device = config["devices"]
        info = device["出口"]
        exit_id = info["serial"]
        for r, s in reader_list:
            if exit_id in str(s):
                return r


def scan_card():
    pythoncom.CoInitialize()  # COM初期化
    # 2. カードリーダーを取得
    register_readers = register_reader()
    if not register_readers:
        logger.error("カードリーダーが接続されてません")
        return None
    # 3. カードリーダーをチェック
    logger.info(f"カードリーダー1をチェック中: {register_readers}")
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
            logger.info(f"登録用リーダーでカードを検出、IDm: {idm}")
            connection.disconnect()
            return idm  # カードIDを返す
        else:

            connection.disconnect()
            return None

    except Exception as e:
        logger.info(f"登録用リーダーでエラーが発生しました: {e}")
        return None


def scan_card_reader() -> int:
    """
    複数のカードリーダーを走査し、カードIDを取得できた
    リーダーのインデックスを返す。見つからなければ -1。
    """
    reader_list = resolve_readers()

    for idx, (reader, serial) in enumerate(reader_list):
        print(idx)
        conn = None

        try:
            conn = reader.createConnection()
            conn.connect()

            GET_IDM_APDU = [
                0xFF,
                0xCA,
                0x00,
                0x00,
                0x00,
            ]

            response, sw1, sw2 = conn.transmit(
                GET_IDM_APDU
            )

            if [sw1, sw2] == [0x90, 0x00] and response:
                idm = "".join(
                    format(byte, "02X")
                    for byte in response
                )

                print(
                    f"カードリーダーでカードを検出、"
                    f"IDm:{idm} / "
                    f"ReaderIndex:{idx} / "
                    f"Serial:{serial}"
                )

                return idx

        except NoCardException:
            continue

        except Exception as e:
            print(f"エラー: {e}")
            continue

        finally:
            try:
                if conn:
                    conn.disconnect()
            except Exception:
                pass

    print("no card")
    return -1

if __name__ == "__main__":
    scan_card()
