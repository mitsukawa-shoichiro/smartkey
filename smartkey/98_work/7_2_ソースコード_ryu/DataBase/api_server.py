import logging
import sys
import subprocess
from flask import Flask, jsonify, request
from flask_cors import CORS
from enum import Enum
import DB
from datetime import datetime
from nfc import nfc_Card_ScanCard


class Status(Enum):
    ADMIN = "admin"            
    USER = "user"

sys.path.append('DataBase')


# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    """ルートパス - API情報を表示"""
    return jsonify({
        'message': '従業員出勤システムAPI',
        'version': '1.0',
        'endpoints': {
            'users': '/api/users',
            'logs': '/api/logs', 
            'attend': '/api/attend',
            'card_lookup': '/api/card/lookup',
            'add_user': '/api/users/add_user',
            'delete_user': '/api/users/delete_user',
            'add_log': '/api/logs/add_access_log',
            'delete_log': '/api/logs/delete_access_log',
            'delete_attend': '/api/attend/delete_attend_record'
        }
    })

@app.route('/api/users', methods=['GET'])
def api_users():
    """ユーザー情報を取得"""
    logger.info("ユーザー情報取得リクエストを受信")
    try:
        users = DB.get_users()
        logger.info(f"{len(users)}人のユーザー情報を正常に取得")
        return jsonify(users)
    except Exception as e:
        logger.error(f"ユーザー情報取得に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def api_logs():
    """出勤記録を取得"""
    logger.info("出勤記録取得リクエストを受信")
    try:
        logs = DB.get_access_logs()
        logger.info(f"{len(logs)}件の出勤記録を正常に取得")
        return jsonify(logs)
    except Exception as e:
        logger.error(f"出勤記録取得に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/attend', methods=['GET'])
def api_attend():
    """出勤サマリーデータを取得"""
    logger.info("出勤サマリーデータ取得リクエストを受信")
    try:
        # まずサマリーデータを更新
        logger.info("出勤サマリーデータの更新を開始")
        DB.update_attendance_summary()
        logger.info("出勤サマリーデータの更新が完了")
        
        # サマリーデータを取得
        summary = DB.get_attendance_summary()
        logger.info(f"{len(summary)}件の出勤サマリー記録を正常に取得")
        
        # 詳細ログを出力
        for record in summary:
            logger.info(f"出勤記録: ユーザーID={record['user_id']}, ユーザー={record['user_name']}, "
                       f"日付={record['work_date']}, 最早={record['earliest_time']}, 最晚={record['latest_time']}")
        
        return jsonify(summary)
    except Exception as e:
        logger.error(f"出勤サマリーデータ取得に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/card/lookup', methods=['POST'])
def api_card_lookup():
    """カードIDと時間でカード所有者を検索"""
    try:
        data = request.get_json()
        card_id = data.get('card_id')
        timestamp = data.get('timestamp')

        logger.info(f"カード検索リクエストを受信: カードID={card_id}, 時間={timestamp}")
        
        if not card_id or not timestamp:
            logger.error("リクエストに必要なパラメータが不足: card_id または timestamp")
            return jsonify({'error': '必要なパラメータが不足: card_id と timestamp'}), 400
        
        # カードIDでユーザーを検索
        logger.info(f"カードID={card_id}の所有者を検索開始")
        user = DB.get_user_by_card_id(card_id)
        
        if user:
            logger.info(f"カード所有者を発見: ユーザーID={user['user_id']}, 名前={user['user_name']}, 役職={user['role']}")
            logger.info(f"カード情報: カードID={user['card_id']}, カード名={user['card_name']}")
            logger.info(f"出勤時間: {timestamp}")
            
            return jsonify({
                'message': 'カード所有者を正常に発見',
                'card_info': {
                    'card_id': card_id,
                    'timestamp': timestamp
                },
                'user_info': user
            })
        else:
            logger.warning(f"カードID={card_id}の所有者が見つかりません")
            return jsonify({
                'message': 'カード所有者が見つかりません',
                'card_info': {
                    'card_id': card_id,
                    'timestamp': timestamp
                },
                'user_info': None
            }), 404
            
    except Exception as e:
        logger.error(f"カード検索に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

#region delete
@app.route('/api/attend/delete_attend_record', methods=['DELETE'])
def delete_attend_record():
    """特定の出勤記録を削除 input:user_id work_date"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        work_date = data.get('work_date')
        
        logger.info(f"出勤記録削除リクエストを受信: ユーザーID={user_id}, 日付={work_date}")
        
        if not user_id or not work_date:
            logger.error("削除リクエストに必要なパラメータが不足: user_id または work_date")
            return jsonify({'error': '必要なパラメータが不足: user_id と work_date'}), 400
        
        # 削除機能を呼び出し
        result = DB.delete_attendance_record(user_id, work_date)
        logger.info(f"出勤記録削除が成功: {result}")
        
        return jsonify({'message': '削除が成功', 'deleted_record': result})
    except Exception as e:
        logger.error(f"出勤記録削除に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/delete_user', methods=['DELETE'])
def delete_user():
    """指定されたユーザーを削除 input:user_id"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        logger.info(f"ユーザー削除リクエストを受信: ユーザーID={user_id}")
        
        if not user_id:
            logger.error("ユーザー削除リクエストに必要なパラメータが不足: user_id")
            return jsonify({'error': '必要なパラメータが不足: user_id'}), 400
        
        # ユーザー削除機能を呼び出し
        result = DB.delete_user(user_id)
        logger.info(f"ユーザー削除が成功: ユーザー={result['user_name']}, 削除された出勤記録={result['deleted_logs_count']}件, "
                   f"削除されたサマリー記録={result['deleted_summary_count']}件")
        
        return jsonify({
            'message': 'ユーザー削除が成功',
            'deleted_user': result
        })
    except Exception as e:
        logger.error(f"ユーザー削除に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs/delete_access_log', methods=['DELETE'])
def delete_access_log():
    """指定された出勤記録を削除 input:log_id"""
    try:
        data = request.get_json()
        log_id = data.get('log_id')
        
        logger.info(f"出勤記録削除リクエストを受信: 記録ID={log_id}")
        
        if not log_id:
            logger.error("出勤記録削除リクエストに必要なパラメータが不足: log_id")
            return jsonify({'error': '必要なパラメータが不足: log_id'}), 400
        
        # 出勤記録削除機能を呼び出し
        result = DB.delete_access_log(log_id)
        logger.info(f"出勤記録削除が成功: ユーザー={result['user_name']}, 時間={result['timestamp']}")
        
        return jsonify({
            'message': '出勤記録削除が成功',
            'deleted_log': result
        })
    except Exception as e:
        logger.error(f"出勤記録削除に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500
#endregion

@app.route('/api/logs/add_access_log', methods=['POST'])
def add_access_log_api():
    """出勤記録を追加"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        timestamp = data.get('timestamp')
        card_id = data.get('card_id')
        
        logger.info(f"出勤記録追加リクエストを受信: ユーザーID={user_id}, 時間={timestamp}, カード番号={card_id}")
        
        if not user_id or not timestamp or not card_id:
            logger.error("出勤記録追加リクエストに必要なパラメータが不足: user_id または timestamp または card_id")
            return jsonify({'error': '必要なパラメータが不足: user_id と timestamp と card_id'}), 400
        
        result = DB.add_access_log(user_id, timestamp, card_id)
        logger.info(f"出勤記録追加が成功: ユーザーID={user_id}, 時間={timestamp}, カード番号={card_id}")
        
        return jsonify({
            'message': '出勤記録追加が成功',
            'added_log': result
        })
    except Exception as e:
        logger.error(f"出勤記録追加に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500
        
@app.route('/api/users/add_user', methods=['POST'])
def add_user_api():
    """ユーザーを追加"""
    try:
        data = request.get_json()
        name = data.get('name')
        role = data.get('role')
        card_id = data.get('card_id')
        card_name = data.get('card_name')
        register_date = data.get('register_date')
        
        logger.info(f"ユーザー追加リクエストを受信: 名前={name}, 役職={role}, カード番号={card_id}, カード名={card_name}")
        
        if not name or not role or not card_id or not card_name:
            logger.error("ユーザー追加リクエストに必要なパラメータが不足: name または role または card_id または card_name")
            return jsonify({'error': '必要なパラメータが不足: name, role, card_id, card_name'}), 400
        
        result = DB.add_user(name, role, card_id, card_name, register_date)
        logger.info(f"ユーザー追加が成功: ユーザーID={result['user_id']}, 名前={result['user_name']}, 役職={result['role']}")
        
        return jsonify({
            'message': 'ユーザー追加が成功',
            'added_user': result
        })
    except Exception as e:
        logger.error(f"ユーザー追加に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/check_card', methods=['POST'])
def check_card_api():
    """カードIDでユーザーを確認"""
    try:
        data = request.get_json()
        card_id = data.get('card_id')
        
        logger.info(f"ユーザー確認リクエストを受信: カード番号={card_id}")
        
        user = DB.get_user_by_card_id(card_id)
        if user:
            logger.info(f"ユーザー確認成功: {user}")
            #解錠指令送る
            result = subprocess.run(
                ["node", "sesami.js"],  
                capture_output=True,
                text=True,
                check=True
            )
            timestamp = datetime.now()
            DB.add_access_log(user['user_id'], timestamp, card_id)
            logger.info(f"出勤記録追加: {user}"+str(timestamp))
            return jsonify({'message': 'ユーザーが見つかりました', 'user': user})

        else:
            logger.warning(f"ユーザーが見つかりません: カード番号={card_id}")
            return jsonify({'message': 'ユーザーが見つかりません'}), 404
    except Exception as e:
        logger.error(f"ユーザー確認に失敗: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scan_card')
def scan_card():
    """
    カードリーダーでカードIDを取得し返す
    """
    try:
        print("test")
        result = nfc_Card_ScanCard.scan_card()
        # 假设输出里有"カードのIDm: xxxxx"
        print(result)
        if result:  
            return jsonify({"card_id": result})
        return jsonify({"error": "カードID取得失敗"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logger.info("APIサーバーを起動中...")
    logger.info("現在のデータベース状態を出力:")
    
    try:
        users = DB.get_users()
        logger.info(f"現在のユーザー数: {len(users)}")
        for user in users:
            logger.info(f"ユーザー: ID={user['user_id']}, 名前={user['user_name']}, 役職={user['role']}")
        
        logs = DB.get_access_logs()
        logger.info(f"現在の出勤記録数: {len(logs)}")
        logger.info(f"現在の出勤記録数: {logs}")
        summary = DB.get_attendance_summary()
        logger.info(f"現在の出勤サマリー記録数: {len(summary)}")
        
    except Exception as e:
        logger.error(f"初期化時にデータ取得に失敗: {str(e)}")
    
    app.run(debug=True, port=5000)
