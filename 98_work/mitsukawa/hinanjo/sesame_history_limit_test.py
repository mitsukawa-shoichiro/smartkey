# -*- coding: utf-8 -*-
"""
Your Chronicle 不満周回オート (pyautogui版)
  - ボタンは画像テンプレート検索 (UIの位置ズレ・解放待ちに強い)
  - ゲージ/ロードはピクセル色判定
  前提: 画面解像度800x600、ゲームウィンドウ最大化、
        このファイルと同じ場所に yc_templates/ フォルダ

  セットアップ: pip install pyautogui opencv-python pillow
  実行:         python yc_loop.py
  停止:         Ctrl+C (コンソール) or マウスを画面左上隅へ(FAILSAFE)
"""
import sys
import time
import logging
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pyautogui as pg

pg.FAILSAFE = True          # マウスを画面左上隅に投げると例外で緊急停止
pg.PAUSE = 0.05

TPL_DIR = Path(__file__).parent / "yc_templates"
CONF = 0.80                 # テンプレ一致のしきい値

# ---- テンプレごとの検索範囲 (left, top, width, height) ----------
# 画面全体から探すと別の場所の日本語テキストに誤マッチするため、
# 各UIが存在しうる領域だけに絞る
REGIONS = {
    "menu_gishiki":  (0, 100, 90, 220),     # 左メニュー列
    "menu_routine":  (0, 100, 90, 220),
    "tab_familiar":  (85, 100, 80, 320),    # ルーティンのタブ列
    "tab_envy":      (85, 100, 80, 320),
    "kusamushiri":   (150, 90, 200, 190),   # Instant Action列
    "holy_ritual":   (250, 110, 260, 130),  # 儀式画面 中央上部
    "tensei_detail": (500, 270, 200, 130),  # 儀式画面 転生パネル
    "chronicle_ed1": (80, 100, 150, 320),   # クロニクル一覧(左列)
    "back_btn":      (670, 20, 130, 50),    # クリア画面 右上
    "close_btn":     (560, 95, 160, 45),    # 転生詳細ビューの「閉じる」
    "tensei_btn":    (380, 170, 220, 100),  # 転生ボタン周辺
    "ok_btn":        (330, 300, 150, 130),   # 転生確認OK (鍵の数で上下にずれるため縦広め)
    "next_charisma": (400, 230, 160, 60),    # 転生確認の「次の戦略：カリスマ」(鍵で上下)
    "row_pigman":    (150, 80, 420, 400),   # 使い魔リスト領域
    "row_lonely":    (150, 80, 420, 400),
    "row_manpukudo": (150, 170, 220, 260),  # 嫉妬カリスマのルーティン行領域(行数変動に対応)
    "queue_play":    (540, 25, 30, 27),     # 全キュー開始「>」(停止中のみ一致)
}

# 漢字2文字ボタン同士(嫉妬/強欲/憤怒/怠惰…)は0.80だと互いに誤マッチするため、
# メニュー・タブ・行ラベルは高めのしきい値を要求する (本物は0.95+で一致する)
CONF_OVERRIDES = {
    "menu_gishiki": 0.95, "menu_routine": 0.95,
    "tab_familiar": 0.96, "tab_envy": 0.96,
    "row_pigman": 0.95, "row_lonely": 0.95,
    "kusamushiri": 0.90,   # 再実測: 本物0.97+ / 2位0.43。中央に文字がある正しいテンプレに差し替え済み
    "row_manpukudo": 0.95,
    "close_btn": 0.92, "tensei_btn": 0.92,   # 灰色ボタン他人の空似対策
    "back_btn": 0.90, "ok_btn": 0.85,        # OKは専用ダイアログなので誤マッチ源が少ない
    "next_charisma": 0.85,
    "queue_play": 0.85,    # 実測: 停止中1.00 / 稼働中0.35
}

# ---- 固定座標 (上部バーは不動なので座標でOK) --------------------
SLOT = {1: (612, 38), 2: (641, 38), 3: (670, 38), 4: (699, 38),
        5: (728, 38), 6: (757, 38), 7: (786, 38)}
