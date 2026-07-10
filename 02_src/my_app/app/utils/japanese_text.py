"""
日本語文字列の検索用正規化ユーティリティ。

Autocomplete検索で「ひらがな」「カタカナ」「ローマ字」のどれで入力されても
同じ人物にヒットさせたい場合に使う。

主な用途:
    normalize_candidate(kanji, kana) -> (kanji, kana_katakana, romaji) のタプルを作る
    normalize_query(query) -> 入力文字列を、比較に使える形(カタカナ形/ローマ字形)に変換する

外部ライブラリ(pykakashi等)を使わず標準ライブラリのみで実装しているため、
変換精度は完全ではない(特にローマ字化は代表的な表記のみ対応)。
より高精度な変換が必要になった場合は pykakasi 等の導入を検討すること。
"""
import re

# ===================================================
# ひらがな <-> カタカナ
# ===================================================

def hiragana_to_katakana(text: str) -> str:
    """ひらがなをカタカナへ変換する(該当しない文字はそのまま)"""
    return "".join(
        chr(ord(ch) + 0x60) if "ぁ" <= ch <= "ゖ" else ch
        for ch in text
    )


def katakana_to_hiragana(text: str) -> str:
    """カタカナをひらがなへ変換する(該当しない文字はそのまま)"""
    return "".join(
        chr(ord(ch) - 0x60) if "ァ" <= ch <= "ヶ" else ch
        for ch in text
    )


# ===================================================
# カタカナ -> ローマ字(ヘボン式相当、簡易版)
# ===================================================

# 2文字の拗音(キャ行など)を先にマッチさせるため、長い綴りから順に定義する。
_KATAKANA_TO_ROMAJI = {
    "キャ": "kya", "キュ": "kyu", "キョ": "kyo",
    "シャ": "sha", "シュ": "shu", "ショ": "sho",
    "チャ": "cha", "チュ": "chu", "チョ": "cho",
    "ニャ": "nya", "ニュ": "nyu", "ニョ": "nyo",
    "ヒャ": "hya", "ヒュ": "hyu", "ヒョ": "hyo",
    "ミャ": "mya", "ミュ": "myu", "ミョ": "myo",
    "リャ": "rya", "リュ": "ryu", "リョ": "ryo",
    "ギャ": "gya", "ギュ": "gyu", "ギョ": "gyo",
    "ジャ": "ja", "ジュ": "ju", "ジョ": "jo",
    "ビャ": "bya", "ビュ": "byu", "ビョ": "byo",
    "ピャ": "pya", "ピュ": "pyu", "ピョ": "pyo",
    "ファ": "fa", "フィ": "fi", "フェ": "fe", "フォ": "fo",
    "ウィ": "wi", "ウェ": "we", "ウォ": "wo",
    "ティ": "ti", "ディ": "di", "デュ": "dyu",

    "ア": "a", "イ": "i", "ウ": "u", "エ": "e", "オ": "o",
    "カ": "ka", "キ": "ki", "ク": "ku", "ケ": "ke", "コ": "ko",
    "サ": "sa", "シ": "shi", "ス": "su", "セ": "se", "ソ": "so",
    "タ": "ta", "チ": "chi", "ツ": "tsu", "テ": "te", "ト": "to",
    "ナ": "na", "ニ": "ni", "ヌ": "nu", "ネ": "ne", "ノ": "no",
    "ハ": "ha", "ヒ": "hi", "フ": "fu", "ヘ": "he", "ホ": "ho",
    "マ": "ma", "ミ": "mi", "ム": "mu", "メ": "me", "モ": "mo",
    "ヤ": "ya", "ユ": "yu", "ヨ": "yo",
    "ラ": "ra", "リ": "ri", "ル": "ru", "レ": "re", "ロ": "ro",
    "ワ": "wa", "ヲ": "wo", "ン": "n",
    "ガ": "ga", "ギ": "gi", "グ": "gu", "ゲ": "ge", "ゴ": "go",
    "ザ": "za", "ジ": "ji", "ズ": "zu", "ゼ": "ze", "ゾ": "zo",
    "ダ": "da", "ヂ": "ji", "ヅ": "zu", "デ": "de", "ド": "do",
    "バ": "ba", "ビ": "bi", "ブ": "bu", "ベ": "be", "ボ": "bo",
    "パ": "pa", "ピ": "pi", "プ": "pu", "ペ": "pe", "ポ": "po",
    "ヴ": "vu",
}

