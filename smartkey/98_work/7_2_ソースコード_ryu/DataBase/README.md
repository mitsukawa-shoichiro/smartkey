# 出勤汇总システム

このシステムは、従業員の出勤記録を管理し、日別の出勤汇总データを表示するWebアプリケーションです。

## 機能

- ユーザー情報の管理
- アクセスログ（打刻記録）の管理
- 日別出勤汇总データの自動生成　ーーこちら、即ちattendance_summaryのデータはまず無視してください。その後余裕があれば追加したい部分です
- NFCカードによる認証・登録
- Webインターフェースでのデータ表示

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. データベースの初期化

```bash
python DB.py
```

これにより、サンプルデータが含まれたデータベースが作成されます。

### 3. APIサーバーの起動

```bash
python api_server.py
```

サーバーは `http://localhost:5000` で起動します。

## 使用方法

### DataBase操作メソッド

#### 【取得系】
- `get_users()` ユーザー情報を全件取得
- `get_access_logs()` アクセスログを全件取得
- `get_attendance_summary()` 出勤集計データを全件取得
- `get_user_by_card_id(card_id)` カードIDでユーザー情報を取得

#### 【追加系】
- `add_user(name, role, card_id, card_name, register_date=None)` ユーザーを追加
- `add_access_log(user_id, timestamp, card_id)` アクセスログを追加
- `insert_sample_data()` サンプルデータを挿入

#### 【削除系】
- `delete_user(user_id)` ユーザーと関連データを削除
- `delete_access_log(log_id)` 指定ログを削除
- `delete_attendance_record(user_id, work_date)` 指定ユーザー・日付の出勤汇总記録を削除
- `clear_db()` 全データを削除（テーブル構造は残す）

#### 【更新系】
- `update_attendance_summary()` access_logsから出勤汇总データを再集計
（理由）

#### 【初期化】
- `init_db()` データベースとテーブルを初期化

### APIエンドポイント

#### 【GET】
- `/api/users` ユーザー情報を取得
- `/api/logs` アクセスログ（打刻記録）を取得
- `/api/attend` 出勤汇总データを取得
- `/api/scan_card` NFCカードをスキャンしてカードIDを取得

#### 【POST】
- `/api/users/add_user` ユーザーを追加
- `/api/users/check_card` カードIDでユーザーを認証
- `/api/logs/add_access_log` アクセスログを追加
- `/api/card/lookup` カードIDでユーザー情報を検索

#### 【DELETE】
- `/api/users/delete_user` ユーザーを削除
- `/api/logs/delete_access_log` アクセスログを削除
- `/api/attend/delete_attend_record` 出勤汇总データを削除

### フロントエンド

ブラウザで `index.html` または `webtest/` ディレクトリ内のページを開いて、出勤汇总データを表示できます。

## データベース構造

### users テーブル
- user_id: ユーザーID（主キー）
- user_name: ユーザー名
- role: 役職
- card_id: カードID
- card_name: カード名
- register_date: 登録日

### access_logs テーブル
- id: ログID（主キー）
- user_id: ユーザーID（外部キー）
- timestamp: 打刻時間
- card_id: カードID

### attendance_summary テーブル
- user_id: ユーザーID（複合主キー）
- user_name: ユーザー名
- work_date: 勤務日（複合主キー）
- earliest_time: 最早打刻時間
- latest_time: 最遅打刻時間

## 注意事項

- データベースファイルは `access_control.db` として保存されます
- APIサーバーはポート5000で動作します
- フロントエンドはAPIサーバーが起動している必要があります 
