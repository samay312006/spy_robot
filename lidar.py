import serial
import threading
import time

class TFLuna:
    def __init__(self, port, baudrate):
        self.ser = serial.Serial(port, baudrate, timeout=0.1)
        self.distance_cm = 0
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        while self._running:
            # Sync to 0x59 0x59 header
            b = self.ser.read(1)
            if b == b'\x59':
                b = self.ser.read(1)
                if b == b'\x59':
                    data = self.ser.read(7)
                    if len(data) == 7:
                        dist = data[0] + data[1] * 256
                        with self._lock:
                            self.distance_cm = dist if dist > 0 else None
                else:
                    continue

    def get_distance(self):
        """Returns distance in cm, or None if invalid."""
        with self._lock:
            return self.distance_cm

    def is_obstacle(self, threshold_cm):
        dist = self.get_distance()
        if dist is not None and dist < threshold_cm:
            return True
        return False

    def stop(self):
        self._running = False
        self.ser.close()
