import time
# pyrefly: ignore [missing-import]
import paho.mqtt.client as mqtt
import json
import threading
import subprocess
import signal
import os
import urllib.request
import config
from motor import MotorController
from lidar import TFLuna
# pyrefly: ignore [missing-import]
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

        self.patrol = Patrol(self.motor, self.lidar, self._publish_status)
        self.mqtt.tls_set() 

        self._publish_distance = True
        threading.Thread(target=self._distance_publisher, daemon=True).start()

        # go2rtc process handle
        self._go2rtc_proc = None

    def _start_go2rtc(self):
        """Start go2rtc as a subprocess for camera streaming."""
        go2rtc_bin = os.path.abspath(config.GO2RTC_PATH)
        go2rtc_cfg = os.path.abspath(config.GO2RTC_CONFIG)

        if not os.path.isfile(go2rtc_bin):
            logger.error(f"go2rtc binary not found at {go2rtc_bin}")
            logger.error("Download from: https://github.com/AlexxIT/go2rtc/releases")
            return

        logger.info(f"Starting go2rtc: {go2rtc_bin} -config {go2rtc_cfg}")
        self._go2rtc_proc = subprocess.Popen(
            [go2rtc_bin, "-config", go2rtc_cfg],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Log go2rtc output in a background thread
        def _log_go2rtc():
            for line in self._go2rtc_proc.stdout:
                logger.info(f"[go2rtc] {line.decode().rstrip()}")
        threading.Thread(target=_log_go2rtc, daemon=True).start()

        logger.info(f"go2rtc started (PID {self._go2rtc_proc.pid}), "
                     f"API on port {config.GO2RTC_API_PORT}")

    def _stop_go2rtc(self):
        """Stop the go2rtc subprocess."""
        if self._go2rtc_proc and self._go2rtc_proc.poll() is None:
            logger.info("Stopping go2rtc...")
            self._go2rtc_proc.terminate()
            try:
                self._go2rtc_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._go2rtc_proc.kill()
            logger.info("go2rtc stopped")

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
            client.subscribe(config.PATROL_SCHEDULE_TOPIC)
            client.subscribe(config.PATROL_PATH_TOPIC)
            client.subscribe(config.WEBRTC_OFFER_TOPIC)
        else:
            print(f"Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = msg.payload.decode()
            if topic == config.CMD_TOPIC:
                self._handle_command(payload)
            elif topic == config.PATROL_SCHEDULE_TOPIC:
                self.patrol.load_schedule(payload)
            elif topic == config.PATROL_PATH_TOPIC:
                self.patrol.load_waypoints(payload)
            elif topic == config.WEBRTC_OFFER_TOPIC:
                self._handle_webrtc_offer(payload)
        except Exception as e:
            print("Error handling message:", e)

    def _handle_webrtc_offer(self, payload):
        def _process():
            try:
                data = json.loads(payload)
                client_id = data.get('client_id')
                offer_sdp = data.get('sdp')
                
                if not client_id or not offer_sdp:
                    return

                req_body = json.dumps({"type": "offer", "sdp": offer_sdp}).encode('utf-8')
                req = urllib.request.Request(
                    f"http://127.0.0.1:{config.GO2RTC_API_PORT}/api/webrtc?src=picam",
                    data=req_body,
                    headers={'Content-Type': 'application/json'}
                )
                
                with urllib.request.urlopen(req, timeout=5) as response:
                    res_body = response.read()
                    answer_data = json.loads(res_body.decode('utf-8'))
                    
                    answer_payload = json.dumps({
                        "client_id": client_id,
                        "answer": answer_data
                    })
                    self.mqtt.publish(config.WEBRTC_ANSWER_TOPIC, answer_payload)
            except Exception as e:
                logger.error(f"WebRTC signaling error: {e}")
                
        threading.Thread(target=_process, daemon=True).start()

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
        # Start go2rtc for camera streaming
        self._start_go2rtc()

        # Connect to MQTT broker on port 8884 (WebSocket)
        self.mqtt.connect(config.MQTT_BROKER, 8884, 60)
        self.mqtt.loop_start()

        threading.Thread(target=self.patrol.run_scheduler_loop, daemon=True).start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()

    def shutdown(self):
        self._publish_distance = False
        self._stop_go2rtc()
        self.lidar.stop()
        self.motor.cleanup()
        self.mqtt.loop_stop()

if __name__ == "__main__":
    robot = Robot()
    robot.start()
