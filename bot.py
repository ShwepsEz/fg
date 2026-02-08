import tkinter as tk
from tkinter import Toplevel, messagebox
import pyautogui
import cv2
import numpy as np
import threading
import time


class FastMatchTester:
    def __init__(self, root):
        self.root = root
        self.root.title("FAST Visual Matcher (v2.0)")
        self.root.attributes("-topmost", True)
        self.root.geometry("450x420")  # Немного увеличил высоту для новой кнопки

        self.template = None
        self.is_testing = False

        # Панель управления
        frame = tk.Frame(root, pady=10)
        frame.pack(fill="x", padx=20)

        tk.Label(frame, text="Точность (Match):").pack()
        self.sc_match = tk.Scale(frame, from_=0.10, to=1.00, resolution=0.01, orient=tk.HORIZONTAL)
        self.sc_match.set(0.76)
        self.sc_match.pack(fill="x")

        tk.Label(frame, text="Мин. яркость (Brightness):", fg="blue").pack()
        self.sc_bright = tk.Scale(frame, from_=0, to=255, orient=tk.HORIZONTAL)
        self.sc_bright.set(53)
        self.sc_bright.pack(fill="x")

        tk.Button(root, text="ВЫДЕЛИТЬ ШАБЛОН", bg="orange", font=("Arial", 10, "bold"),
                  command=self.start_capture).pack(pady=5, padx=20, fill="x")

        # --- НОВАЯ КНОПКА ---
        tk.Button(root, text="📋 СКОПИРОВАТЬ НАСТРОЙКИ ДЛЯ GEMINI", bg="#b3e5fc", font=("Arial", 9),
                  command=self.copy_settings).pack(pady=5, padx=20, fill="x")

        self.status_label = tk.Label(root, text="Статус: Ожидание шаблона", font=("Arial", 11))
        self.status_label.pack()

        tk.Label(root, text="Нажми 'Q' в окне видео для выхода", fg="red").pack()

    # Функция для подготовки текста настроек
    def copy_settings(self):
        m = self.sc_match.get()
        b = self.sc_bright.get()
        settings_text = f"РЕЗУЛЬТАТ ТЕСТА: Match {m}, Brightness {b}"

        # Вывод в консоль
        print("\n" + "=" * 30)
        print(settings_text)
        print("=" * 30 + "\n")

        # Копирование в буфер обмена Windows через Tkinter
        self.root.clipboard_clear()
        self.root.clipboard_append(settings_text)

        messagebox.showinfo("Готово", f"Настройки скопированы в буфер обмена!\n\n{settings_text}")

    def start_capture(self):
        self.is_testing = False
        self.root.iconify()
        time.sleep(0.5)
        AreaSelector(self.process_selection)

    def process_selection(self, x, y, w, h):
        self.root.deiconify()
        if w < 2 or h < 2: return
        shot = pyautogui.screenshot(region=(x, y, w, h))
        self.template = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)
        self.status_label.config(text="Статус: ТЕСТИРОВАНИЕ", fg="green")

        if not self.is_testing:
            self.is_testing = True
            threading.Thread(target=self.run_loop, daemon=True).start()

    def run_loop(self):
        th, tw = self.template.shape[:2]
        cv2.namedWindow("Fast Check", cv2.WINDOW_NORMAL)

        while self.is_testing:
            start_time = time.time()
            min_match = self.sc_match.get()
            min_v = self.sc_bright.get()

            screen_np = np.array(pyautogui.screenshot())
            screen_bgr = cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR)

            res = cv2.matchTemplate(screen_bgr, self.template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(res >= min_match)

            boxes = []
            points = list(zip(*loc[::-1]))

            for pt in points:
                roi = screen_bgr[pt[1]:pt[1] + th, pt[0]:pt[0] + tw]
                if roi.size == 0: continue
                hsv_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                avg_v = np.mean(hsv_roi[:, :, 2])
                if avg_v >= min_v:
                    boxes.append([int(pt[0]), int(pt[1]), int(tw), int(th)])

            if len(boxes) > 0:
                boxes, _ = cv2.groupRectangles(boxes, 1, 0.2)
                for (x, y, w, h) in boxes:
                    cv2.rectangle(screen_bgr, (x, y), (x + w, y + h), (0, 255, 0), 2)

            fps = 1.0 / (time.time() - start_time)
            cv2.putText(screen_bgr, f"FPS: {int(fps)}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            preview = cv2.resize(screen_bgr, (0, 0), fx=0.5, fy=0.5)
            cv2.imshow("Fast Check", preview)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.is_testing = False
                break

        cv2.destroyAllWindows()
        self.root.after(0, lambda: self.status_label.config(text="Статус: Остановлен", fg="red"))


# (Класс AreaSelector остается без изменений)
class AreaSelector:
    def __init__(self, callback):
        self.win = Toplevel()
        self.win.attributes("-fullscreen", True, "-alpha", 0.3, "-topmost", True)
        self.canvas = tk.Canvas(self.win, bg="grey", cursor="cross")
        self.canvas.pack(fill="both", expand=True)
        self.sx = self.sy = 0;
        self.rect = None
        self.canvas.bind("<ButtonPress-1>", self.on_press);
        self.canvas.bind("<B1-Motion>", self.on_drag);
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.callback = callback

    def on_press(self, e): self.sx, self.sy = e.x, e.y; self.rect = self.canvas.create_rectangle(e.x, e.y, e.x, e.y,
                                                                                                 outline="red", width=3)

    def on_drag(self, e): self.canvas.coords(self.rect, self.sx, self.sy, e.x, e.y)

    def on_release(self, e):
        c = self.canvas.coords(self.rect);
        self.win.destroy()
        if c: self.callback(int(min(c[0], c[2])), int(min(c[1], c[3])), int(abs(c[0] - c[2])), int(abs(c[1] - c[3])))


if __name__ == "__main__":
    root = tk.Tk();
    app = FastMatchTester(root);
    root.mainloop()