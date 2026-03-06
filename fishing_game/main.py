import pygame
import random
import json
import os
import sys
import subprocess
from datetime import datetime

pygame.init()
pygame.mixer.init()

# ---------------------------
# ウィンドウ（リサイズ対応）
# ---------------------------
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("まったり釣りゲーム")

font       = pygame.font.SysFont("meiryo", 28)
big_font   = pygame.font.SysFont("meiryo", 48)
small_font = pygame.font.SysFont("meiryo", 22)

clock = pygame.time.Clock()
FPS   = 60

# ---------------------------
# 素材読み込み
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_image(filename, convert_alpha=True):
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return None
    img = pygame.image.load(path)
    return img.convert_alpha() if convert_alpha else img.convert()

bg_img_src   = load_image("background.png", convert_alpha=False)
girl_img     = load_image("girl_transparent.png")

# ---------------------------
# 音声読み込み
# ---------------------------
def load_bgm(filename):
    path = os.path.join(BASE_DIR, filename)
    if os.path.exists(path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)

SE_VOLUME = 0.3  # SE音量（0.0〜1.0）

def load_se(filename):
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return None
    se = pygame.mixer.Sound(path)
    se.set_volume(SE_VOLUME)
    return se

load_bgm("bgm.mp3")
se_hit  = load_se("se_hit.wav")
se_wave = load_se("se_wave.wav")

# ---------------------------
# リサイズ対応の描画ヘルパー
# ---------------------------
def get_scaled_bg():
    if bg_img_src:
        return pygame.transform.scale(bg_img_src, (WIDTH, HEIGHT))
    return None

def girl_pos():
    if girl_img:
        gx = -10
        gy = HEIGHT - girl_img.get_height() - 10
        return gx, gy
    return 0, HEIGHT - 420

def rod_tip():
    gx, gy = girl_pos()
    return gx + 250, gy - 5

def uki_pos(sink=0):
    ux = int(WIDTH * 0.88)
    uy = int(HEIGHT * 0.95) + sink
    return ux, uy

def quit_btn_rect():
    return pygame.Rect(WIDTH - 80, 10, 70, 32)

def save_btn_rect():
    return pygame.Rect(WIDTH - 80, 50, 70, 32)

def score_panel_rect():
    return pygame.Rect(10, 10, 245, 146)

def enc_panel_rect(enc_count):
    h = 30 + max(enc_count, 1) * 26
    return pygame.Rect(WIDTH - 215, int(HEIGHT * 0.5), 205, h)

# ---------------------------
# 魚データ
# ---------------------------
fish_table = [
    {"name": "メダカ",       "weight": 40, "min": 3,  "max": 8,   "base": 10,  "reaction": 0.4},
    {"name": "アジ",         "weight": 25, "min": 10, "max": 25,  "base": 30,  "reaction": 0.5},
    {"name": "ブラックバス", "weight": 15, "min": 20, "max": 50,  "base": 70,  "reaction": 0.65},
    {"name": "タイ",         "weight": 10, "min": 30, "max": 80,  "base": 150, "reaction": 0.8},
    {"name": "伝説の魚",     "weight": 10, "min": 50, "max": 150, "base": 500, "reaction": 1.0},
]

atmosphere_texts = [
    "水面が静かだ",
    "風が吹いた",
    "波の音が大きくなった",
    "気配がする！",
    "懐かしい匂いがする",
    "鳥が飛んでいく",
    "糸がわずかに引かれた",
    "すこし寒さを感じる",
]

# レアメッセージ（1/50の確率・赤色表示）
rare_atmosphere_texts = [
    "喧騒が聞こえない",
    "これは本当に魚...？",
    "世界に別れを",
    "「Hキーを.....」",
    "亡き日々を思い出す",
]

# ---------------------------
# セーブ（ゲーム進行データ）
# ---------------------------
SAVE_FILE   = os.path.join(BASE_DIR, "fishing_save.json")
SCORES_FILE = os.path.join(BASE_DIR, "scores.json")

