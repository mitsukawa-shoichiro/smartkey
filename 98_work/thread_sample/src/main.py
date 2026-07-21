
import threading
import signal

# スレッド停止通知用のイベント
# set() が呼ばれると全スレッドに停止を通知できる
stop_event = threading.Event()

# 起動したスレッドを保持するリスト
threads = []


def worker(name):
    """
    ワーカースレッド処理
    stop_event がセットされるまで繰り返し処理を行う
    """
    while not stop_event.is_set():
        print(f"{name}: working...")

        # 最大1秒待機
        # stop_event がセットされた場合は即座に復帰する
        stop_event.wait(1)

    print(f"{name}: stopped")


def signal_handler(sig, frame):
    """
    Ctrl+C(SIGINT)受信時の処理
    全スレッドへ停止要求を通知する
    """
    print("\nShutdown requested")
    stop_event.set()


def wait_event(interval_sec):
    """
    メインスレッドの待機処理

    stop_event がセットされるまで待機を継続する。
    wait() を使用することで停止要求を即時検知できる。
    """
    while not stop_event.is_set():
        stop_event.wait(interval_sec)


def main():
    try:
        # 3スレッド起動
        for i in range(3):
            t = threading.Thread(
                target=worker,
                args=(f"Thread-{i}",)
            )

            # スレッド開始
            t.start()

            # join用に保持
            threads.append(t)

        # 停止要求が来るまで待機
        wait_event(0.5)

    except Exception as e:
        # エラー発生時は停止要求を通知
        print(f"エラー: {e}")
        stop_event.set()

    finally:
        # 正常終了・異常終了を問わず停止要求を通知
        stop_event.set()

        # 全スレッドの終了を待機
        for t in threads:
            t.join()

    print("All threads stopped")


# Ctrl+C(SIGINT)時に signal_handler を呼び出す
signal.signal(signal.SIGINT, signal_handler)

# プログラムのエントリーポイント
if __name__ == '__main__':
    main()
