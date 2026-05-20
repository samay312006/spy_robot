import asyncio, json, logging, time, traceback
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
from aiortc.contrib.media import MediaStreamTrack
from av import VideoFrame
from picamera2 import Picamera2
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webrtc")

class VideoTrack(MediaStreamTrack):
    kind = "video"
    def __init__(self):
        super().__init__()
        self.picam2 = Picamera2()
        self.picam2.configure(
            self.picam2.create_video_configuration(main={"size": config.VIDEO_SIZE})
        )
        self.picam2.start()
        self._start_time = time.time()

    async def recv(self):
        img = self.picam2.capture_array()
        if img.ndim == 3 and img.shape[2] == 4:      # BGRA → BGR
            img = img[:, :, :3]
        frame = VideoFrame.from_ndarray(img, format="bgr24")
        elapsed = time.time() - self._start_time
        frame.pts = int(elapsed * 90000)
        return frame

    def stop(self):
        """Release the camera hardware."""
        try:
            self.picam2.stop()
            self.picam2.close()
            logger.info("Camera stopped")
        except Exception as e:
            logger.warning(f"Error stopping camera: {e}")

class WebRTCManager:
    def __init__(self, mqtt_client):
        self.mqtt = mqtt_client
        self.pc = None
        self.loop = None
        self.video_track = VideoTrack()          # initial camera start
        self._restart_lock = asyncio.Lock()

    async def start(self):
        await self._create_and_send_offer()

    async def restart(self):
        """Stop the camera, restart it, and send a new offer (full refresh)."""
        async with self._restart_lock:
            logger.info("=== Full camera restart requested ===")
            
            # 1. Stop the current camera if running
            if self.video_track:
                self.video_track.stop()
                self.video_track = None
                # Give the kernel a moment to release the device
                await asyncio.sleep(1)

            # 2. Close old peer connection
            if self.pc:
                try:
                    await self.pc.close()
                except Exception as e:
                    logger.warning(f"Error closing old PC: {e}")
                self.pc = None

            # 3. Create a brand new camera track
            logger.info("Starting new camera...")
            self.video_track = VideoTrack()

            # 4. Send offer with the fresh track
            await self._create_and_send_offer()

    async def _create_and_send_offer(self):
        try:
            logger.info("Creating new RTCPeerConnection and offer")
            self.pc = RTCPeerConnection()
            self.pc.addTrack(self.video_track)

            @self.pc.on("icecandidate")
            async def on_icecandidate(candidate):
                if candidate:
                    msg = json.dumps({
                        "candidate": candidate.candidate,
                        "sdpMid": candidate.sdpMid,
                        "sdpMLineIndex": candidate.sdpMLineIndex
                    })
                    self.mqtt.publish(config.WEBRTC_SIGNAL_TOPIC, msg)

            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            offer_msg = json.dumps({
                "sdp": self.pc.localDescription.sdp,
                "type": self.pc.localDescription.type
            })
            self.mqtt.publish(config.WEBRTC_SIGNAL_TOPIC, offer_msg)
            logger.info("Offer published – video ready")
        except Exception as e:
            logger.error(f"FATAL ERROR in _create_and_send_offer: {e}")
            traceback.print_exc()

    def handle_signal(self, payload):
        try:
            msg = json.loads(payload)
        except:
            return
        logger.info(f"Signal received: {msg.get('type', 'candidate')}")
        if "sdp" in msg:
            if msg["type"] == "offer":
                logger.info("Ignoring incoming offer")
                return
            sdp = RTCSessionDescription(sdp=msg["sdp"], type=msg["type"])
            asyncio.run_coroutine_threadsafe(self._set_remote(sdp), self.loop)
        elif "candidate" in msg:
            try:
                candidate_dict = {
                    "candidate": msg["candidate"],
                    "sdpMid": msg["sdpMid"],
                    "sdpMLineIndex": msg["sdpMLineIndex"]
                }
                asyncio.run_coroutine_threadsafe(
                    self.pc.addIceCandidate(candidate_dict), self.loop
                )
            except Exception as e:
                logger.error(f"ICE candidate error: {e}")

    async def _set_remote(self, sdp):
        if not self.pc:
            logger.warning("No peer connection, ignoring remote description")
            return
        logger.info(f"Setting remote description: {sdp.type}")
        await self.pc.setRemoteDescription(sdp)
        if sdp.type == "offer":
            answer = await self.pc.createAnswer()
            await self.pc.setLocalDescription(answer)
            self.mqtt.publish(
                config.WEBRTC_SIGNAL_TOPIC,
                json.dumps({"sdp": self.pc.localDescription.sdp, "type": "answer"})
            )

    def run(self, loop):
        self.loop = loop
        asyncio.run_coroutine_threadsafe(self.start(), loop)

    def shutdown(self):
        if self.video_track:
            self.video_track.stop()
        if self.pc:
            asyncio.run_coroutine_threadsafe(self.pc.close(), self.loop)
