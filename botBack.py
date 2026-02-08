import tkinter as tk
from tkinter import scrolledtext, Toplevel
import pyautogui, pydirectinput, threading, time, json, os, cv2, random
import numpy as np
from datetime import datetime
from pynput import keyboard
import pytesseract
from tkinter import ttk  # Добавляем для работы вкладок
from datetime import datetime, timedelta
import scipy.interpolate as interp # Для создания кривых


# --- НАСТРОЙКИ ---
pyautogui.PAUSE = 0
THR_WINDOW = 0.55
THR_CRYSTAL = 0.55
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
CONFIG_FILE = "settings.json"
ITEMS_DIR = "items"
DEBUG_DIR = "debug"
WINDOW_TEMPLATES = [os.path.join(ITEMS_DIR, f"price_window_{i}.png") for i in range(1, 5)]
CRYSTAL_TEMPLATE = os.path.join(ITEMS_DIR, "crystal_anchor.png")

for d in [ITEMS_DIR, DEBUG_DIR]:
    if not os.path.exists(d): os.makedirs(d)


    class AreaSelector:
        def __init__(self, callback):
            self.callback = callback
            self.root = tk.Tk()
            self.root.attributes("-alpha", 0.3, "-topmost", True, "-fullscreen", True)
            self.root.config(cursor="cross")
            self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey")
            self.canvas.pack(fill="both", expand=True)
            self.start_x = self.start_y = None
            self.rect = None
            self.canvas.bind("<ButtonPress-1>", self.on_press)
            self.canvas.bind("<B1-Motion>", self.on_drag)
            self.canvas.bind("<ButtonRelease-1>", self.on_release)
            self.root.mainloop()

        def on_press(self, e):
            self.start_x, self.start_y = e.x, e.y
            self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)

        def on_drag(self, e):
            self.canvas.coords(self.rect, self.start_x, self.start_y, e.x, e.y)

        def on_release(self, e):
            x1, y1, x2, y2 = min(self.start_x, e.x), min(self.start_y, e.y), max(self.start_x, e.x), max(self.start_y,
                                                                                                         e.y)
            self.root.destroy()
            if x2 - x1 > 2 and y2 - y1 > 2:
                self.callback(x1, y1, x2 - x1, y2 - y1)

class BotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Divine Bot v21.2 [FINAL AUTO]")
        self.root.geometry("285x545")
        self.root.attributes("-topmost", True)
        self.is_running = False
        self.start_time = None  # Время нажатия ПУСК
        self.end_time = None  # Время, когда бот должен выключиться
        self.stats = {"cycles": 0, "bought": 0}
        self.real_stock = {n: 0 for n in ["Герб Охоты", "Герб Войны", "Герб Могущества", "Герб Механизмов"]}
        self.config = self.load_config()
        self.create_widgets()
        self.listener = keyboard.Listener(on_press=self.on_hotkey)
        self.listener.start()
        self.log("🤖 Бот запущен. Логика D -> T -> ЛКМ добавлена.")

    def click_image_random(self, name, thr=0.55, clicks=1):
        if not self.is_running: return False
        rect = self.find_img_rect(name, thr)
        if rect:
            x, y, w, h = rect
            # Генерируем одну точку для всей серии кликов
            rx = x + random.randint(int(w * 0.2), int(w * 0.8))
            ry = y + random.randint(int(h * 0.2), int(h * 0.8))

            self.smooth_move(rx, ry)

            # Цикл для нескольких нажатий
            for i in range(clicks):
                if not self.is_running: break
                pydirectinput.click()
                if clicks > 1:
                    # Короткая пауза между кликами, чтобы игра засчитала их
                    time.sleep(random.uniform(0.04, 0.08))
            return True
        return False

    def load_config(self):
        default = {"click_zones": {}, "stock_zones": {}, "tg_token": "", "tg_chat_id": "", "cycles": 10, "min_stock": 1}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for key, value in default.items():
                        if key not in loaded: loaded[key] = value
                    return loaded
            except:
                return default
        return default

    def save_cfg(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(self.config, f)

    def log(self, message):
        now = datetime.now().strftime("%H:%M:%S")

        def append():
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, f"[{now}] {message}\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state='disabled')

        self.root.after(0, append)

    def smart_sleep(self, sec):
        st = time.time()
        while time.time() - st < sec:
            if not self.is_running: return False
            time.sleep(0.05)
        return True

    def smooth_move(self, x, y):
        if not self.is_running: return

        start_x, start_y = pyautogui.position()
        dist = np.hypot(x - start_x, y - start_y)

        if dist < 5: return

        # 1. Генерируем контрольные точки для кривой
        cp_count = random.randint(2, 3)
        x_pts = np.linspace(start_x, x, cp_count + 2)
        y_pts = np.linspace(start_y, y, cp_count + 2)

        # Смещение для дуги (0.1 - небольшая дуга, 0.2 - сильная)
        offset = dist * random.uniform(0.1, 0.15)

        for i in range(1, len(x_pts) - 1):
            x_pts[i] += random.uniform(-offset, offset)
            y_pts[i] += random.uniform(-offset, offset)

        try:
            t = np.linspace(0, 1, cp_count + 2)
            px = interp.interp1d(t, x_pts, kind='quadratic')
            py = interp.interp1d(t, y_pts, kind='quadratic')

            # --- РЕГУЛИРОВКА СКОРОСТИ ---
            # Уменьшаем число в делителе (было 15-25, стало 5-10), чтобы шагов стало БОЛЬШЕ
            steps = int(dist / random.randint(5, 10))
            if steps < 20: steps = 20  # Минимальное кол-во шагов для плавности

            for i in range(steps + 1):
                if not self.is_running: break
                curr_t = i / steps

                # Двигаем мышь
                pyautogui.moveTo(int(px(curr_t)), int(py(curr_t)))

                # Увеличиваем паузу (было 0.001, стало 0.005 - 0.01)
                # Это основной параметр замедления
                time.sleep(random.uniform(0.003, 0.0010))

        except Exception as e:
            # Резервный вариант: увеличиваем duration (было 0.3-0.6, стало 0.7-1.2)
            pyautogui.moveTo(x, y, duration=random.uniform(0.5, 0.8), tween=pyautogui.easeInOutQuad)

        # Пауза после завершения движения перед кликом
        time.sleep(random.uniform(0.1, 0.2))

    def type_smart(self, text):
        for char in text:
            if char == '.':
                pydirectinput.press('/')
            else:
                pydirectinput.press(char)
            time.sleep(random.uniform(0.05, 0.1))

    def preprocess_for_ocr(self, img_np):
        b, g, r = cv2.split(img_np)
        gray = cv2.max(r, cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY))
        gray = cv2.resize(gray, None, fx=15, fy=15, interpolation=cv2.INTER_CUBIC)
        gray = cv2.blur(gray, (2, 2))
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        return thresh

    def find_img_rect(self, name, thr=0.55, force_brightness=None):
        if not self.is_running: return None
        path = os.path.join(ITEMS_DIR, f"{name}.png")
        if not os.path.exists(path): return None

        # Читаем шаблон и получаем его размеры
        template = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        th, tw = template.shape[:2]

        # Делаем скриншот
        screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)

        # Поиск совпадений
        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if max_val >= thr:
            # Возвращаем (X, Y, W, H)
            return (max_loc[0], max_loc[1], tw, th)
        return None

    def random_click(self, key):
        if not self.is_running: return False
        z = self.config.get("click_zones", {}).get(key)
        if not z: return False
        rx, ry = z['x'] + random.randint(5, z['w'] - 5), z['y'] + random.randint(5, z['h'] - 5)
        self.smooth_move(rx, ry);
        pydirectinput.click()
        return True

    def update_all_stocks(self):
        if not self.is_running: return
        pydirectinput.press('d')
        self.smart_sleep(random.uniform(0.4, 0.6))
        # 1. Сначала ищем кнопку, чтобы узнать, куда кликать "в никуда"
        rect = self.find_img_rect("btn_divine_trial", thr=0.65)

        if rect:
            x, y, w, h = rect
            press_count = random.randint(1, 3)
            self.log(f"💠 Кнопка найдена. Прокликиваю {press_count} раз(а)...")

            # Генерируем одну точку клика для всей серии
            rx = x + random.randint(int(w * 0.2), int(w * 0.8))
            ry = y + random.randint(int(h * 0.2), int(h * 0.8))

            # 1. ПЛАВНО подводим мышь один раз
            self.smooth_move(rx, ry)

            # 2. МГНОВЕННО стреляем кликами
            for i in range(press_count):
                pydirectinput.click()
                # Минимальный микро-сон, чтобы игра не "подавилась" скоростью
                time.sleep(random.uniform(0.01, 0.03))
                self.log(f"🖱️ Клик {i + 1} выполнен")
        else:
            self.log("⚠️ Не нашел кнопку 'Испытание', пропускаю прокликивание")
            return

        self.smart_sleep(0.8)
        items = ["Герб Охоты", "Герб Войны", "Герб Могущества", "Герб Механизмов"]
        for n in items:
            zone = self.config.get("stock_zones", {}).get(n)
            if zone:
                img = pyautogui.screenshot(region=(zone['x'], zone['y'], zone['w'], zone['h']))
                processed = self.preprocess_for_ocr(cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR))
                txt = pytesseract.image_to_string(processed, config=r'--psm 7 -c tessedit_char_whitelist=0123456789/')
                try:
                    self.real_stock[n] = int(txt.split('/')[0])
                except:
                    self.real_stock[n] = 0
        self.log(f"📋 Запас обновлен: {list(self.real_stock.values())}")

    def collect_from_market(self):
        pydirectinput.press('esc');
        self.smart_sleep(random.uniform(0.11, 0.15))
        self.random_click("btn_market_history_1");
        self.smart_sleep(random.uniform(0.11, 0.15))
        self.random_click("btn_market_history_2");
        self.smart_sleep(random.uniform(0.11, 0.15))
        if self.random_click("btn_collect_all"): self.smart_sleep(random.uniform(4, 5))
        pydirectinput.press('space')

    def get_market_price(self):
        if not self.is_running: return 0.0
        try:
            screen = np.array(pyautogui.screenshot())
            screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
            found_win = None
            for path in WINDOW_TEMPLATES:
                if not os.path.exists(path): continue
                win_tmpl = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_GRAYSCALE)
                res_win = cv2.matchTemplate(screen_gray, win_tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_val_w, _, max_loc_w = cv2.minMaxLoc(res_win)
                if max_val_w >= THR_WINDOW:
                    found_win = (max_loc_w, win_tmpl.shape);
                    break
            if not found_win: return 0.0
            (wx, wy), (wh, ww) = found_win[0], found_win[1]
            roi_gray = screen_gray[wy:wy + wh, wx:wx + ww]
            crys_tmpl = cv2.imdecode(np.fromfile(CRYSTAL_TEMPLATE, np.uint8), cv2.IMREAD_GRAYSCALE)
            res_crys = cv2.matchTemplate(roi_gray, crys_tmpl, cv2.TM_CCOEFF_NORMED)
            locs = np.where(res_crys >= THR_CRYSTAL)
            found = []
            for pt in zip(*locs[::-1]):
                if not any(abs(pt[1] - c[1]) < 10 for c in found): found.append(pt)
            found.sort(key=lambda x: x[1])
            if len(found) > 0:
                target_idx = 4 if len(found) >= 5 else (len(found) - 1)
                cx, cy = found[target_idx]
                digit_x, digit_y = wx + cx + 25, wy + cy - 5
                roi_digits = screen[digit_y:digit_y + 35, digit_x:digit_x + 110]
                processed = self.preprocess_for_ocr(roi_digits)
                text = pytesseract.image_to_string(processed, config=r'--psm 7 -c tessedit_char_whitelist=0123456789.')
                price_str = "".join(c for c in text if c.isdigit() or c == '.')
                if price_str: return float(price_str)
        except:
            pass
        return 0.0

    def market_buy_process(self, name):
        try:
            target = int(self.target_limit_ent.get())
            current = self.real_stock.get(name, 0)
            need = target - current
        except:
            need = 100
        if need <= 0: return
        self.log(f"🛒 Рынок: {name}. Нужно: {need}")
        self.smart_sleep(random.uniform(0.11, 0.1))
        pydirectinput.press('b');
        self.smart_sleep(random.uniform(0.15, 0.2))
        if not self.random_click("btn_trade_house"): return
        self.smart_sleep(random.uniform(0.11, 0.12))
        if not self.random_click("btn_search_input"): return
        for _ in range(5): pydirectinput.press('backspace')
        pydirectinput.keyDown('shift');
        pydirectinput.press('u');
        pydirectinput.keyUp('shift')
        pydirectinput.press('t');
        pydirectinput.press('h');
        pydirectinput.press(',');
        pydirectinput.press('enter')
        self.smart_sleep(random.uniform(0.11, 0.2))
        cat_pos = self.find_img(name, thr=0.40)
        if not cat_pos: pydirectinput.press('space'); return
        self.smooth_move(cat_pos[0], cat_pos[1]);
        pydirectinput.click();
        self.smart_sleep(1)
        btn_pos = self.find_img("Цена_1") or self.find_img("Цена_2")
        if btn_pos:
            self.smooth_move(btn_pos[0], btn_pos[1]);
            pydirectinput.click();
            self.smart_sleep(1.5)
            base_p = self.get_market_price()
            if base_p > 0:
                price_to_type = "{:.2f}".format(base_p + 0.1)
                off_pos = self.find_img("offers_btn_template")
                if off_pos:
                    self.smooth_move(off_pos[0], off_pos[1]);
                    pydirectinput.click();
                    self.smart_sleep(1)
                    filt_pos = self.find_img("price_filter_template")
                    if filt_pos:
                        self.smooth_move(filt_pos[0], filt_pos[1]);
                        pydirectinput.click();
                        self.smart_sleep(1)
                        if self.random_click("btn_item_price"):
                            for _ in range(4): pydirectinput.press('backspace')
                            self.type_smart(price_to_type);
                            pydirectinput.press('enter');
                            self.smart_sleep(0.13)
                            conf_pos = self.find_img("Подтвердить")
                            if conf_pos: self.smooth_move(conf_pos[0],
                                                          conf_pos[1]); pydirectinput.click(); self.smart_sleep(0.6)
        bought_in_session = 0
        bought_any = False
        page_count = 1
        while self.is_running and bought_in_session < need and page_count <= 5:
            screen_cv = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
            processed_screen = cv2.convertScaleAbs(screen_cv, alpha=1.0, beta=0)
            path = os.path.join(ITEMS_DIR, f"{name}_список.png")
            if not os.path.exists(path): break
            template = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
            th, tw = template.shape[:2]
            res = cv2.matchTemplate(processed_screen, template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= 0.90)
            rects = []
            for pt in zip(*loc[::-1]):
                rects.append([int(pt[0]), int(pt[1]), int(tw), int(th)])
                rects.append([int(pt[0]), int(pt[1]), int(tw), int(th)])
            rects, _ = cv2.groupRectangles(rects, 1, 0.2)
            for (x, y, w, h) in rects:
                if not self.is_running or bought_in_session >= need: break
                roi = screen_cv[y:y + h, x:x + w]
                if np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)) < 70: continue
                cx, cy = x + w // 2, y + h // 2
                ix, iy = int(cx - 30), int(cy - 80)
                lot_shot = pyautogui.screenshot(region=(ix, iy, 100, 100))
                lot_cv = cv2.resize(cv2.cvtColor(np.array(lot_shot), cv2.COLOR_RGB2BGR), None, fx=2, fy=2)
                _, thresh_lot = cv2.threshold(lot_cv, 150, 255, cv2.THRESH_BINARY_INV)
                txt = pytesseract.image_to_string(thresh_lot, config=r'--psm 11 -c tessedit_char_whitelist=0123456789')
                try:
                    lot_count = int("".join(txt.split())) if txt.strip() else 1
                except:
                    lot_count = 1
                self.smooth_move(cx, cy);
                pydirectinput.click();
                time.sleep(random.uniform(0.4, 0.6))
                buy_btn = self.find_img("Купить", thr=0.40)
                if buy_btn:
                    self.smooth_move(buy_btn[0], buy_btn[1]);
                    pydirectinput.click();
                    time.sleep(random.uniform(0.4, 0.6))
                    conf_btn = self.find_img("Подтвердить_закупку", thr=0.55)
                    if conf_btn:
                        self.smooth_move(conf_btn[0], conf_btn[1]);
                        pydirectinput.click()
                        bought_in_session += lot_count;
                        self.stats["bought"] += lot_count;
                        bought_any = True
                        self.log(f"✅ Куплено: {lot_count}");
                        self.root.after(0, self.update_stat_ui);
                        self.smart_sleep(0.5)
                else:
                    pydirectinput.click(cx + 200, cy)
            if bought_in_session < need:
                nxt = self.find_img("next_page", thr=0.55)
                if nxt:
                    self.smooth_move(nxt[0], nxt[1]); pydirectinput.click(); page_count += 1; self.smart_sleep(1.5)
                else:
                    break
            else:
                break
        if bought_any:
            self.log("📦 Сбор купленного...");
            for _ in range(2): pydirectinput.press('esc'); self.smart_sleep(0.4)
            self.collect_from_market();
            self.update_all_stocks()
        else:
            pydirectinput.press('space')

    def wait_for_loading_and_move(self):
        if not self.is_running: return False

        # --- ШАГ 1: ОЖИДАНИЕ ЗАГРУЗКИ В БОЙ ---
        if not self.wait_for_img_with_log("Область_загрузки", "⏳ Ожидание загрузки боя..."):
            return False

        # --- ШАГ 2: ДЕЙСТВИЯ В БОЮ ---
        z_aim = self.config.get("click_zones", {}).get("zone_move_aim")
        if z_aim:
            rx, ry = self.get_random_pt(z_aim)
            self.smooth_move(rx, ry) # Движение по кривой
            self.hold_key('w', random.uniform(0.56, 0.65))

            self.log("🤖 Активация механики + хаотичный обзор...")
            pydirectinput.press('d')
            time.sleep(random.uniform(0.05, 0.1))
            pydirectinput.press('t')

            # Хаос вместо паузы
            start_wait = time.time()
            wait_duration = random.uniform(1.5, 2.0)
            while time.time() - start_wait < wait_duration:
                if not self.is_running: break
                mx = random.randint(-50, 50)
                my = random.randint(-40, 40)
                pyautogui.moveRel(mx, my, duration=random.uniform(0.1, 0.2))
                time.sleep(random.uniform(0.05, 0.1))

            # Остановка
            z_stop = self.config.get("click_zones", {}).get("zone_stop_mech")
            if z_stop:
                sx, sy = self.get_random_pt(z_stop)
                self.smooth_move(sx, sy) # Возврат по кривой
                pydirectinput.click()
                self.loot_process()

                time.sleep(random.uniform(0.1, 0.2))
                pydirectinput.press('d')

        # --- ШАГ 3: ВОЗВРАТ В ГОРОД ---
        time.sleep(random.uniform(0.3, 0.4))
        town_img = "Область_загрузки_city" if os.path.exists(
            os.path.join(ITEMS_DIR, "Область_загрузки_city.png")) else "Область_загрузки"

        if self.wait_for_img_with_log(town_img, "⏳ Ожидание загрузки города..."):
            z_town = self.config.get("click_zones", {}).get("zone_town_aim")
            if z_town:
                tx, ty = self.get_random_pt(z_town)
                self.smooth_move(tx, ty)
                self.hold_key('w', random.uniform(0.55, 0.65))

                pydirectinput.press('d')
                self.smart_sleep(random.uniform(0.8, 1.0))

                # Цепочка диалогов с рандомными кликами (1-3)
                if self.random_click_v2("btn_npc_dialog_text"):
                    self.smart_sleep(random.uniform(0.4, 0.6))
                    if self.random_click_v2("zone_finish_call"):
                        self.smart_sleep(random.uniform(0.4, 0.6))
                        if self.random_click_v2("zone_confirm_exit"):
                            self.log("✅ Вызов завершен.")
                            self.smart_sleep(random.uniform(0.4, 0.6))
                            pydirectinput.press('space')
                            return True
        return False

    def random_click_v2(self, key):
        """Вспомогательный метод для рандомного кол-ва кликов по зоне"""
        count = random.randint(1, 3)
        for _ in range(count):
            if not self.random_click(key): return False
            time.sleep(random.uniform(0.04, 0.07))
        return True

    def get_random_pt(self, z):
        return (z['x'] + random.randint(5, max(6, z['w'] - 5)),
                z['y'] + random.randint(5, max(6, z['h'] - 5)))

    def hold_key(self, key, duration):
        pydirectinput.keyDown(key)
        time.sleep(duration)
        pydirectinput.keyUp(key)

    def loot_process(self):
        if random.choice([True, False]):
            clicks = random.randint(5, 7)
            for _ in range(clicks):
                pydirectinput.press('a')
                time.sleep(random.uniform(0.01, 0.1))
        else:
            self.hold_key('a', random.uniform(2.0, 3.0))

    def wait_for_img_with_log(self, img_name, log_msg):
        self.log(log_msg)
        start = time.time()
        while time.time() - start < 25:
            if not self.is_running: return False
            # Используем rect, так как find_img удален
            if self.find_img_rect(img_name, thr=0.55): return True
            time.sleep(random.uniform(0.8, 1))
        return False

    def start_farm_process(self):
        if not self.is_running: return False
        self.log("⚔️ Поиск кнопок входа по шаблонам...")

        # 1. Кликаем на "Начать_фарм" (от 1 до 3 раз)
        count_start = random.randint(1, 3)
        if self.click_image_random("Начать_фарм", thr=0.55, clicks=count_start):
            self.log(f"✅ Нажал 'Начать' ({count_start} раз)")
            self.smart_sleep(random.uniform(0.7, 1.2))

            # 2. Кликаем на "Подтвердить_фарм" (от 1 до 3 раз)
            count_conf = random.randint(1, 3)
            if self.click_image_random("Подтвердить_фарм", thr=0.55, clicks=count_conf):
                self.log(f"✅ Нажал 'Подтвердить' ({count_conf} раз)")
                self.smart_sleep(random.uniform(0.3, 0.5))
                return self.wait_for_loading_and_move()
            else:
                self.log("⚠️ Не нашел 'Подтвердить_фарм' на экране")
        else:
            self.log("❌ Не нашел 'Начать_фарм' на экране")

        return False

    def bot_loop(self):
        try:
            # Считываем время из поля ввода
            try:
                hours = float(self.work_time_ent.get().replace(',', '.'))
            except:
                hours = 6.0
                self.log("⚠️ Ошибка ввода времени, ставлю 6ч")

            self.start_time = datetime.now()
            self.end_time = self.start_time + timedelta(hours=hours)

            self.log(f"🕒 Старт. Бот проработает до {self.end_time.strftime('%H:%M:%S')}")

            # --- ОБРАТНЫЙ ОТСЧЕТ ---
            for i in range(5, 0, -1):
                if not self.is_running: return
                self.log(f"🕒 Старт через {i}... Переключитесь на игру!")
                time.sleep(1)

                # ВАЖНО: Делаем клик, чтобы окно игры стало активным
            self.log("🖱️ Активирую окно игры...")
            pydirectinput.click()
            time.sleep(0.5)

            self.log("🚀 Поехали! Нажимаю D...")
            # ------------------------------------

            items = ["Герб Охоты", "Герб Войны", "Герб Могущества", "Герб Механизмов"]

            while self.is_running:
                if datetime.now() >= self.end_time:
                    self.log("⏰ Время работы вышло.")
                    break

                self.update_all_stocks()
                ready = True

                for name in items:
                    if not self.is_running: return

                    # Если ресурса не хватает
                    if self.real_stock[name] < int(self.min_stock_ent.get() or 1):
                        ready = False
                        pydirectinput.press('space')  # Закрыть всё
                        self.market_buy_process(name)  # Закупка

                        # --- ЦИКЛ 5 ПОПЫТОК НАЖАТЬ "ИСПЫТАНИЕ" ---
                        found_button = False
                        for attempt in range(1, 6):
                            if not self.is_running: return
                            self.log(f"🔄 Попытка {attempt}/5: открываю меню NPC...")

                            pydirectinput.press('space')
                            self.smart_sleep(0.5)
                            pydirectinput.press('d')

                            # Ждем появления кнопки 2.5 секунды
                            wait_start = time.time()
                            while time.time() - wait_start < 2.5:
                                if not self.is_running: return
                                rect_loop = self.find_img_rect("btn_divine_trial", thr=0.55)
                                if rect_loop:
                                    lx, ly, lw, lh = rect_loop
                                    rx = lx + random.randint(5, lw - 5)
                                    ry = ly + random.randint(5, lh - 5)
                                    self.smooth_move(rx, ry)

                                    for _ in range(random.randint(1, 3)):
                                        pydirectinput.click()
                                        time.sleep(random.uniform(0.05, 0.1))

                                    found_button = True
                                    break  # Выход из while
                                time.sleep(0.2)

                            if found_button: break  # Выход из for (попытки)

                        if not found_button:
                            self.log("❌ Не вошел в меню за 5 попыток. Стоп.")
                            self.is_running = False
                            return

                        # ВАЖНО: После закупки и нажатия кнопки мы прерываем цикл предметов,
                        # чтобы снова зайти в update_all_stocks и убедиться, что всё купилось.
                        break

                        # ТОЛЬКО КОГДА ВСЕ ПРЕДМЕТЫ ПРОВЕРЕНЫ И ready == True
                if ready and self.is_running:
                    self.log("🚀 Все ресурсы готовы, начинаю фарм...")
                    if self.start_farm_process():
                        self.stats["cycles"] += 1
                        self.root.after(0, self.update_stat_ui)
                        self.log(f"🏁 Круг #{self.stats['cycles']} завершен.")
                        self.smart_sleep(random.uniform(1.0, 2.0))
                else:
                    self.log("🔄 Ресурсы не готовы или была дозакупка, проверяю снова...")
                    self.smart_sleep(1.0)

                if ready and self.is_running:
                    # Начинаем фарм (метод доделает круг до конца, даже если время выйдет в процессе)
                    if self.start_farm_process():
                        self.stats["cycles"] += 1
                        self.root.after(0, self.update_stat_ui)
                        self.log(f"🏁 Круг #{self.stats['cycles']} завершен.")
                        self.smart_sleep(random.uniform(0.4, 1.3))
                else:
                    self.log("🔄 Ресурсы не готовы, повтор...")
        finally:
            self.is_running = False
            self.root.after(0, self.finish_stop_ui)

    def toggle_bot(self):
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(text="СТОП (F7)", bg="red")
            threading.Thread(target=self.bot_loop, daemon=True).start()
        else:
            self.is_running = False
            self.start_btn.config(text="ОСТАНОВКА...", bg="orange", state=tk.DISABLED)

    def on_hotkey(self, key):
        if key == keyboard.Key.f7: self.root.after(0, self.toggle_bot)

    def finish_stop_ui(self):
        self.start_btn.config(text="ПУСК (F7)", bg="green", state=tk.NORMAL)
        self.log("🏁 Бот остановлен.")

    def update_stat_ui(self):
        st = f"Циклы: {self.stats['cycles']} | Всего: {self.stats['bought']}\n"
        det = " | ".join([f"{k[:4]}: {v}" for k, v in self.real_stock.items()])
        self.stat_label.config(text=st + det)

    def create_widgets(self):
        for child in self.root.winfo_children():
            child.destroy()

        tabControl = ttk.Notebook(self.root)
        tab_main = ttk.Frame(tabControl)
        tab_config = ttk.Frame(tabControl)
        tab_templates = ttk.Frame(tabControl)

        tabControl.add(tab_main, text=' 🚀 Фарм ')
        tabControl.add(tab_config, text=' ⚙️ Настройки ')
        tabControl.add(tab_templates, text=' 📸 Шаблоны ')
        tabControl.pack(expand=1, fill="both")

        # --- ВКЛАДКА: ФАРМ (tab_main) ---
        self.start_btn = tk.Button(tab_main, text="ПУСК (F7)", bg="green", fg="white",
                                   font=("Arial", 12, "bold"), height=2, command=self.toggle_bot)
        self.start_btn.pack(fill="x", padx=10, pady=10)

        self.stat_label = tk.Label(tab_main, text="Циклы: 0 | Осталось: --:--:--", font=("Arial", 10, "bold"))
        self.stat_label.pack(pady=5)

        self.log_area = scrolledtext.ScrolledText(tab_main, height=20, bg="black", fg="#00FF00")
        self.log_area.pack(fill="both", padx=10, expand=True, pady=5)
        self.log_area.configure(state='disabled')

        # --- ВКЛАДКА: НАСТРОЙКИ (tab_config) ---
        f_time = tk.LabelFrame(tab_config, text=" Параметры времени и ресурсов ")
        f_time.pack(fill="x", padx=10, pady=5)

        # (Поля ввода времени и запаса остаются без изменений)
        tk.Label(f_time, text="Работать (ч):").grid(row=0, column=0, padx=5, pady=5)
        self.work_time_ent = tk.Entry(f_time, width=8);
        self.work_time_ent.insert(0, "6.0");
        self.work_time_ent.grid(row=0, column=1)
        tk.Label(f_time, text="Мин. запас:").grid(row=0, column=2, padx=5);
        self.min_stock_ent = tk.Entry(f_time, width=5);
        self.min_stock_ent.insert(0, "1");
        self.min_stock_ent.grid(row=0, column=3)

        # 2. Зоны кликов (УДАЛИЛИ ИСПЫТАНИЕ ОТСЮДА)
        f_zones = tk.LabelFrame(tab_config, text=" 📍 Технические зоны клика ")
        f_zones.pack(fill="x", padx=10, pady=5)

        btn_list = [
            ("Торговый дом", "btn_trade_house"), ("Поиск", "btn_search_input"),
            ("Цена товара", "btn_item_price"), ("История 1 клик", "btn_market_history_1"),
            ("История 2 клик", "btn_market_history_2"), ("Забрать все", "btn_collect_all"),
            ("🎯 Область для W", "zone_move_aim"), ("🛑 Стоп лигмеха", "zone_stop_mech"),
            ("🏠 Город W", "zone_town_aim"), ("💬 Текст NPC", "btn_npc_dialog_text"),
            ("🏁 Закончить вызов", "zone_finish_call"), ("✅ Подтверд. выход", "zone_confirm_exit")
        ]

        r, c = 0, 0
        for t, k in btn_list:
            # Зоны для бега подсветим другим цветом для удобства
            color = "#fff3e0" if "zone" in k else "SystemButtonFace"
            tk.Button(f_zones, text=t, bg=color, command=lambda key=k: self.cap_pt(key),
                      width=18, font=("Arial", 8)).grid(row=r, column=c, padx=3, pady=2)
            c += 1
            if c > 1:
                c = 0
                r += 1

        # --- ВАЖНО: Эти блоки ТЕПЕРЬ ВНЕ ЦИКЛА btn_list ---

        # 3. Зоны гербов (OCR - Координаты цифр)
        f_ocr = tk.LabelFrame(tab_config, text=" 📊 Зоны запаса (Гербы) ")
        f_ocr.pack(fill="x", padx=10, pady=5)
        for n in ["Герб Охоты", "Герб Войны", "Герб Могущества", "Герб Механизмов"]:
            tk.Button(f_ocr, text=n[:4], command=lambda name=n: self.cap_stock(name),
                      width=7).pack(side="left", expand=True, fill="x", padx=1)

        # 4. Иконки гербов (Шаблоны .png для поиска картинок)
        f_img_caps = tk.LabelFrame(tab_config, text=" 📸 Создать шаблоны гербов ")
        f_img_caps.pack(fill="x", padx=10, pady=5)

        for n in ["Герб Охоты", "Герб Войны", "Герб Могущества", "Герб Механизмов"]:
            row = tk.Frame(f_img_caps)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=n, width=15, anchor="w", font=("Arial", 8)).pack(side="left")
            # Кнопка для поиска в левом меню аукциона
            tk.Button(row, text="Меню", command=lambda name=n: self.cap_img(name),
                      width=7, bg="#e3f2fd").pack(side="left", padx=2)
            # Кнопка для поиска в списке лотов
            tk.Button(row, text="Список", command=lambda name=n: self.cap_img(f"{name}_список"),
                      width=7, bg="#fce4ec").pack(side="left", padx=2)

        # --- ВКЛАДКА: ШАБЛОНЫ (tab_templates) ---
        canvas = tk.Canvas(tab_templates)
        scrollbar = ttk.Scrollbar(tab_templates, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        img_btns = [
            ("⚓ ОКНО ЦЕНЫ #1", "price_window_1"), ("⚓ ОКНО ЦЕНЫ #2", "price_window_2"),
            ("⚓ ОКНО ЦЕНЫ #3", "price_window_3"), ("⚓ ОКНО ЦЕНЫ #4", "price_window_4"),
            ("💎 КРИСТАЛЛ В ОКНЕ ЦЕН", "crystal"), ("⏳ ЗАГРУЗКА В ЛИГМЕХУ", "Область_загрузки"),
            ("⏳ ЗАГРУЗКА В ГОРОД", "Область_загрузки_city"), ("🚀 СТАРТ", "Начать_фарм"),
            ("🆗 ПОДТВЕРДИТЬ СТАРТ", "Подтвердить_фарм"), ("🛒 КУПИТЬ", "Купить"),
            ("💎 ПОДТВЕРДИТЬ ЗАКУПКУ", "Подтвердить_закупку"), ("➡️ СЛЕД. СТРАНИЦА", "next_page"),
            ("✅ ПОДТВЕРДИТЬ ФИЛЬТР", "Подтвердить"), ("⭐ ПРЕДЛОЖЕНИЯ", "offers_btn_template"),
            ("🔍 ФИЛЬТР ЦЕНЫ", "price_filter_template"), ("Цена_1", "Цена_1"), ("Цена_2", "Цена_2"),
            # ДОБАВЬ ЭТУ СТРОКУ НИЖЕ:
            ("💠 ТЕКСТ: ИСПЫТАНИЕ БОЖЕСТВЕННОСТИ", "btn_divine_trial")
        ]

        for t, n in img_btns:
            if "price_window" in n:
                idx = n.split('_')[-1]
                tk.Button(scroll_frame, text=t, command=lambda i=idx: self.make_win_tmpl(i), width=35).pack(pady=1)
            elif n == "crystal":
                tk.Button(scroll_frame, text=t, command=self.make_crys_tmpl, width=35).pack(pady=1)
            else:
                tk.Button(scroll_frame, text=t, command=lambda name=n: self.cap_img(name), width=35).pack(pady=1)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def find_img(self, name, thr=0.55):
        rect = self.find_img_rect(name, thr)
        if rect:
            return (rect[0] + rect[2] // 2, rect[1] + rect[3] // 2)  # Центр
        return None

    def make_win_tmpl(self, idx):
        self.root.iconify()
        time.sleep(random.uniform(0.4, 0.6))
        AreaSelector(lambda x, y, w, h: (
            pyautogui.screenshot(region=(x, y, w, h)).save(os.path.join(ITEMS_DIR, f"price_window_{idx}.png")),
            self.root.deiconify()))

    def make_crys_tmpl(self):
        self.root.iconify()
        time.sleep(random.uniform(0.4, 0.6))
        AreaSelector(lambda x, y, w, h: (pyautogui.screenshot(region=(x, y, w, h)).save(CRYSTAL_TEMPLATE),
                                         self.root.deiconify()))

    def cap_pt(self, k):
        self.root.iconify()
        time.sleep(random.uniform(0.4, 0.6))
        AreaSelector(lambda x, y, w, h: (self.config["click_zones"].update({k: {"x": x, "y": y, "w": w, "h": h}}),
                                         self.save_cfg(), self.root.deiconify()))

    def cap_img(self, n):
        self.root.iconify()
        time.sleep(random.uniform(0.4, 0.6))
        AreaSelector(
            lambda x, y, w, h: (pyautogui.screenshot(region=(x, y, w, h)).save(os.path.join(ITEMS_DIR, f"{n}.png")),
                                self.root.deiconify()))

    def cap_stock(self, k):
        self.root.iconify()
        time.sleep(random.uniform(0.4, 0.6))
        AreaSelector(lambda x, y, w, h: (self.config["stock_zones"].update({k: {"x": x, "y": y, "w": w, "h": h}}),
                                         self.save_cfg(), self.root.deiconify()))


class AreaSelector:
    def __init__(self, callback):
        self.win = Toplevel()
        self.win.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        self.canvas = tk.Canvas(self.win, bg="grey", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.sx = self.sy = 0
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.callback = callback

    def on_press(self, e):
        self.sx, self.sy = e.x, e.y
        self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=3)

    def on_drag(self, e):
        self.canvas.coords(self.rect, self.sx, self.sy, e.x, e.y)

    def on_release(self, e):
        c = self.canvas.coords(self.rect)
        self.win.destroy()
        if c:
            # Считаем координаты правильно, даже если выделяли снизу вверх
            x1, y1, x2, y2 = int(c[0]), int(c[1]), int(c[2]), int(c[3])
            self.callback(min(x1, x2), min(y1, y2), abs(x1 - x2), abs(y1 - y2))


if __name__ == "__main__":
    root = tk.Tk()
    app = BotApp(root)
    root.mainloop()