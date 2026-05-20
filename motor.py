import RPi.GPIO as GPIO
import config

class MotorController:
    def __init__(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(config.DIR_L, GPIO.OUT)
        GPIO.setup(config.PWM_L, GPIO.OUT)
        GPIO.setup(config.DIR_R, GPIO.OUT)
        GPIO.setup(config.PWM_R, GPIO.OUT)

        self.pwmL = GPIO.PWM(config.PWM_L, 1000)
        self.pwmR = GPIO.PWM(config.PWM_R, 1000)
        self.pwmL.start(0)
        self.pwmR.start(0)

    def stop(self):
        self.pwmL.ChangeDutyCycle(0)
        self.pwmR.ChangeDutyCycle(0)
        print("STOP")

    def _set_motor(self, dir_pin, pwm, direction, speed):
        """direction: 1=forward/right, 0=backward/left. speed 0-100"""
        GPIO.output(dir_pin, direction)
        pwm.ChangeDutyCycle(speed)

    def move(self, left_dir, left_speed, right_dir, right_speed):
        """low‑level: left_dir=1 means left motor forward, etc."""
        self._set_motor(config.DIR_L, self.pwmL, left_dir, left_speed)
        self._set_motor(config.DIR_R, self.pwmR, right_dir, right_speed)

    def forward(self, speed=80):
        self.move(1, speed, 1, speed)

    def backward(self, speed=80):
        self.move(0, speed, 0, speed)

    def left(self, speed=80):
        self.move(0, speed, 1, speed)

    def right(self, speed=80):
        self.move(1, speed, 0, speed)

    def cleanup(self):
        self.stop()
        self.pwmL.stop()
        self.pwmR.stop()
        GPIO.cleanup()
