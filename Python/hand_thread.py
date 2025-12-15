import cv2
import mediapipe as mp
from pythonosc import udp_client

# Setup OSC client (kirim ke Unity di port 9000 misalnya)
client = udp_client.SimpleUDPClient("127.0.0.1", 5065)

# MediaPipe modules
mp_face = mp.solutions.face_mesh
mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

face = mp_face.FaceMesh(max_num_faces=1)
pose = mp_pose.Pose()
hands = mp_hands.Hands(max_num_hands=2)

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Face tracking
    face_results = face.process(img_rgb)
    if face_results.multi_face_landmarks:
        for lm in face_results.multi_face_landmarks:
            # contoh: kirim koordinat hidung
            nose = lm.landmark[1]  # landmark index 1 = nose tip
            client.send_message("/face/nose", [nose.x, nose.y, nose.z])

    # Pose tracking
    pose_results = pose.process(img_rgb)
    if pose_results.pose_landmarks:
        for i, lm in enumerate(pose_results.pose_landmarks.landmark):
            client.send_message(f"/pose/{i}", [lm.x, lm.y, lm.z])

    # Hand tracking
    hand_results = hands.process(img_rgb)
    if hand_results.multi_hand_landmarks:
        for h, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
            for i, lm in enumerate(hand_landmarks.landmark):
                # kirim tiap jari (21 titik per tangan)
                client.send_message(f"/hand/{h}/{i}", [lm.x, lm.y, lm.z])
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    cv2.imshow("Tracking", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
