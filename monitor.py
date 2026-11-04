
import json
import os
import urllib.request
from pathlib import Path

API_URL = (
    "https://maplestatus.info/api/games/"
    "maplestory/japan/worlds/servers"
)
STATE_FILE = Path("state.json")


def get_status():
    req = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": "JMSentinel/1.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        worlds = json.load(response)

    statuses = [
        server["status"]
        for world in worlds
        for server in world["data"]
    ]

    if not statuses:
        raise RuntimeError("No server data")

    if any(type(s) is not int or s not in (0, 1) for s in statuses):
        raise RuntimeError("Unknown server status")

    # 0=offline, 1=online は暫定
    return "online" if any(s == 1 for s in statuses) else "offline"


def send_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": (
            "🟢 メイプルストーリー JMS 復旧！\n"
            "サーバーへの接続が確認できました。\n"
            "メンテナンスが終了した可能性があります。"
        ),
    }).encode()

    with urllib.request.urlopen(url, data=data, timeout=20):
        pass


def main():
    state = (
        json.loads(STATE_FILE.read_text())
        if STATE_FILE.exists()
        else {"last": None, "count": 0, "notified": False}
    )

    current = get_status()

    if current == state["last"]:
        state["count"] += 1
    else:
        state["last"] = current
        state["count"] = 1

    if current == "offline" and state["count"] >= 2:
        state["notified"] = False

    if current == "online" and state["count"] >= 2:
        if not state.get("offline_confirmed", False):
            state["notified"] = True

    if current == "offline" and state["count"] >= 2:
        state["offline_confirmed"] = True

    if (
        current == "online"
        and state["count"] >= 2
        and not state["notified"]
    ):
        if os.environ.get("ENABLE_NOTIFICATIONS") == "true":
            send_telegram()
            state["notified"] = True

    STATE_FILE.write_text(json.dumps(state, indent=2))
    print(f"Status: {current}, count: {state['count']}")


if __name__ == "__main__":
    main()
