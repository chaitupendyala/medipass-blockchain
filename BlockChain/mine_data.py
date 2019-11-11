import requests
import time

while 4!=3:
    r = requests.get("http://<SERVER-ADDRESS>:1000/mine")
    time.sleep(2)