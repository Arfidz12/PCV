# clientUDP.py
# Simple UDP client wrapper that runs as a thread and provides sendMessage and stop/close
import socket
import threading
import time

class ClientUDP(threading.Thread):
    def __init__(self, ip='127.0.0.1', port=52733, autoReconnect=True, bind_local=False):
        super().__init__()
        self.ip = ip
        self.port = int(port)
        self.autoReconnect = autoReconnect
        self.bind_local = bind_local
        self.socket = None
        self._running = False
        self._connected = False
        self._stop_event = threading.Event()
        self.daemon = True

    def run(self):
        # Thread lifecycle: try to connect and stay alive until stopped
        while not self._stop_event.is_set():
            if not self._connected:
                try:
                    self._create_socket()
                    self._connected = True
                except Exception:
                    # If connect fails and autoReconnect enabled, wait then retry
                    if not self.autoReconnect:
                        break
                    time.sleep(1)
                    continue
            # Idle loop to keep thread alive and responsive to stop()
            time.sleep(0.1)

        # cleanup on exit
        self._cleanup_socket()

    def _create_socket(self):
        # create UDP socket and connect (connect is optional for UDP but convenient)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.bind_local:
            try:
                self.socket.bind(('0.0.0.0', 0))
            except Exception:
                pass
        # connect does not establish TCP connection but sets default remote address
        self.socket.connect((self.ip, self.port))
        # set a short timeout so send/recv won't block indefinitely if needed
        self.socket.settimeout(1.0)

    def isConnected(self):
        return self._connected

    def sendMessage(self, message: str):
        if not message:
            return
        try:
            payload = f"{message}<EOM>".encode('utf-8')
            if self.socket:
                # use send for connected UDP socket; fallback to sendto if needed
                try:
                    self.socket.send(payload)
                except Exception:
                    # fallback one-shot sendto if socket broken
                    tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        tmp.sendto(payload, (self.ip, self.port))
                    finally:
                        tmp.close()
            else:
                # one-shot send if thread socket not available
                tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    tmp.sendto(payload, (self.ip, self.port))
                finally:
                    tmp.close()
        except (ConnectionRefusedError, ConnectionResetError) as ex:
            # server not available; mark disconnected and optionally reconnect
            self._connected = False
            if self._stop_event.is_set():
                return
            if self.autoReconnect:
                # attempt reconnect in background thread loop
                time.sleep(1)
        except Exception:
            # swallow other send errors to avoid crashing producer
            pass

    def disconnect(self):
        # Graceful disconnect without recursive reconnect calls
        self._connected = False
        try:
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None
        except Exception:
            pass

    def stop(self):
        # Signal thread to stop and close socket
        self._stop_event.set()
        self._connected = False
        try:
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None
        except Exception:
            pass

    def close(self):
        # alias for stop
        self.stop()
