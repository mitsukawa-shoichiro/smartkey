# コード説明書

## カードリーダー

- **カードスキャン**  
  - `nfc_Card_ScanCard`

- **ユーザー登録**  
  - `nfc_card_add_users.py`

- **カード認証**  
  - `nfc_card_check_card.py`

---

## sesami通信

- **sesami.js**  
  - sesamiに開錠指令送る
  - `sesami.js`
    - 但し、npm install axios node-aes-cmacでライブラリ導入必要



---

## データベース

- **データベース**  
  - DB.py

- **API提供**  
  - `api_server.py`  
    - データアクセスインターフェースの提供者
    - pip install -r requirements.txt　ライブラリ導入必要

---

## 必要事項
- **ライブラリ導入**  
  - pip install -r requirements.txt　pythonライブラリ導入必要
  - npm install axios node-aes-cmac jsライブラリ導入必要
- **使う方法**  
  - 先にapi_server.pyを執行して
  - その後nfc_card_add_users.pyでユーザー登録して、nfc_card_check_card.pyでユーザー確認してください

## 参考資料

- **flask**  
  - データアクセスインターフェースの提供者  
  - 参考資料：初心者プログラマーのWebアプリ#1 簡単なページ作成 [リンク](https://qiita.com/Bashi50/items/30065e8f54f7e8038323)

- **データベース チュートリアル**  
  - [SQLite チュートリアル](https://www.javadrive.jp/sqlite/)

- **nfcカード**  
  - カードスキャンしてそのidmを記録  
  - 参考資料：NFCリーダー+Python+nfcpyで学生証の情報を読み取る [リンク](https://zenn.dev/3w36zj6/articles/d3894e83cb7423)  
    - ※ RC-S300はnfcpyに対応していない


- **SESAME5使い方**  
  - [リンク](https://note.com/xh_ichikawa/n/nd5ceb0b60cfe)

- **ホームページ**  
  - [CANDYHOUSE](https://biz.candyhouse.co/)

- **API**  
  - [SESAME API ドキュメント](https://doc.candyhouse.co/ja/SesameAPI)
