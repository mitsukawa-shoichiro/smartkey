"""
登録モード中、reader_daemon.pyから送られてくるIDm通知を受信するモジュール。

daemon(別プロセス)が出口リーダーで検知したIDmをUDPで送ってくるので、
それを専用ポートで待ち受けて、GUI側から参照できる場所に保持する。
"""
import re
import socket
import threading
import logging

from my_app.service.daemon_bridge.protocol import LOCALHOST, REGISTER_NOTIFY_PORT

logger = logging.getLogger(__name__)

# daemon側は bytes(response).hex().upper() を送ってくる想定
_IDM_PATTERN = re.compile(r"\A[0-9A-F]{8,32}\Z")


def is_valid_idm(value: str) -> bool:
    """IDmとして妥当な形式か判定する(大文字16進、8〜32文字)"""
    return bool(_IDM_PATTERN.match(value))


class RegisterListener:
    """
    daemonからのIDm通知をUDPで受信し、最新の1件を保持するリスナー。

    ライフサイクル
        start()  -> bindしてから受信スレッドを開始(bind失敗はFalseで通知)
        receive_idm() -> 新着を待って取り出す
        stop()   -> 停止フラグを立ててjoinまで待つ

    stop()がjoinまで待つのは、直後のstart()で「古いスレッドが生存中」と
    誤判定されて起動がスキップされるのを防ぐため。
    """

    def __init__(self, host: str = LOCALHOST, port: int = REGISTER_NOTIFY_PORT,
                 recv_timeout: float = 1.0):
        self.host = host
        self.port = port
        self.recv_timeout = recv_timeout   # stop()できるよう定期的にブロックを抜けさせる

        self._latest_idm: str | None = None
        self._lock = threading.Lock()
        self._new_idm_event = threading.Event()

        self._thread: threading.Thread | None = None
        self._stop_flag = threading.Event()

    # region ライフサイクル
    def start(self) -> bool:
        """
        受信スレッドを開始する。registering画面の表示開始時に呼ぶこと。

        bindはこのメソッド内で同期的に行うため、ポート競合などの失敗を戻り値で判定できる。

        Returns:
            bool: 起動できた(既に起動中も含む) -> True / bind失敗 -> False
        """
        if self.is_running():
            logger.debug("リスナーは既に起動中です")
            return True

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((self.host, self.port))
            sock.settimeout(self.recv_timeout)
        except OSError:
            sock.close()
            logger.exception(
                "登録モード通知の受信ポートを確保できません(多重起動の可能性): %s:%s",
                self.host, self.port)
            return False

        self._stop_flag.clear()
        self.clear()
        self._thread = threading.Thread(
            target=self._listen_loop, args=(sock,),
            name="RegisterListener", daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout: float = 2.0):
        """受信スレッドを止める。registering画面を離れる時に呼ぶこと。"""
        self._stop_flag.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
            if thread.is_alive():
                logger.warning("リスナースレッドが%s秒以内に終了しませんでした", timeout)
        self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
    # endregion

    # region IDmの取り出し
    def receive_idm(self, timeout: float = 1.0) -> str | None:
        """
        新しいIDmが届くまで(最大timeout秒)待ち、届いたIDmを返す。

        Returns:
            str | None: IDm(時間内に届かなければNone)
        """
        if not self._new_idm_event.wait(timeout=timeout):
            return None
        self._new_idm_event.clear()
        return self.get_idm()

    def get_idm(self) -> str | None:
        """現在保持している最新のIDmを取得する(無ければNone)"""
        with self._lock:
            return self._latest_idm

    def clear(self):
        """保持しているIDmと通知フラグをリセットする(次の登録に備える)"""
        with self._lock:
            self._latest_idm = None
        self._new_idm_event.clear()
    # endregion

    def _listen_loop(self, sock: socket.socket):
        """
        UDPでIDm通知を待ち受け続けるループ。別スレッドで動かす想定。
        ソケットはstart()でbind済みのものを受け取り、ここで責任を持って閉じる。
        """
        logger.info("登録モード通知の受信待機を開始しました: %s:%s", self.host, self.port)
        try:
            with sock:
                while not self._stop_flag.is_set():
                    try:
                        data, addr = sock.recvfrom(100)
                    except TimeoutError:
                        continue
                    except OSError:
                        logger.exception("登録モード通知の受信中にソケットエラーが発生しました")
                        break

                    # 入口で大文字に正規化しておく(以降どこでも同じ形だと信じられる)
                    idm = data.decode("utf-8", errors="replace").strip().upper()
                    if not is_valid_idm(idm):
                        logger.warning("不正なIDm通知を無視: %r (from %s)", idm, addr)
                        continue

                    logger.info("登録モード: daemonからIDmを受信しました: %s (from %s)",
                                idm, addr)
                    with self._lock:
                        self._latest_idm = idm
                    self._new_idm_event.set()
        finally:
            logger.info("登録モード通知の受信待機を終了しました")


# GUI全体で1つのリスナーを共有する(受信ポートは1つしか確保できないため)
listener = RegisterListener()

# 既存の呼び出し側が壊れないようモジュール関数として公開する
start_listener = listener.start
stop_listener = listener.stop
receive_idm = listener.receive_idm
get_idm = listener.get_idm
clear_idm = listener.clear

# 旧名の互換エイリアス(呼び出し側の置き換えが済んだら削除)
wait_for_card_number = receive_idm
get_card_number = get_idm
clear_card_number = clear_idm