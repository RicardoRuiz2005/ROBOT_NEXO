import RPi.GPIO as GPIO

ENA, IN1, IN2 = 18, 23, 24
ENB, IN3, IN4 = 13, 27, 6

GPIO.setmode(GPIO.BCM)
GPIO.setup([IN1, IN2, IN3, IN4], GPIO.OUT, initial=GPIO.LOW)
GPIO.setup([ENA, ENB], GPIO.OUT)
_pwmL, _pwmR = GPIO.PWM(ENA, 1000), GPIO.PWM(ENB, 1000)
_pwmL.start(0); _pwmR.start(0)

def set_speed(l, r): _pwmL.ChangeDutyCycle(l); _pwmR.ChangeDutyCycle(r)
def forward(): GPIO.output([IN1, IN3], GPIO.HIGH); GPIO.output([IN2, IN4], GPIO.LOW)
def backward(): GPIO.output([IN1, IN3], GPIO.LOW); GPIO.output([IN2, IN4], GPIO.HIGH)
def left_turn(): GPIO.output(IN1,0); GPIO.output(IN2,1); GPIO.output(IN3,1); GPIO.output(IN4,0)
def right_turn(): GPIO.output(IN1,1); GPIO.output(IN2,0); GPIO.output(IN3,0); GPIO.output(IN4,1)
def stop_motors(): GPIO.output([IN1,IN2,IN3,IN4], GPIO.LOW); set_speed(0,0)
def cleanup(): stop_motors(); _pwmL.stop(); _pwmR.stop(); GPIO.cleanup()
