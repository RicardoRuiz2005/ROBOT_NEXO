import cv2
import numpy as np

def detectar_color(frame, color_name):
    if frame is None:
        return None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # ---- RANGOS EXACTOS TIPO “AMIGO” ----
    if color_name == "rojo":
        lower1 = np.array([0, 100, 20])
        upper1 = np.array([10, 255, 255])
        lower2 = np.array([160, 100, 20])
        upper2 = np.array([179, 255, 255])

        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = mask1 + mask2

    elif color_name == "verde":
        lower = np.array([35, 50, 50])
        upper = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)

    elif color_name == "azul":
        lower = np.array([90, 120, 50])
        upper = np.array([140, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)

    elif color_name == "amarillo":
        lower = np.array([20, 100, 100])
        upper = np.array([30, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)

    else:
        return None

    # ---- Detección sin filtros estrictos ----
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    c = max(cnts, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(c)

    return (x, y, w, h)
