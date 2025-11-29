#pipe server
from body import BodyThread
from face_thread import FaceThread
import time
import global_vars
from sys import exit

if __name__ == "__main__":
    # start body tracking thread
    body_thread = BodyThread()
    body_thread.start()

    # start face tracking thread
    face_thread = FaceThread()
    face_thread.start()

    try:
        i = input("Press Enter to stop...\n")
    except Exception:
        # if input is interrupted, still proceed to shutdown
        pass

    print("Exiting…")
    global_vars.KILL_THREADS = True
    # allow threads to exit gracefully
    time.sleep(0.5)
    exit()