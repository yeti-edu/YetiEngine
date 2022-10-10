from time import sleep
from yetitools import OUTPUT_PATH
import os
import io
import gc
from sys import modules, path

path.append("./code")

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

# call folder code runner
def run_files():
    import runner

# 
while True:
    s = bytearray()
    os.dupterm(DUP(s))
    run_files()
    if s:
        with open(OUTPUT_PATH, "wb") as file:
            file.write(s)
    os.dupterm(None)

