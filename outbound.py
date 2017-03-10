
import requests
import json

server_addr = 'localhost'
app_name = 'hello-world'
username = 'asterisk'
password = 'asterisk'

url = "ws://%s:8088/ari/events?app=%s&api_key=%s:%s" % (server_addr, app_name, username, password)
req_base = "http://%s:8088/ari/" % server_addr

class Outbound:
    def __init__(self):
        self.req_str = req_base + "channels?endpoint={0}&app={1}&appArgs={2}&callerId={3}" .format('SIP/3004', 'hello-world', 'outbound 1001 SIP/3004', 'manjil-mobile')
        self.stat = requests.post(self.req_str, auth=(username, password))
        print self.stat.text


if __name__ == '__main__':
    Outbound()


