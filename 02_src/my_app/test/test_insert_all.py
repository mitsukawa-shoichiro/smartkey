"""
4テーブル(user / card / face / access_logs)全部にサンプルデータを入れるスクリプト。

テーブル間には外部キーの依存関係があるため、必ず以下の順で挿入する:
    1. user      (他のテーブルから参照される親)
    2. card      (user_id が必要)
    3. face      (user_id が必要)
    4. access_logs (user_id / card_id / face_id を参照)

実行方法(02_srcをカレントにして、.venvのpythonで):
    cd C:\\smartkey\\02_src
    C:\\smartkey\\.venv\\Scripts\\python.exe -m my_app.test.test_insert_all

注意: DBのテーブルが未作成の場合は、先に create_database() を通しておくこと
      (main.pyw を一度起動する、または schema を実行する)。
"""
import my_app.db.repository as repo
from my_app.models.ENUMS import CardType, EventType
from my_app.models.entity.access_log import AccessLog


# ------------------------------------------------------------------
# 1. user
# ------------------------------------------------------------------
def insert_users():
    """サンプルユーザーを挿入し、挿入されたユーザーの一覧(id付き)を返す"""
    sample_users = [
        ("山田太郎", "ヤマダタロウ"),
        ("鈴木花子", "スズキハナコ"),
        ("佐藤一郎", "サトウイチロウ"),
        ("田中美咲", "タナカミサキ"),
        ("高橋健", "タカハシケン"),
    ]
    for name, kana in sample_users:
        repo.insert_user(name, kana)
        print(f"  user: {name}({kana})")

    users = repo.get_all_users()
    print(f"→ user を {len(sample_users)} 件挿入\n")
    return users


# ------------------------------------------------------------------
# 2. card
# ------------------------------------------------------------------
def insert_cards(users):
    """各ユーザーに2枚ずつ、3種類のCardTypeをローテーションで割り当てて挿入"""
    card_types = list(CardType)  # [IC_CARD, CREDIT_CARD, ELSE_CARD]
    counter = 1
    # {user_id: [card_id, ...]} を後段(access_logs)で使うため覚えておく
    cards_by_user = {}

    for user in users:
        cards_by_user[user.id] = []
        for _ in range(2):
            idm = format(counter, "016X")          # ダミーIDm(16進16桁)
            card_type = card_types[counter % len(card_types)]
            card_id = repo.insert_card(idm, card_type, user.id)
            cards_by_user[user.id].append(card_id)
            print(f"  card: id={card_id}, {card_type.value}, "
                  f"{user.user_name}")
            counter += 1

    print(f"→ card を {counter - 1} 件挿入\n")
    return cards_by_user


# ------------------------------------------------------------------
# 3. face
# ------------------------------------------------------------------
def insert_faces(users):
    """各ユーザーに1件ずつ顔情報を挿入(画像ファイル自体は作らない=DBレコードのみ)"""
    faces_by_user = {}
    count = 0
    for user in users:
        face_id = repo.insert_face(user.id)
        faces_by_user[user.id] = face_id
        print(f"  face: id={face_id}, {user.user_name}")
        count += 1

    print(f"→ face を {count} 件挿入\n")
    return faces_by_user


# ------------------------------------------------------------------
# 4. access_logs
# ------------------------------------------------------------------
def insert_access_logs(users, cards_by_user, faces_by_user):
    """
    入退室ログを挿入。カード認証・顔認証の両パターンを混ぜる。
    method と event_type を変えて、一覧画面で見栄えがするようにする。
    """
    count = 0
    for i, user in enumerate(users):
        # --- カードで入室(ENTRY) ---
        card_id = cards_by_user[user.id][0]
        repo.insert_access_log(AccessLog(
            id=None, timestamp=None,
            method="カード", event_type=EventType.ENTRY,
            user_id=user.id, card_id=card_id, face_id=None,
        ))
        count += 1

        # --- 顔で退室(EXIT) ---
        face_id = faces_by_user[user.id]
        repo.insert_access_log(AccessLog(
            id=None, timestamp=None,
            method="顔認証", event_type=EventType.EXIT,
            user_id=user.id, card_id=None, face_id=face_id,
        ))
        count += 1
        print(f"  access_logs: {user.user_name} の入室(カード)・退室(顔)")

    print(f"→ access_logs を {count} 件挿入\n")


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------
def insert_all():
    print("=== サンプルデータ投入開始 ===\n")

    # 既にユーザーが居る場合は二重投入を避ける
    existing = repo.get_all_users()
    if existing:
        print(f"既にユーザーが {len(existing)} 件あります。")
        print("二重投入を避けるため中止します。まっさらにしたい場合は")
        print("database.db を削除してから create_database() で作り直してください。")
        return

    users = insert_users()
    cards_by_user = insert_cards(users)
    faces_by_user = insert_faces(users)
    insert_access_logs(users, cards_by_user, faces_by_user)

    print("=== 全テーブルへのサンプルデータ投入が完了しました ===")


if __name__ == "__main__":
    insert_all()