"""
daemon(reader_daemon) と GUI 間のUDP通信の取り決め。
両者が同じ定義を参照することで、ポート番号の不一致を防ぐ。
"""
LOCALHOST = "127.0.0.1"

# GUI -> daemon: 認証/登録モードの切り替え
DAEMON_MODE_PORT = 10000

# daemon -> GUI: 登録モード中に検知したIDmの通知
REGISTER_NOTIFY_PORT = 10001

# daemon -> check_alive: 生存通知
HEARTBEAT_PORT = 54321

MODE_REGISTERING = "registering"
MODE_AUTHENTICATING = "authenticating"
VALID_MODES = frozenset({MODE_REGISTERING, MODE_AUTHENTICATING})