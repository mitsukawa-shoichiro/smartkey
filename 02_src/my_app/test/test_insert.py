"""
カードのテストデータ挿入スクリプト。

card は user_id で user テーブルを参照しているため、先にユーザーが
存在している必要がある。このスクリプトは既存の全ユーザーを取得し、
各ユーザーに数枚ずつ、3種類の CardType をローテーションで割り当てて挿入する。

実行方法(02_srcをカレントにして、.venvのpythonで):
    cd C:\\smartkey\\02_src
    C:\\smartkey\\.venv\\Scripts\\python.exe -m my_app.test.test_insert_card

ユーザーがまだ居ない場合は、先に test_insert(ユーザー投入)を実行すること。
"""
import my_app.db.repository as repo
from my_app.models.ENUMS import CardType


# 何周してもIDmが重複しないよう、連番から16進16桁のダミーIDmを作る
def make_dummy_idm(n: int) -> str:
    return format(n, "016X")  # 例: 1 -> "0000000000000001"


def insert_test_cards(cards_per_user: int = 2):
    users = repo.get_all_users()

    if not users:
        print("ユーザーが1人も居ません。先にユーザーのテストデータを投入してください。")
        return

    card_types = list(CardType)  # [IC_CARD, CREDIT_CARD, ELSE_CARD]
    counter = 1
    inserted = 0

    for user in users:
        for i in range(cards_per_user):
            idm = make_dummy_idm(counter)
            # user_id と枚数に応じて種別をローテーションさせ、3種類が混ざるようにする
            card_type = card_types[counter % len(card_types)]

            card_id = repo.insert_card(idm, card_type, user.id)
            print(f"  card_id={card_id}: idm={idm}, type={card_type.value}, "
                f"user={user.user_name}(id={user.id})")

            counter += 1
            inserted += 1

    print(f"\nカードを {inserted} 件挿入しました(ユーザー {len(users)} 人 × {cards_per_user} 枚)")


if __name__ == "__main__":
    insert_test_cards()