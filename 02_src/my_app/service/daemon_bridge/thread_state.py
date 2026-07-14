"""
複数のGUI画面(card_check.py等)から共有される、
登録処理用スレッドの状態を保持するモジュール。

スレッドをそれぞれ別のモジュールから開始したり停止したりする関係上、ここに切り離しました。
登録スレッド開始時にthreading.Thread(~~~)をこのthread_handleに入れてください、
"""
import threading

thread_handle: threading.Thread | None = None
stop_event = threading.Event()