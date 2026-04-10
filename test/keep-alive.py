import serial
import json
import logging
from logger import get_logger

raceBoxLogger = get_logger("Race Box")
appLogger = get_logger("App")
ser = serial.Serial('COM5', 115200, timeout=1)

while True:
    line = ser.readline().decode('utf-8').rstrip()
    if line:
        json_data = json.loads(line)
        if json_data.get("packet-type") == "keep-alive":
            ser.write(b'{"packet-type" : "keep-alive-response"}\n')
        elif json_data.get("packet-type") == "log":
            if (json_data.get("type") == "info"):
                raceBoxLogger.info(json_data.get("message"))
            elif (json_data.get("type") == "warn"):
                raceBoxLogger.warning(json_data.get("message"))
            elif (json_data.get("type") == "error"):
                raceBoxLogger.error(json_data.get("message"))
        elif json_data.get("packet-type") == "button-input":
            appLogger.info(f"Button {json_data.get('button')} has been pressed.")

  