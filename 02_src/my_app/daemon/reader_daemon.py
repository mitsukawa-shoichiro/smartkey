# reader_daemon.py
import threading
import queue
import time

import logging
import socket
import pythoncom
import sqlite3
from smartcard.Exceptions import NoCardException

import my_app.logs.log_config_service
from my_app.config.reader_config import READER_COUNT, REGISTER_SERIAL, norm_serial
from my_app.service.utils.usb_card_readers import resolve_readers
from my_app.service import card_sys

now = time.time()
HEARTBEAT_ERROR_GAP_S = 10
HEARTBEAT_HOST = '127.0.0.1'
HEARTBEAT_PORT = 54321
heart_beat_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 登録モード中、検知したIDmをGUI(register.py)へ送り返すための宛先。
# GUI側はこのポートでUDP受信待ちをする(daemon -> GUIの一方向通知)。
REGISTER_NOTIFY_HOST = '127.0.0.1'
REGISTER_NOTIFY_PORT = 10001

#localhost指定
DAEMON_HOST = '127.0.0.1'
#受信ポート番号
DAEMON_PORT = 10000

state = "authenticating"
REGISTERING_TIMEOUT_S = 45
state_changed_at = time.time()


stop_event = threading.Event()
_threads = []


GET_IDM_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
event_q = queue.Queue()
logger = logging.getLogger(__name__)  # logに書き込む用

def sender():
    """
    キューで受け取った値を実際に認証する関数に渡す関数
    非同期送信スレッド、ポーリングをブロックしない
    """
    while not stop_event.is_set():
        #ここでキューから受け取り
        try:
            idm, reader_serial = event_q.get(timeout=1)
        except queue.Empty:
            continue
        try:
            #ここで認証
            card_sys.receive_card(idm, reader_serial)
            logger.info(f"送信成功（リーダー{int(reader_serial)+1}）")

        except sqlite3.Error as e:
            logger.error(f"DBエラーにより送信失敗: {e}")

        except Exception as e:
            logger.exception(f"不明なエラーにより送信失敗: {e}")


def wait_readers() -> None:
    """
    カードリーダーを確認してJSONファイルで設定した数より少ない場合に停止状態にする関数です。
    reader_loopの最初で呼ばれています。
    """
    logged = False
    while not stop_event.is_set():
        reader_list = resolve_readers()  # [(reader, serial), ...]
        if len(reader_list) >= 1:
            logger.info("カードリーダーの数が設定台数と一致しましたのでカードの読み込みがスタートしました。")
            return reader_list

        if  not logged:
            logger.error(
                f"カードリーダーの数が不足しているためカードの読み込みがスタートしていません: {len(reader_list)} / {READER_COUNT}")
            logged = True
        msg = "DEAD"
        send_message(msg)
        stop_event.wait(1)



VALID_STATES = {"registering", "authenticating"}

def receiver():
    """
    GUI(register.py)からのUDPを待ち受け、認証/登録モードの切り替えを受け取る。
    受信した文字列はVALID_STATESで検証したうえでchangeState()へ渡す。
    """
    try:
        sock_check = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        logger.exception("受信ソケットの生成に失敗")
        return

    try:
        with sock_check:                       # ← with が close を保証
            sock_check.bind((DAEMON_HOST, DAEMON_PORT))
            sock_check.settimeout(1)
            logger.info("receiver待受開始: %s:%s", DAEMON_HOST, DAEMON_PORT)

            while not stop_event.is_set():
                try:
                    data, addr = sock_check.recvfrom(100)
                except TimeoutError:
                    continue
                except OSError:
                    logger.exception("recvfromでエラー")
                    break

                message = data.decode("utf-8", errors="replace").strip()
                if not message:
                    continue

                if message not in VALID_STATES:
                    logger.warning("不正な状態指定を無視: %r (from %s)", message, addr)
                    continue

                try:
                    changeState(message)       # ← 例外をループ内で閉じ込める
                except Exception:
                    logger.exception("状態変更に失敗: %r", message)

    except OSError:
        logger.exception("受信ソケットの初期化に失敗（多重起動の可能性）")
    finally:
        logger.info("receiverを終了します")


def send_message(message, host=HEARTBEAT_HOST, port=HEARTBEAT_PORT):
    """
    UDPで1回だけメッセージを送る汎用関数。
    宛先を省略すると、check_aliveへのハートビート送信になる。
    登録モードの通知(GUI宛て)など、別ポートへ送りたい場合はhost/portを指定する。
    """
    try:
        heart_beat_socket.sendto(message.encode('utf-8'), (host, port))
    except Exception as e:
        logger.error(f"メッセージ送信失敗: {e} (宛先: {host}:{port}, 内容: {message})")


