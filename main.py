import time
import paho.mqtt.client as mqtt
import json
import threading
import asyncio
import config
from motor import MotorController
from lidar import TFLuna
from webrtc import WebRTCManager
from patrol import Patrol
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")
class Robot:
    def __init__(self):
        self.motor = MotorController()
        self.lidar = TFLuna(config.LIDAR_PORT, config.LIDAR_BAUDRATE)

        # WebSocket MQTT client (WSS) – works behind firewalls
        self.mqtt = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            transport="websockets"      # <-- key change
        )
        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_message = self._on_message
        self.mqtt.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
        # NO tls_set() needed – WSS handles encryption automatically

        self.webrtc = WebRTCManager(self.mqtt)
        self.patrol = Patrol(self.motor, self.lidar, self._publish_status)
        self.mqtt.tls_set() 

        self._publish_distance = True
        threading.Thread(target=self._distance_publisher, daemon=True).start()

    def _publish_status(self, topic, msg):
        self.mqtt.publish(topic, msg)

    def _distance_publisher(self):
        while self._publish_distance:
            dist = self.lidar.get_distance()
            if dist is not None:
                self.mqtt.publish(config.DISTANCE_TOPIC, str(dist))
            time.sleep(0.2)

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("MQTT connected")
            client.subscribe(config.CMD_TOPIC)
            client.subscribe(config.WEBRTC_SIGNAL_TOPIC)
            client.subscribe(config.PATROL_SCHEDULE_TOPIC)
            client.subscribe(config.PATROL_PATH_TOPIC)
            client.subscribe(config.WEBRTC_REFRESH_TOPIC)
        else:
            print(f"Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            if topic == config.CMD_TOPIC:
                self._handle_command(payload)
            elif topic == config.WEBRTC_SIGNAL_TOPIC:
                self.webrtc.handle_signal(payload)
            elif topic == config.PATROL_SCHEDULE_TOPIC:
                self.patrol.load_schedule(payload)
            elif topic == config.PATROL_PATH_TOPIC:
                self.patrol.load_waypoints(payload)
            elif topic == config.WEBRTC_REFRESH_TOPIC:
                 logger.info("Received refresh request from dashboard")
                 asyncio.run_coroutine_threadsafe(self.webrtc.restart(), self.webrtc.loop)
    # Schedule a restart on the asyncio loop
                 asyncio.run_coroutine_threadsafe(self.webrtc.restart(), self.webrtc.loop)
        except Exception as e:
            print("Error handling message:", e)

    def _handle_command(self, cmd):
        if cmd == 'f':
            if self.lidar.is_obstacle(config.OBSTACLE_THRESHOLD_CM):
                self.motor.stop()
                print("OBSTACLE AHEAD")
            else:
                self.motor.forward()
        elif cmd == 'b':
            self.motor.backward()
        elif cmd == 'l':
            self.motor.left()
        elif cmd == 'r':
            self.motor.right()
        elif cmd == 's':
            self.motor.stop()
        else:
            try:
                data = json.loads(cmd)
                c = data.get('cmd')
                sp = data.get('speed', 80)
                if c == 'f':
                    if self.lidar.is_obstacle(config.OBSTACLE_THRESHOLD_CM):
                        self.motor.stop()
                    else:
                        self.motor.forward(sp)
                elif c == 'b': self.motor.backward(sp)
                elif c == 'l': self.motor.left(sp)
                elif c == 'r': self.motor.right(sp)
                elif c == 's': self.motor.stop()
            except:
                pass

    def start(self):
        # Connect to port 8884 (WebSocket)
      #  print(f"Connecting to MQTT broker: {config.MQTT_BROKER}:8884")
        self.mqtt.connect(config.MQTT_BROKER, 8884, 60)
        self.mqtt.loop_start()

        loop = asyncio.new_event_loop()
        threading.Thread(target=self._start_webrtc, args=(loop,), daemon=True).start()

        threading.Thread(target=self.patrol.run_scheduler_loop, daemon=True).start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def _start_webrtc(self, loop):
        asyncio.set_event_loop(loop)
        self.webrtc.run(loop)
        loop.run_forever()

    def shutdown(self):
        self._publish_distance = False
        self.lidar.stop()
        self.motor.cleanup()
        self.mqtt.loop_stop()

if __name__ == "__main__":
    robot = Robot()
    robot.start()
