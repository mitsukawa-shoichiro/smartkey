# APIドキュメント

## 使用方法  
1. `main.py` を実行してください。  
2. 必要なライブラリが不足している場合は、以下のコマンドでインストールしてください：  
   ```bash
   pip install -r requirements.txt
   ```
## 最も基本的な使い方（Python例）

```python
import requests

# 状態を設定
url = "http://127.0.0.1:5000/api/card/set_state"
data = {"state": "registering"}
response = requests.post(url, json=data)
print("set_stateの返り値：", response.json())

# カードIDを取得
url2 = "http://127.0.0.1:5000/api/card/get_card"
response2 = requests.get(url2)
print("get_cardの返り値：", response2.json())
```

---

## 1. 状態設定
- **エンドポイント**: /api/card/set_state
- **メソッド**: POST
- **パラメータ**: { "state": "registering" | "authenticating" }
- **返り値**: { "state": "registering" | "authenticating" }

## 2. 状態取得
- **エンドポイント**: /api/card/get_state
- **メソッド**: GET
- **返り値**: { "state": "registering" | "authenticating" }

## 3. カードID取得（NFCリーダー）
- **エンドポイント**: /api/card/get_card
- **メソッド**: GET
- **返り値**: { "card_id": "xxxxxx" }

---


