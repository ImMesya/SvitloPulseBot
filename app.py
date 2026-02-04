"""
Flask-сервер для відстеження наявності світла (heartbeat).
Якщо heartbeat не приходить > 5 хв — відправляє в Telegram "світло вимкнули".
Після відновлення heartbeat — "світло увімкнули".
"""

import threading
import time
from datetime import datetime, timezone

import requests
from flask import Flask, request

# --- Конфігурація ---
TELEGRAM_TOKEN = "..."
CHAT_ID = "..."
SECRET_TOKEN = "XYZ"

# Пороги
HEARTBEAT_TIMEOUT_SEC = 5 * 60   # 5 хвилин
CHECK_INTERVAL_SEC = 30

app = Flask(__name__)

# Стан (потокобезпечний доступ)
_lock = threading.Lock()
_last_seen = None   # datetime | None
_online = True     # True = світло є, False = вимкнено (щоб не спамити)


def _send_telegram(text: str) -> bool:
    """Відправити повідомлення в Telegram. Повертає True при успіху."""
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "...":
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        return r.status_code == 200
    except Exception:
        return False


def _background_check():
    """Цикл перевірки: кожні 30 с перевіряє last_seen і при потребі шле в Telegram."""
    global _last_seen, _online
    while True:
        time.sleep(CHECK_INTERVAL_SEC)
        with _lock:
            now = datetime.now(timezone.utc)
            if _last_seen is None:
                # Ще ні одного heartbeat не було - нічого не робимо
                continue
            elapsed = (now - _last_seen).total_seconds()
            if elapsed > HEARTBEAT_TIMEOUT_SEC:
                if _online:
                    _online = False
                    _send_telegram("⚠ Світло вимкнули")
            else:
                if not _online:
                    _online = True
                    _send_telegram("✅ Світло увімкнули")


@app.route("/heartbeat", methods=["GET"])
def heartbeat():
    """GET /heartbeat?token=XYZ - оновлює last_seen і вмикає статус 'онлайн'."""
    global _last_seen, _online
    token = request.args.get("token")
    if token != SECRET_TOKEN:
        return {"ok": False, "error": "invalid token"}, 403
    with _lock:
        was_offline = not _online
        _last_seen = datetime.now(timezone.utc)
        _online = True
    if was_offline:
        _send_telegram("✅ світло увімкнули")
    return {"ok": True, "last_seen": _last_seen.isoformat()}


def main():
    t = threading.Thread(target=_background_check, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
