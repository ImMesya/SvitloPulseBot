"""
Flask-сервер для відстеження наявності світла (heartbeat).
Якщо heartbeat не приходить > 5 хв — відправляє в Telegram "світло вимкнули".
Після відновлення heartbeat — "світло увімкнули".
Стан зберігається в state.json, щоб після перезапуску сервера тривалості й часи залишалися коректними.
"""

import json
import os
import threading
import time
from datetime import datetime, timezone

import requests
from flask import Flask, request

# --- Конфігурація ---
TELEGRAM_TOKEN = "..."
CHAT_ID = "..."
SECRET_TOKEN = "XYZ"

HEARTBEAT_TIMEOUT_SEC = 5 * 60
CHECK_INTERVAL_SEC = 30

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

app = Flask(__name__)

_lock = threading.Lock()
_last_seen = None
_online = True
_last_online_at = None
_offline_since = None


def _load_state():
    """Відновити стан з файлу після перезапуску сервера."""
    global _last_seen, _online, _last_online_at, _offline_since
    if not os.path.isfile(STATE_FILE):
        return
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("last_seen"):
            _last_seen = datetime.fromisoformat(data["last_seen"].replace("Z", "+00:00"))
        if "online" in data:
            _online = bool(data["online"])
        if data.get("last_online_at"):
            _last_online_at = datetime.fromisoformat(data["last_online_at"].replace("Z", "+00:00"))
        if data.get("offline_since"):
            _offline_since = datetime.fromisoformat(data["offline_since"].replace("Z", "+00:00"))
        else:
            _offline_since = None
    except Exception:
        pass


def _save_state():
    """Зберегти поточний стан у файл (викликати при зміні стану)."""
    data = {
        "last_seen": _last_seen.isoformat() if _last_seen else None,
        "online": _online,
        "last_online_at": _last_online_at.isoformat() if _last_online_at else None,
        "offline_since": _offline_since.isoformat() if _offline_since else None,
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _format_duration(seconds: float) -> str:
    m = int(seconds // 60)
    if m < 60:
        return f"{m} хв"
    h, m = m // 60, m % 60
    if m == 0:
        return f"{h} год"
    return f"{h} год {m} хв"


def _format_time(dt: datetime) -> str:
    return dt.strftime("%d.%m %H:%M")


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
    global _last_seen, _online, _last_online_at, _offline_since
    while True:
        time.sleep(CHECK_INTERVAL_SEC)
        with _lock:
            now = datetime.now(timezone.utc)
            if _last_seen is None:
                continue
            elapsed = (now - _last_seen).total_seconds()
            if elapsed > HEARTBEAT_TIMEOUT_SEC:
                if _online:
                    _online = False
                    _offline_since = now
                    on_duration = (_last_seen - _last_online_at).total_seconds() if _last_online_at else 0
                    msg = "⚠ Світло вимкнули."
                    if _last_online_at is not None:
                        msg += f" Світло було {_format_duration(on_duration)} (останній сигнал о {_format_time(_last_seen)})."
                    _send_telegram(msg)
                    _save_state()


@app.route("/heartbeat", methods=["GET"])
def heartbeat():
    global _last_seen, _online, _last_online_at, _offline_since
    token = request.args.get("token")
    client_ip = request.remote_addr or "unknown"
    if token != SECRET_TOKEN:
        app.logger.warning("heartbeat: invalid token from %s", client_ip)
        return {"ok": False, "error": "invalid token"}, 403
    app.logger.info("heartbeat: OK from %s", client_ip)
    with _lock:
        was_offline = not _online
        now = datetime.now(timezone.utc)
        _last_seen = now
        _online = True
        if was_offline or _last_online_at is None:
            _last_online_at = now
        if was_offline and _offline_since is not None:
            off_duration = (now - _offline_since).total_seconds()
            msg = "✅ Світло увімкнули."
            msg += f" Без світла було {_format_duration(off_duration)} (вимкнули о {_format_time(_offline_since)})."
            _send_telegram(msg)
        _save_state()
    return {"ok": True, "last_seen": _last_seen.isoformat()}


def main():
    _load_state()
    t = threading.Thread(target=_background_check, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