# 長い綴り(2文字)から順にマッチさせるためのキー一覧
_KATAKANA_KEYS_SORTED = sorted(_KATAKANA_TO_ROMAJI.keys(), key=len, reverse=True)

_VOWELS = {"a", "i", "u", "e", "o"}


def katakana_to_romaji(text: str) -> str:
    """
    カタカナ文字列をローマ字(ヘボン式相当)に変換する。
    促音(ッ)による子音重複、長音(ー)による直前母音の繰り返しに対応。
    変換テーブルにない文字はそのまま(小文字化して)出力する。
    """
    result = []
    i = 0
    length = len(text)

    while i < length:
        ch = text[i]

        # 促音(ッ): 次の音の子音を1つ重ねる
        if ch == "ッ":
            matched_next = None
            for key in _KATAKANA_KEYS_SORTED:
                if text.startswith(key, i + 1):
                    matched_next = key
                    break
            if matched_next:
                next_romaji = _KATAKANA_TO_ROMAJI[matched_next]
                if next_romaji and next_romaji[0] not in _VOWELS:
                    result.append(next_romaji[0])  # 子音を1つ重ねる
            i += 1
            continue

        # 長音(ー): 直前の母音を繰り返す
        if ch == "ー":
            if result and result[-1]:
                result.append(result[-1][-1])
            i += 1
            continue

        # 2文字の拗音などを優先してマッチ
        matched = None
        for key in _KATAKANA_KEYS_SORTED:
            if len(key) == 2 and text.startswith(key, i):
                matched = key
                break
        if matched:
            result.append(_KATAKANA_TO_ROMAJI[matched])
            i += 2
            continue

        if ch in _KATAKANA_TO_ROMAJI:
            result.append(_KATAKANA_TO_ROMAJI[ch])
        else:
            result.append(ch.lower())
        i += 1

    return "".join(result)


# ===================================================
# 検索用の正規化ヘルパー
# ===================================================

def build_search_key(kanji: str, kana: str) -> str:
    """
    1人のユーザーについて、検索マッチング用の1つの文字列を作る。
    漢字・カタカナ・ローマ字を全部連結しておき、部分一致で判定できるようにする。
    """
    romaji = katakana_to_romaji(kana)
    return f"{kanji} {kana} {romaji}".lower()


def normalize_query(query: str) -> list:
    """
    入力された検索文字列を、比較に使える複数の形へ変換する。
    ひらがな入力・カタカナ入力・ローマ字入力のどれでも、
    build_search_keyで作った文字列に対して部分一致検索できるようにする。

    Returns:
        list[str]: 候補となる正規化済み文字列のリスト(いずれかがヒットすればOK)
    """
    if not query:
        return []

    forms = set()
    lowered = query.lower()
    forms.add(lowered)

    # ひらがな -> カタカナ -> ローマ字
    katakana_form = hiragana_to_katakana(query)
    forms.add(katakana_form.lower())
    forms.add(katakana_to_romaji(katakana_form).lower())

    # カタカナ -> ひらがな(念のため)
    forms.add(katakana_to_hiragana(query).lower())

    return list(forms)


def matches(query: str, kanji: str, kana: str) -> bool:
    """
    query(ユーザー入力)が、kanji/kana(候補者の名前)にマッチするかを判定する。
    """
    search_key = build_search_key(kanji, kana)
    for form in normalize_query(query):
        if form and form in search_key:
            return True
    return False