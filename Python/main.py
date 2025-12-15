#pipe server
from body_thread import BodyThread
import time
import global_vars
from sys import exit

if __name__ == "__main__":
    # start body tracking thread
    body_thread = BodyThread()
    body_thread.start()

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