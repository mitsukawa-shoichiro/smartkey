# card_sys.py 利用方法

## 概要
`card_sys.py` はカードリーダーの状態管理、カードIDの取得、認証・登録処理、解錠操作などを行うモジュールです。

## 主な関数
- `set_state(state: str)`
  - カードリーダーの状態を設定します。
  - 引数: `"registering"` または `"authenticating"`
  - 返り値: 現在の状態文字列

- `get_state() -> str`
  - 現在のカードリーダー状態を取得します。
  - 返り値: 状態文字列

- `get_card() -> str`
  - カードIDを読み取ります。
  - 返り値: カードID（失敗時は空文字列）

- `receive_card(card_id: str)`
  - 現在の状態に応じてカードIDを処理します。
  - 認証状態なら認証、登録状態なら登録処理を行います。

- `unlock()`
  - 解錠操作を実行します。

# 使い方例
## import方法
if SERVICE_PATH not in sys.path:

   sys.path.insert(0, SERVICE_PATH)
    
from service import card_sys

## 状態を「登録」に設定
card_sys.set_state("registering")

## 状態を取得
state = card_sys.get_state()

## カードIDを取得
card_id = card_sys.get_card()

## 状態を「認証」に設定
card_sys.set_state("authenticating")


