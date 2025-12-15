from body_thread import BodyThread
import time
import global_vars
from sys import exit

if __name__ == "__main__":
    body_thread = BodyThread()
    body_thread.start()

    try:
        i = input("Press Enter to stop...\n")
    except Exception:
        pass

    print("Exiting…")
    global_vars.KILL_THREADS = True
    time.sleep(0.5)

    exit()
