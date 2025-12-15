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
        while not self._stop_event.is_set():
            if not self._connected:
                try:
                    self._create_socket()
                    self._connected = True
                except Exception:
                    if not self.autoReconnect:
                        break
                    time.sleep(1)
                    continue
            time.sleep(0.1)

        self._cleanup_socket()

    def _create_socket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.bind_local:
            try:
                self.socket.bind(('0.0.0.0', 0))
            except Exception:
                pass
        self.socket.connect((self.ip, self.port))
        self.socket.settimeout(1.0)

    def isConnected(self):
        return self._connected

    def sendMessage(self, message: str):
        if not message:
            return
        try:
            payload = f"{message}<EOM>".encode('utf-8')
            if self.socket:
                try:
                    self.socket.send(payload)
                except Exception:
                    tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        tmp.sendto(payload, (self.ip, self.port))
                    finally:
                        tmp.close()
            else:
                tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    tmp.sendto(payload, (self.ip, self.port))
                finally:
                    tmp.close()
        except (ConnectionRefusedError, ConnectionResetError) as ex:
            self._connected = False
            if self._stop_event.is_set():
                return
            if self.autoReconnect:
                time.sleep(1)
        except Exception:
            pass

    def disconnect(self):
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
        self.stop()

