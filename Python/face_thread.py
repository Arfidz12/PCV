import threading
import time
import json
import socket
import global_vars
import cv2
import mediapipe as mp
import numpy as np

cap = cv2.VideoCapture(global_vars.CAM_INDEX)
if global_vars.USE_CUSTOM_CAM_SETTINGS:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, global_vars.WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, global_vars.HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, global_vars.FPS)

# Try to use clientUDP module from repo if available (optional)
_use_client_udp = False
try:
    import clientUDP
    if hasattr(clientUDP, "send") or hasattr(clientUDP, "send_data") or hasattr(clientUDP, "send_json"):
        _use_client_udp = True
except Exception:
    _use_client_udp = False

UDP_IP = "127.0.0.1"
UDP_PORT = 5065

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
mp_face = mp.solutions.face_mesh
face_mesh = mp_face.FaceMesh(static_image_mode=False,
                             max_num_faces=1,
                             refine_landmarks=True,
                             min_detection_confidence=0.5,
                             min_tracking_confidence=0.5)

def landmarks_to_np(landmarks, w, h):
    return np.array([[lm.x * w, lm.y * h, lm.z * w] for lm in landmarks])

def avg_of_indices(pts, indices):
    return np.mean(pts[list(indices)], axis=0)

def indices_from_connections(connections):
    s = set()
    for a, b in connections:
        s.add(a); s.add(b)
    return sorted(list(s))

LEFT_EYE_IDX = indices_from_connections(mp_face.FACEMESH_LEFT_EYE)
RIGHT_EYE_IDX = indices_from_connections(mp_face.FACEMESH_RIGHT_EYE)
LIPS_IDX = indices_from_connections(mp_face.FACEMESH_LIPS)
LEFT_EYEBROW_IDX = indices_from_connections(mp_face.FACEMESH_LEFT_EYEBROW)
RIGHT_EYEBROW_IDX = indices_from_connections(mp_face.FACEMESH_RIGHT_EYEBROW)
NOSE_IDX = indices_from_connections(mp_face.FACEMESH_NOSE) if hasattr(mp_face, 'FACEMESH_NOSE') else [1]

def eye_open_metric(pts, idxs):
    eye_pts = pts[idxs]
    v = np.max(eye_pts[:, 1]) - np.min(eye_pts[:, 1])
    h = np.max(eye_pts[:, 0]) - np.min(eye_pts[:, 0]) + 1e-6
    return float(v / h)

def compute_face_metrics(pts):
    left_eye = avg_of_indices(pts, LEFT_EYE_IDX)
    right_eye = avg_of_indices(pts, RIGHT_EYE_IDX)
    eye_center = (left_eye + right_eye) / 2.0
    eye_dist = np.linalg.norm(left_eye[:2] - right_eye[:2]) + 1e-6

    # Mulut: improved calibration, lower offset/higher scale
    lips_pts = pts[LIPS_IDX]
    mouth_top = np.min(lips_pts[:, 1])
    mouth_bottom = np.max(lips_pts[:, 1])
    mouth_open_raw = float((mouth_bottom - mouth_top) / eye_dist)
    # Tuning: calibrate so mouth_open_raw when closed ~0.08, when wide open >=0.3
    mouth_open = max(0.0, min(1.0, (mouth_open_raw - 0.40) * 4.2))

    # Mata kiri & kanan (independent, improved calibration)
    left_eye_open_raw = eye_open_metric(pts, LEFT_EYE_IDX)
    right_eye_open_raw = eye_open_metric(pts, RIGHT_EYE_IDX)
    left_eye_open = max(0.0, min(1.0, left_eye_open_raw * 2.6 - 0.22))
    right_eye_open = max(0.0, min(1.0, right_eye_open_raw * 2.6 - 0.22))

    # Alis
    left_brow_pts = pts[LEFT_EYEBROW_IDX] if len(LEFT_EYEBROW_IDX) > 0 else pts[LEFT_EYE_IDX]
    right_brow_pts = pts[RIGHT_EYEBROW_IDX] if len(RIGHT_EYEBROW_IDX) > 0 else pts[RIGHT_EYE_IDX]
    left_brow_y = np.mean(left_brow_pts[:, 1])
    right_brow_y = np.mean(right_brow_pts[:, 1])
    left_brow_raise = max(-1.0, min(1.0, (left_eye[1] - left_brow_y) / eye_dist * 1.7))
    right_brow_raise = max(-1.0, min(1.0, (right_eye[1] - right_brow_y) / eye_dist * 1.7))

    metrics = {
        "mouth": {"open": mouth_open},
        "left_eye": {"open": left_eye_open},
        "right_eye": {"open": right_eye_open},
        "brow": {"left": left_brow_raise, "right": right_brow_raise}
    }
    # LOG untuk cek value: tutup/buka mulut/mata satu-satu untuk kalibrasi!
    print(f"[FaceMetrics] Mouth: {mouth_open:.2f}, LeftEye: {left_eye_open:.2f}, RightEye: {right_eye_open:.2f}, BrowL:{left_brow_raise:.2f}, BrowR:{right_brow_raise:.2f}")
    return metrics

class FaceThread(threading.Thread):
    def __init__(self, camera_index=0, udp_ip=UDP_IP, udp_port=UDP_PORT, send_interval=0.01):
        super(FaceThread, self).__init__()
        self.camera_index = camera_index
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.send_interval = send_interval
        self.daemon = True
        self._sock = None
        if not _use_client_udp:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _send_payload(self, payload_str):
        if _use_client_udp:
            try:
                if hasattr(clientUDP, "send_json"):
                    clientUDP.send_json(payload_str)
                elif hasattr(clientUDP, "send"):
                    clientUDP.send(payload_str.encode('utf-8'))
                elif hasattr(clientUDP, "send_data"):
                    clientUDP.send_data(payload_str)
                else:
                    clientUDP.send(payload_str.encode('utf-8'))
            except Exception:
                if self._sock:
                    try:
                        self._sock.sendto(payload_str.encode('utf-8'), (self.udp_ip, self.udp_port))
                    except Exception:
                        pass
        else:
            try:
                self._sock.sendto(payload_str.encode('utf-8'), (self.udp_ip, self.udp_port))
            except Exception:
                pass

    def run(self):
        mp_face_mesh = mp_face.FaceMesh(static_image_mode=False,
                                       max_num_faces=1,
                                       refine_landmarks=True,
                                       min_detection_confidence=0.5,
                                       min_tracking_confidence=0.5)
        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            print("FaceThread: cannot open camera index", self.camera_index)
            return

        try:
            while not getattr(global_vars, "KILL_THREADS", False):
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue
                h, w = frame.shape[:2]
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = mp_face_mesh.process(frame_rgb)
                if results.multi_face_landmarks:
                    landmarks = results.multi_face_landmarks[0].landmark
                    try:
                        pts = landmarks_to_np(landmarks, w, h)
                        metrics = compute_face_metrics(pts)
                        payload = json.dumps(metrics)
                        self._send_payload(payload)
                    except Exception:
                        pass
                time.sleep(self.send_interval)
        finally:
            cap.release()
            mp_face_mesh.close()
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass