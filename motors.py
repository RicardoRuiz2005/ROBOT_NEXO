# motors.py
import RPi.GPIO as GPIO

ENA, IN1, IN2 = 18, 23, 24
ENB, IN3, IN4 = 13, 27, 6

GPIO.setmode(GPIO.BCM)
GPIO.setup([IN1, IN2, IN3, IN4], GPIO.OUT, initial=GPIO.LOW)
GPIO.setup([ENA, ENB], GPIO.OUT)

_pwmL = GPIO.PWM(ENA, 1000)
_pwmR = GPIO.PWM(ENB, 1000)
_pwmL.start(0)
_pwmR.start(0)

def set_speed(left, right):
    _pwmL.ChangeDutyCycle(max(0, min(100, left)))
    _pwmR.ChangeDutyCycle(max(0, min(100, right)))

def forward():
    GPIO.output(IN1,1); GPIO.output(IN2,0)
    GPIO.output(IN3,1); GPIO.output(IN4,0)

def backward():
    GPIO.output(IN1,0); GPIO.output(IN2,1)
    GPIO.output(IN3,0); GPIO.output(IN4,1)

def left_turn():
    GPIO.output(IN1,0); GPIO.output(IN2,1)
    GPIO.output(IN3,1); GPIO.output(IN4,0)

def right_turn():
    GPIO.output(IN1,1); GPIO.output(IN2,0)
    GPIO.output(IN3,0); GPIO.output(IN4,1)

def stop_motors():
    GPIO.output([IN1, IN2, IN3, IN4], GPIO.LOW)
    set_speed(0, 0)

def cleanup():
    try:
        stop_motors()
        _pwmL.stop()
        _pwmR.stop()
    finally:
        GPIO.cleanup()
