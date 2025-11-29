#!/usr/bin/env python3
"""
mediapipeavatar/face_thread.py

Thread yang menangani face tracking (MediaPipe FaceMesh) dan mengirimkan data
sebagai JSON lewat UDP. Thread akan berhenti saat global_vars.KILL_THREADS = True.
"""
import threading
import time
import json
import socket

try:
    import cv2
    import mediapipe as mp
    import numpy as np
except Exception as e:
    raise RuntimeError("face_thread.py requires opencv, mediapipe, numpy: " + str(e))

import global_vars

# Try to use clientUDP module from repo if available (optional)
_use_client_udp = False
try:
    import clientUDP
    # expected clientUDP to have a send function; if not, we'll fallback
    if hasattr(clientUDP, "send") or hasattr(clientUDP, "send_data") or hasattr(clientUDP, "send_json"):
        _use_client_udp = True
except Exception:
    _use_client_udp = False

# UDP fallback settings (used if clientUDP not available)
UDP_IP = "127.0.0.1"
UDP_PORT = 5065

mp_face = mp.solutions.face_mesh

def landmarks_to_np(landmarks, w, h):
    pts = np.array([[lm.x * w, lm.y * h, lm.z * w] for lm in landmarks])
    return pts

def avg_of_indices(pts, indices):
    return np.mean(pts[list(indices)], axis=0)

def indices_from_connections(connections):
    s = set()
    for a, b in connections:
        s.add(a); s.add(b)
    return sorted(list(s))

# try to derive index sets from MediaPipe constants (some constants may not exist depending on version)
try:
    LEFT_EYE_IDX = indices_from_connections(mp_face.FACEMESH_LEFT_EYE)
    RIGHT_EYE_IDX = indices_from_connections(mp_face.FACEMESH_RIGHT_EYE)
    LIPS_IDX = indices_from_connections(mp_face.FACEMESH_LIPS)
    LEFT_EYEBROW_IDX = indices_from_connections(mp_face.FACEMESH_LEFT_EYEBROW)
    RIGHT_EYEBROW_IDX = indices_from_connections(mp_face.FACEMESH_RIGHT_EYEBROW)
    NOSE_IDX = indices_from_connections(mp_face.FACEMESH_NOSE) if hasattr(mp_face, 'FACEMESH_NOSE') else [1]
except Exception:
    # fallback simple sets (very small) if constants not present
    LEFT_EYE_IDX = [33, 133]
    RIGHT_EYE_IDX = [362, 263]
    LIPS_IDX = [61, 291]
    LEFT_EYEBROW_IDX = [65, 55]
    RIGHT_EYEBROW_IDX = [295, 285]
    NOSE_IDX = [1]

def compute_face_metrics(pts):
    left_eye = avg_of_indices(pts, LEFT_EYE_IDX)
    right_eye = avg_of_indices(pts, RIGHT_EYE_IDX)
    eye_center = (left_eye + right_eye) / 2.0
    eye_dist = float(np.linalg.norm(left_eye[:2] - right_eye[:2]) + 1e-6)

    # mouth open metric
    lips_pts = pts[LIPS_IDX]
    mouth_top = float(np.min(lips_pts[:,1]))
    mouth_bottom = float(np.max(lips_pts[:,1]))
    mouth_open = float((mouth_bottom - mouth_top) / eye_dist)

    def eye_open_metric(idxs):
        eye_pts = pts[idxs]
        h = float(np.max(eye_pts[:,1]) - np.min(eye_pts[:,1]))
        w = float(np.max(eye_pts[:,0]) - np.min(eye_pts[:,0]) + 1e-6)
        return float(h / w)

    left_eye_open = eye_open_metric(LEFT_EYE_IDX)
    right_eye_open = eye_open_metric(RIGHT_EYE_IDX)

    left_brow_pts = pts[LEFT_EYEBROW_IDX] if len(LEFT_EYEBROW_IDX) > 0 else pts[LEFT_EYE_IDX]
    right_brow_pts = pts[RIGHT_EYEBROW_IDX] if len(RIGHT_EYEBROW_IDX) > 0 else pts[RIGHT_EYE_IDX]
    left_brow_y = float(np.mean(left_brow_pts[:,1]))
    right_brow_y = float(np.mean(right_brow_pts[:,1]))

    left_brow_raise = float((left_eye[1] - left_brow_y) / eye_dist)
    right_brow_raise = float((right_eye[1] - right_brow_y) / eye_dist)

    dx = right_eye[0] - left_eye[0]
    dy = right_eye[1] - left_eye[1]
    roll = float(np.degrees(np.arctan2(dy, dx)))

    nose_pt = avg_of_indices(pts, NOSE_IDX) if len(NOSE_IDX) > 0 else eye_center
    yaw = float((nose_pt[0] - eye_center[0]) / eye_dist) * 60.0
    pitch = float((eye_center[1] - nose_pt[1]) / eye_dist) * 60.0

    # clip / scale to friendly ranges
    mouth_open = max(0.0, min(1.5, mouth_open * 2.0))
    left_eye_open = max(0.0, min(1.0, left_eye_open * 2.5))
    right_eye_open = max(0.0, min(1.0, right_eye_open * 2.5))
    left_brow_raise = max(-1.0, min(1.0, left_brow_raise * 1.5))
    right_brow_raise = max(-1.0, min(1.0, right_brow_raise * 1.5))

    return {
        "head": {"pitch": float(pitch), "yaw": float(yaw), "roll": float(roll)},
        "mouth": {"open": float(mouth_open)},
        "left_eye": {"open": float(left_eye_open)},
        "right_eye": {"open": float(right_eye_open)},
        "brow": {"left": float(left_brow_raise), "right": float(right_brow_raise)},
        "meta": {"eye_dist": float(eye_dist)}
    }

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
                # try common method names
                if hasattr(clientUDP, "send_json"):
                    clientUDP.send_json(payload_str)
                elif hasattr(clientUDP, "send"):
                    clientUDP.send(payload_str.encode('utf-8'))
                elif hasattr(clientUDP, "send_data"):
                    clientUDP.send_data(payload_str)
                else:
                    # fallback: try calling send with bytes
                    clientUDP.send(payload_str.encode('utf-8'))
            except Exception:
                # fallback to raw UDP socket if clientUDP fails
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
                        # ignore single-frame failures
                        pass

                # small sleep to avoid pegging CPU; send_interval controls rate
                time.sleep(self.send_interval)
        finally:
            cap.release()
            mp_face_mesh.close()
            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass