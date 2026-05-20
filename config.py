# MQTT
MQTT_BROKER = "5b5d1fc229d14745991d15a955fef7ca.s1.eu.hivemq.cloud"   # public test – replace later with your own cloud broker
MQTT_PORT = 1883
MQTT_USER = "spyrobot"
MQTT_PASS = "MySecurePass123"
TOPIC_PREFIX = "spy_robot/robot1"
CMD_TOPIC = f"{TOPIC_PREFIX}/control"
STATUS_TOPIC = f"{TOPIC_PREFIX}/status"
DISTANCE_TOPIC = f"{TOPIC_PREFIX}/distance"
PATROL_SCHEDULE_TOPIC = f"{TOPIC_PREFIX}/patrol/schedule"
PATROL_PATH_TOPIC = f"{TOPIC_PREFIX}/patrol/path"
# Motor pins (your existing pins)
DIR_L = 19
PWM_L = 26
DIR_R = 20
PWM_R = 21

# LiDAR (TF‑Luna)
LIDAR_PORT = "/dev/serial0"
LIDAR_BAUDRATE = 115200
OBSTACLE_THRESHOLD_CM = 40      # cm – stop if closer
OBSTACLE_REAR_THRESHOLD = 20    # optional, only if rear sensor added

# Audio devices (check with `arecord -l` and `aplay -l`)
MIC_DEVICE = "plughw:1,0"       # USB microphone (usually card 1, device 0)
SPEAKER_DEVICE = "plughw:0,0"   # I2S output (card 0, device 0 – adjust if needed)
AUDIO_SAMPLE_RATE = 48000

# Video
VIDEO_SIZE = (640, 480)

# go2rtc – video streaming server
GO2RTC_PATH = "./go2rtc"          # path to binary (in project root)
GO2RTC_CONFIG = "./go2rtc.yaml"
GO2RTC_API_PORT = 1984
