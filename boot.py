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
while True:
    yetitools.start_editor()
    s = bytearray()
    os.dupterm(DUP(s))
    import main
    with open(yetitools.OUTPUT_PATH, "wb") as file:
        file.write(s)
    os.dupterm(None)


