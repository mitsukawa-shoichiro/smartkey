# SmartKey Service モジュール

このディレクトリは、スマートキーシステムの主要なサービスロジックを管理します。
Windowsサービスとして動作し、カードリーダーやバックシステムの監視・制御を行います。もし異常を察知したら、mail.jsonの指定先のメールに送信します

## 主なファイル

- `main.py`
  サービスのエントリーポイント。ログ初期化後、back_systemとCardCheckを起動します。

- `backsys/back_system.py`
  バックエンドシステムの監視・制御ロジック。

- `daemon/reader_daemon.py`
  NFCカードリーダーの認証・管理ロジック。

- `windowsservice.py`
  Windowsサービスとして登録・管理するためのスクリプト。

## 依存ライブラリ

- Python 標準ライブラリ（logging, os, sys, time, subprocess, threading など）
-  [Pythonサービス化して処理を常駐 #Python - Qiita](https://share.google/baszBReBVmBUCFa1U)

## 実行方法

1. 必要なライブラリをインストール
   ```
   pip install -r requirements.txt
   ```

2. サービス登録（管理者権限で実行）
   ```
   python windowsservice.py install
   ```

3. サービス開始
   ```
   python windowsservice.py start
   ```

4. サービス停止・削除
   ```
   python windowsservice.py stop
   python windowsservice.py remove
   ```

## ログ

- ログは `../logs/service.log` に出力されます。

## 注意事項

- サービス登録・起動には管理者権限が必要です。
