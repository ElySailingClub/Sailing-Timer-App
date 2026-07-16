"""Serial communication handler for ESC Race Box.

Uses JSON packets over serial, compatible with the Race Box firmware protocol.
Packet format: one JSON object per line, terminated with newline.

Supported incoming packets:
  {"packet-type": "keep-alive"}
  {"packet-type": "button-input", "button": "store"|"recall"|"shortened"}
  {"packet-type": "log", "type": "info"|"warn"|"error", "message": "..."}

Supported outgoing packets:
  {"packet-type": "keep-alive-response"}
  {"packet-type": "output", "sound": "horn"|"bell"|"shortened"}
"""

import json

import serial
import serial.tools.list_ports
from PySide6.QtCore import QThread, Signal


class SerialHandler(QThread):
    packet_received = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ser = None
        self._running = False
        self._port = None
        self._baudrate = 115200

    @property
    def is_connected(self):
        return self._ser is not None and self._ser.is_open

    def connect_port(self, port, baudrate=115200):
        if self.isRunning():
            self.disconnect_port()
        self._port = port
        self._baudrate = baudrate
        self.start()

    def disconnect_port(self):
        self._running = False
        self.wait(3000)

    def run(self):
        try:
            self._ser = serial.Serial(self._port, self._baudrate, timeout=1)
            self._running = True
            self.connection_changed.emit(True)
            while self._running:
                line = self._ser.readline().decode("utf-8").rstrip()
                if line:
                    try:
                        data = json.loads(line)
                        if data.get("packet-type") == "keep-alive":
                            self.send_packet({"packet-type": "keep-alive-response"})
                        self.packet_received.emit(data)
                    except json.JSONDecodeError:
                        pass
        except serial.SerialException as e:
            print(f"Serial error: {e}")
        finally:
            if self._ser and self._ser.is_open:
                self._ser.close()
            self._ser = None
            self._running = False
            self.connection_changed.emit(False)

    def send_packet(self, data):
        if self._ser and self._ser.is_open:
            try:
                msg = json.dumps(data) + "\n"
                self._ser.write(msg.encode("ascii"))
            except serial.SerialException:
                pass

    def send_sound(self, sound_type):
        """Send a sound command: 'horn', 'bell', or 'shortened'."""
        self.send_packet({"packet-type": "output", "sound": sound_type})

    @staticmethod
    def available_ports():
        return [p.device for p in serial.tools.list_ports.comports()]
