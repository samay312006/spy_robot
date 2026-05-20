import paho.mqtt.client as mqtt
import time

broker = "5b5d1fc229d14745991d15a955fef7ca.s1.eu.hivemq.cloud"
port = 8884
user = "spyrobot"
password = "MySecurePass123"

def on_connect(client, userdata, flags, rc, properties=None):
    client.subscribe("spy_robot/robot1/webrtc/offer")
    client.subscribe("spy_robot/robot1/webrtc/answer")

def on_message(client, userdata, msg):
    with open('mqtt.log', 'a') as f:
        f.write(f"[{msg.topic}] {msg.payload.decode()[:200]}\n")

client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, transport="websockets")
client.username_pw_set(user, password)
client.on_connect = on_connect
client.on_message = on_message
client.tls_set()
client.connect(broker, port, 60)
client.loop_start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
