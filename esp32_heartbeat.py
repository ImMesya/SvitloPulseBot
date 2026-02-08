import network
import socket
import time

WIFI_SSID = "your_ssid"
WIFI_PASS = "your_password"
VPS_IP = "192.168.1.100"
VPS_PORT = 5000
TOKEN = "XYZ"
INTERVAL_SEC = 60


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
    return wlan


def wifi_ready():
    wlan = network.WLAN(network.STA_IF)
    return wlan.active() and wlan.isconnected()


def send_heartbeat():
    path = "/heartbeat?token=" + TOKEN
    s = socket.socket()
    s.settimeout(10)
    try:
        s.connect((VPS_IP, VPS_PORT))
        req = "GET {} HTTP/1.0\r\nHost: {}\r\nConnection: close\r\n\r\n".format(path, VPS_IP)
        s.send(req.encode())
        s.recv(256)
    except Exception:
        pass
    finally:
        s.close()


def main():
    time.sleep(2)
    connect_wifi()
    while True:
        if not wifi_ready():
            connect_wifi()
        send_heartbeat()
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
