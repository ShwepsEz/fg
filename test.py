import cv2
import numpy as np
import pyautogui
import os

# --- ТВОИ НАСТРОЙКИ ---
TARGET_THR = 0.9
BRIGHT_LIMIT = 70
BRIGHTNESS_FACTOR = 1

ITEMS_DIR = "items"
HERBS = ["Герб Охоты_список", "Герб Войны_список", "Герб Могущества_список", "Герб Механизмов_список"]


def test_vision():
    print(f"🔍 Тест запущен. Группировка рамок включена.")
    screen = cv2.cvtColor(np.array(pyautogui.screenshot()), cv2.COLOR_RGB2BGR)
    processed_screen = cv2.convertScaleAbs(screen, alpha=BRIGHTNESS_FACTOR, beta=0)
    debug_img = screen.copy()

    for name in HERBS:
        path = os.path.join(ITEMS_DIR, f"{name}.png")
        if not os.path.exists(path): continue

        template = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        if template is None: continue
        th, tw = template.shape[:2]

        res = cv2.matchTemplate(processed_screen, template, cv2.TM_CCOEFF_NORMED)

        # 1. Собираем все точки, где совпадение выше порога
        loc = np.where(res >= TARGET_THR * 0.8)  # Берем чуть шире для группировки
        rects = []
        for pt in zip(*loc[::-1]):
            # Добавляем каждый найденный прямоугольник в список
            rects.append([int(pt[0]), int(pt[1]), int(tw), int(th)])
            rects.append([int(pt[0]), int(pt[1]), int(tw), int(th)])  # Дублируем для работы groupRectangles

        # 2. Группируем рамки (сливаем те, что рядом)
        # 1 - минимальное кол-во соседей, 0.2 - порог близости
        rects, weights = cv2.groupRectangles(rects, 1, 0.2)

        for (x, y, w, h) in rects:
            # Считаем яркость и точность для сгруппированной рамки
            roi = screen[y:y + h, x:x + w]
            avg_bright = np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY))
            match_val = res[y, x]

            # Логика цвета
            if match_val < TARGET_THR:
                color = (0, 0, 255)  # КРАСНЫЙ
                status = "BAD_MATCH"
            elif avg_bright < BRIGHT_LIMIT:
                color = (255, 0, 0)  # СИНИЙ (ТЕМНЫЙ)
                status = "DARK_SKIP"
            else:
                color = (0, 255, 0)  # ЗЕЛЕНЫЙ (КУПИТЬ)
                status = "BUY"

            cv2.rectangle(debug_img, (x, y), (x + w, y + h), color, 2)
            label = f"{status} M:{match_val:.2f} B:{int(avg_bright)}"
            cv2.putText(debug_img, label, (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.imshow("TEST: GROUPING ENABLED", debug_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_vision()