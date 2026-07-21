import threading
import signal
import time

stop_event = threading.Event()
threads = []

def worker(name):
    while not stop_event.is_set():
        print(f"{name}: working...")
        stop_event.wait(1)

    print(f"{name}: stopped")

def signal_handler(sig, frame):
    print("\nShutdown requested")
    stop_event.set()

def wait_event(interval_sec):
    while not stop_event.is_set():
        stop_event.wait(interval_sec)

def main():
    try:
        # 3スレッド起動
        for i in range(3):
            t = threading.Thread(target=worker, args=(f"Thread-{i}",))
            t.start()
            threads.append(t)

        wait_event(0.5)
    except Exception as e:
        print(f"エラー: {e}")
        stop_event.set()
    finally:
        stop_event.set()

        for t in threads:
            t.join()


    print("All threads stopped")

signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    main()
