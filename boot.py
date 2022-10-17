# boot.py -- run on boot-up
import networkpicker
import yetitools

global wlan

import io
import os


wlan = networkpicker.get_connection()

yetitools.start_server(networkpicker.host_ip)
    
import main
