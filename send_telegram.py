import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}

def save_config(cfg):
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

def get_chat_id(bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    results = data.get("result", [])
    for update in reversed(results):
        msg = update.get("message") or update.get("my_chat_member") or update.get("edited_message")
        if msg and "chat" in msg:
            return str(msg["chat"]["id"])
    return None

def send_message(bot_token, chat_id, text):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    # Telegram max message length is 4096 characters
    if len(text) > 4000:
        text = text[:3990] + "\n..."
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def main():
    cfg = load_config()
    bot_token = cfg.get("bot_token")
    if not bot_token:
        print("ERROR: Missing bot_token in config.json", file=sys.stderr)
        sys.exit(1)

    chat_id = cfg.get("chat_id")
    if not chat_id:
        chat_id = get_chat_id(bot_token)
        if not chat_id:
            print("NO_CHAT_ID: Aucun message trouvé. Veuillez ouvrir https://t.me/marwa_emploi_2026_bot sur Telegram, cliquer sur Démarrer (Start) et envoyer un message.", file=sys.stderr)
            sys.exit(2)
        cfg["chat_id"] = chat_id
        save_config(cfg)
        print(f"Detected and saved chat_id: {chat_id}")

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        p = Path(arg)
        if p.exists() and p.is_file():
            text = p.read_text(encoding="utf-8")
        else:
            text = arg
        res = send_message(bot_token, chat_id, text)
        print(f"Message sent successfully (message_id={res.get('result', {}).get('message_id')})")
    else:
        print(f"Ready. chat_id={chat_id}")

if __name__ == "__main__":
    main()
