print("all code to be imported:")
from sys import modules, path
import gc 

# reload module function
def reload(mod):
  mod_name = mod.__name__
  del modules[mod_name]
  gc.collect()
  return __import__(mod_name)

path.append("/code")

import main1
import main2
import main3
import main4
import main5
import main6
import main7
import main8
import main9
import main10

reload(main1)
reload(main2)
reload(main3)
reload(main4)
reload(main5)
reload(main6)
reload(main7)
reload(main8)
reload(main9)
reload(main10)