if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        save_data = json.load(f)
else:
    save_data = {"score": 0, "highscore": 0, "ms_highscore": 0, "encyclopedia": {}}

# scores.jsonが無ければ空で作成
if not os.path.exists(SCORES_FILE):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False, indent=2)

score        = save_data["score"]
highscore    = save_data["highscore"]  # 一匹で得た最高得点
ms_highscore = save_data.get("ms_highscore", 0)  # 最速反応時間（ms、0は未記録）
encyclopedia = save_data["encyclopedia"]

def save_game():
    save_data["score"]        = score
    save_data["highscore"]    = highscore
    save_data["ms_highscore"] = ms_highscore
    save_data["encyclopedia"] = encyclopedia
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

def save_score_with_name(player_name):
    """プレイヤー名・スコア・日時をscores.jsonに追記保存（スコア降順）"""
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = []

    records.append({
        "name":      player_name,
        "score":     score,
        "highscore": highscore,
        "date":      datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    records.sort(key=lambda r: r["score"], reverse=True)

    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

def get_fish():
    weights = [f["weight"] for f in fish_table]
    return random.choices(fish_table, weights=weights)[0]

def get_size(fish):
    return random.triangular(fish["min"], fish["max"], fish["min"])

# ---------------------------
# テキスト描画
# ---------------------------
def draw_text(text, fnt, color, x, y, shadow=False):
    if shadow:
        s = fnt.render(text, True, (0, 0, 0))
        screen.blit(s, (x+2, y+2))
    screen.blit(fnt.render(text, True, color), (x, y))

def draw_text_center(text, fnt, color, y, shadow=False):
    surf = fnt.render(text, True, color)
    x = WIDTH // 2 - surf.get_width() // 2
    if shadow:
        s = fnt.render(text, True, (0, 0, 0))
        screen.blit(s, (x+2, y+2))
    screen.blit(surf, (x, y))

# ---------------------------
# プレイヤー名入力ダイアログ

def draw_input_dialog(input_text, notice=""):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    dw, dh = 420, 180
    dx = WIDTH  // 2 - dw // 2
    dy = HEIGHT // 2 - dh // 2

    pygame.draw.rect(screen, (40, 60, 80),    (dx, dy, dw, dh), border_radius=12)
    pygame.draw.rect(screen, (120, 180, 255), (dx, dy, dw, dh), 2, border_radius=12)

    draw_text_center("プレイヤー名を入力",             font,       (220, 240, 255), dy + 18)
    draw_text_center("Enterで保存  /  Escでキャンセル", small_font, (160, 200, 220), dy + 52)

    box_rect = pygame.Rect(dx + 20, dy + 90, dw - 40, 36)
    pygame.draw.rect(screen, (255, 255, 255), box_rect, border_radius=6)
    pygame.draw.rect(screen, (100, 160, 255), box_rect, 2, border_radius=6)
    draw_text(input_text + "|", font, (30, 30, 30), box_rect.x + 8, box_rect.y + 4)

    if notice:
        draw_text_center(notice, small_font, (255, 100, 100), dy + 142)

# ---------------------------
# ゲーム状態


state              = "WAIT"
hit_timer          = 0
atm_timer          = 0
atm_message        = ""
atm_is_rare        = False
current_fish       = None
strike_window      = 0
strike_window_max  = 0
strike_clicked     = False
strike_start_time  = 0
reaction_ms        = 0
result_message     = ""
result_timer       = 0
main_message       = "クリックで釣り開始！"
notify_message     = ""  # 保存・リセット完了などの通知
notify_timer       = 0

# 名前入力ダイアログ用
input_mode   = False
input_text   = ""
input_notice = ""

# 白フラッシュ用（0〜255、255が最大輝度）
flash_alpha = 0

bg_img_scaled = get_scaled_bg()

running = True

while running:
    clock.tick(FPS)

    # 背景描画
    if bg_img_scaled:
        screen.blit(bg_img_scaled, (0, 0))
    else:
        screen.fill((135, 206, 235))
        pygame.draw.rect(screen, (30, 100, 180), (0, int(HEIGHT * 0.53), WIDTH, HEIGHT))

    # ---------------------------
    # イベント
    # ---------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.VIDEORESIZE:
            WIDTH, HEIGHT = event.w, event.h
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
            bg_img_scaled = get_scaled_bg()

        # ---- 名前入力モード中のキー処理 ----
        if input_mode:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    name = input_text.strip()
                    if name == "":
                        input_notice = "名前を入力してください"
                    else:
                        save_score_with_name(name)
                        input_mode   = False
                        input_text   = ""
                        input_notice = ""
                        notify_message = f"「{name}」で保存しました！"
                        notify_timer   = 3 * FPS
                        main_message = f"「{name}」で保存しました！"
                elif event.key == pygame.K_ESCAPE:
                    input_mode   = False
                    input_text   = ""
                    input_notice = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if len(input_text) < 12:
                        input_text += event.unicode
            continue  # 入力モード中は他のイベントをスキップ

        # ---- 通常モード ----
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r and state == "WAIT":
                score        = 0
                highscore    = 0
                ms_highscore = 0
                encyclopedia = {}
                save_game()
                notify_message = "リセットしました！"
                notify_timer   = 2 * FPS

            # 隠し要素：Hキーでストーリーファイルを開く
            elif event.key == pygame.K_h:
                story_path = os.path.join(BASE_DIR, "story.txt")
                if os.path.exists(story_path):
                    if sys.platform == "win32":
                        os.startfile(story_path)
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", story_path])
                    else:
                        subprocess.Popen(["xdg-open", story_path])

            # Sキーでスコアボードを開く
            elif event.key == pygame.K_s and not input_mode:
                if sys.platform == "win32":
                    os.startfile(SCORES_FILE)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", SCORES_FILE])
                else:
                    subprocess.Popen(["xdg-open", SCORES_FILE])

        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            if quit_btn_rect().collidepoint(mx, my):
                running = False
            elif save_btn_rect().collidepoint(mx, my):
                input_mode   = True
                input_text   = ""
                input_notice = ""
            elif state == "WAIT":
                state        = "HIT_WAIT"
                hit_timer    = random.randint(10 * FPS, 30 * FPS)
                atm_timer    = random.randint(FPS, 3 * FPS)
                atm_message  = "ウキを投げた…"
                main_message = ""
                if se_wave:
                    se_wave.play()
            elif state == "HIT_WAIT":
                result_message = "早い、なにも釣れなかった…"
                result_timer   = 2 * FPS
                atm_message    = ""
                state          = "RESULT"
            elif state == "STRIKE":
                strike_clicked = True


    # ---------------------------
    # 状態処理

    if state == "HIT_WAIT":
        hit_timer -= 1
        atm_timer -= 1
        if atm_timer <= 0:
            if random.randint(1, 50) == 1:
                atm_message  = random.choice(rare_atmosphere_texts)
                atm_is_rare  = True
            else:
                atm_message  = random.choice(atmosphere_texts)
                atm_is_rare  = False
            atm_timer = random.randint(int(2.5 * FPS), int(5 * FPS))  # 1秒延長
        if hit_timer <= random.randint(FPS, 2 * FPS) and state == "HIT_WAIT":
            current_fish      = get_fish()
            base_window       = int(FPS * 2.5)
            strike_window_max = max(int(base_window * (1.0 - current_fish["reaction"] * 0.5)), int(FPS * 1.0))
            strike_window     = strike_window_max
            strike_clicked    = False
            strike_start_time = pygame.time.get_ticks()
            atm_message       = "HIT!! クリック！"
            state             = "STRIKE"
            flash_alpha       = 255  # 白フラッシュ開始
            if se_hit:
                se_hit.play()
            pygame.mixer.music.set_volume(0.3)

    elif state == "STRIKE":
        # フラッシュ・SE演出中はゲージを止める
        if flash_alpha <= 0:
            strike_window -= 1
        if strike_clicked:
            reaction_ms    = pygame.time.get_ticks() - strike_start_time
            ratio          = strike_window / strike_window_max
            bonus          = 1.0 + ratio * 0.5
            size           = get_size(current_fish)
            avg            = (current_fish["min"] + current_fish["max"]) / 2
            gained         = int(current_fish["base"] * (size / avg) * bonus)
            score         += gained
            # ★ highscoreは一匹で得た最高得点に変更
            if gained > highscore:
                highscore = gained
            # ★ ms_highscoreは最速反応時間（小さいほど優秀）
            if ms_highscore == 0 or reaction_ms < ms_highscore:
                ms_highscore = reaction_ms
            name = current_fish["name"]
            encyclopedia[name] = encyclopedia.get(name, 0) + 1
            save_game()
            timing_str     = "完璧！" if ratio > 0.7 else ("グッド" if ratio > 0.3 else "ギリギリ")
            result_message = f"{timing_str}  {name}  {size:.1f}cm  +{gained}点  {reaction_ms}ms"
            result_timer   = 4 * FPS  # 3→4秒
            state          = "RESULT"
            pygame.mixer.music.set_volume(0.5)
        elif strike_window <= 0:
            result_message = f"{current_fish['name']}に逃げられた…"
            result_timer   = 3 * FPS  # 2→3秒
            state          = "RESULT"
            pygame.mixer.music.set_volume(0.5)

    elif state == "RESULT":
        result_timer -= 1
        if result_timer <= 0:
            atm_message  = ""
            main_message = "クリックで釣り開始！"
            state        = "WAIT"

    # 通知タイマー更新
    if notify_timer > 0:
        notify_timer -= 1
        if notify_timer <= 0:
            notify_message = ""

    # ---------------------------
    # ウキ・釣り糸描画
    # ---------------------------
    ticks = pygame.time.get_ticks()
    rtx, rty = rod_tip()

    if state in ("HIT_WAIT", "WAIT"):
        bob   = int(3 * pygame.math.Vector2(1, 0).rotate(ticks / 8).y)
        ux, uy = uki_pos(bob)
        pygame.draw.line(screen, (220, 220, 200), (rtx, rty), (ux, uy), 2)
        pygame.draw.ellipse(screen, (220, 60, 60),   (ux-6, uy-14, 12, 20))
        pygame.draw.ellipse(screen, (255, 255, 255), (ux-6, uy,    12,  8))

    elif state == "STRIKE":
        ratio = strike_window / strike_window_max
        sink  = int((1 - ratio) * 25)
        ux, uy = uki_pos(sink)
        pygame.draw.line(screen, (220, 220, 200), (rtx, rty), (ux, uy), 2)
        pygame.draw.ellipse(screen, (220, 60, 60),   (ux-6, uy-14, 12, 20))
        pygame.draw.ellipse(screen, (255, 255, 255), (ux-6, uy,    12,  8))

        bar_w  = int(WIDTH * 0.47)
        bar_x0 = WIDTH // 2 - bar_w // 2
        bar_y0 = 55
        pygame.draw.rect(screen, (30, 30, 30),    (bar_x0-2, bar_y0-2, bar_w+4, 24), border_radius=5)
        fill  = int(bar_w * ratio)
        bcol  = (50, 220, 50) if ratio > 0.5 else ((220, 180, 0) if ratio > 0.2 else (220, 50, 50))
        pygame.draw.rect(screen, bcol,            (bar_x0, bar_y0, fill, 20), border_radius=4)
        pygame.draw.rect(screen, (255, 255, 255), (bar_x0, bar_y0, bar_w, 20), 2, border_radius=4)

    # ---------------------------
    # キャラクター描画
    # ---------------------------
    if girl_img:
        screen.blit(girl_img, girl_pos())

    # ---------------------------
    # UI
    # ---------------------------
    # 終了ボタン
    qr = quit_btn_rect()
    pygame.draw.rect(screen, (180, 40, 40), qr, border_radius=6)
    draw_text("終了", small_font, (255, 255, 255), qr.x + 12, qr.y + 7)

    # 保存ボタン
    sr = save_btn_rect()
    pygame.draw.rect(screen, (40, 120, 200), sr, border_radius=6)
    draw_text("保存", small_font, (255, 255, 255), sr.x + 12, sr.y + 7)

    # スコアパネル
    pr = score_panel_rect()
    panel = pygame.Surface((pr.w, pr.h), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 110))
    screen.blit(panel, (pr.x, pr.y))
    draw_text(f"Score : {score}",          font,       (255, 255, 255), pr.x+8, pr.y+8,  shadow=True)
    draw_text(f"1匹Best: {highscore}",     font,       (255, 220, 80),  pr.x+8, pr.y+38, shadow=True)
    ms_hs_str = f"{ms_highscore}ms" if ms_highscore > 0 else "---"
    draw_text(f"反射Best: {ms_hs_str}",    small_font, (100, 255, 180), pr.x+8, pr.y+70, shadow=True)
    draw_text(f"反射  : {reaction_ms}ms",  small_font, (180, 230, 255), pr.x+8, pr.y+94)
    draw_text("R:リセット  S:スコアボード", small_font, (180, 180, 180), pr.x+8, pr.y+118)

    # メインメッセージ
    if state == "WAIT":
        draw_text_center(main_message, font, (255, 255, 255), int(HEIGHT * 0.38), shadow=True)

    # 通知メッセージ（保存・リセット完了など、パネル直下に緑色表示）
    if notify_message:
        draw_text(notify_message, small_font, (120, 220, 120), 20, 132, shadow=True)

    # 雰囲気テキスト
    if state in ("HIT_WAIT", "STRIKE") and atm_message:
        if state == "STRIKE":
            col = (255, 80, 80)
            fnt = big_font
        elif atm_is_rare:
            col = (255, 50, 50)   # レアは赤色
            fnt = font
        else:
            col = (230, 245, 255)
            fnt = font
        draw_text_center(atm_message, fnt, col, int(HEIGHT * 0.33), shadow=True)

    # リザルト
    if state == "RESULT":
        draw_text_center(result_message, font, (255, 255, 100), int(HEIGHT * 0.38), shadow=True)

    # 図鑑パネル
    er = enc_panel_rect(len(encyclopedia))
    ep = pygame.Surface((er.w, er.h), pygame.SRCALPHA)
    ep.fill((0, 0, 0, 110))
    screen.blit(ep, (er.x, er.y))
    draw_text("図鑑", small_font, (220, 240, 255), er.x+30, er.y+4)
    ey = er.y + 28
    for name, count in encyclopedia.items():
        draw_text(f"{name}: {count}匹", small_font, (200, 230, 255), er.x+8, ey)
        ey += 26

    # 白フラッシュ（最前面、ダイアログより手前）
    if flash_alpha > 0:
        flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash_surf.fill((255, 255, 255, flash_alpha))
        screen.blit(flash_surf, (0, 0))
        flash_alpha = max(0, flash_alpha - 25)  # 約10フレームでフェードアウト
        # フラッシュが消えた瞬間に反射計測をリセット
        if flash_alpha == 0:
            strike_start_time = pygame.time.get_ticks()

    # 名前入力ダイアログ（最前面）
    if input_mode:
        draw_input_dialog(input_text, input_notice)

    pygame.display.flip()

pygame.quit()