import time
import json
import logging
import datetime

logger = logging.getLogger("patrol")

class Patrol:
    def __init__(self, motor, lidar, publish_status_cb):
        self.motor = motor
        self.lidar = lidar
        self.publish_status = publish_status_cb
        self.schedule = []
        self.waypoints = []
        self.is_patrolling = False

    def load_schedule(self, payload):
        try:
            # Payload is a JSON list of times, e.g., ["08:00", "18:00"]
            self.schedule = json.loads(payload)
            logger.info(f"Schedule loaded: {self.schedule}")
        except Exception as e:
            logger.error(f"Failed to load schedule: {e}")

    def load_waypoints(self, payload):
        try:
            # Payload is a JSON list of dicts, e.g., [{"cmd":"f","duration":2,"speed":80}]
            self.waypoints = json.loads(payload)
            logger.info(f"Waypoints loaded: {self.waypoints}")
        except Exception as e:
            logger.error(f"Failed to load waypoints: {e}")

    def run_scheduler_loop(self):
        """Runs continuously in a background thread to check for scheduled times."""
        while True:
            now = datetime.datetime.now().strftime("%H:%M")
            if now in self.schedule and not self.is_patrolling:
                self.is_patrolling = True
                logger.info(f"Starting scheduled patrol for {now}")
                self._execute_patrol()
                self.is_patrolling = False
                
                # Sleep a minute to avoid re-triggering during the same minute
                time.sleep(60)
            
            time.sleep(1)

    def _execute_patrol(self):
        """Executes the loaded waypoints one by one."""
        if not self.waypoints:
            logger.warning("No waypoints loaded for patrol.")
            return

        for wp in self.waypoints:
            cmd = wp.get("cmd")
            duration = wp.get("duration", 1)
            speed = wp.get("speed", 80)

            logger.info(f"Patrol executing: {cmd} for {duration}s at {speed}%")

            if cmd == "f":
                # Drive forward but constantly check for obstacles
                end_time = time.time() + duration
                while time.time() < end_time:
                    # Configured obstacle threshold is usually around 40cm
                    if self.lidar.is_obstacle(40):
                        self.motor.stop()
                        logger.warning("Obstacle detected! Stopping patrol segment.")
                        # Break out of this waypoint early
                        break
                    else:
                        self.motor.forward(speed)
                    time.sleep(0.1)
                self.motor.stop()
                
            elif cmd == "b":
                self.motor.backward(speed)
                time.sleep(duration)
                self.motor.stop()
                
            elif cmd == "l":
                self.motor.left(speed)
                time.sleep(duration)
                self.motor.stop()
                
            elif cmd == "r":
                self.motor.right(speed)
                time.sleep(duration)
                self.motor.stop()
            
            # Short pause between waypoints
            time.sleep(0.5)
            
        logger.info("Patrol complete")
