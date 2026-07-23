"""
解錠操作をいつ実行すべきか判断する層(施錠はまだ実装してませんがここにあってもいいと思います。)
責務は「いつすべきかの判断」まで。
SESAMEの細かい仕様はsesame.pyへ、
ここではあくまで開ける、閉める、確認する程度の粒度

"""
import threading
import time
import logging
from my_app.service.utils.sesame import is_sesame_locked
from my_app.service.utils.sesame_dispatch import unlock_by_config

logger = logging.getLogger(__name__)

class UnlockGate:
    """
    解錠リクエスト -> 施錠間 の解錠リクエストと連続解錠リクエストをはじくためのゲート
    主要機能
    -解錠したら"施錠待ち"状態に移行
    -施錠待ち状態中はtry_unlockがFalseを返し解錠リクエストをはじく
    -施錠待ち状態中はスレッドでSESAMEが施錠済を返すまでポーリング
    -ポーリングは取りこぼす可能性を考慮し、施錠待ち状態は30秒で解除される
    """

    def __init__(self, poll_interval_sec=4.0, max_wait_sec=30.0, min_cooldown_sec=6.0):
        self.poll_interval_sec = float(poll_interval_sec)# ポーリング間隔
        self.max_wait_sec = float(max_wait_sec)# 最大施錠待ち時間
        self.min_cooldown_sec = float(min_cooldown_sec)# 連続解錠クールダウン

        self._lock = threading.Lock()
        self._waiting_for_lock = False# 施錠待ちブロッキング状態
        self._unlocked_at = 0.0# 最後に解錠された時間
        self._poll_thread = None# ポーリングスレッドハンドル

    def try_unlock(self, user_id):
        """
        解錠待ち or 解錠クールダウン中 の解錠リクエストをはじく
        Args:
            user_id (int): ユーザーID

        Returns:
            解錠コマンドを送信しない時  -> False
            解錠コマンドを送信する時    -> True
        """
        with self._lock:
            now = time.monotonic()

            if self._waiting_for_lock:
                logger.debug("施錠待ち中の為解錠リクエストをスキップ user_id=%s", user_id)
                return False

            if now - self._unlocked_at < self.min_cooldown_sec:
                logger.debug("クールダウン中の為解錠リクエストをスキップ user_id=%s", user_id)
                return False

            # 解錠送信中状態変数
            self._waiting_for_lock = True
            self._unlocked_at = now

        ok = unlock_by_config(user_id)# 解錠コマンド送信

        # 解錠送信失敗時は一応状態の解除もしておく
        if not ok:
            with self._lock:
                self._waiting_for_lock = False

            logger.warning("解錠コマンド送信失敗、施錠待ちの解除 user_id=%s", user_id)
            return False
        logger.info("解錠コマンド送信成功、施錠待ち開始 user_id=%s", user_id)

        # スレッド開始
        self._start_lock_watch()
        return True

    def _start_lock_watch(self):
        """
        ポーリングスレッドを開始する関数。
        既にある時は作成しない、ハンドルも設定
        """
        if self._poll_thread is not None and self._poll_thread.is_alive():
            return
        self._poll_thread = threading.Thread(
            target=self._watch_until_locked, name="SesameLockWatch", daemon=True
        )
        self._poll_thread.start()

    def _watch_until_locked(self):
        """
        スレッド本体、poll_interval_secごとに施錠状態か確認する関数
        """
        started = time.monotonic()
        try:
            while True:
                time.sleep(self.poll_interval_sec)

                elapsed = time.monotonic() - started
                if elapsed >= self.max_wait_sec:
                    logger.warning("施錠確認がタイムアウト(%.0f秒)、施錠待ちを解除", self.max_wait_sec,)
                    break

                locked = is_sesame_locked()

                if locked is True:
                    logger.info("施錠の確認、施錠待ちの解除(所要 %.1f秒)", elapsed)
                    break
                elif locked is None:
                    logger.debug("施錠状態の取得に失敗、リトライします(%.1f秒経過)", elapsed)
                    continue
                # 解錠後 未施錠状態 = False
                else:
                    logger.debug("未施錠、ポーリング継続(%.1f秒経過)", elapsed)
        finally:
            with self._lock:
                self._waiting_for_lock = False

# グローバルな変数 (全認証は共通クールダウン)
unlock_gate = UnlockGate(poll_interval_sec=4.0, max_wait_sec=30.0, min_cooldown_sec=6.0)

def request_unlock(user_id):
    """
    解錠リクエストの入り口
    """
    return unlock_gate.try_unlock(user_id)