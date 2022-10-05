# boot.py -- run on boot-up
import yetitools

global wlan

import io
import os
class DUP(io.IOBase):

    def __init__(self, s):
        self.s = s

    def write(self, data):
        self.s += data + "\n"
        return len(data)

    def readinto(self, data):
        return 0

wlan = yetitools.get_connection()
yetitools.start_server()
    
while True:
    s = bytearray()
    os.dupterm(DUP(s))
    # import main
    if s:
        with open(yetitools.OUTPUT_PATH, "wb") as file:
            file.write(s)
    os.dupterm(None)


