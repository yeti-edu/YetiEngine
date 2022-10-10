# boot.py -- run on boot-up
import yetitools

global wlan

import io
import os


wlan = yetitools.get_connection()
yetitools.start_server()
    
import main
