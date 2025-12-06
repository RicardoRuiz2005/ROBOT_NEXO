from flask import Flask, render_template, request, Response
from motors import forward, backward, left_turn, right_turn, stop_motors, set_speed, cleanup
from voz import hablar
import atexit, cv2, threading, time
import numpy as np

current_color = None

# ============================
#   CLASE CÁMARA
# ============================
class CameraStream:
    def __init__(self, src=0):
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        self.camera = cv2.VideoCapture(src, cv2.CAP_V4L2)
        self.camera.set(cv2.CAP_PROP_FOURCC, fourcc)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.frame = None
        self.running = True
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while self.running:
            ok, frame = self.camera.read()
            if ok:
                self.frame = frame

    def get_frame(self):
        return self.frame


camera_stream = CameraStream()
app = Flask(__name__)
atexit.register(cleanup)

BASE_SPEED = 60

# ============================
#   RANGOS DE COLORES
# ============================
COLOR_RANGES = {
    'rojo': [(np.array([0,100,50]), np.array([10,255,255])),
             (np.array([170,100,50]), np.array([180,255,255]))],
    'azul': [(np.array([95,120,50]), np.array([140,255,255]))],
    'amarillo': [(np.array([20,120,120]), np.array([32,255,255]))],
    'verde': [(np.array([40,40,40]), np.array([85,255,255]))],
}

# ============================
#   DETECCIÓN DE COLOR
# ============================
def detectar_color(frame, color_name):
    if frame is None:
        return None

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

    if color_name in COLOR_RANGES:
        for lower, upper in COLOR_RANGES[color_name]:
            mask |= cv2.inRange(hsv, lower, upper)

    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)

    if area > 120000 or area < 400:
        return None

    x, y, w, h = cv2.boundingRect(c)
    cx = x + w//2
    cy = y + h//2

    centro_x = frame.shape[1] // 2
    centro_y = frame.shape[0] // 2

    if abs(cx - centro_x) > 140 or abs(cy - centro_y) > 140:
        return None

    return (x, y, w, h)

# ============================
#   ESTABILIZADOR DE CÁMARA
# ============================
def estabilizar_cam(muestras=5, delay=0.06):
    ultimo_frame = None
    for _ in range(muestras):
        time.sleep(delay)
        f = camera_stream.get_frame()
        if f is not None:
            ultimo_frame = f
    return ultimo_frame

def detectar_color_estable(color_name):
    conteo = 0
    for _ in range(3):
        f = camera_stream.get_frame()
        if f is None:
            continue
        if detectar_color(f, color_name):
            conteo += 1
        time.sleep(0.02)
    return conteo >= 2

# ============================
#   AVANZAR HACIA EL COLOR
# ============================
def avanzar_hacia_color(color_objetivo):
    hablar("Avanzando hacia el color")
    for _ in range(6):
        if not detectar_color_estable(color_objetivo):
            stop_motors()
            return forward()  # Igual que antes

        forward()
        set_speed(55, 55)
        time.sleep(0.28)
        stop_motors()
        time.sleep(0.10)

# ============================
#   BÚSQUEDA AUTOMÁTICA
# ============================
def buscar_color(color_objetivo):
    try:
        hablar(f"Buscando el color {color_objetivo}")
        encontrado = False

        for _ in range(12):
            right_turn()
            set_speed(BASE_SPEED, BASE_SPEED)
            time.sleep(0.25)
            stop_motors()

            frame = estabilizar_cam()
            if frame is None:
                continue

            if detectar_color_estable(color_objetivo):
                encontrado = True
                hablar("Color encontrado")
                avanzar_hacia_color(color_objetivo)
                break

        stop_motors()

        if not encontrado:
            hablar("Color no encontrado")

    except:
        hablar("Error al usar la cámara")
        stop_motors()

# ============================
#   RUTAS WEB
# ============================
@app.route('/')
def index():
    if request.args.get("screen") == "1" or request.args.get("retry") == "1":
        return render_template("index.html", pantalla=1, usuario=None, mensaje=None)
    return render_template("index.html", pantalla=0)

@app.route('/login', methods=['POST'])
def login():
    usuario = request.form['usuario']
    clave = request.form['clave']

    if clave == "123456":
        mensaje_bienvenida = (
            "Hola, que tal. Mucho gusto. "
            "Soy VitaRobotics, un robot diseñado para traer medicinas. "
            "Te invito a escoger alguno de estos colores que simulan la medicina que llevaré."
        )
        return render_template('index.html', pantalla=2, usuario=usuario, mensaje=mensaje_bienvenida)

    else:
        return render_template('error.html')

@app.route('/color', methods=['POST'])
def color():
    global current_color
    usuario = request.form['usuario']
    color = request.form['color']
    current_color = color

    mensaje = f"{usuario} ha seleccionado el color {color}"
    hablar(mensaje)

    threading.Thread(target=buscar_color, args=(color,), daemon=True).start()

    return render_template('index.html', pantalla=3, usuario=usuario, mensaje=mensaje, color=color)

@app.route('/video_feed')
def video_feed():
    def gen():
        global current_color
        while True:
            frame = camera_stream.get_frame()
            if frame is None:
                continue

            if current_color:
                rect = detectar_color(frame, current_color)
                if rect:
                    x, y, w, h = rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    cv2.putText(frame, current_color.upper(), (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
                   buffer.tobytes() + b'\r\n')

    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ============================
#   INICIO DEL SERVIDOR
# ============================
# ============================
#      CONTROL POR MQTT
# ============================
import paho.mqtt.client as mqtt

MQTT_BROKER = "127.0.0.1"   # o la IP de la Raspberry si usas otra máquina
MQTT_PORT = 1883
MQTT_TOPIC = "robot/move"   # tópico donde recibes comandos

def on_connect(client, userdata, flags, rc):
    print("MQTT conectado con código:", rc)
    client.subscribe(MQTT_TOPIC)
    print("Suscrito a:", MQTT_TOPIC)

def on_message(client, userdata, msg):
    comando = msg.payload.decode().strip().lower()
    print("Comando MQTT recibido:", comando)

    if comando == "adelante":
        forward(); set_speed(60, 60)

    elif comando == "atras":
        backward(); set_speed(60, 60)

    elif comando == "izquierda":
        left_turn(); set_speed(60, 60)

    elif comando == "derecha":
        right_turn(); set_speed(60, 60)

    elif comando == "stop":
        stop_motors()

    else:
        print("⚠ Comando MQTT desconocido:", comando)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def mqtt_listener():
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
    mqtt_client.loop_forever()

threading.Thread(target=mqtt_listener, daemon=True).start()

# ============================
#   CONTROL PLAY/PAUSA IO2
# ============================
import RPi.GPIO as GPIO, time

GPIO.setmode(GPIO.BCM)
IO2 = 17  # PLAY/PAUSA
GPIO.setup(IO2, GPIO.OUT)
GPIO.output(IO2, GPIO.HIGH)

def pulse_play_pause():
    GPIO.output(IO2, GPIO.LOW)
    time.sleep(0.15)
    GPIO.output(IO2, GPIO.HIGH)

@app.route("/music_toggle", methods=["POST"])
def music_toggle():
    pulse_play_pause()
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