PHASE_A_SLOT = 1            # 村脱出テンプレ
PHASE_B_SLOT = 2            # 強欲
QUEUE_TOGGLE = (554, 38)    # 全キュー開始「>」
CHARISMA_SUBTAB = (233, 123)
FAM_CHECK_X = 665           # 使い魔チェックボックス列(実測: 800px画面で中心x≈665)
PARK = (400, 520)           # クリック後にマウスを逃がす位置(ホバー対策)

# ---- ピクセル判定 (実測色) --------------------------------------
GAUGE_COL_X = 560           # ゲージ列のX (行のYは満腹度ラベルから動的に決める)
GAUGE_RED = (200, 80, 80)   # 0xC85050
LOADSCREEN = (50, 50, 50)   # 0x323232 Click to Start背景
UI_READY = (188, 188, 188)  # 0xBCBCBC 村画面メインボタン点灯
TOL = 25
GREED_SETTLE_SEC = 45   # 強欲投入後、欲望の最大値拡張(1秒1段階)が完走するのを待つ
DECAY_CONFIRM_SEC = 5
DECAY_TIMEOUT_SEC = 14 * 60   # 監視が成立しない周でも14分固定周回として完走させる

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler(Path(__file__).parent / "yc_loop.log", encoding="utf-8")],
)
log = logging.getLogger("yc")

# ================= ログ閲覧 + Web操作サーバー ======================
# 手元PCのブラウザから http://<VPSのIP>:8777/ でログ閲覧とマクロ操作。
# 画面操作とは別スレッドで動くのでpyautoguiに干渉しない。
# ※VPSパネルのパケットフィルターで TCP 8777 を開けること。
LOG_PORT = 8777
LOG_FILE = Path(__file__).parent / "yc_loop.log"
CONTROL_KEY = "mob-yc"   # 操作用の合言葉 (URLに含める。好きな文字列に変えてOK)

# Web操作の共有状態。操作は「安全地帯」(周回の区切り・ゲージ監視中)でのみ効く
CONTROL = {"paused": False, "stop_after_lap": False, "status": "起動中"}

def set_status(s):
    CONTROL["status"] = s

def checkpoint():
    """安全地帯での操作反映ポイント。一時停止中はここで待機する"""
    if CONTROL["paused"]:
        log.info("[Web操作] 一時停止中 (再開ボタンで続行)")
        prev = CONTROL["status"]
        set_status("一時停止中")
        while CONTROL["paused"]:
            time.sleep(1.0)
        set_status(prev)
        log.info("[Web操作] 再開しました")

