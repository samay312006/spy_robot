import urllib.request
import json
import traceback

offer_sdp = "v=0\r\no=- 2882950411434993454 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"
req_body = json.dumps({"type": "offer", "sdp": offer_sdp}).encode('utf-8')
req = urllib.request.Request(
    "http://127.0.0.1:1984/api/webrtc?src=picam",
    data=req_body,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=5) as response:
        res_body = response.read()
        print("Response body:", res_body)
        try:
            answer_data = json.loads(res_body.decode('utf-8'))
            print("Parsed JSON:", answer_data)
        except Exception as e:
            print("JSON parse error:", e)
except Exception as e:
    print("HTTP error:", e)
    if hasattr(e, 'read'):
        print(e.read())
    traceback.print_exc()
