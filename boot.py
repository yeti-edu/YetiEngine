# boot.py -- run on boot-up
import yetitools

global wlan

wlan = yetitools.get_connection()
while True:
    yetitools.start_editor()
    #print = yetitools.logger.info
    import main

