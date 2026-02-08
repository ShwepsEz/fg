import tkinter as tk
from tkinter import scrolledtext, Toplevel, messagebox, Scale, HORIZONTAL
import pyautogui, pydirectinput, threading, time, json, os, cv2, requests, random
import numpy as np
from datetime import datetime
from pynput import keyboard
import ctypes
import traceback

# --- НАСТРОЙКИ БЕЗОПАСНОСТИ ---
pyautogui.PAUSE = 0.01
pyautogui.FAILSAFE = True

CONFIG_FILE = "settings.json"
TARGET_DIR = "targets"
LOG_FILE = "bot_errors.log"

if not os.path.exists(TARGET_DIR): os.makedirs(TARGET_DIR)


class BotStopException(Exception): pass


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


class BotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Divine Bot v18.1.9 [Full Stats]")

        if not is_admin():
            messagebox.showwarning("Запуск", "Запустите от имени Администратора!")

        self.full_size = "338x780"
        self.mini_size = "338x185"
        self.is_mini = False
        self.root.geometry(self.full_size)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.is_running = False
        self.total_cycles = 0
        self.start_time = None
        self.final_elapsed = "00:00:00"
        self.final_cph = 0
        self.active_recording_key = None
        self.mouse_lock = threading.Lock()

        # Данные прошлого сеанса
        self.prev_cycles = 0
        self.prev_time = "00:00:00"
        self.prev_cph = 0

        self.config = self.load_config()
        self.create_widgets()

        self.listener = keyboard.Listener(on_press=self.on_hotkey)
        self.listener.start()
        self.update_stats_loop()

    def log(self, message):
        now = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, lambda: self._safe_log(f"[{now}] {message}\n"))

    def _safe_log(self, text):
        self.log_area.insert(tk.END, text)
        self.log_area.see(tk.END)

    def set_status(self, text, color="black"):
        self.root.after(0, lambda: self.status_label.config(text=text, fg=color))

    def load_config(self):
        default = {"telegram": {"token": "", "chat_id": ""}, "coords": {}, "vision_zones": {},
                   "settings": {"t_farm_run": 4.5, "smooth_min": 0.1, "smooth_max": 0.2},
                   "last_session": {"cycles": 0, "time": "00:00:00", "cph": 0}}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ls = data.get("last_session", {})
                    self.prev_cycles = ls.get("cycles", 0)
                    self.prev_time = ls.get("time", "00:00:00")
                    self.prev_cph = ls.get("cph", 0)
                    return data
            except:
                return default
        return default

    def save_config(self):
        self.config["telegram"]["token"] = self.tg_token_entry.get().strip()
        self.config["telegram"]["chat_id"] = self.tg_chat_id_entry.get().strip()
        self.config["last_session"] = {"cycles": self.prev_cycles, "time": self.prev_time, "cph": self.prev_cph}
        try:
            self.config["settings"]["t_farm_run"] = float(self.farm_time_entry.get())
            self.config["settings"]["smooth_min"] = self.smooth_min.get()
            self.config["settings"]["smooth_max"] = self.smooth_max.get()
        except:
            pass
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def human_press(self, key):
        if not self.is_running: return
        pydirectinput.keyDown(key)
        time.sleep(random.uniform(0.01, 0.06))
        pydirectinput.keyUp(key)
        time.sleep(random.uniform(0.1, 0.13))

    def smart_move(self, x, y):
        if not self.is_running: return
        with self.mouse_lock:
            dur = random.uniform(self.smooth_min.get(), self.smooth_max.get())
            pyautogui.moveTo(x, y, duration=dur, tween=pyautogui.easeInOutQuad)
            time.sleep(random.uniform(0.05, 0.15))

    def human_click(self, x=None, y=None):
        if x and y: self.smart_move(x, y)
        pydirectinput.mouseDown()
        time.sleep(random.uniform(0.04, 0.09))
        pydirectinput.mouseUp()
        time.sleep(random.uniform(0.15, 0.3))

    def wait_for_image(self, name, click=False, timeout=30, required=True):
        path = os.path.join(TARGET_DIR, f"{name}.png")
        zone = self.config["vision_zones"].get(name)
        if not os.path.exists(path) or not zone:
            if required: raise Exception(f"Файл/зона для '{name}' отсутствуют")
            return False

        template = cv2.imread(path)
        start_t = time.time()
        while time.time() - start_t < timeout:
            if not self.is_running: raise BotStopException()
            img = cv2.cvtColor(np.array(pyautogui.screenshot(region=(zone['x'], zone['y'], zone['w'], zone['h']))),
                               cv2.COLOR_RGB2BGR)
            res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val > 0.6:
                rx = random.randint(zone['x'] + 5, zone['x'] + zone['w'] - 5)
                ry = random.randint(zone['y'] + 5, zone['y'] + zone['h'] - 5)
                if click: self.human_click(rx, ry)
                return True
            time.sleep(random.uniform(0.35, 0.5))
        if required: raise Exception(f"Не найден: {name}")
        return False

    def bot_loop(self):
        try:
            for i in range(5, 0, -1):
                if not self.is_running: return
                self.log(f"⏳ Старт через {i} сек...");
                time.sleep(1.0)

            self.human_press('d')
            self.wait_for_image("npc_dial", click=True, timeout=10)

            while self.is_running:
                self.wait_for_image("btn_start", click=True, timeout=15)
                time.sleep(random.uniform(0.1, 0.3))
                self.wait_for_image("btn_confirm", click=True, timeout=10)

                coord_start = self.config["coords"].get("pos_w_start")
                if coord_start: self.smart_move(coord_start[0], coord_start[1])
                self.wait_for_image("loc_trigger", timeout=45)

                for _ in range(4):
                    pydirectinput.press('w')
                    time.sleep(random.uniform(0.011, 0.014))

                coord_mech = self.config["coords"].get("stop_mech")
                if coord_mech: self.smart_move(coord_mech[0], coord_mech[1])

                pydirectinput.mouseDown(button='right')
                pydirectinput.press('d')
                time.sleep(random.uniform(0, 0.1))
                pydirectinput.press('t')

                fs = time.time();
                f_lim = float(self.farm_time_entry.get())
                while time.time() - fs < f_lim:
                    if not self.is_running: break
                    time.sleep(0.05)

                pydirectinput.mouseUp(button='right')
                time.sleep(random.uniform(0, 0.1))

                if coord_mech: self.human_click(coord_mech[0], coord_mech[1])
                for _ in range(7):
                    pydirectinput.press('a')
                    time.sleep(0.01)

                self.human_press('d')
                coord_final = self.config["coords"].get("pos_w_final")
                if coord_final: self.smart_move(coord_final[0], coord_final[1])
                self.wait_for_image("exit_trigger", timeout=35)

                for _ in range(4):
                    pydirectinput.press('w')
                    time.sleep(random.uniform(0.011, 0.014))

                zone_npc = self.config["vision_zones"].get("final_npc")
                if zone_npc: self.smart_move(zone_npc['x'] + zone_npc['w'] // 2, zone_npc['y'] + zone_npc['h'] // 2)
                time.sleep(0.01)
                pydirectinput.press('d')

                self.wait_for_image("final_npc", click=True, timeout=15)
                self.wait_for_image("btn_close", click=True, timeout=10, required=False)
                self.wait_for_image("btn_ok", click=True, timeout=10, required=False)

                self.total_cycles += 1
                self.log(f"✅ Цикл {self.total_cycles} готов.")

                lim = int(self.limit_entry.get()) if self.limit_entry.get().isdigit() else 0
                if lim > 0 and self.total_cycles >= lim:
                    self.stop_bot_logic()
                    break

                time.sleep(random.uniform(0.2, 0.7))

        except BotStopException:
            pass
        except Exception as e:
            err_trace = traceback.format_exc()
            with open(LOG_FILE, "a") as f:
                f.write(f"[{datetime.now()}] {err_trace}\n")
            self.log(f"🛑 ОШИБКА (проверь {LOG_FILE})")
            self.send_tg(f"🛑 Бот упал: {e}")
        finally:
            self.is_running = False
            self.root.after(500, self.finalize_stop)

    def toggle_bot(self):
        if not self.is_running:
            self.is_running = True;
            self.total_cycles = 0;
            self.start_time = datetime.now()
            self.save_config();
            self.start_btn.config(text="СТОП (F7)", bg="#e74c3c")
            self.set_status("РАБОТАЕТ", "green")
            threading.Thread(target=self.bot_loop, daemon=True).start()
        else:
            self.stop_bot_logic()

    def stop_bot_logic(self):
        if not self.is_running: return
        # Обновляем "Прошлый сеанс" перед сбросом текущего
        self.prev_cph = self.get_cycles_per_hour()
        self.prev_cycles = self.total_cycles
        self.prev_time = self.get_elapsed_time()

        self.final_elapsed = self.prev_time
        self.final_cph = self.prev_cph

        self.is_running = False
        self.save_config()
        self.start_btn.config(state='disabled', text="ОСТАНОВКА...", bg="#95a5a6")
        self.send_final_report("Остановка")

    def finalize_stop(self):
        self.start_btn.config(state='normal', text="ЗАПУСТИТЬ", bg="#27ae60")
        self.set_status("ГОТОВ", "black")

    def test_tg(self):
        self.save_config();
        self.send_tg("🔔 Тест ТГ: OK")

    def send_tg(self, message):
        t = self.tg_token_entry.get().strip();
        c = self.tg_chat_id_entry.get().strip()
        if t and c: threading.Thread(target=lambda: requests.post(f"https://api.telegram.org/bot{t}/sendMessage",
                                                                  data={"chat_id": c, "text": message}),
                                     daemon=True).start()

    def get_elapsed_time(self):
        if not self.is_running: return self.final_elapsed
        if not self.start_time: return "00:00:00"
        return str(datetime.now() - self.start_time).split(".")[0]

    def get_cycles_per_hour(self):
        if not self.is_running: return self.final_cph
        if not self.start_time or self.total_cycles == 0: return 0
        h = (datetime.now() - self.start_time).total_seconds() / 3600
        return round(self.total_cycles / h, 1) if h > 0 else 0

    def create_widgets(self):
        self.btn_mode = tk.Button(self.root, text="МИНИ РЕЖИМ", font=('Arial', 7), command=self.toggle_mode)
        self.btn_mode.pack(anchor="ne", padx=5, pady=2)

        self.settings_frame = tk.Frame(self.root);
        self.settings_frame.pack(fill="x")

        tg = tk.LabelFrame(self.settings_frame, text=" Telegram ", fg="#2980b9")
        tg.pack(fill="x", padx=10, pady=2)
        self.tg_token_entry = tk.Entry(tg);
        self.tg_token_entry.insert(0, self.config["telegram"]["token"]);
        self.tg_token_entry.pack(fill="x", padx=5)
        self.tg_chat_id_entry = tk.Entry(tg);
        self.tg_chat_id_entry.insert(0, self.config["telegram"]["chat_id"]);
        self.tg_chat_id_entry.pack(fill="x", padx=5)
        tk.Button(tg, text="ТЕСТ ТЕЛЕГРАМ", font=('Arial', 7), command=self.test_tg).pack(fill="x", padx=5, pady=2)

        extra = tk.LabelFrame(self.settings_frame, text=" Настройки ", fg="#d35400")
        extra.pack(fill="x", padx=10, pady=2)
        self.smooth_min = Scale(extra, from_=0.05, to=1.0, resolution=0.05, orient=HORIZONTAL, label="Мышь (мин)")
        self.smooth_min.set(self.config["settings"].get("smooth_min", 0.1));
        self.smooth_min.pack(fill="x")
        self.smooth_max = Scale(extra, from_=0.1, to=1.5, resolution=0.05, orient=HORIZONTAL, label="Мышь (макс)")
        self.smooth_max.set(self.config["settings"].get("smooth_max", 0.2));
        self.smooth_max.pack(fill="x")
        tk.Label(extra, text="Время атаки (сек):", font=('Arial', 7)).pack()
        self.farm_time_entry = tk.Entry(extra, justify='center');
        self.farm_time_entry.insert(0, str(self.config["settings"].get("t_farm_run", 4.5)));
        self.farm_time_entry.pack()

        vis = tk.LabelFrame(self.settings_frame, text=" Зоны и Координаты ", fg="#8e44ad")
        vis.pack(fill="x", padx=10, pady=2)
        v_btns = [("НПС", "npc_dial"), ("Нач", "btn_start"), ("Подт", "btn_confirm"), ("Триг", "loc_trigger"),
                  ("Вых", "exit_trigger"), ("Ф.НПС", "final_npc"), ("Закр", "btn_close"), ("Ок", "btn_ok")]
        for i, (txt, k) in enumerate(v_btns):
            tk.Button(vis, text=txt, font=('Arial', 7), command=lambda key=k: self.capture_target(key)).grid(row=i // 4,
                                                                                                             column=i % 4,
                                                                                                             sticky="ew")
        tk.Button(vis, text="📍 W Старт", font=('Arial', 7), command=lambda: self.prepare_coord("pos_w_start")).grid(
            row=2, column=0, columnspan=2, sticky="ew")
        tk.Button(vis, text="📍 Стоп Мех", font=('Arial', 7), command=lambda: self.prepare_coord("stop_mech")).grid(
            row=2, column=2, columnspan=2, sticky="ew")
        tk.Button(vis, text="📍 W Финал", font=('Arial', 7), command=lambda: self.prepare_coord("pos_w_final")).grid(
            row=3, column=0, columnspan=4, sticky="ew")
        vis.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # --- БЛОК СТАТИСТИКИ (ПОЛНЫЙ) ---
        self.stats_frame = tk.LabelFrame(self.root, text=" Статистика (Текущая | Прошлая) ", fg="green")
        self.stats_frame.pack(fill="x", padx=10, pady=2)

        stats_grid = tk.Frame(self.stats_frame)
        stats_grid.pack(fill="x", padx=5)

        self.lbl_cycles = tk.Label(stats_grid, text="Циклы: 0", font=('Arial', 8, 'bold'), anchor="w")
        self.lbl_cycles.grid(row=0, column=0, sticky="w")
        self.lbl_prev_cycles = tk.Label(stats_grid, text=f"Было: {self.prev_cycles}", font=('Arial', 8), fg="grey",
                                        anchor="e")
        self.lbl_prev_cycles.grid(row=0, column=1, sticky="e")

        self.lbl_time = tk.Label(stats_grid, text="Время: 00:00:00", font=('Arial', 8), anchor="w")
        self.lbl_time.grid(row=1, column=0, sticky="w")
        self.lbl_prev_time = tk.Label(stats_grid, text=f"За: {self.prev_time}", font=('Arial', 8), fg="grey",
                                      anchor="e")
        self.lbl_prev_time.grid(row=1, column=1, sticky="e")

        self.lbl_cph = tk.Label(stats_grid, text="Ц/час: 0", font=('Arial', 8), anchor="w")
        self.lbl_cph.grid(row=2, column=0, sticky="w")
        self.lbl_prev_cph = tk.Label(stats_grid, text=f"Было: {self.prev_cph}", font=('Arial', 8), fg="grey",
                                     anchor="e")
        self.lbl_prev_cph.grid(row=2, column=1, sticky="e")

        stats_grid.columnconfigure(0, weight=1)
        stats_grid.columnconfigure(1, weight=1)

        limit_f = tk.Frame(self.stats_frame);
        limit_f.pack(fill="x", padx=5, pady=2)
        tk.Label(limit_f, text="Лимит циклов:", font=('Arial', 7)).pack(side="left")
        self.limit_entry = tk.Entry(limit_f, width=8, justify='center');
        self.limit_entry.insert(0, "0");
        self.limit_entry.pack(side="left", padx=5)

        self.start_btn = tk.Button(self.root, text="ЗАПУСТИТЬ", bg="#27ae60", fg="white", height=2,
                                   font=('Arial', 10, 'bold'), command=self.toggle_bot)
        self.start_btn.pack(fill="x", padx=10, pady=5)
        self.status_label = tk.Label(self.root, text="Готов", font=('Arial', 9, 'bold'));
        self.status_label.pack()
        self.log_area = scrolledtext.ScrolledText(self.root, height=7, font=('Consolas', 8));
        self.log_area.pack(fill="both", expand=True, padx=10)

    def toggle_mode(self):
        if not self.is_mini:
            self.root.geometry(self.mini_size); self.settings_frame.pack_forget(); self.log_area.pack_forget()
        else:
            self.root.geometry(self.full_size); self.settings_frame.pack(fill="x",
                                                                         before=self.stats_frame); self.log_area.pack(
                fill="both", expand=True)
        self.is_mini = not self.is_mini

    def update_stats_loop(self):
        self.lbl_cycles.config(text=f"Циклы: {self.total_cycles}")
        self.lbl_time.config(text=f"Время: {self.get_elapsed_time()}")
        self.lbl_cph.config(text=f"Ц/час: {self.get_cycles_per_hour()}")
        self.lbl_prev_cycles.config(text=f"Было: {self.prev_cycles}")
        self.lbl_prev_time.config(text=f"За: {self.prev_time}")
        self.lbl_prev_cph.config(text=f"Было: {self.prev_cph}")
        self.root.after(1000, self.update_stats_loop)

    def on_hotkey(self, key):
        try:
            k = key.name if hasattr(key, 'name') else str(key)
            if 'f8' in k and self.active_recording_key:
                pos = pyautogui.position()
                self.config["coords"][self.active_recording_key] = [pos.x, pos.y]
                self.save_config();
                self.log(f"📍 Точка {self.active_recording_key} записана");
                self.active_recording_key = None
            if 'f7' in k: self.root.after(0, self.stop_bot_logic)
        except:
            pass

    def send_final_report(self, reason):
        diff = round(self.final_cph - self.prev_cph, 1)
        trend = f"(↑ {diff})" if diff > 0 else f"(↓ {abs(diff)})" if diff < 0 else ""

        msg = (f"📊 СТАТИСТИКА: {reason}\n"
               f"------------------------\n"
               f"✅ Текущий: {self.total_cycles} циклов\n"
               f"⏱ Время: {self.final_elapsed}\n"
               f"⚡️ Скорость: {self.final_cph} ц/час {trend}\n"
               f"⏮ Прошлый: {self.prev_cycles} за {self.prev_time} ({self.prev_cph} ц/ч)")
        self.send_tg(msg)

    def capture_target(self, name):
        def save_logic(x, y, w, h):
            pyautogui.screenshot(region=(x, y, w, h)).save(os.path.join(TARGET_DIR, f"{name}.png"))
            self.config["vision_zones"][name] = {"x": x, "y": y, "w": w, "h": h}
            self.save_config();
            self.log(f"📸 Зона '{name}' сохранена")

        self.root.iconify();
        time.sleep(0.5);
        AreaSelector(save_logic);
        self.root.deiconify()

    def prepare_coord(self, key):
        self.active_recording_key = key; self.log(f"📍 Укажите точку и нажмите F8")


class AreaSelector:
    def __init__(self, callback):
        self.root = Toplevel();
        self.root.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey");
        self.canvas.pack(fill="both", expand=True)
        self.start_x = self.start_y = 0;
        self.rect = None;
        self.callback = callback
        self.canvas.bind("<ButtonPress-1>", self.on_press);
        self.canvas.bind("<B1-Motion>", self.on_drag);
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

    def on_press(self, event): self.start_x, self.start_y = event.x, event.y; self.rect = self.canvas.create_rectangle(
        self.start_x, self.start_y, 1, 1, outline="red", width=2)

    def on_drag(self, event): self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event): c = self.canvas.coords(self.rect); self.root.destroy(); self.callback(int(c[0]),
                                                                                                       int(c[1]),
                                                                                                       int(max(1,
                                                                                                               c[2] - c[
                                                                                                                   0])),
                                                                                                       int(max(1,
                                                                                                               c[3] - c[
                                                                                                                   1])))


if __name__ == "__main__":
    root = tk.Tk();
    app = BotApp(root);
    root.mainloop()