def notify_registered_card(idm: str):
    """
    登録モード中に出口リーダーで検知したIDmを、GUI(register.py)へ通知する。
    通常の認証フロー(event_q/card_sys.receive_card)は一切経由しない。
    """
    send_message(idm, host=REGISTER_NOTIFY_HOST, port=REGISTER_NOTIFY_PORT)
    logger.info(f"登録モード: IDmをGUIへ通知しました: {idm}")

def reader_loop():
    """
    バックシステムの本体、この関数がスレッドで回り続けて
    各関数の呼び出し等の音頭を取っています。

    主要関数一覧
        get_reader(): カードリーダー状態確認
        get_readers(): カードリーダー情報読み取り
        notify_registered_card(idm): 登録用スレッドへIDm(カード番号)を送信
        eventq.put((idm, reader_serial)): 認証用スレッドへIDm(カード番号)を送信
        changeState(newState): 登録/認証状態の変更
    """
    global now

    pythoncom.CoInitialize()          # スレッドにつき1回
    try:
        logger.info("設定台数: %s", READER_COUNT)
        wait_readers()                  # 起動時にリーダーが揃うまで待つ

        while not stop_event.is_set():
            try:
                reader_list = resolve_readers()

                for reader, reader_serial in reader_list:
                    conn = None
                    try:
                        conn = reader.createConnection()
                        conn.connect()
                        response, sw1, sw2 = conn.transmit(GET_IDM_APDU)

                        if [sw1, sw2] != [0x90, 0x00]:
                            logger.debug("リーダー%s 応答異常 SW=%02X%02X", reader_serial, sw1, sw2)
                            continue

                        idm = bytes(response).hex().upper()
                        logger.info("リーダー %s でカード検出 IDm: %s", reader_serial, idm)

                        if state == "registering":
                            if len(reader_list) == 1 or norm_serial(reader_serial) == REGISTER_SERIAL:
                                notify_registered_card(idm)
                        else:
                            event_q.put((idm, reader_serial))
                        break
                    except NoCardException:
                        pass                                     # カード無しは正常系
                    except Exception:
                        logger.exception("カードリーダー %s でエラー", reader_serial)
                    finally:
                        if conn is not None:
                            try:
                                conn.disconnect()
                            except Exception:
                                logger.exception("disconnect失敗 (リーダー%s)", reader_serial)

                gap = time.time() - now
                now = time.time()
                if gap > HEARTBEAT_ERROR_GAP_S:
                    logger.error("ポーリングが遅延しています: %.1f秒", gap)

                if state == "registering" and time.time() - state_changed_at > REGISTERING_TIMEOUT_S:
                    logger.warning("登録状態が%s秒を超えたためauthenticatingへ戻します", REGISTERING_TIMEOUT_S)
                    changeState("authenticating")

                send_message("DEAD" if len(reader_list) < READER_COUNT else "ALIVE")

            except Exception:
                logger.exception("カードリーダーループでエラーが発生しました")
                send_message("DEAD")
            finally:
                stop_event.wait(1)     # 正常・異常どちらでも必ず待つ
    finally:
        pythoncom.CoUninitialize()


def changeState(newState):
    global state, state_changed_at
    state = newState
    state_changed_at = time.time()
    logger.info(f"状態が変更されました: {state}")


def main():
    global _threads
    stop_event.clear()
    _threads = [
    threading.Thread(target=sender, daemon=True, name="sender"),
    threading.Thread(target=receiver, daemon=True, name="receiver"),
    threading.Thread(target=reader_loop, daemon=True, name="reader_loop"),
    ]
    for t in _threads:
        t.start()


def stop(timeout: float = 5.0):
    """
    停止シグナルを立て、各スレッドの終了を待つ。

    timeout秒待っても終わらないスレッドは諦める(daemon=Trueなので、
    プロセス終了時に強制的に終わる)。SESAMEへのリクエスト中などは
    どうしても待たされるため、無限には待たない。
    """
    logger.info("reader_daemonの停止を開始します")
    stop_event.set()

    # receiverはrecvfromでブロックしている可能性があるため、
    # 自分自身にダミーを送って起こす(settimeoutでも起きるが、こちらの方が速い)
    try:
        heart_beat_socket.sendto(b"", (DAEMON_HOST, DAEMON_PORT))
    except OSError:
        pass

    for t in _threads:
        t.join(timeout=timeout)
        if t.is_alive():
            logger.warning("%sが%s秒以内に終了しませんでした", t.name, timeout)

    logger.info("reader_daemonを停止しました")


if __name__ == "__main__":
    main()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()