from flask import Flask, render_template, request, Response
from motors import forward, backward, left_turn, right_turn, stop_motors, set_speed, cleanup
from voz import hablar
import atexit, cv2, numpy as np, os, threading, time

# === COLOR SELECCIONADO ===
current_color = None

# === HILO DE LA CAMARA (RÁPIDO) ===
class CameraStream:
    def __init__(self, src=0):
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self.camera = cv2.VideoCapture(src, cv2.CAP_V4L2)

        # Forzar MJPG
        self.camera.set(cv2.CAP_PROP_FOURCC, fourcc)

        # Resolución rápida
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)

        # evitar buffering
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.frame = None
        self.running = True

        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while self.running:
            # DESCARTA frames viejos
            self.camera.grab()
            self.camera.grab()

            ok, frame = self.camera.read()
            if ok:
                self.frame = frame

    def get_frame(self):
        return self.frame


camera_stream = CameraStream()

app = Flask(__name__)
atexit.register(cleanup)

BASE_SPEED = 60
AREA_UMBRAL = 50000

# === MEJORES RANGOS DE COLOR HSV ===
COLOR_RANGES = {
    'rojo': [
        (np.array([0, 100, 50]), np.array([10, 255, 255])),
        (np.array([170, 100, 50]), np.array([180, 255, 255]))
    ],
    'azul': [
        (np.array([95, 120, 50]), np.array([140, 255, 255]))
    ],
    'amarillo': [
        (np.array([20, 120, 120]), np.array([32, 255, 255]))
    ],
    'verde': [
        (np.array([40, 40, 40]), np.array([85, 255, 255]))
    ],
}

# === DETECCION PROFESIONAL DE COLOR (como tu amigo, pero más eficiente) ===
def detectar_color(frame, color_name):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

    if color_name in COLOR_RANGES:
        for lower, upper in COLOR_RANGES[color_name]:
            mask |= cv2.inRange(hsv, lower, upper)

    # Limpieza de ruido
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)

    # ---- FILTROS NUEVOS (MUY IMPORTANTES) ----

    # 1. No detectar paredes enormes
    if area > 50000:  # demasiado grande = pared / silla / ropa
        return None

    # 2. No detectar objetos demasiado pequeños
    if area < 1500:  # ruido / manchas / reflejos
        return None

    x, y, w, h = cv2.boundingRect(c)

    # 3. SOLO si está al centro
    cx = x + w//2
    cy = y + h//2
    centro_x = frame.shape[1] // 2
    centro_y = frame.shape[0] // 2

    tolerancia_centro = 80  # más pequeño = más estricto

    if abs(cx - centro_x) > tolerancia_centro or abs(cy - centro_y) > tolerancia_centro:
        return None

    return (x, y, w, h)


# === LOGICA DEL ROBOT ===
def buscar_color(color_objetivo):
    try:
        hablar(f"Buscando el color {color_objetivo}")
        encontrado = False

        # Giro de 360° (12 pasos de 30°)
        for _ in range(12):
            right_turn()
            set_speed(BASE_SPEED, BASE_SPEED)
            time.sleep(0.25)   # giro pequeño
            stop_motors()

            frame = camera_stream.get_frame()
            if frame is None:
                continue

            rect = detectar_color(frame, color_objetivo)
            if rect:
                encontrado = True
                break

        stop_motors()

        if encontrado:
            hablar(f"Color {color_objetivo} detectado, deteniendo giro.")
        else:
            hablar("Color no encontrado en la vuelta completa.")

    except Exception as e:
        print("Error en detección:", e)
        hablar("Error al usar la cámara")


# === RUTAS WEB ===
@app.route('/')
def index():
    return render_template('index.html', pantalla=1, usuario=None, mensaje=None)


@app.route('/login', methods=['POST'])
def login():
    usuario = request.form['usuario']
    clave = request.form['clave']
    if clave == '123456':
        return render_template('index.html', pantalla=2, usuario=usuario, mensaje=None)
    else:
        return render_template('error.html')


@app.route('/color', methods=['POST'])
def color():
    global current_color
    usuario = request.form['usuario']
    color = request.form['color']

    current_color = color

    mensaje = f"{usuario} ha seleccionado el color {color}, en camino"
    hablar(mensaje)

    threading.Thread(target=buscar_color, args=(color,), daemon=True).start()

    return render_template('index.html', pantalla=3, usuario=usuario, mensaje=mensaje, color=color)


# === STREAM DE VIDEO ===
@app.route('/video_feed')
def video_feed():
    def gen_frames():
        global current_color

        while True:
            frame = camera_stream.get_frame()
            if frame is None:
                continue

            rect = None
            if current_color:
                rect = detectar_color(frame, current_color)

            # === SOLO dibujar si está en el centro ===
            if rect:
                x, y, w, h = rect
                cx = x + w//2
                cy = y + h//2

                centro_x = frame.shape[1] // 2
                centro_y = frame.shape[0] // 2

                tolerancia = 120  # ajustable

                if abs(cx - centro_x) < tolerancia and abs(cy - centro_y) < tolerancia:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0,255,0), 2)

            # enviar frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
