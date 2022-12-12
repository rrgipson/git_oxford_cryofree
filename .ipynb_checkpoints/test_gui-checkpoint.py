from time import sleep
from threading import Thread
from oxford import SerialPort
from gui import *

test_gui = GUI()


test_gui.warning_popup('title','message')
test_gui.mainloop()
