print("running main")
from time import sleep
from yetitools import OUTPUT_PATH
import os
import io
import gc
from sys import modules

# reload module function
def reload(mod):
  mod_name = mod.__name__
  del modules[mod_name]
  gc.collect()
  return __import__(mod_name)

#mock for overriding std
class DUP(io.IOBase):

    def __init__(self, s):
        self.s = s

    def write(self, data):
        self.s += data + "\n"
        return len(data)

    def readinto(self, data):
        return 0

s = bytearray()
os.dupterm(DUP(s))
import runner
while True:
    print("entering main loop")
    s = bytearray()
    os.dupterm(DUP(s))
    # call folder code runner
    print("importing runner")
    reload(runner)
    print("finished importing")
    if s:
        with open(OUTPUT_PATH, "wb") as file:
            file.write(s)
    os.dupterm(None)

