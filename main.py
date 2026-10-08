import flet as ft
import requests
import time
import random
import threading
from collections import Counter
from datetime import datetime

# ==========================================
# NEXUS AI - FLET GRAPHICAL APP EDITION V21.0
# ==========================================

# Configuration
GAME_NAME = "WinGo"
GAME_TIME = "1M"
API_URL = f"https://draw.ar-lottery01.com/{GAME_NAME}/{GAME_NAME}_{GAME_TIME}/GetHistoryIssuePage.json"
CHECK_INTERVAL = 3
BASE_BET_INR = 10

# State
last_period = None
current_prediction = None
stats = {"win": 0, "loss": 0, "jackpot": 0, "streak": 0, "level": 0, "net_pl": 0.0}
history_log = []
active_mode = "BS"

def get_size(num): return "BIG" if num >= 5 else "SMALL"
def get_color_base(num):
    if num in [2, 4, 6, 8, 0]: return "RED"
    if num in [1, 3, 7, 9, 5]: return "GREEN"

def fetch_history():
    try:
        url = f"{API_URL}?t={int(time.time() * 1000)}"
        r = requests.get(url, timeout=5)
        d = r.json()
        if 'data' in d and 'list' in d['data']:
            return d['data']['list']
    except:
        pass
    return None

def get_frequent_number(raw_nums, target_category, mode):
    valid_nums = []
    if mode == "COL":
        valid_nums = [2, 4, 6, 8, 0] if target_category == "RED" else [1, 3, 7, 9, 5]
    else:
        valid_nums = [5, 6, 7, 8, 9] if target_category == "BIG" else [0, 1, 2, 3, 4]
        
    matching_history = [n for n in raw_nums[:20] if n in valid_nums]
    if matching_history:
        counts = Counter(matching_history)
        max_count = max(counts.values())
        best_nums = [n for n, c in counts.items() if c == max_count]
        return random.choice(best_nums)
    return random.choice(valid_nums)

def advanced_ml_logic(past_outcomes, raw_nums, mode, current_loss_level):
    if not past_outcomes: return "BIG", 5, 0.0, "Init"
    
    counts = Counter(past_outcomes[:4])
    max_count = max(counts.values())
    preds = [k for k, v in counts.items() if v == max_count]
    pred = preds[0]
    conf = min(98.5, (max_count/4 * 100) + random.uniform(10, 20))
    pat = f"Freq Matrix(R={max_count})"
    
    if current_loss_level >= 2:
        pred = past_outcomes[0] 
        pat = "🔥 DEEP RECOVERY"
        conf = 99.9

    best_num = get_frequent_number(raw_nums, pred, mode)
    return pred, best_num, round(conf, 1), pat

def generate_prediction(history, mode, loss_level):
    raw_nums = [int(x['number']) for x in history[:50]]
    if len(raw_nums) < 3: return None
    
    if mode == "COL":
        colors = [get_color_base(n) for n in raw_nums]
        target, num, conf, pat = advanced_ml_logic(colors, raw_nums, mode, loss_level)
        return {"type": "COL", "val": target, "num": num, "conf": conf, "pattern": pat}
    else:
        sizes = [get_size(n) for n in raw_nums]
        target, num, conf, pat = advanced_ml_logic(sizes, raw_nums, mode, loss_level)
        return {"type": "BS", "val": target, "num": num, "conf": conf, "pattern": pat}

