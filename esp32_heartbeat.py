import network
import socket
import time
import machine

# --- Конфігурація ---
WIFI_SSID = "Your_SSID"
WIFI_PASS = "Your_Password"
VPS_IP = "IP_ADDRESS"
VPS_PORT = 5000
TOKEN = "XYZ"
INTERVAL_SEC = 60

# Світлодіод на платі (зазвичай D2 - це GPIO 2)
led = machine.Pin(2, machine.Pin.OUT)


def connect_wifi():
    """Підключення до Wi-Fi мережі."""
    wlan = network.WLAN(network.STA_IF)
    led.off()  # Вимикаємо світлодіод на початку підключення
    
    if not wlan.isconnected():
        print('Connecting to network...', WIFI_SSID)
        wlan.active(False)  # Скидання стейка Wi-Fi
        time.sleep(1)
        wlan.active(True)
        
        # Спроба встановити ім'я хоста (допомагає деяким роутерам)
        try:
            wlan.config(dhcp_hostname="SvitloPulseESP")
        except:
            pass

        try:
            wlan.connect(WIFI_SSID, WIFI_PASS)
            
            # Чекаємо підключення до 30 секунд
            max_wait = 30
            while max_wait > 0:
                status = wlan.status()
                # 3 = STAT_GOT_IP, або просто перевіряємо isconnected()
                if status == 3 or wlan.isconnected():
                    break
                
                max_wait -= 1
                time.sleep(1)
                
            if not wlan.isconnected():
                print("Failed to connect to WiFi. Status:", wlan.status())
        except OSError as e:
            print(f"WiFi OSError: {e}")
            # Перевірка специфічної помилки внутрішнього стану Wi-Fi на ESP32
            if "Internal State Error" in str(e):
                print("Hardware WiFi stack error detected. Hard resetting...")
                machine.reset()  # Повне перезавантаження заліза
    
    if wlan.isconnected():
        print('Connection established:', wlan.ifconfig())
        led.on()  # ВМИКАЄМО світлодіод при успішному підключенні
    return wlan


def wifi_ready():
    """Перевірка статусу підключення."""
    wlan = network.WLAN(network.STA_IF)
    return wlan.active() and wlan.isconnected()


def send_heartbeat():
    """Відправка сигналу (heartbeat) на сервер."""
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
    """Головний цикл програми."""
    # Невелика затримка перед стартом для стабілізації живлення
    time.sleep(2)
    connect_wifi()
    while True:
        if not wifi_ready():
            connect_wifi()
        send_heartbeat()
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
