import tkinter as tk
from tkinter import Toplevel
import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import Image, ImageTk
import time

# --- УКАЖИТЕ ПУТЬ К TESSERACT ЗДЕСЬ ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class OCRProfessionalTester:
    def __init__(self, root):
        self.root = root
        self.root.title("PRO OCR Debug Tool v2.2 [RED CHANNEL ADDED]")
        self.root.geometry("600x950")
        self.root.attributes("-topmost", True)

        self.capture_zone = None
        self.start_x = 0
        self.start_y = 0

        main_frame = tk.Frame(root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. Кнопка захвата
        tk.Button(main_frame, text="📸 ВЫБРАТЬ ЗОНУ (ESC для выхода)",
                  command=self.select_zone, bg="#4CAF50", fg="white",
                  font=("Arial", 11, "bold"), height=2).pack(fill="x", pady=5)

        # 2. Панель настроек
        settings_frame = tk.LabelFrame(main_frame, text=" Настройки обработки ")
        settings_frame.pack(fill="x", pady=5)

        # Твои предустановки: Scale 10, Thr 102, Blur 2, Morph 0
        self.add_slider(settings_frame, "Увеличение (Scale)", "scale", 1, 15, 10)
        self.add_slider(settings_frame, "Порог (Threshold)", "thr", 0, 255, 102)
        self.add_slider(settings_frame, "Размытие (Blur)", "blur", 0, 10, 2)
        self.add_slider(settings_frame, "Толщина линий (Morph)", "morph", -5, 5, 0)

        # Чекбоксы
        self.var_red_fix = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Улучшать КРАСНЫЙ (для 0 эмблем)",
                       variable=self.var_red_fix, fg="red", font=("Arial", 9, "bold")).pack(anchor="w")

        self.var_invert = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Инверсия (Черный текст на белом)", variable=self.var_invert).pack(anchor="w")

        self.var_otsu = tk.BooleanVar(value=False)
        tk.Checkbutton(settings_frame, text="Авто-порог (Otsu)", variable=self.var_otsu).pack(anchor="w")

        # Настройки Tesseract
        tess_frame = tk.Frame(settings_frame)
        tess_frame.pack(fill="x", pady=5)
        tk.Label(tess_frame, text="PSM Режим:").pack(side="left", padx=5)
        self.psm_val = tk.StringVar(value="7")
        tk.Entry(tess_frame, textvariable=self.psm_val, width=5).pack(side="left")

        # 3. Вывод результата
        self.res_label = tk.Label(main_frame, text="ВИДИТ: ---",
                                  font=("Consolas", 24, "bold"), fg="#FF5722", bg="#212121")
        self.res_label.pack(fill="x", pady=10)

        # 4. Предпросмотр картинки
        self.img_label = tk.Label(main_frame, bg="#333", relief="sunken")
        self.img_label.pack(pady=10, fill="both", expand=True)

        self.update_loop()

    def add_slider(self, parent, label, attr, f, t, default):
        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=5)
        tk.Label(frame, text=label, font=("Arial", 9)).pack(side="left")
        slider = tk.Scale(frame, from_=f, to=t, orient="horizontal", length=200)
        slider.set(default)
        slider.pack(side="right")
        setattr(self, f"slider_{attr}", slider)

    def select_zone(self):
        self.root.withdraw()
        time.sleep(0.3)
        selector = Toplevel()
        selector.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        selector.config(cursor="cross")
        canvas = tk.Canvas(selector, bg="grey", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        rect = [None]

        def on_down(e):
            self.start_x, self.start_y = e.x, e.y
            rect[0] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="red", width=2)
        def on_drag(e):
            if rect[0]: canvas.coords(rect[0], self.start_x, self.start_y, e.x, e.y)
        def on_up(e):
            x1, y1 = int(min(self.start_x, e.x)), int(min(self.start_y, e.y))
            w, h = int(abs(self.start_x - e.x)), int(abs(self.start_y - e.y))
            if w > 5 and h > 5: self.capture_zone = (x1, y1, w, h)
            selector.destroy()
            self.root.deiconify()

        canvas.bind("<ButtonPress-1>", on_down)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_up)
        selector.bind("<Escape>", lambda e: (selector.destroy(), self.root.deiconify()))

    def process(self):
        if not self.capture_zone: return None, "Зона не выбрана"
        try:
            x, y, w, h = self.capture_zone
            img = np.array(pyautogui.screenshot(region=(x, y, w, h)))
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            # ЛОГИКА КРАСНОГО ЦВЕТА
            if self.var_red_fix.get():
                b, g, r = cv2.split(img)
                # Берем максимум между красным каналом и яркостью, чтобы усилить красные цифры
                gray = cv2.max(r, cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
            else:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Масштаб (Scale)
            sc = self.slider_scale.get()
            gray = cv2.resize(gray, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)

            # Размытие (Blur)
            bl = self.slider_blur.get()
            if bl > 0:
                # Ядро должно быть нечетным
                k_size = bl if bl % 2 != 0 else bl + 1
                gray = cv2.GaussianBlur(gray, (k_size, k_size), 0)

            # Порог (Threshold)
            if self.var_otsu.get():
                _, final = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:
                _, final = cv2.threshold(gray, self.slider_thr.get(), 255, cv2.THRESH_BINARY)

            # Инверсия
            if self.var_invert.get():
                final = cv2.bitwise_not(final)

            # Морфология (Morph)
            m_val = self.slider_morph.get()
            if m_val != 0:
                kernel = np.ones((abs(m_val), abs(m_val)), np.uint8)
                if m_val > 0: final = cv2.dilate(final, kernel, iterations=1)
                else: final = cv2.erode(final, kernel, iterations=1)

            # OCR
            psm = self.psm_val.get()
            config = f'--psm {psm} -c tessedit_char_whitelist=0123456789/'
            text = pytesseract.image_to_string(final, config=config).strip()

            return final, text
        except Exception as e:
            return None, str(e)

    def update_loop(self):
        proc_img, text = self.process()
        if proc_img is not None:
            self.res_label.config(text=f"ВИДИТ: {text}")
            img_pil = Image.fromarray(proc_img)
            img_pil.thumbnail((500, 350))
            img_tk = ImageTk.PhotoImage(img_pil)
            self.img_label.config(image=img_tk)
            self.img_label.image = img_tk
        self.root.after(500, self.update_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRProfessionalTester(root)
    root.mainloop()