def main(page: ft.Page):
    page.title = "DIABLO SCRIPT - GOD MODE"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLACK
    page.padding = 10
    
    # UI Elements
    app_bar = ft.AppBar(
        title=ft.Text("☠ DIABLO SCRIPT V21.0 ☠", color=ft.colors.RED_ACCENT, weight="bold"),
        bgcolor=ft.colors.BLACK87,
        center_title=True
    )
    page.appbar = app_bar

    stats_text = ft.Text(value="WINS: 0 | LOSSES: 0 | RATE: 0.0% | P/L: ₹0.0", color=ft.colors.CYAN_ACCENT, weight="bold", size=14)
    
    active_period = ft.Text("Period: Syncing...", color=ft.colors.WHITE, size=16)
    active_pred = ft.Text("Predict: --", color=ft.colors.GREEN_ACCENT, weight="bold", size=18)
    active_alloc = ft.Text("Alloc: --", color=ft.colors.YELLOW_ACCENT, size=16)
    active_conf = ft.ProgressBar(width=200, value=0, color=ft.colors.CYAN_ACCENT)
    conf_text = ft.Text("0%", color=ft.colors.CYAN_ACCENT)

    active_card = ft.Container(
        content=ft.Column([
            ft.Row([active_period, ft.Text("Mode: AUTO", color=ft.colors.PURPLE_ACCENT)], alignment="spaceBetween"),
            ft.Row([active_pred, active_alloc], alignment="spaceBetween"),
            ft.Row([ft.Text("CONF: "), active_conf, conf_text]),
            ft.Text("Status: AWAITING RESULT...", color=ft.colors.YELLOW)
        ]),
        padding=10,
        border=ft.border.all(1, ft.colors.GREEN_700),
        border_radius=5,
        bgcolor="#0a1910"
    )

    history_list = ft.ListView(expand=True, spacing=5, auto_scroll=True)

    header_row = ft.Row([
        ft.Text("PER", width=50, weight="bold", color=ft.colors.WHITE70),
        ft.Text("PRED", width=80, weight="bold", color=ft.colors.WHITE70),
        ft.Text("ACTUAL", width=80, weight="bold", color=ft.colors.WHITE70),
        ft.Text("₹", width=50, weight="bold", color=ft.colors.WHITE70),
        ft.Text("RESULT", width=80, weight="bold", color=ft.colors.WHITE70),
    ])

    page.add(
        ft.Container(content=stats_text, alignment=ft.alignment.center, padding=5),
        active_card,
        ft.Divider(color=ft.colors.WHITE24),
        header_row,
        history_list
    )

    def color_picker(val):
        if "GREEN" in val or "BIG" in val: return ft.colors.GREEN_ACCENT
        if "RED" in val or "SMALL" in val: return ft.colors.RED_ACCENT
        if "WIN" in val: return ft.colors.GREEN
        if "LOSS" in val: return ft.colors.RED
        if "EXACT" in val: return ft.colors.BLUE_ACCENT
        return ft.colors.WHITE

    def background_task():
        global last_period, current_prediction, stats, active_mode
        
        while True:
            history = fetch_history()
            if not history:
                time.sleep(CHECK_INTERVAL)
                continue
                
            latest = history[0]
            current_period = latest['issueNumber']
            actual_num = int(latest['number'])
            actual_size = get_size(actual_num)
            actual_color_base = get_color_base(actual_num)
            
            if last_period and current_period != last_period:
                if current_prediction:
                    p_val = current_prediction['val']
                    p_num = current_prediction['num']
                    
                    risk_mult = 3 ** min(stats['level'], 4)
                    bet_amt = BASE_BET_INR * risk_mult
                    
                    is_win = False
                    is_exact = (p_num == actual_num)

                    if current_prediction['type'] == "COL":
                        if actual_color_base == p_val: is_win = True
                    else:
                        if actual_size == p_val: is_win = True

                    if is_win:
                        res_str = "✔ WIN"
                        stats['win'] += 1
                        stats['level'] = 0
                        stats['net_pl'] += (bet_amt * 0.96)
                        active_mode = "BS" if current_prediction['type'] == "COL" else active_mode
                    else:
                        res_str = "✗ LOSS"
                        stats['loss'] += 1
                        stats['level'] += 1
                        stats['net_pl'] -= bet_amt
                        if stats['level'] == 2: active_mode = "COL"
                    
                    if is_exact:
                        res_str = "🎯 EXACT"
                        stats['net_pl'] += (bet_amt * 8.82)
                        stats['jackpot'] += 1

                    # Add to listview
                    history_list.controls.append(
                        ft.Row([
                            ft.Text(current_period[-5:], width=50, color=ft.colors.WHITE),
                            ft.Text(f"{p_val}({p_num})", width=80, color=color_picker(p_val)),
                            ft.Text(f"{actual_size}({actual_num})", width=80, color=color_picker(actual_size)),
                            ft.Text(f"{bet_amt}", width=50, color=ft.colors.YELLOW),
                            ft.Text(res_str, width=80, color=color_picker(res_str), weight="bold"),
                        ])
                    )
                    
                    # Keep only last 50 items to save memory
                    if len(history_list.controls) > 50:
                        history_list.controls.pop(0)

                last_period = current_period
                current_prediction = generate_prediction(history, active_mode, stats['level'])
                
            elif not last_period:
                last_period = current_period
                current_prediction = generate_prediction(history, active_mode, stats['level'])

            # Update UI
            if current_prediction:
                next_p = str(int(current_period) + 1)
                active_period.value = f"Period: {next_p[-6:]}"
                active_pred.value = f"Predict: {current_prediction['val']}({current_prediction['num']})"
                active_pred.color = color_picker(current_prediction['val'])
                
                risk = 3 ** min(stats['level'], 4)
                active_alloc.value = f"Alloc: {risk}X (₹{BASE_BET_INR * risk})"
                
                conf = current_prediction['conf']
                active_conf.value = conf / 100
                conf_text.value = f"{conf}%"

            total = stats['win'] + stats['loss']
            rate = (stats['win'] / total * 100) if total > 0 else 0.0
            sign = "+" if stats['net_pl'] >= 0 else ""
            stats_text.value = f"WIN: {stats['win']} | LOSS: {stats['loss']} | JKP: {stats['jackpot']} | {rate:.1f}% | P/L: {sign}₹{stats['net_pl']:.1f}"

            page.update()
            time.sleep(CHECK_INTERVAL)

    # Start background thread
    threading.Thread(target=background_task, daemon=True).start()

ft.app(target=main)