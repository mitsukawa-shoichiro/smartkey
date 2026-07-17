"""
一覧画面のページング状態を扱うモジュール。

offset計算・ページ数計算・前後移動の可否判定を1箇所にまとめ、
各画面が nonlocal で offset / all_page を持ち回るのをやめるためのもの。
"""


class Pagination:
    """
    一覧画面のページング状態。

    current は 0 始まり(内部用)、label は 1 始まり(表示用)。
    総件数は DB から取得するたびに update_total() で渡す。
    """

    def __init__(self, per_page: int = 100):
        self.per_page = per_page
        self.current = 0
        self.total_pages = 1

    @property
    def offset(self) -> int:
        """SQLのOFFSETに渡す値"""
        return self.current * self.per_page

    def update_total(self, total_count: int):
        """DBから取得した総件数を反映して、総ページ数を再計算する"""
        self.total_pages = max(1, (total_count + self.per_page - 1) // self.per_page)

    def reset(self):
        """検索条件が変わった時など、1ページ目に戻す"""
        self.current = 0

    def next(self) -> bool:
        """次ページへ。移動できたら True(呼び出し側は True の時だけ再読込すればよい)"""
        if self.current + 1 < self.total_pages:
            self.current += 1
            return True
        return False

    def prev(self) -> bool:
        """前ページへ。移動できたら True"""
        if self.current > 0:
            self.current -= 1
            return True
        return False

    @property
    def is_first(self) -> bool:
        """先頭ページか(前へボタンのdisabled用)"""
        return self.current == 0

    @property
    def is_last(self) -> bool:
        """最終ページか(次へボタンのdisabled用)"""
        return self.current + 1 >= self.total_pages

    @property
    def label(self) -> str:
        """「3 / 10 ページ」の表示用文字列"""
        return f"{self.current + 1} / {self.total_pages} ページ"