class _LogHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # --- 操作エンドポイント: /ctl?k=<KEY>&cmd=... ---
        if self.path.startswith("/ctl"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            if q.get("k", [""])[0] == CONTROL_KEY:
                cmd = q.get("cmd", [""])[0]
                if cmd == "pause":
                    CONTROL["paused"] = True
                    log.info("[Web操作] 一時停止を予約 (安全地帯で停止します)")
                elif cmd == "resume":
                    CONTROL["paused"] = False
                elif cmd == "stoplap":
                    CONTROL["stop_after_lap"] = True
                    log.info("[Web操作] この周での停止を予約しました")
                elif cmd == "clearstop":
                    CONTROL["stop_after_lap"] = False
                    log.info("[Web操作] 停止予約を解除しました")
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        # --- ログ表示 + 操作パネル ---
        try:
            text = LOG_FILE.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            text = f"(ログ読み込みエラー: {e})"
        tail = "\n".join(text.splitlines()[-300:])   # 直近300行
        pause_btn = (f"<a class='btn' href='/ctl?k={CONTROL_KEY}&cmd=resume'>▶ 再開</a>"
                     if CONTROL["paused"] else
                     f"<a class='btn' href='/ctl?k={CONTROL_KEY}&cmd=pause'>⏸ 一時停止</a>")
        stop_btn = (f"<a class='btn' href='/ctl?k={CONTROL_KEY}&cmd=clearstop'>停止予約を解除</a>"
                    if CONTROL["stop_after_lap"] else
                    f"<a class='btn' href='/ctl?k={CONTROL_KEY}&cmd=stoplap'>⏹ この周で停止</a>")
        flags = []
        if CONTROL["paused"]:
            flags.append("一時停止")
        if CONTROL["stop_after_lap"]:
            flags.append("この周で停止予約")
        flag_s = (" / " + "・".join(flags)) if flags else ""
        html = (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta http-equiv='refresh' content='5'>"   # 5秒ごと自動更新
            "<title>YC Loop</title>"
            "<style>body{background:#1a1b26;color:#c0caf5;font-family:monospace;"
            "font-size:13px;margin:0;padding:10px}pre{white-space:pre-wrap;word-break:break-all}"
            ".err{color:#f7768e}.warn{color:#e0af68}"
            ".bar{position:sticky;top:0;background:#24283b;padding:8px;margin:-10px -10px 10px;"
            "border-bottom:1px solid #414868}"
            ".btn{display:inline-block;background:#414868;color:#c0caf5;padding:4px 12px;"
            "margin-right:8px;text-decoration:none;border-radius:4px}"
            ".st{color:#9ece6a}</style></head><body>"
            f"<div class='bar'>状態: <span class='st'>{CONTROL['status']}{flag_s}</span>"
            f"<br><br>{pause_btn}{stop_btn}</div><pre>"
        )
        for line in tail.splitlines():
            cls = "err" if "ERROR" in line else ("warn" if "WARNING" in line else "")
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html += f"<span class='{cls}'>{safe}</span>\n" if cls else safe + "\n"
        html += "</pre></body></html>"
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass   # アクセスログは黙らせる

def start_log_server():
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", LOG_PORT), _LogHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log.info("ログ閲覧サーバー起動: http://<このVPSのIP>:%d/", LOG_PORT)
    except Exception as e:
        log.warning("ログサーバーを起動できませんでした: %s", e)

# ================= 基本ユーティリティ =============================
def near(c1, c2, tol=TOL):
    return all(abs(a - b) <= tol for a, b in zip(c1, c2))

def px(x, y):
    return pg.pixel(x, y)

import cv2
import numpy as np
from collections import namedtuple

Point = namedtuple("Point", "x y")
_TPL_CACHE = {}

def _tpl(name):
    if name not in _TPL_CACHE:
        _TPL_CACHE[name] = cv2.imread(str(TPL_DIR / f"{name}.png"),
                                      cv2.IMREAD_GRAYSCALE)
    return _TPL_CACHE[name]

def find(name, conf=None):
    """テンプレ画像を画面から探す (cv2で最高スコアの一点を採用)。
    pyautogui標準の「最初にしきい値を超えた場所」方式は
    似た漢字ボタンに先取りされるため使わない"""
    if conf is None:
        conf = CONF_OVERRIDES.get(name, CONF)
    region = REGIONS.get(name)  # (left, top, w, h) or None
    shot = pg.screenshot(region=region)
    screen = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
    tpl = _tpl(name)
    if tpl is None or screen.shape[0] < tpl.shape[0] or screen.shape[1] < tpl.shape[1]:
        return None
    res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    log.debug("find %s score=%.3f", name, mx)
    if mx < conf:
        return None
    ox, oy = (region[0], region[1]) if region else (0, 0)
    return Point(ox + loc[0] + tpl.shape[1] // 2,
                 oy + loc[1] + tpl.shape[0] // 2)

def wait_find(name, timeout=30, interval=1.0, conf=None):
    t0 = time.time()
    while time.time() - t0 < timeout:
        p = find(name, conf)
        if p:
            return p
        time.sleep(interval)
    # 未発見時: 原因調査用に画面を保存
    snap = Path(__file__).parent / f"miss_{name}_{int(time.time())}.png"
    try:
        pg.screenshot(str(snap))
        log.warning("未発見: %s (画面を保存: %s)", name, snap.name)
    except Exception:
        log.warning("未発見: %s", name)
    return None

def click_img(name, timeout=15, park=True, conf=None):
    p = wait_find(name, timeout=timeout, conf=conf)
    if not p:
        log.warning("テンプレ未発見: %s", name)
        return False
    pg.click(p)
    if park:
        pg.moveTo(*PARK)
    return True

def click_xy(xy, wait=1.0):
    pg.click(*xy)
    time.sleep(wait)

# ================= 画面遷移 =======================================
def ensure_focus():
    """ゲームウィンドウへフォーカスを移す。
    非アクティブ状態への初回クリックはフォーカス取得に消費されて
    ゲームに届かないことがあるため、無害な場所を先にクリックしておく"""
    pg.click(*PARK)
    time.sleep(0.4)

def press_slot(n):
    """ショートカットスロットを起動。
    キー押下と座標クリックの二段構え(ロード直後の入力取りこぼし対策。
    同一テンプレの二重ロードは直後なら実害なし)"""
    ensure_focus()
    pg.press(str(n))
    time.sleep(0.8)
    pg.click(SLOT[n][0], SLOT[n][1])
    pg.moveTo(*PARK)
    time.sleep(1.5)

def ensure_queue_stopped():
    """全キューを停止状態にする(転生の直前に呼ぶ)。
    キューは3系統あり、どれかが動いていると「II」表示になるため
    グローバル表示から本体キューの状態は判定できない。
    そこで転生前に必ず全停止し、転生後の状態を「停止」で確定させる"""
    if find("queue_play"):
        return True                    # 既に全停止(「>」表示)
    click_xy(QUEUE_TOGGLE, wait=0.8)   # 停止トグル
    for _ in range(6):
        if find("queue_play"):
            log.info("全キュー停止を確認")
            return True
        time.sleep(0.5)
    log.warning("キュー停止を確認できません")
    return False

def ensure_queue_running():
    """全キューを開始する(転生直後に呼ぶ)。
    転生前にensure_queue_stoppedで全停止済みのため「>」が見えるはず。
    確認してからクリックし、万一見えない場合のみ保険で一度トグルを押す"""
    for _ in range(8):
        p = find("queue_play")
        if p:
            pg.click(p)
            pg.moveTo(*PARK)
            time.sleep(0.8)
            log.info("全キュー開始")
            return True
        time.sleep(0.5)
    log.warning("「>」を確認できないため保険でトグルを押します")
    click_xy(QUEUE_TOGGLE, wait=0.8)
    return False

def go_gishiki(timeout=600):
    """儀式画面へ遷移する。
    毎ループの先頭で「既に儀式画面か」を検証してから、必要ならメニューをクリック。
    (クリック直後の検証が描画待ちで失敗しても、次のループで検出できる)"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if find("holy_ritual") or find("tensei_detail"):
            log.info("儀式画面に入りました")
            return True
        if find("tensei_btn") and find("close_btn"):
            # 転生詳細ビューが開きっぱなし (転生と閉じるが同時に見える) → 閉じて戻す
            log.info("転生詳細ビューを検出 → 閉じます")
            p = find("close_btn")
            if p:
                pg.click(p)
                pg.moveTo(*PARK)
            time.sleep(1.5)
            continue
        p = find("menu_gishiki")
        if p:
            pg.click(p)
            pg.moveTo(*PARK)
        time.sleep(2.0)
    log.error("儀式画面に入れませんでした(タイムアウト)")
    return False

def open_routine():
    """ルーティン画面を開く。毎回ルーティンを押す。
    既に選択中だと非選択テンプレが一致しないので、その場合はタブの有無で判定"""
    p = find("menu_routine")
    if p:
        pg.click(p)
        pg.moveTo(*PARK)
        time.sleep(0.8)
    # タブ列の描画待ち (どちらかのタブが選択中でも、もう片方は非選択で見えるはず)
    for _ in range(8):
        if find("tab_familiar") or find("tab_envy"):
            return True
        time.sleep(1.0)
    log.warning("ルーティン画面を確認できません")
    return False

def set_familiar(target):
    """使い魔切り替え。target: 'lonely' or 'pig'
    行ラベルをテンプレで探し、同じ行のチェックボックス列をクリック"""
    open_routine()
    p = find("tab_familiar")          # 既に使い魔画面なら非選択テンプレは一致しない(正常)
    if p:
        pg.click(p)
        pg.moveTo(*PARK)
    time.sleep(0.8)
    off_row = "row_pigman" if target == "lonely" else "row_lonely"
    on_row = "row_lonely" if target == "lonely" else "row_pigman"
    for name in (off_row, on_row):        # 現行OFF → 目標ON
        p = wait_find(name, timeout=10)
        if not p:
            log.warning("使い魔行が見つからない: %s", name)
            continue
        pg.click(FAM_CHECK_X, p.y)
        time.sleep(0.5)
    pg.moveTo(*PARK)

SUBTAB_XS = (358, 265, 170)   # カリスマ/創造性/身体 の実測中心x (y=123)。カリスマ優先で総当たり

def open_envy_charisma():
    """嫉妬→カリスマ表示を開き、満腹度の行が見えることを確認する"""
    open_routine()
    click_img("tab_envy", timeout=5)      # 既に嫉妬選択中なら未発見でOK
    time.sleep(0.8)
    for x in SUBTAB_XS:
        if find("row_manpukudo"):
            return True                   # 満腹度が見えている=カリスマ表示OK
        pg.click(x, 123)
        pg.moveTo(*PARK)
        time.sleep(0.8)
    return find("row_manpukudo") is not None

def gauge_color():
    """満腹度行を探し、その行のゲージ監視点の色を返す。見えなければNone"""
    p = find("row_manpukudo")
    if not p:
        return None
    return px(GAUGE_COL_X, p.y)

# ================= フェーズ =======================================
def phase_a():
    log.info("フェーズA: 仕込み開始")
    press_slot(PHASE_A_SLOT)                    # 村脱出テンプレ (数字キー)
    ensure_queue_running()                      # 停止中のときだけ開始
    # 草むしり×10: 解禁されるまで待つ(キューの進行に依存するため長め)
    # ボタン位置は動くので毎クリック探し直す
    missed = 0
    for i in range(10):
        p = wait_find("kusamushiri", timeout=(300 if i == 0 else 5))
        if p:
            pg.click(p)
            time.sleep(0.35)
        else:
            missed += 1
    pg.moveTo(*PARK)
    if missed:
        log.warning("草むしり: %d回分スキップ", missed)
    if not go_gishiki():
        return False
    click_img("holy_ritual", timeout=30)        # 聖なる儀式 実行
    log.info("聖なる儀式を実行")
    time.sleep(1.0)
    set_familiar("lonely")
    log.info("使い魔: 寂しがりに変更")
    log.info("フェーズA: 完了")
    return True

def _is_gray(c, tol=8):
    r, g, b = c
    return abs(r - g) <= tol and abs(g - b) <= tol and abs(r - b) <= tol

def handle_interruptions():
    """放置中の割り込みを検出して閉じる。
    ① Backボタン付きのクリア画面 → Backで閉じる
    ② Backなしの全画面イベント(一枚絵) → UI定点2箇所が無彩色でないことで検出し、
       クリックして進める (手動フローの「クリア画面を踏む」に相当)"""
    if find("back_btn"):
        log.info("クロニクルクリア画面(Backあり)を検出 → 閉じます")
        click_img("back_btn", timeout=5)
        time.sleep(1.5)
        return True
    if not _is_gray(px(40, 117)) and not _is_gray(px(612, 38)):
        log.info("全画面イベントを検出 → クリックで進めます")
        pg.click(400, 300)
        pg.moveTo(*PARK)
        time.sleep(1.5)
        if find("back_btn"):
            click_img("back_btn", timeout=5)
            time.sleep(1.0)
        return True
    return False

def wait_decay():
    """満腹度ゲージの減衰開始を待つ。
    段階1: ゲージが赤(上限中)であることを確認できるまで、
           嫉妬カリスマ画面を定期的に開き直す (嫉妬の解禁待ちを兼ねる)
    段階2: 赤→非赤の遷移をもって減衰開始と判定する
    これにより「違う画面を見ていた」ことによる偽検知が構造的に起きない"""
    log.info("ゲージ監視開始 (まず上限中の赤を確認します)")
    t0 = time.time()
    # --- 段階1: 赤の確認 ---
    while time.time() - t0 < DECAY_TIMEOUT_SEC:
        c = gauge_color()
        if c and near(c, GAUGE_RED):
            log.info("ゲージ赤を確認 (%.1f分経過) → 減衰待ちへ", (time.time() - t0) / 60)
            break
        if not handle_interruptions():
            open_envy_charisma()      # 未解禁/画面ズレなら開き直す
        time.sleep(15.0)
    else:
        log.warning("赤を確認できないまま%d分経過 → 固定周期として回収へ", DECAY_TIMEOUT_SEC // 60)
        return
    # --- 段階2: 赤→非赤の遷移待ち ---
    # 「ゲージが見えて非赤」だけを減衰としてカウントする。
    # 「ゲージが見えない」は割り込みや画面ズレなので、復旧してカウントしない
    non_red = 0
    while time.time() - t0 < DECAY_TIMEOUT_SEC:
        c = gauge_color()
        if c is None:
            non_red = 0
            if not handle_interruptions():
                open_envy_charisma()
            time.sleep(2.0)
            continue
        non_red = 0 if near(c, GAUGE_RED) else non_red + 1
        if non_red >= DECAY_CONFIRM_SEC:
            log.info("減衰検知 (%.1f分経過)", (time.time() - t0) / 60)
            return
        time.sleep(1.0)
    log.warning("監視タイムアウト → 強制回収")

def is_loadscreen():
    return near(px(600, 450), LOADSCREEN) and near(px(40, 117), LOADSCREEN)

def wait_loadscreen(timeout=60):
    """転生成功の確定判定: Click to Start画面が来るのを待つ"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        if is_loadscreen():
            return True
        time.sleep(1.0)
    return False

def do_tensei(max_tries=5):
    """転生シーケンスを実行し、Click to Start画面の出現をもって成功と判定。
    失敗したら割り込みを掃除してシーケンス丸ごとリトライ"""
    for i in range(max_tries):
        handle_interruptions()
        ensure_queue_stopped()                      # 転生前に必ず全停止(状態を確定)
        if not go_gishiki(timeout=90):
            continue
        click_img("tensei_detail", timeout=10)      # 詳細を開く
        time.sleep(1.0)
        click_img("chronicle_ed1", timeout=8)       # 復讐の意思 → クリア画面
        time.sleep(2.0)
        if find("back_btn"):                        # クリア画面が出ていればBack
            click_img("back_btn", timeout=5)
            time.sleep(1.0)
        click_img("tensei_btn", timeout=8)          # 転生
        time.sleep(1.0)
        # 転生確認ダイアログで戦略チェック(カリスマでなければ警告)
        if find("ok_btn") and not find("next_charisma"):
            log.error("!!! 次の戦略がカリスマではありません。強欲研究が半減効率の可能性 !!!")
        click_img("ok_btn", timeout=8)              # 確認OK
        if wait_loadscreen(60):                     # ← ここが成功の唯一の証拠
            log.info("転生を確認 (Click to Start到達)")
            return True
        log.warning("転生が確認できません → シーケンスをリトライ (%d/%d)", i + 1, max_tries)
    log.error("転生に%d回失敗しました", max_tries)
    return False

def phase_b():
    log.info("フェーズB: 回収・転生開始")
    for _ in range(3):                          # 割り込み(クリア画面等)を先に掃除
        if not handle_interruptions():
            break
        time.sleep(1.0)
    set_familiar("pig")
    log.info("使い魔: ピッグマンに変更")
    # フェーズAのキューが稼働中だと ensure_queue_running の保険トグルが
    # 逆に停止させてしまうため、先に全停止を確定させてから読込→開始する
    ensure_queue_stopped()
    press_slot(PHASE_B_SLOT)                    # 強欲ショートカット (数字キー)
    ensure_queue_running()                      # 「>」を確認して開始
    log.info("強欲キュー起動 → 欲望の最大値拡張を%d秒待機", GREED_SETTLE_SEC)
    time.sleep(GREED_SETTLE_SEC)
    if not do_tensei():
        return False
    log.info("フェーズB: 完了(転生)")
    return True

def wait_load():
    """(転生確認済み前提) Click to Start をクリック → 村画面UI点灯まで待つ。
    遷移フェード中の色を誤検知しないよう、UI点灯が3秒連続した時点で完了とする"""
    log.info("ロード待ち")
    time.sleep(1.5)
    pg.click(400, 300)                          # Click to Start
    stable = 0
    for _ in range(180):
        if near(px(40, 117), UI_READY):
            stable += 1
            if stable >= 3:                     # 3秒連続でUI点灯を確認
                time.sleep(4.0)                 # ゲーム内部の初期化・入力受付待ち
                log.info("ロード完了")
                return
        else:
            stable = 0
            if is_loadscreen():
                pg.click(400, 300)              # クリックが早すぎた場合の再押下
        time.sleep(1.0)
    log.warning("UI復帰を確認できないまま続行")

# ================= sinラッシュモード ==============================
# リサーチ枯渇などの異常時用: 強欲・ゲージ監視・使い魔切替を全部スキップし、
# 転生可能(必要ランク到達)になった瞬間に転生してsin(上限42/転生)だけを
# 最速で回収するモード。リサーチを一切消費しない。
# 起動: py yc_loop.py sinrush

def phase_sinrush():
    """最小の仕込み: テンプレ起動＋キュー開始＋草むしり(軽量版)"""
    press_slot(PHASE_A_SLOT)                    # 村脱出テンプレ
    ensure_queue_running()                      # 停止中のときだけ開始
    # 草むしり軽量版: 最大15秒だけ粘る。見つからなければ潔く諦める(missスクショも出さない)
    clicks, t0 = 0, time.time()
    while clicks < 10 and time.time() - t0 < 15:
        p = find("kusamushiri")
        if p:
            pg.click(p)
            clicks += 1
            time.sleep(0.3)
        else:
            time.sleep(1.0)
    pg.moveTo(*PARK)
    if clicks:
        log.info("草むしり x%d", clicks)

def wait_tensei_unlock(timeout=900):
    """転生パネル(詳細を開く)の出現 = 必要ランク到達を待つ"""
    go_gishiki(timeout=180)                     # まず儀式画面へ(解禁待ち込み)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if find("tensei_detail"):
            log.info("転生パネル出現 (%.1f分)", (time.time() - t0) / 60)
            return True
        if not handle_interruptions():
            p = find("menu_gishiki")            # 画面がズレていたら儀式へ戻す
            if p:
                pg.click(p)
                pg.moveTo(*PARK)
        time.sleep(3.0)
    log.warning("転生パネルが%d分以内に出現しませんでした", timeout // 60)
    return False

def main_sinrush():
    lap = 0
    while True:
        lap += 1
        t0 = time.time()
        log.info("===== [sinラッシュ] 周回 %d 開始 =====", lap)
        phase_sinrush()
        wait_tensei_unlock()
        while not do_tensei():
            log.error("転生失敗。30秒後にリトライ")
            time.sleep(30)
        wait_load()
        log.info("===== [sinラッシュ] 周回 %d 完了 (%.1f分) =====", lap, (time.time() - t0) / 60)

# ================= メイン =========================================
def main():
    lap = 0
    while True:
        lap += 1
        t0 = time.time()
        log.info("===== 周回 %d 開始 =====", lap)
        if not phase_a():
            log.error("フェーズA失敗。60秒後にリトライ")
            time.sleep(60)
            continue
        wait_decay()
        while not phase_b():
            log.error("フェーズB失敗。60秒後に転生からリトライします")
            time.sleep(60)
        wait_load()
        log.info("===== 周回 %d 完了 (%.1f分) =====", lap, (time.time() - t0) / 60)

if __name__ == "__main__":
    start_log_server()
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "normal"
    if mode in ("sinrush", "sin"):
        log.info("モード: sinラッシュ (高速転生 / 強欲・監視スキップ / リサーチ消費なし)")
        runner = main_sinrush
    else:
        log.info("モード: 通常 (不満周回)")
        runner = main
    log.info("5秒後に開始します。ゲーム画面を前面にしてください (中断: Ctrl+C / マウス左上隅)")
    time.sleep(5)
    try:
        runner()
    except pg.FailSafeException:
        log.info("FAILSAFE発動: 停止しました")
    except KeyboardInterrupt:
        log.info("Ctrl+C: 停止しました")