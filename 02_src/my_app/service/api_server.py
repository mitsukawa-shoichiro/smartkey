import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from enum import Enum
import db_manager
import os
import time
import subprocess
from nfcutils.card_scan import scan_card

class CardReaderState(Enum):
    REGISTERING = "registering"      # カード登録状態
    AUTHENTICATING = "authenticating" # カード認証状態

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.." + "/db"
DB_PATH = os.path.join(BASE_DIR, 'dataBase.db')
sys.path.append('DataBase')
app = Flask(__name__)
CORS(app)

#region status

# グローバル状態管理
current_state = CardReaderState.AUTHENTICATING  # デフォルト状態

@app.route('/api/card/set_state', methods=['POST'])
def set_state():
    global current_state
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body"}), 400
    state = data.get('state')
    if state == "registering":
        current_state = CardReaderState.REGISTERING
    elif state == "authenticating":
        current_state = CardReaderState.AUTHENTICATING
    else:
        return jsonify({"error": "Invalid state"}), 400
    return jsonify({"state": current_state.value})

@app.route('/api/card/get_state', methods=['GET'])
def get_state():
    return jsonify({"state": current_state.value})
    
#endregion

@app.route('/api/card/get_card', methods=['GET'])
def get_card():
    card_id=scan_card()
    return jsonify({"card_id": card_id})


def receive_card(card_id):
    if current_state == CardReaderState.AUTHENTICATING:
        if(db_manager.check_card(card_id)):
            unlock()
    
    elif current_state == CardReaderState.REGISTERING:
        get_card()

def unlock():
    server_dir = os.path.dirname(os.path.abspath(__file__))
    sesami_path = os.path.join(server_dir, "utils", "sesami.js")
    result = subprocess.run(
        ["node", sesami_path],
        capture_output=True,
        text=True,
        check=True
    )
    time.sleep(6) 

if __name__ == '__main__':
    app.run(debug=True, port=5000)
