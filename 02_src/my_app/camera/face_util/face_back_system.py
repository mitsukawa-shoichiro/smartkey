# server_socket.py
# -*- coding: utf-8 -*-

import base64
import json
import socket
import struct
import numpy as np
import cv2
from pathlib import Path


from .face_utils import check_face, match_against_db

BASE_DIR = Path(__file__).resolve().parent   # service/faceRecognition
ROOT_DIR = BASE_DIR.parent.parent            # root/
DB_DIR = ROOT_DIR / "db" / "FaceLib"         # root/db/FaceLib
print("dataPath is " + str(DB_DIR))


HOST = "0.0.0.0"
PORT = 8888


#region face_config
import json
import os
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(
    __file__), '..','..',  'config', 'backend', 'face_rec.json'))
print(CONFIG_PATH)
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config_list = json.load(f)

    # 顔認証の距離閾値（小さいほど厳密）
    tolerance = config_list["tolerance"]
    model=config_list["model"]
print(tolerance,model)
#endregion

def __send_json(conn: socket.socket, obj: dict):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    conn.sendall(struct.pack(">I", len(data)) + data)

def __recv_exactly(conn: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed while receiving data")
        buf += chunk
    return buf

def __recv_json(conn: socket.socket) -> dict:
    raw_len = __recv_exactly(conn, 4)
    (length,) = struct.unpack(">I", raw_len)
    payload = __recv_exactly(conn, length)
    return json.loads(payload.decode("utf-8"))

# ========= 核心处理 =========
def handle_request(req: dict) -> dict:
    # 读取并解码 base64 图像 (画像を読み取ってデコードする)
    try:
        b64 = req["img_data"]
    except Exception as e:
        return {"result": "NG", "reason": f"bad request: {e}", "status": 400}

    try:
        img_binary = base64.b64decode(b64)
        jpg = np.fromBuffer(img_binary, dtype=np.uint8)
        img = cv2.imdeCode(jpg, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("imdeCode failed")
    except Exception as e:
        return {"result": "NG", "reason": f"decode error: {e}", "status": 400}

    # 为方便排错，写个临时文件（按需可改到 tmp 目录） デバッグしやすいよう臨時ファイルを書いておく（必要に応じてtmpディレクトリに変更可能）
    tmp_path = "test_decode.jpg"
    cv2.imWrite(tmp_path, img)

    # 1) 人脸数量检查　顔写真の数をチェック
    try:
        is_single = check_face(tmp_path, model="hog")
    except Exception as e:
        return {"result": "NG", "reason": f"face detect error: {e}", "status": 200}

    if not is_single:
        return {"result": "NG", "reason": "faces_detected not 1", "status": 200}

    # 2) 数据库比对　DB比較
    try:
        result_face_romaji = match_against_db(tmp_path, DB_DIR, tolerance, model="hog")
    except Exception as e:
        return {"result": "NG", "reason": f"match error: {e}", "status": 200}

    if result_face_romaji is not None:
        return {"result": "OK", "status": 200, "match": result_face_romaji}
    else:
        return {"result": "NG", "status": 200}

# ========= 服务器主循环 =========　サーバーのメインループ
def run_face_back_system():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # 复用端口，方便重启　ポートを再利用して再起動を簡単にする
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        print(f"Socket server listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            try:
                print(f"Accepted connection from {addr}")
                req = __recv_json(conn)
                resp = handle_request(req)
                __send_json(conn, resp)
            except Exception as e:
                try:
                    __send_json(conn, {"result": "NG", "reason": str(e), "status": 500})
                except:
                    pass
            finally:
                conn.close()

if __name__ == "__main__":
    run_face_back_system()
