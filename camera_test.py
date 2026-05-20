import time
from picamera2 import Picamera2

def test_camera():
    try:
        print("Initialising camera...")
        picam2 = Picamera2()
        config = picam2.create_still_configuration(main={"size": (640, 480)})
        picam2.configure(config)
        picam2.start()
        time.sleep(2)  # allow sensor to settle

        print("Capturing frame...")
        picam2.capture_file("camera_test.jpg")
        print("Success! Saved 'camera_test.jpg' in the current directory.")
        picam2.stop()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_camera()
