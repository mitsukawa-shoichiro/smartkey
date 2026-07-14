# logs ディレクトリについて

このディレクトリは、ドア開閉システムのログ管理に関する各種設定ファイルおよびログファイルを格納するためのものです。

## 構成

- `log_config_app.py`
  アプリケーション全体のロギング設定モジュールです。`import my_app.logs.log_config_app` でどこからでも利用できます。
  - ログは `app.log` に出力されます。

  - INFO以上のログがファイルに記録され、DEBUG以上のログがコンソールに表示されます。

- `log_config_service.py`
  サービス用のロギング設定モジュールです。`import my_app.logs.log_config_service` で利用できます。
  - ログは `service.log` に出力されます。

  - WARNING以上のログがファイルに記録され、DEBUG以上のログがコンソールに表示されます。

- `app.log`
  - アプリケーションの実行ログファイルです。

- `service.log`
  - サービスの実行ログファイルです。

- `__pycache__/`
  Pythonのバイトコードキャッシュディレクトリです。通常は手動で編集・削除する必要はありません。
